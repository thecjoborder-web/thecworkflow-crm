from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


# 🔁 Redirect root domain to login page
def root_redirect(request):
    return redirect('/accounts/login/')


urlpatterns = [
    path('', root_redirect),  # 👈 THIS handles www.thecworkflow.com

    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('dashboard/', include('dashboards.urls')),
]


# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
