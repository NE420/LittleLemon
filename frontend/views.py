from decimal import Decimal
from urllib.parse import parse_qsl, urlencode

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from . import api_client
from .api_client import APIError

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


# ---------- Helpers ----------

def get_token(request):
    return request.session.get("auth_token")


def get_roles(request):
    return request.session.get("roles", {})


def derive_roles(user):
    """Turn Djoser's /users/me/ payload into the flags the UI uses."""
    groups = user.get("groups", [])
    is_admin = bool(user.get("is_superuser") or user.get("is_staff"))
    return {
        "is_admin": is_admin,
        "is_manager": is_admin or "Manager" in groups,
        "is_delivery_crew": "Delivery crew" in groups,
    }


def describe(error):
    """Turn an APIError into a short, readable message."""
    detail = error.detail
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            text = ", ".join(str(v) for v in value) if isinstance(value, (list, tuple)) else str(value)
            parts.append(text if key in ("detail", "non_field_errors") else f"{key}: {text}")
        text = "; ".join(parts)
    elif isinstance(detail, list):
        text = ", ".join(str(d) for d in detail)
    else:
        text = str(detail)
    return text[:300]


def results(data):
    """DRF list payloads are paginated dicts; plain lists pass through."""
    return data if isinstance(data, list) else data.get("results", [])


def total_count(data):
    return len(data) if isinstance(data, list) else data.get("count", 0)


def api_params(request, *names):
    """Pick the named GET params to forward to the API."""
    return {name: request.GET[name] for name in names if request.GET.get(name)}


def paginate(request, data, keep=()):
    """
    Split a paginated API response into (items, page). `page` feeds
    partials/_pagination.html; `keep` lists the GET params (search, sort)
    that the page links should carry along.
    """
    items = results(data)
    if isinstance(data, list):
        return items, None
    try:
        number = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        number = 1
    extra = urlencode({k: request.GET[k] for k in keep if request.GET.get(k)})
    has_previous = bool(data.get("previous"))
    has_next = bool(data.get("next"))
    return items, {
        "number": number,
        "count": data.get("count", len(items)),
        "has_previous": has_previous,
        "has_next": has_next,
        "has_other_pages": has_previous or has_next,
        "previous_number": number - 1,
        "next_number": number + 1,
        "query": f"&{extra}" if extra else "",
    }


def redirect_back(request, url_name):
    """
    Redirect to a list page, restoring the page / search / sort the person
    was on. Forms on single-item views send that as a hidden `next_query`.
    Only the query string is taken from the form, never the path.
    """
    url = reverse(url_name)
    query = urlencode(parse_qsl(request.POST.get("next_query", "")))
    return redirect(f"{url}?{query}" if query else url)


# ---------- Access control ----------
# Rule of thumb used throughout:
#   * a whole page only some roles may open  -> gate it here, in the view
#   * a page everyone opens, with extra controls for some roles
#                                            -> one template + {% if is_manager %}
# Templates only hide controls; these mixins (and ultimately the API) are
# what actually refuse the request.

class RoleRequiredMixin:
    """
    roles_any:            session role flags; having any one of them is enough
                          (empty = just be logged in)
    open_to_safe_methods: let anyone, even anonymous, GET the page
    denied_url:           where people without the role are sent
    """
    roles_any = ()
    open_to_safe_methods = False
    denied_url = "frontend:index"

    def dispatch(self, request, *args, **kwargs):
        if not (self.open_to_safe_methods and request.method in SAFE_METHODS):
            if not get_token(request):
                messages.error(request, "Please log in first.")
                return redirect("frontend:login")
            if self.roles_any:
                user_roles = get_roles(request)
                if not any(user_roles.get(role) for role in self.roles_any):
                    messages.error(request, "You don't have permission to do that.")
                    return redirect(self.denied_url)
        return super().dispatch(request, *args, **kwargs)


class TokenRequiredMixin(RoleRequiredMixin):
    """Logged in is enough; no particular role."""


# ---------- Home ----------

class IndexView(View):
    def get(self, request):
        try:
            menu_page = api_client.get_menu_items()
        except APIError:
            menu_page = {}
        try:
            category_page = api_client.get_categories()
        except APIError:
            category_page = {}

        stats = {
            "menu items": total_count(menu_page),
            "categories": total_count(category_page),
        }
        token = get_token(request)
        if token:
            try:
                stats["orders"] = total_count(api_client.get_orders(token))
            except APIError:
                pass

        return render(request, "frontend/index.html", {
            "menu_preview": results(menu_page),
            "stats": stats,
        })


# ---------- Auth ----------

class LoginView(View):
    def get(self, request):
        return render(request, "frontend/login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        try:
            data = api_client.login(username, password)
        except APIError as e:
            messages.error(request, f"Login failed: {describe(e)}")
            return render(request, "frontend/login.html")

        token = data.get("auth_token")
        # Look the person's roles up once and keep them in the session.
        # They change when someone is added to / removed from a group, and
        # show up after the next login.
        try:
            me = api_client.get_current_user(token)
            # Djoser's default serializer answers without `groups`; treat
            # that as a failure rather than silently making everyone a customer.
            if "groups" not in me:
                raise APIError(200, "current_user serializer returns no groups")
            roles = derive_roles(me)
        except APIError:
            roles = {}
            messages.warning(
                request,
                "Logged in, but your role couldn't be loaded, so manager "
                "features are hidden. Check DJOSER['SERIALIZERS']['current_user'].",
            )

        request.session["auth_token"] = token
        request.session["username"] = username
        request.session["roles"] = roles
        return redirect("frontend:index")


class LogoutView(View):
    def post(self, request):
        token = get_token(request)
        if token:
            try:
                api_client.logout(token)
            except APIError:
                pass
        request.session.flush()
        return redirect("frontend:login")


# ---------- Categories ----------
# Everyone can browse. Only managers see the create form, and only
# managers get past the mixin on POST.

class CategoriesView(RoleRequiredMixin, View):
    roles_any = ("is_manager",)
    open_to_safe_methods = True
    denied_url = "frontend:categories"

    def get(self, request):
        try:
            categories = api_client.get_all_categories()
        except APIError as e:
            messages.error(request, f"Could not load categories: {describe(e)}")
            categories = []
        return render(request, "frontend/categories.html", {"categories": categories})

    def post(self, request):
        if request.POST.get("action") == "create":
            data = {"title": request.POST.get("title"), "slug": request.POST.get("slug")}
            try:
                api_client.create_category(data, get_token(request))
                messages.success(request, "Category created.")
            except APIError as e:
                messages.error(request, f"Could not create category: {describe(e)}")
        return redirect("frontend:categories")


# ---------- Menu items ----------
# MenuItemsView: list + create (menu-items/)
# SingleMenuItemView: update / delete one item (menu-items/<pk>/)
# The API identifies a menu item's category by its title (SlugRelatedField),
# both in what it returns and in what it accepts.

class MenuItemsView(RoleRequiredMixin, View):
    roles_any = ("is_manager",)
    open_to_safe_methods = True
    denied_url = "frontend:menu-items"

    def get(self, request):
        params = api_params(request, "search", "ordering", "page")
        try:
            items, page = paginate(
                request, api_client.get_menu_items(params), keep=("search", "ordering")
            )
        except APIError as e:
            messages.error(request, f"Could not load the menu: {describe(e)}")
            items, page = [], None

        try:
            categories = api_client.get_all_categories()
        except APIError:
            categories = []

        # The API already returns the category's title.
        for item in items:
            item["category_title"] = item.get("category") or "Uncategorised"

        return render(request, "frontend/menu_items.html", {
            "items": items,
            "categories": categories,
            "page": page,
        })

    def post(self, request):
        if request.POST.get("action") == "create":
            data = {
                "title": request.POST.get("title"),
                "price": request.POST.get("price"),
                "category": request.POST.get("category"),  # a category title
                "featured": request.POST.get("featured") == "on",
            }
            try:
                api_client.create_menu_item(data, get_token(request))
                messages.success(request, "Menu item created.")
            except APIError as e:
                messages.error(request, f"Could not create item: {describe(e)}")
        return redirect("frontend:menu-items")


class SingleMenuItemView(RoleRequiredMixin, View):
    roles_any = ("is_manager",)
    denied_url = "frontend:menu-items"

    def post(self, request, pk):
        token = get_token(request)
        action = request.POST.get("action")

        if action == "update":
            data = {
                "title": request.POST.get("title"),
                "price": request.POST.get("price"),
                "category": request.POST.get("category"),  # a category title
                "featured": request.POST.get("featured") == "on",
            }
            try:
                api_client.update_menu_item(pk, data, token)
                messages.success(request, "Menu item updated.")
            except APIError as e:
                messages.error(request, f"Could not update item: {describe(e)}")

        elif action == "delete":
            try:
                api_client.delete_menu_item(pk, token)
                messages.success(request, "Menu item deleted.")
            except APIError as e:
                messages.error(request, f"Could not delete item: {describe(e)}")

        return redirect_back(request, "frontend:menu-items")


# ---------- Cart ----------
#   action=add       -> item_id, quantity
#   action=clear
#   action=checkout

class CartView(TokenRequiredMixin, View):
    def get(self, request):
        token = get_token(request)
        try:
            items = api_client.get_cart(token)
        except APIError as e:
            messages.error(request, f"Could not load your cart: {describe(e)}")
            items = []

        # Cart lines only carry the menu item's id; look the titles up.
        titles = {}
        for line in items:
            menu_id = line["menuitem"]
            if menu_id not in titles:
                try:
                    titles[menu_id] = api_client.get_menu_item(menu_id)["title"]
                except APIError:
                    titles[menu_id] = f"Item #{menu_id}"
            line["menuitem_title"] = titles[menu_id]

        total = sum((Decimal(str(line["price"])) for line in items), Decimal("0"))
        return render(request, "frontend/cart.html", {"items": items, "total": total})

    def post(self, request):
        token = get_token(request)
        action = request.POST.get("action")

        if action == "add":
            item_id = request.POST.get("item_id")
            try:
                quantity = max(int(request.POST.get("quantity", 1)), 1)
            except ValueError:
                quantity = 1
            try:
                menu_item = api_client.get_menu_item(item_id)
                # The API works out unit_price and price itself.
                api_client.add_to_cart({"menuitem": item_id, "quantity": quantity}, token)
                messages.success(request, f"Added {menu_item['title']} to your cart.")
            except APIError as e:
                # A user can hold each menu item only once (unique_together).
                if "unique" in describe(e).lower():
                    messages.info(request, "That item is already in your cart.")
                else:
                    messages.error(request, f"Could not add to cart: {describe(e)}")

        elif action == "clear":
            try:
                api_client.clear_cart(token)
                messages.success(request, "Cart cleared.")
            except APIError as e:
                messages.error(request, f"Could not clear the cart: {describe(e)}")

        elif action == "checkout":
            try:
                api_client.create_order(token)
                messages.success(request, "Order placed.")
                return redirect("frontend:orders")
            except APIError as e:
                messages.error(request, f"Checkout failed: {describe(e)}")

        return redirect("frontend:cart")


# ---------- Orders ----------
# OrdersView: list (customers see their own, delivery crew see theirs,
# managers see all). SingleOrderView: update one order (orders/<pk>/).

class OrdersView(TokenRequiredMixin, View):
    def get(self, request):
        token = get_token(request)
        try:
            orders, page = paginate(
                request, api_client.get_orders(token, api_params(request, "page"))
            )
        except APIError as e:
            messages.error(request, f"Could not load orders: {describe(e)}")
            orders, page = [], None

        # Managers assign orders to crew members, so they need the crew list.
        crew = []
        if get_roles(request).get("is_manager"):
            try:
                crew = api_client.list_delivery_crew(token)
            except APIError:
                crew = []

        return render(request, "frontend/orders.html", {
            "orders": orders,
            "crew": crew,
            "page": page,
        })


class SingleOrderView(RoleRequiredMixin, View):
    roles_any = ("is_manager", "is_delivery_crew")
    denied_url = "frontend:orders"

    def post(self, request, pk):
        data = {}
        if request.POST.get("status") in ("0", "1"):
            data["status"] = request.POST["status"]
        # Only managers hand orders to the crew; the crew just update status.
        if get_roles(request).get("is_manager") and "delivery_crew" in request.POST:
            data["delivery_crew"] = request.POST["delivery_crew"] or None

        if data:
            try:
                api_client.update_order(pk, data, get_token(request))
                messages.success(request, f"Order #{pk} updated.")
            except APIError as e:
                messages.error(request, f"Could not update order #{pk}: {describe(e)}")
        return redirect_back(request, "frontend:orders")


# ---------- Managers (admins only) ----------
#   action=add    -> username
#   action=remove -> username

class ManagersView(RoleRequiredMixin, View):
    roles_any = ("is_admin",)

    def get(self, request):
        try:
            managers = api_client.list_managers(get_token(request))
        except APIError as e:
            messages.error(request, f"Could not load managers: {describe(e)}")
            managers = []
        return render(request, "frontend/managers.html", {"managers": managers})

    def post(self, request):
        token = get_token(request)
        action = request.POST.get("action")
        username = request.POST.get("username")
        try:
            if action == "add":
                api_client.add_manager(username, token)
                messages.success(request, f"{username} is now a manager.")
            elif action == "remove":
                api_client.remove_manager(username, token)
                messages.success(request, f"{username} is no longer a manager.")
        except APIError as e:
            messages.error(request, f"Could not update managers: {describe(e)}")
        return redirect("frontend:managers")


# ---------- Delivery crew (managers and admins) ----------

class DeliveryCrewView(RoleRequiredMixin, View):
    roles_any = ("is_manager",)

    def get(self, request):
        try:
            crew = api_client.list_delivery_crew(get_token(request))
        except APIError as e:
            messages.error(request, f"Could not load the delivery crew: {describe(e)}")
            crew = []
        return render(request, "frontend/delivery_crew.html", {"crew": crew})

    def post(self, request):
        token = get_token(request)
        action = request.POST.get("action")
        username = request.POST.get("username")
        try:
            if action == "add":
                api_client.add_delivery_crew(username, token)
                messages.success(request, f"{username} joined the delivery crew.")
            elif action == "remove":
                api_client.remove_delivery_crew(username, token)
                messages.success(request, f"{username} left the delivery crew.")
        except APIError as e:
            messages.error(request, f"Could not update the delivery crew: {describe(e)}")
        return redirect("frontend:delivery-crew")