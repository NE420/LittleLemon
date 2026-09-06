from django.urls import path
from . import views
 
app_name = 'frontend'

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
 
    path("categories/", views.categories_view, name="categories"),
    path("menu-items/", views.menu_items_view, name="menu-items"),
    path("cart/", views.cart_view, name="cart"),
    path("orders/", views.orders_view, name="orders"),
    path("managers/", views.managers_view, name="managers"),
    path("delivery-crew/", views.delivery_crew_view, name="delivery-crew"),
]