# Little Lemon

An ordering system for a coffee shop. It has two parts that live in one Django project:

- **A REST API** (`LittlelemonAPI`) built with Django REST Framework and Djoser. It owns the data: categories, menu items, carts, orders and staff groups.
- **A web storefront** (`frontend`) built with Django class-based views and templates. It has no database access of its own. Every page gets its data by calling the API over HTTP, the same way a mobile app would.

Customers browse the menu, fill a cart and place orders. Delivery crew see and complete the orders assigned to them. Managers run the menu, assign deliveries and manage the crew. Admins manage the managers.

---

## Contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Getting started](#getting-started)
4. [Roles and permissions](#roles-and-permissions)
5. [Using the storefront](#using-the-storefront)
6. [Drink photos](#drink-photos)
7. [API reference](#api-reference)
8. [Project structure](#project-structure)
9. [How the pieces fit together](#how-the-pieces-fit-together)
10. [Known limitations](#known-limitations)
11. [Before deploying](#before-deploying)

---

## Features

- Token login through Djoser, with the person's role read once at login and kept in the session
- Menu with search (by item or category title), sorting (price or name) and pagination
- Photos for each drink, matched by name from the `media/` folder, with a placeholder when there is no photo
- Cart with quantities. Prices are always worked out on the server, never trusted from the client
- Checkout that turns the cart into an order inside a database transaction, so a failure never leaves a half-built order
- Role-aware interface: pages and controls appear only for the roles that can use them
- Manager tools to add, edit and delete menu items and to add categories
- Order management: managers assign a delivery crew member and set status, crew mark their orders completed
- Group management pages for managers and delivery crew
- Responsive layout that works from phone to desktop, with keyboard focus styles and reduced-motion support

## Tech stack

| Layer | Tools |
|---|---|
| Language | Python 3.10 or newer |
| Framework | Django 5.2 |
| API | Django REST Framework 3.17, Djoser 2.3 (token auth) |
| Frontend | Django templates, one hand-written stylesheet (no CSS framework), a few lines of JavaScript for the mobile menu |
| HTTP client | `requests` (the frontend calling the API) |
| Database | SQLite |
| Fonts | Bricolage Grotesque and Figtree, loaded from Google Fonts |

---

## Getting started

### 1. Install

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
pip install python-dotenv
```

`settings.py` imports `python-dotenv`, but it is missing from `requirements.txt`, so install it separately for now. Adding it to `requirements.txt` fixes this for good. If `pip install -r` complains about the file's encoding, re-save `requirements.txt` as UTF-8.

### 2. Configure

Create a `.env` file in the project root (next to `manage.py`). It is listed in `.gitignore` and should never be committed.

```env
SECRET_KEY=replace-this-with-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

You can generate a key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### 3. Create the database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Create the two role groups

The code looks groups up by exact name, so spell them exactly like this. Without them, adding people to a group fails.

Either open `http://127.0.0.1:8000/admin/` and add the groups **Manager** and **Delivery crew**, or run:

```bash
python manage.py shell
```
```python
from django.contrib.auth.models import Group
Group.objects.get_or_create(name="Manager")
Group.objects.get_or_create(name="Delivery crew")
```

### 5. Run

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

**Run it on port 8000.** The frontend calls the API at `http://127.0.0.1:8000`, which is set at the top of `frontend/api_client.py`. If you use another port or host, change `BASE_URL`, `AUTH_BASE_URL` and the endpoints built from them.

### 6. Add some data and people

1. Log in at `/login/` with your superuser. You get the admin role, so every page is available.
2. Add a category on the **Categories** page, then add menu items on the **Menu** page.
3. Create customers. There is no sign-up page in the storefront. Create users in `/admin/`, or register one through the API with `POST /auth/users/` and a `username` and `password`.
4. Make staff: on the **Managers** page add a username to the Manager group, and on the **Delivery crew** page add a username to the crew.

A person who belongs to neither group is a customer.

> **After you change someone's group, they need to log out and back in.** Roles are read once at login and stored in the session.

---

## Roles and permissions

Roles come from the logged-in user's account. The storefront works them out like this:

| Role | Who counts |
|---|---|
| Admin | a superuser or a staff user |
| Manager | an admin, or a member of the **Manager** group |
| Delivery crew | a member of the **Delivery crew** group |
| Customer | logged in, and neither a manager nor delivery crew |
| Visitor | not logged in |

What each role can do in the storefront:

| | Visitor | Customer | Delivery crew | Manager | Admin |
|---|:---:|:---:|:---:|:---:|:---:|
| Browse menu and categories | yes | yes | yes | yes | yes |
| Add to cart, check out | | yes | | | |
| See orders | | own | assigned to them | all | all |
| Update order status | | | own assigned orders | any | any |
| Assign an order to a crew member | | | | yes | yes |
| Add a category | | | | yes | yes |
| Add, edit, delete menu items | | | | yes | yes |
| Manage the delivery crew | | | | yes | yes |
| Manage the managers | | | | | yes |

Access is enforced in three places, and the last one is the real boundary:

1. **Templates** hide controls a role cannot use (`{% if is_manager %}` and similar).
2. **Views** refuse requests from the wrong role. Whole pages are gated with `RoleRequiredMixin` in `frontend/views.py`.
3. **The API** checks permissions on every request with the classes in `LittlelemonAPI/permissions.py`.

---

## Using the storefront

| Page | URL | Notes |
|---|---|---|
| Dashboard | `/` | Hero with your drink photos, counts, a menu preview and shortcuts for your role |
| Menu | `/menu-items/` | Search, sort, paginate. Managers get create, edit and delete. Customers get "Add to cart" |
| Categories | `/categories/` | Each card links to the menu filtered by that category. Managers can add one |
| Cart | `/cart/` | Items, total, "Place order" and "Clear cart" |
| Orders | `/orders/` | Cards per order. Managers and crew get an "Update order" panel |
| Delivery crew | `/delivery-crew/` | Managers: add and remove crew members |
| Managers | `/managers/` | Admins: add and remove managers |
| Log in | `/login/` | Logout is a button in the header (it is a POST request) |

Things worth knowing:

- Each menu item can be in your cart once. Adding it again shows "That item is already in your cart."
- Messages (success, errors, warnings) appear at the top of the page.
- Edit and delete on the menu return you to the same page, search and sort you were on.

---

## Drink photos

Menu items have no image field. A photo is matched to a drink by its **name**:

| Menu item title | Photo it uses |
|---|---|
| Coffee | `media/Coffee.jpg` |
| Iced coffee | `media/Iced_coffee.jpg` |
| Iced tea | `media/Iced_tea.jpg` |
| Tea | `media/Tea.jpg` |

The match ignores capital letters, spaces, underscores and hyphens, so `Iced coffee`, `iced_coffee` and `Iced-Coffee.jpg` all work. `.jpg`, `.jpeg`, `.png`, `.webp` and `.avif` are supported.

To add a drink photo, save the picture in `media/` named after the drink, then create a menu item with that title. A drink with no matching photo shows a lemon-slice placeholder.

The matching code is in `frontend/templatetags/frontend_extras.py`. The `media/` folder is served at `/media/` while `DEBUG=True`.

---

## API reference

The API lives under `/api/` and Djoser's auth endpoints under `/auth/`. Send the token on every authenticated request:

```
Authorization: Token <auth_token>
```

### Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/auth/users/` | Register (`username`, `password`, optional `email`) |
| POST | `/auth/token/login/` | Log in with `username` and `password`. Returns `{"auth_token": "..."}` |
| POST | `/auth/token/logout/` | Invalidate the token |
| GET | `/auth/users/me/` | The current user: `id`, `username`, `email`, `groups`, `is_staff`, `is_superuser` |

`/auth/users/me/` uses `CurrentUserSerializer` (set in `DJOSER["SERIALIZERS"]`). The storefront needs the `groups` field from it to know someone's role. The role fields are read-only, so nobody can promote themselves through this endpoint.

### Menu and categories

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/api/categories` | anyone | List categories |
| POST | `/api/categories` | manager, staff, superuser | Create a category (`title`, `slug`) |
| GET | `/api/categories/<id>` | anyone | One category |
| PUT, PATCH, DELETE | `/api/categories/<id>` | manager, staff, superuser | Change or delete one |
| GET | `/api/menu-items` | anyone | List menu items |
| POST | `/api/menu-items` | manager, staff, superuser | Create an item |
| GET | `/api/menu-items/<id>` | anyone | One item |
| PUT, PATCH, DELETE | `/api/menu-items/<id>` | manager, staff, superuser | Change or delete one |

`GET /api/menu-items` accepts `?search=` (item title or category title), `?ordering=price`, `price` reversed as `-price`, or `title`, and `?page=`.

A menu item looks like this. The category is identified by its **title**, both when reading and when writing:

```json
{ "id": 3, "title": "Iced tea", "price": "3.75", "category": "Drinks", "featured": true }
```

### Cart

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/api/cart/menu-items` | logged in | Your cart |
| POST | `/api/cart/menu-items` | logged in | Add an item: `{"menuitem": 3, "quantity": 2}` |
| DELETE | `/api/cart/menu-items` | logged in | Empty your cart |

The server sets `unit_price` and `price` from the menu item, so prices sent by a client are ignored. `quantity` must be at least 1.

### Orders

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/api/orders` | logged in | Customers see their own, delivery crew see the ones assigned to them, managers see all |
| POST | `/api/orders` | logged in | Place an order from your current cart. Send an empty body |
| GET | `/api/orders/<id>` | logged in | One order |
| PUT, PATCH | `/api/orders/<id>` | see [Known limitations](#known-limitations) | Change `status` and `delivery_crew` only |

Placing an order copies the cart into order items, works out the total on the server, and empties the cart, all in one transaction. An empty cart returns a 400.

An order looks like this. `user` and `delivery_crew` are user ids:

```json
{
  "id": 12, "user": 4, "delivery_crew": 7, "status": false,
  "date": "2026-11-23", "total": "11.50",
  "orderitem": [ { "order": 12, "menuitem": 3, "quantity": 2, "price": "7.50" } ]
}
```

`delivery_crew` must be someone in the Delivery crew group, or `null` to unassign.

### Groups

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/api/groups/manager/users` | manager, superuser | List managers |
| POST, DELETE | `/api/groups/manager/users` | manager, superuser | Add or remove one: `{"username": "mona"}` |
| GET | `/api/groups/delivery-crew/users` | logged in | List the crew |
| POST, DELETE | `/api/groups/delivery-crew/users` | manager, superuser | Add or remove one: `{"username": "omar"}` |

### Paging and limits

List endpoints are paginated with `PAGE_SIZE = 2` and return `{"count", "next", "previous", "results"}`. The storefront follows the `next` links whenever it needs a full list, for example for dropdowns and the cart.

Requests are throttled to 20 per minute for anonymous callers and 50 per minute for each logged-in user.

---

## Project structure

```
LittleLemon/
├── manage.py
├── requirements.txt
├── README.md
├── .env                        your local settings (not committed)
├── db.sqlite3                  local database (not committed)
├── media/                      drink photos, e.g. Iced_tea.jpg
│
├── Littlelemon/                project configuration
│   ├── settings.py             apps, REST framework, Djoser, media settings
│   └── urls.py                 routes: frontend at /, API at /api/, Djoser at /auth/
│
├── LittlelemonAPI/             the REST API
│   ├── models.py               Category, menuItem, Cart, Order, OrderItem
│   ├── serializers.py          includes CartSerializer, OrderUpdateSerializer, CurrentUserSerializer
│   ├── views.py                generic class-based API views and group viewsets
│   ├── permissions.py          IsManager, IsManagerOrReadOnly, CanUpdateOrder, DeliveryCrewPermission
│   ├── urls.py
│   └── migrations/
│
└── frontend/                   the storefront
    ├── views.py                class-based views, role mixin, helpers
    ├── urls.py                 page routes (namespace "frontend")
    ├── api_client.py           every call to the API lives here
    ├── context_processors.py   makes is_manager, is_customer, logged_in... available in templates
    ├── templatetags/
    │   └── frontend_extras.py  finds the photo for a drink
    ├── static/frontend/css/
    │   └── littlelemon.css     the whole design
    └── templates/frontend/
        ├── base.html           header, navigation, messages, footer
        ├── index.html, menu_items.html, categories.html, cart.html,
        │   orders.html, login.html, managers.html, delivery_crew.html
        └── partials/           menu card, forms, pagination, drink image...
```

`LittlelemonAPI/templates/` holds an older set of HTML templates. No view uses them.

---

## How the pieces fit together

**The storefront is a client of the API.** A page request goes: browser, then a `frontend` view, then `api_client.py` (an HTTP call to `/api/...`), then an API view, then the database. The frontend never imports the API's models.

**Login.** `LoginView` posts the username and password to `/auth/token/login/`, then reads `/auth/users/me/` to learn the person's groups. The token, username and role flags go into the Django session. Later requests send the token to the API.

**Roles in templates.** `context_processors.roles` turns the session into `logged_in`, `is_admin`, `is_manager`, `is_delivery_crew` and `is_customer`, available in every template. A simple rule decides where a check goes:

- a page only some roles may open: check in the view (`RoleRequiredMixin`)
- a page everyone opens, with extra controls for some roles: one template with `{% if is_manager %}` around the extra parts, kept in `partials/`

**Class-based views.** Pages that only need one URL are one class with `get` and `post`. Menu items and orders are split the way the API is: a list view (`menu-items/`, `orders/`) and a single-item view (`menu-items/<pk>/`, `orders/<pk>/`) that handles edits and deletes.

**Prices and totals are computed on the server.** The cart serializer sets each line's price from the menu item, and order creation sums the cart itself.

---


## Before deploying

- Set `DEBUG=False`, a strong `SECRET_KEY`, and `ALLOWED_HOSTS` to your real domain.
- Replace the hard-coded `127.0.0.1:8000` in `frontend/api_client.py` with a setting or environment variable.
- Serve `/media/` and static files from your web server or a storage service. The `static()` route in `Littlelemon/urls.py` only works while `DEBUG=True`.
- Run `python manage.py collectstatic` and set `STATIC_ROOT`.
- Switch from SQLite to a production database, and serve Django with a real application server such as gunicorn.
