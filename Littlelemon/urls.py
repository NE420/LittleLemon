from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontend.urls')),
    path('api/', include('LittlelemonAPI.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('token/login', views.obtain_auth_token),
]

# Serves the drink photos from /media/ while DEBUG is on (does nothing in production).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
