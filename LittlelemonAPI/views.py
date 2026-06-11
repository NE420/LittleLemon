from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Category, menuItem, Cart, Order, OrderItem
from .serializers import CategorySerializer, MenuItemSerializer, CartSerializer, OrderSerializer, UserSerilializer
from rest_framework.response import Response

from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth.models import Group, User

from rest_framework import viewsets
from rest_framework import status


def is_manager(user):
    return bool(user and (user.is_superuser or user.groups.filter(name='Manager').exists()))


class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get(self, request, *args, **kwargs):
        if 'text/html' in request.headers.get('Accept', ''):
            queryset = self.filter_queryset(self.get_queryset())
            return render(request, 'LittlelemonAPI/categories.html', {
                'categories': queryset,
                'is_manager': is_manager(request.user),
            })
        return super().get(request, *args, **kwargs)

    def get_permissions(self):
        permission_classes = []
        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

class MenuItemsView(generics.ListCreateAPIView):
    queryset = menuItem.objects.all()
    serializer_class = MenuItemSerializer
    search_fields = ['category__title']
    ordering_fields = ['price', 'inventory']

    def get(self, request, *args, **kwargs):
        if 'text/html' in request.headers.get('Accept', ''):
            queryset = self.filter_queryset(self.get_queryset())
            search_query = request.GET.get('q', '').strip()
            category_id = request.GET.get('category', '')
            if search_query:
                queryset = queryset.filter(title__icontains=search_query)
            if category_id:
                queryset = queryset.filter(category_id=category_id)

            paginator = Paginator(queryset.order_by('title'), 6)
            page_number = request.GET.get('page', 1)
            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            return render(request, 'LittlelemonAPI/menu_items.html', {
                'page_obj': page_obj,
                'categories': Category.objects.all().order_by('title'),
                'search_query': search_query,
                'selected_category': category_id,
                'is_manager': is_manager(request.user),
            })
        return super().get(request, *args, **kwargs)

    def get_permissions(self):
        permission_classes = []
        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]


class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        permission_classes = []
        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = menuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        permission_classes = []
        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.all().filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        if 'text/html' in request.headers.get('Accept', ''):
            cart_items = self.get_queryset().select_related('menuitem', 'menuitem__category', 'user').order_by('-id')
            total = sum(item.price for item in cart_items)
            return render(request, 'LittlelemonAPI/cart.html', {
                'cart_items': cart_items,
                'total': total,
                'is_manager': is_manager(request.user),
            })
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        Cart.objects.all().filter(user=self.request.user).delete()
        return Response("ok")


class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'GET' and 'text/html' in self.request.headers.get('Accept', ''):
            return [AllowAny()]
        return [IsAuthenticated()]

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
        # else:
        #     return Order.objects.all()

    def get(self, request, *args, **kwargs):
        if 'text/html' in request.headers.get('Accept', ''):
            orders = self.get_queryset().select_related('user', 'delivery_crew').order_by('-date', '-id')
            paginator = Paginator(orders, 6)
            page_number = request.GET.get('page', 1)
            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
            return render(request, 'LittlelemonAPI/orders.html', {
                'page_obj': page_obj,
                'is_manager': is_manager(request.user),
            })
        return super().get(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        menuitem_count = Cart.objects.all().filter(user=self.request.user).count()
        if menuitem_count == 0:
            return Response({"message:": "no item in cart"})

        data = request.data.copy()
        total = self.get_total_price(self.request.user)
        data['total'] = total
        data['user'] = self.request.user.id
        order_serializer = OrderSerializer(data=data)
        if (order_serializer.is_valid()):
            order = order_serializer.save()

            items = Cart.objects.all().filter(user=self.request.user).all()

            for item in items.values():
                orderitem = OrderItem(
                    order=order,
                    menuitem_id=item['menuitem_id'],
                    price=item['price'],
                    quantity=item['quantity'],
                )
                orderitem.save()

            Cart.objects.all().filter(user=self.request.user).delete() #Delete cart items

            result = order_serializer.data.copy()
            result['total'] = total
            return Response(order_serializer.data)
    
    def get_total_price(self, user):
        total = 0
        items = Cart.objects.all().filter(user=user).all()
        for item in items.values():
            total += item['price']
        return total


class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        if self.request.user.groups.count()==0: # Normal user, not belonging to any group = Customer
            return Response('Not Ok')
        else: #everyone else - Super Admin, Manager and Delivery Crew
            return super().update(request, *args, **kwargs)



class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        if 'text/html' in self.request.headers.get('Accept', ''):
            return [AllowAny()]
        return [IsAdminUser()]

    def list(self, request):
        users = User.objects.all().filter(groups__name='Manager').distinct().order_by('username')
        if 'text/html' in request.headers.get('Accept', ''):
            return render(request, 'LittlelemonAPI/managers.html', {'managers': users})
        items = UserSerilializer(users, many=True)
        return Response(items.data)

    def create(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.add(user)
        return Response({"message": "user added to the manager group"}, 200)

    def destroy(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.remove(user)
        return Response({"message": "user removed from the manager group"}, 200)

class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if 'text/html' in self.request.headers.get('Accept', ''):
            return [AllowAny()]
        return [IsAuthenticated()]

    def list(self, request):
        users = User.objects.all().filter(groups__name='Delivery crew').distinct().order_by('username')
        if 'text/html' in request.headers.get('Accept', ''):
            return render(request, 'LittlelemonAPI/delivery_crew.html', {'crew': users})
        items = UserSerilializer(users, many=True)
        return Response(items.data)

    def create(self, request):
        #only for super admin and managers
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists() == False:
                return Response({"message":"forbidden"}, status.HTTP_403_FORBIDDEN)

        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery crew")
        dc.user_set.add(user)
        return Response({"message": "user added to the delivery crew group"}, 200)

    def destroy(self, request):
        #only for super admin and managers
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists() == False:
                return Response({"message":"forbidden"}, status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery crew")
        dc.user_set.remove(user)
        return Response({"message": "user removed from the delivery crew group"}, 200)


