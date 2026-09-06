from functools import wraps
 
from django.shortcuts import render, redirect
from django.contrib import messages
 
from . import api_client
from .api_client import APIError
 
 
# ---------- Helpers ----------
 
def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("auth_token"):
            messages.error(request, "Please log in first.")
            return redirect("frontend:login")
        return view_func(request, *args, **kwargs)
    return wrapper
 
 
def get_token(request):
    return request.session.get("auth_token")
 
 
# ---------- Home ----------
 
def index(request):
    try:
        all_items = api_client.get_menu_items({"ordering": "-id"})
        all_items = all_items if isinstance(all_items, list) else []
    except APIError:
        all_items = []
    try:
        categories = api_client.get_categories()
        categories = categories if isinstance(categories, list) else []
    except APIError:
        categories = []
 
    token = get_token(request)
    orders_count = None
    if token:
        try:
            orders = api_client.get_orders(token)
            orders_count = len(orders) if isinstance(orders, list) else None
        except APIError:
            orders_count = None
 
    stats = {
        "menu items": len(all_items),
        "categories": len(categories),
    }
    if orders_count is not None:
        stats["orders"] = orders_count
 
    return render(request, "frontend/index.html", {
        "featured_items": all_items[:6],
        "categories": categories,
        "stats": stats,
    })
 
 
# ---------- Auth ----------
 
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        try:
            data = api_client.login(username, password)
        except APIError as e:
            messages.error(request, f"Login failed: {e.detail}")
            return render(request, "frontend/login.html")
 
        request.session["auth_token"] = data.get("auth_token")
        request.session["username"] = username
        return redirect("frontend:index")
 
    return render(request, "frontend/login.html")
 
 
def logout_view(request):
    token = get_token(request)
    if token:
        try:
            api_client.logout(token)
        except APIError:
            pass
    request.session.flush()
    return redirect("frontend:login")
 
 
# ---------- Categories ----------
# categories.html: expects `categories` (list). If you want a manager-only
# inline "add category" form, POST here with action=create.
 
def categories_view(request):
    token = get_token(request)
 
    if request.method == "POST" and request.POST.get("action") == "create":
        if not token:
            messages.error(request, "Please log in first.")
            return redirect("frontend:login")
        data = {"title": request.POST.get("title"), "slug": request.POST.get("slug")}
        try:
            api_client.create_category(data, token)
            messages.success(request, "Category created.")
        except APIError as e:
            messages.error(request, f"Could not create category: {e.detail}")
        return redirect("frontend:categories")
 
    try:
        categories = api_client.get_categories()
    except APIError as e:
        messages.error(request, f"Could not load categories: {e.detail}")
        categories = []
 
    return render(request, "frontend/categories.html", {"categories": categories})
 
 
# ---------- Menu items ----------
# menu_items.html: expects `items` (list) and `categories` (for a
# create/edit dropdown). Each row's edit/delete form and the top
# create form all POST to this same view, distinguished by `action`.
#
#   action=create  -> title, price, category, featured
#   action=update  -> item_id, title, price, category, featured
#   action=delete  -> item_id
 
def menu_items_view(request):
    token = get_token(request)
 
    if request.method == "POST":
        action = request.POST.get("action")
        if not token:
            messages.error(request, "Please log in first.")
            return redirect("frontend:login")
 
        if action == "create":
            data = {
                "title": request.POST.get("title"),
                "price": request.POST.get("price"),
                "category": request.POST.get("category"),
                "featured": request.POST.get("featured") == "on",
            }
            try:
                api_client.create_menu_item(data, token)
                messages.success(request, "Menu item created.")
            except APIError as e:
                messages.error(request, f"Could not create item: {e.detail}")
 
        elif action == "update":
            item_id = request.POST.get("item_id")
            data = {
                "title": request.POST.get("title"),
                "price": request.POST.get("price"),
                "category": request.POST.get("category"),
            }
            try:
                api_client.update_menu_item(item_id, data, token)
                messages.success(request, "Menu item updated.")
            except APIError as e:
                messages.error(request, f"Could not update item: {e.detail}")
 
        elif action == "delete":
            item_id = request.POST.get("item_id")
            try:
                api_client.delete_menu_item(item_id, token)
                messages.success(request, "Menu item deleted.")
            except APIError as e:
                messages.error(request, f"Could not delete item: {e.detail}")
 
        return redirect("frontend:menu-items")
 
    params = {}
    if request.GET.get("search"):
        params["search"] = request.GET["search"]
    if request.GET.get("ordering"):
        params["ordering"] = request.GET["ordering"]
 
    try:
        items = api_client.get_menu_items(params)
    except APIError as e:
        messages.error(request, f"Could not load menu: {e.detail}")
        items = []
 
    try:
        categories = api_client.get_categories()
    except APIError:
        categories = []
 
    return render(request, "frontend/menu_items.html", {"items": items, "categories": categories})
 
 
# ---------- Cart ----------
# cart.html: expects `items` (list). A per-item "add" form elsewhere
# (e.g. menu_items.html) can also POST here with action=add.
#
#   action=add      -> item_id, quantity
#   action=clear     -> (no fields)
#   action=checkout   -> (no fields)
 
@token_required
def cart_view(request):
    token = get_token(request)
 
    if request.method == "POST":
        action = request.POST.get("action")
 
        if action == "add":
            item_id = request.POST.get("item_id")
            quantity = int(request.POST.get("quantity", 1))
            try:
                menu_item = api_client.get_menu_item(item_id)
                data = {
                    "menuitem": item_id,
                    "quantity": quantity,
                    "unit_price": menu_item["price"],
                    "price": float(menu_item["price"]) * quantity,
                }
                api_client.add_to_cart(data, token)
                messages.success(request, "Added to cart.")
            except APIError as e:
                messages.error(request, f"Could not add to cart: {e.detail}")
 
        elif action == "clear":
            try:
                api_client.clear_cart(token)
                messages.success(request, "Cart cleared.")
            except APIError as e:
                messages.error(request, f"Could not clear cart: {e.detail}")
 
        elif action == "checkout":
            try:
                api_client.create_order(token)
                messages.success(request, "Order placed.")
                return redirect("frontend:orders")
            except APIError as e:
                messages.error(request, f"Checkout failed: {e.detail}")
 
        return redirect("frontend:cart")
 
    try:
        items = api_client.get_cart(token)
    except APIError as e:
        messages.error(request, f"Could not load cart: {e.detail}")
        items = []
 
    return render(request, "frontend/cart.html", {"items": items})
 
 
# ---------- Orders ----------
# orders.html: expects `orders` (list). Managers/delivery crew get an
# inline per-order update form (status / delivery_crew) posting here.
#
#   action=update -> order_id, status and/or delivery_crew
 
@token_required
def orders_view(request):
    token = get_token(request)
 
    if request.method == "POST" and request.POST.get("action") == "update":
        order_id = request.POST.get("order_id")
        data = {}
        if request.POST.get("status") not in (None, ""):
            data["status"] = request.POST.get("status")
        if request.POST.get("delivery_crew"):
            data["delivery_crew"] = request.POST.get("delivery_crew")
        try:
            api_client.update_order(order_id, data, token)
            messages.success(request, "Order updated.")
        except APIError as e:
            messages.error(request, f"Could not update order: {e.detail}")
        return redirect("frontend:orders")
 
    try:
        orders = api_client.get_orders(token)
    except APIError as e:
        messages.error(request, f"Could not load orders: {e.detail}")
        orders = []
 
    return render(request, "frontend/orders.html", {"orders": orders})
 
 
# ---------- Managers ----------
# managers.html: expects `managers` (list). Inline add/remove forms
# POST here.
#
#   action=add    -> username
#   action=remove -> username
 
@token_required
def managers_view(request):
    token = get_token(request)
 
    if request.method == "POST":
        action = request.POST.get("action")
        username = request.POST.get("username")
        try:
            if action == "add":
                api_client.add_manager(username, token)
                messages.success(request, f"{username} added as manager.")
            elif action == "remove":
                api_client.remove_manager(username, token)
                messages.success(request, f"{username} removed from managers.")
        except APIError as e:
            # A 403 here means the current user isn't an admin.
            messages.error(request, f"Not authorized: {e.detail}")
        return redirect("frontend:managers")
 
    try:
        managers = api_client.list_managers(token)
    except APIError as e:
        messages.error(request, f"Not authorized: {e.detail}")
        managers = []
 
    return render(request, "frontend/managers.html", {"managers": managers})
 
 
# ---------- Delivery crew ----------
# delivery_crew.html: expects `crew` (list). Same add/remove pattern.
 
@token_required
def delivery_crew_view(request):
    token = get_token(request)
 
    if request.method == "POST":
        action = request.POST.get("action")
        username = request.POST.get("username")
        try:
            if action == "add":
                api_client.add_delivery_crew(username, token)
                messages.success(request, f"{username} added to delivery crew.")
            elif action == "remove":
                api_client.remove_delivery_crew(username, token)
                messages.success(request, f"{username} removed from delivery crew.")
        except APIError as e:
            messages.error(request, f"Not authorized: {e.detail}")
        return redirect("frontend:delivery-crew")
 
    try:
        crew = api_client.list_delivery_crew(token)
    except APIError as e:
        messages.error(request, f"Not authorized: {e.detail}")
        crew = []
 
    return render(request, "frontend/delivery_crew.html", {"crew": crew})