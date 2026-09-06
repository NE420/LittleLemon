import requests
 
BASE_URL = "http://127.0.0.1:8000/api"
 
# Djoser's own urls (path('auth/', include('djoser.urls')) etc.) use
# trailing slashes. Note: your main urls.py also has a bare
# path('token/login', views.obtain_auth_token) — don't use that one
# here, since it's DRF's stock view and returns {'token': ...} instead
# of Djoser's {'auth_token': ...}.
AUTH_BASE_URL = "http://127.0.0.1:8000/auth"
LOGIN_ENDPOINT = f"{AUTH_BASE_URL}/token/login/"
LOGOUT_ENDPOINT = f"{AUTH_BASE_URL}/token/logout/"
CURRENT_USER_ENDPOINT = f"{AUTH_BASE_URL}/users/me/"
 
 
class APIError(Exception):
    """Raised when the backend returns a non-2xx response."""
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")
 
 
def _headers(token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    return headers
 
 
def _handle(response):
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise APIError(response.status_code, detail)
    if response.status_code == 204 or not response.content:
        return None
    return response.json()
 
 
# ---------- Auth ----------
 
def login(username, password):
    """Returns Djoser's payload: {'auth_token': '...'}"""
    resp = requests.post(
        LOGIN_ENDPOINT,
        data={"username": username, "password": password},
    )
    return _handle(resp)
 
 
def logout(token):
    """Invalidates the token server-side (Djoser deletes it)."""
    resp = requests.post(LOGOUT_ENDPOINT, headers=_headers(token))
    return _handle(resp)
 
 
def get_current_user(token):
    """
    Djoser's default UserSerializer only returns id/username/email —
    no groups. If you need role info here (Manager / Delivery crew /
    Customer) on the frontend, either:
      a) customize DJOSER['SERIALIZERS']['current_user'] on the backend
         to include groups, or
      b) keep using the try/except-403 approach in views.py.
    """
    resp = requests.get(CURRENT_USER_ENDPOINT, headers=_headers(token))
    return _handle(resp)
 
 
# ---------- Categories ----------
 
def get_categories():
    resp = requests.get(f"{BASE_URL}/categories")
    return _handle(resp)
 
 
def create_category(data, token):
    resp = requests.post(f"{BASE_URL}/categories", json=data, headers=_headers(token))
    return _handle(resp)
 
 
# ---------- Menu items ----------
 
def get_menu_items(params=None):
    """params: dict, e.g. {'search': 'pasta', 'ordering': 'price'}"""
    resp = requests.get(f"{BASE_URL}/menu-items", params=params or {})
    return _handle(resp)
 
 
def get_menu_item(item_id):
    resp = requests.get(f"{BASE_URL}/menu-items/{item_id}")
    return _handle(resp)
 
 
def create_menu_item(data, token):
    resp = requests.post(f"{BASE_URL}/menu-items", json=data, headers=_headers(token))
    return _handle(resp)
 
 
def update_menu_item(item_id, data, token):
    resp = requests.put(f"{BASE_URL}/menu-items/{item_id}", json=data, headers=_headers(token))
    return _handle(resp)
 
 
def delete_menu_item(item_id, token):
    resp = requests.delete(f"{BASE_URL}/menu-items/{item_id}", headers=_headers(token))
    return _handle(resp)
 
 
# ---------- Cart ----------
 
def get_cart(token):
    resp = requests.get(f"{BASE_URL}/cart/menu-items", headers=_headers(token))
    return _handle(resp)
 
 
def add_to_cart(data, token):
    """data: {'menuitem': id, 'quantity': n, 'unit_price': ..., 'price': ...}"""
    resp = requests.post(f"{BASE_URL}/cart/menu-items", json=data, headers=_headers(token))
    return _handle(resp)
 
 
def clear_cart(token):
    resp = requests.delete(f"{BASE_URL}/cart/menu-items", headers=_headers(token))
    return _handle(resp)
 
 
# ---------- Orders ----------
 
def get_orders(token):
    resp = requests.get(f"{BASE_URL}/orders", headers=_headers(token))
    return _handle(resp)
 
 
def get_order(order_id, token):
    resp = requests.get(f"{BASE_URL}/orders/{order_id}", headers=_headers(token))
    return _handle(resp)
 
 
def create_order(token):
    """Backend builds the order from whatever is currently in the user's cart."""
    resp = requests.post(f"{BASE_URL}/orders", json={}, headers=_headers(token))
    return _handle(resp)
 
 
def update_order(order_id, data, token):
    """data typically: {'delivery_crew': id} or {'status': 0/1}"""
    resp = requests.patch(f"{BASE_URL}/orders/{order_id}", json=data, headers=_headers(token))
    return _handle(resp)
 
 
# ---------- Manager group ----------
 
def list_managers(token):
    resp = requests.get(f"{BASE_URL}/groups/manager/users", headers=_headers(token))
    return _handle(resp)
 
 
def add_manager(username, token):
    resp = requests.post(
        f"{BASE_URL}/groups/manager/users", json={"username": username}, headers=_headers(token)
    )
    return _handle(resp)
 
 
def remove_manager(username, token):
    resp = requests.delete(
        f"{BASE_URL}/groups/manager/users", json={"username": username}, headers=_headers(token)
    )
    return _handle(resp)
 
 
# ---------- Delivery crew group ----------
 
def list_delivery_crew(token):
    resp = requests.get(f"{BASE_URL}/groups/delivery-crew/users", headers=_headers(token))
    return _handle(resp)
 
 
def add_delivery_crew(username, token):
    resp = requests.post(
        f"{BASE_URL}/groups/delivery-crew/users", json={"username": username}, headers=_headers(token)
    )
    return _handle(resp)
 
 
def remove_delivery_crew(username, token):
    resp = requests.delete(
        f"{BASE_URL}/groups/delivery-crew/users", json={"username": username}, headers=_headers(token)
    )
    return _handle(resp)