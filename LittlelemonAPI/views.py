from urllib import request

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group, User
from rest_framework import viewsets, status

from .models import Category, menuItem, Cart, Order, OrderItem
from .serializers import CategorySerializer, MenuItemSerializer, CartSerializer, OrderSerializer, UserSerilializer
from .permissions import IsManager, IsManagerOrReadOnly, CanUpdateOrder, DeliveryCrewPermission


class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly]
   

class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly]


class MenuItemsView(generics.ListCreateAPIView):
    queryset = menuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsManagerOrReadOnly]
    search_fields = ['category__title']
    ordering_fields = ['price', 'inventory']
    

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = menuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsManagerOrReadOnly]


class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.all().filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        Cart.objects.all().filter(user=self.request.user).delete()
        return Response("ok")


class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            if 'text/html' in self.request.headers.get('Accept', ''):
                return Order.objects.all().order_by('-date', '-id')
            return Order.objects.none()

        if user.is_superuser:
            return Order.objects.all()
        if user.groups.count() == 0:
            return Order.objects.all().filter(user=user)
        if user.groups.filter(name='Delivery crew').exists():
            return Order.objects.all().filter(delivery_crew=user)
        return Order.objects.all()

    def create(self, request, *args, **kwargs):
        menuitem_count = Cart.objects.all().filter(user=self.request.user).count()
        if menuitem_count == 0:
            return Response({"message:": "no item in cart"})

        total = self.get_total_price(self.request.user)

        order_serializer = OrderSerializer(data=request.data)
        if order_serializer.is_valid():
            order = order_serializer.save(user=self.request.user, total=total)
            
            items = Cart.objects.all().filter(user=self.request.user).all()
            for item in items.values():
                OrderItem.objects.create(
                    order=order,
                    menuitem_id=item['menuitem_id'],
                    price=item['price'],
                    quantity=item['quantity'],
                )
            Cart.objects.all().filter(user=self.request.user).delete()
            
            return Response(order_serializer.data)
        
        return Response(order_serializer.errors, status=400)

    def get_total_price(self, user):
        total = 0
        items = Cart.objects.all().filter(user=user).all()
        for item in items.values():
            total += item['price']
        return total


class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, CanUpdateOrder]


class GroupMembershipViewSet(viewsets.ViewSet):
    group_name = None  # override in subclass

    def list(self, request):
        users = User.objects.filter(groups__name=self.group_name).distinct().order_by('username')
        return Response(UserSerilializer(users, many=True).data)

    def create(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        group = Group.objects.get(name=self.group_name)
        group.user_set.add(user)
        return Response({"message": f"user added to the {self.group_name} group"}, 200)

    def destroy(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        group = Group.objects.get(name=self.group_name)
        group.user_set.remove(user)
        return Response({"message": f"user removed from the {self.group_name} group"}, 200)


class GroupViewSet(GroupMembershipViewSet):
    group_name = "Manager"
    permission_classes = [IsManager]
    
    
class DeliveryCrewViewSet(GroupMembershipViewSet):
    group_name = "Delivery crew"
    permission_classes = [DeliveryCrewPermission]