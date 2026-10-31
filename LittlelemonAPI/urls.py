from django.urls import path
from . import views

urlpatterns = [
    path('categories', views.CategoriesView.as_view(), name='categories'),
    path('categories/<int:pk>', views.SingleCategoryView.as_view(), name='single_category'),
    path('menu-items', views.MenuItemsView.as_view(), name='menu_items'),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view(), name='single_menu_item'),
    path('cart/menu-items', views.CartView.as_view(), name='cart'),
    path('orders', views.OrderView.as_view(), name='orders'),
    path('orders/<int:pk>', views.SingleOrderView.as_view(), name='single_order'),
    path('groups/manager/users', views.GroupViewSet.as_view(
        {'get': 'list', 'post': 'create', 'delete': 'destroy'}), name='manager_users'),
    path('groups/delivery-crew/users', views.DeliveryCrewViewSet.as_view(
        {'get': 'list', 'post': 'create', 'delete': 'destroy'}), name='delivery_crew_users')
]