from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    path("categories/", views.CategoriesView.as_view(), name="categories"),

    path("menu-items/", views.MenuItemsView.as_view(), name="menu-items"),
    path("menu-items/<int:pk>/", views.SingleMenuItemView.as_view(), name="single-menu-item"),

    path("cart/", views.CartView.as_view(), name="cart"),

    path("orders/", views.OrdersView.as_view(), name="orders"),
    path("orders/<int:pk>/", views.SingleOrderView.as_view(), name="single-order"),

    path("managers/", views.ManagersView.as_view(), name="managers"),
    path("delivery-crew/", views.DeliveryCrewView.as_view(), name="delivery-crew"),
]