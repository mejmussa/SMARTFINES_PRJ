"""
URL configuration for smartfines_prj project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap
from django.views.generic import TemplateView
from django.views.i18n import set_language
from core.views import PWAServeView


sitemaps = {
    'static': StaticViewSitemap,
}


urlpatterns = [
    path('i18n/setlang/', set_language, name='set_language'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('authentication/', include('accounts.urls')),
    path('dashboard/', include('monitoring.urls')),
    path('robots.txt', serve, {'path': 'robots.txt', 'document_root': settings.BASE_DIR / 'templates'}),
    path('59253ba4bbc8403d92d9fc251a422642.txt', serve, {'path': '59253ba4bbc8403d92d9fc251a422642.txt', 'document_root': settings.BASE_DIR / 'templates'}),
    path('pwa/<path:filename>', PWAServeView.as_view(), name='serve-pwa'),
]

if settings.DEBUG:
    # Serve static and media files during development
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if not settings.DEBUG:
    # Serve media files in production using the `serve` view
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}), 
    ]
