"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
# import i18n urls
from django.conf.urls.i18n import i18n_patterns
#import settings
from django.conf import settings
#import static and media urls
from django.conf.urls.static import static
# Import PWA views
from home.views import manifest_view, service_worker_view


# PWA URLs - Must be outside i18n_patterns (browser expects them at root level)
pwa_urlpatterns = [
    path('manifest.json', manifest_view, name='manifest'),
    path('service-worker.js', service_worker_view, name='service_worker'),
]

# Regular URL patterns that will be wrapped with i18n
i18n_urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('home.urls')),
    path('accounts/', include('accounts.urls')),
    path('contact/', include('contact.urls')),
    path('settings/', include('settings.urls')),
    path('menu/', include('menu.urls')),
    path('reservation/', include('reversation.urls')),
]

# Combine: PWA at root + i18n-wrapped patterns
urlpatterns = pwa_urlpatterns + i18n_patterns(*i18n_urlpatterns)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)