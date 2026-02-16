from django.contrib import admin
from django.urls import path, include  # include is required to link app URLs
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # 👈 ADD THIS
    path('dashboard/', include('dashboards.urls')),
]


# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
