from rest_framework import permissions


def _is_manager_or_super(user):
    return bool(
        user and user.is_authenticated and
        (user.is_superuser or user.groups.filter(name='Manager').exists())
    )


class IsManager(permissions.BasePermission):
    """Full access only to superusers or the Manager group."""
    def has_permission(self, request, view):
        return _is_manager_or_super(request.user)


class IsManagerOrReadOnly(permissions.BasePermission):
    """Anyone can read (GET/HEAD/OPTIONS); only Manager/superuser can write."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_manager_or_super(request.user)


class CanUpdateOrder(permissions.BasePermission):
    """
    Any authenticated user can read their own orders (filtered in get_queryset).
    Only users belonging to at least one group (Manager / Delivery crew) —
    or superusers — can update an order.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user and user.is_authenticated and
            (user.is_superuser or user.groups.exists())
        )


class DeliveryCrewPermission(permissions.BasePermission):
    """
    Any authenticated user can list delivery crew.
    Only Manager/superuser can add or remove delivery crew members.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_manager_or_super(user)