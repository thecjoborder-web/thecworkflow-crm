from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Dashboards
    path('supervisor/', views.project_supervisor_dashboard, name='supervisor_dashboard'),
    path('production/', views.production_dashboard, name='production_dashboard'),
    
    # Project Detail
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    
    # API Endpoints (AJAX)
    path('upload/', views.upload_project, name='upload_project'),
    path('<int:project_id>/send-to-production/', views.send_to_production, name='send_to_production'),
    path('<int:project_id>/download/', views.download_project, name='download_project'),
    path('<int:project_id>/update-status/', views.update_project_status, name='update_project_status'),
    
    # Notifications
    path('notifications/get/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
]
