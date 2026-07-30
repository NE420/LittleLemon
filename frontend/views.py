import requests
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from LittlelemonAPI.models import Category, Cart, Order, menuItem
from LittlelemonAPI.serializers import UserSerilializer


def is_manager(user):
    return bool(user and (user.is_superuser or user.groups.filter(name='Manager').exists()))


def index_view(request):
    stats = {
        'categories': Category.objects.count(),
        'menu items': menuItem.objects.count(),
        'orders': Order.objects.count(),
    }
    return render(request, 'frontend/index.html', {'stats': stats, 'is_manager': is_manager(request.user)})


def login_view(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if username and password:
            response = requests.post(
                'http://127.0.0.1:8000/token/login',
                json={'username': username, 'password': password},
                timeout=5,
            )
            if response.status_code == 200:
                token = response.json().get('token')
                if token:
                    request.session['auth_token'] = token
                    return render(request, 'frontend/login.html', {'success': True, 'token': token})
            error = 'Invalid username or password.'
        else:
            error = 'Please enter both username and password.'

    return render(request, 'frontend/login.html', {'error': error})


def categories_view(request):
    queryset = Category.objects.all().order_by('title')
    return render(request, 'frontend/categories.html', {
        'categories': queryset,
        'is_manager': is_manager(request.user),
    })


def menu_items_view(request):
    queryset = menuItem.objects.all()
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

    return render(request, 'frontend/menu_items.html', {
        'page_obj': page_obj,
        'categories': Category.objects.all().order_by('title'),
        'search_query': search_query,
        'selected_category': category_id,
        'is_manager': is_manager(request.user),
    })


def cart_view(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.all().filter(user=request.user).select_related('menuitem', 'menuitem__category', 'user').order_by('-id')
    else:
        cart_items = Cart.objects.none()

    total = sum(item.price for item in cart_items)
    return render(request, 'frontend/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'is_manager': is_manager(request.user),
    })


def orders_view(request):
    orders = Order.objects.all().order_by('-date', '-id')
    paginator = Paginator(orders, 6)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'frontend/orders.html', {
        'page_obj': page_obj,
        'is_manager': is_manager(request.user),
    })


def managers_view(request):
    users = User.objects.all().filter(groups__name='Manager').distinct().order_by('username')
    return render(request, 'frontend/managers.html', {'managers': users})


def delivery_crew_view(request):
    users = User.objects.all().filter(groups__name='Delivery crew').distinct().order_by('username')
    return render(request, 'frontend/delivery_crew.html', {'crew': users})
