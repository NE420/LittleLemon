from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal

from .models import Category, menuItem, Cart, Order, OrderItem


class CategorySerializer (serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug']


class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field='title',
        queryset=Category.objects.all()
    )
    # category = serializers.PrimaryKeyRelatedField(
    # queryset= Category.objects.all()
    # )
    # category = CategorySerializer(read_only=True)
    class Meta:
        model = menuItem
        fields = ['id', 'title', 'price', 'category', 'featured']


class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate(self, attrs):
        attrs['unit_price'] = attrs['menuitem'].price
        attrs['price'] = attrs['quantity'] * attrs['unit_price']
        return attrs

    class Meta:
        model = Cart
        fields = ['user', 'menuitem', 'unit_price', 'quantity', 'price']
        extra_kwargs = {
            'quantity': {'min_value': 1},
            'unit_price': {'read_only': True},
            'price': {'read_only': True},
        }


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order', 'menuitem', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):

    orderitem = OrderItemSerializer(many=True, read_only=True, source='orderitem_set')
    delivery_crew = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(groups__name='Delivery crew'),
        required=False,
        allow_null=True,
    )
    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew',
                  'status', 'date', 'total', 'orderitem']
        extra_kwargs = {
            'total': {'read_only': True}
        }

class OrderUpdateSerializer(serializers.ModelSerializer):
    delivery_crew = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(groups__name='Delivery crew'),
        allow_null=True, required=False,
    )

    class Meta:
        model = Order
        fields = ['status', 'delivery_crew']

class UserSerilializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username','email']

class CurrentUserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'groups', 'is_staff', 'is_superuser']
        read_only_fields = ['username', 'is_staff', 'is_superuser']