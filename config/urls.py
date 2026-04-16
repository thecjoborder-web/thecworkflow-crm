from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


# 🔁 Smart Dashboard Router - redirects based on user role
@login_required(login_url='/accounts/login/')
def dashboard_router(request):
    """
    Route users to their appropriate dashboard based on role:
    - CEO/Superuser -> CEO Dashboard
    - Admin/Staff -> Admin Dashboard
    - Sales Agent -> Sales Dashboard
    """
    user = request.user
    
    # CEO Dashboard
    if user.groups.filter(name='ceo').exists() or user.is_superuser:
        return redirect('/dashboard/ceo/')
    
    # Admin Dashboard
    if user.is_staff or user.is_superuser:
        return redirect('/dashboard/admin/')
    
    # Sales Dashboard (default for anyone else)
    return redirect('/dashboard/sales/')


# 🔁 Redirect root domain to login page or dashboard
def root_redirect(request):
    if request.user.is_authenticated:
        return dashboard_router(request)
    return redirect('/accounts/login/')


urlpatterns = [
    path('', root_redirect),  # 👈 Smart router based on authentication
    
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('dashboard/', include('dashboards.urls')),  # 👈 Includes ceo/, admin/, sales/ routes
]


# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
