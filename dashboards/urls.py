from django.urls import path
from . import views
app_name = "dashboards"
urlpatterns = [
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("ceo/", views.ceo_dashboard, name="ceo_dashboard"),
    path("sales/", views.sales_dashboard, name="sales_dashboard"),

    # Lead actions
    path(
        "lead/<int:lead_id>/contacted/",
        views.mark_lead_contacted,
        name="mark_lead_contacted",
    ),
    path(
        "lead/<int:lead_id>/add-note/",
        views.add_lead_note,
        name="add_lead_note",
    ),

    # AJAX activity logging
    path(
        "log-activity/",
        views.log_activity,
        name="log_activity",
    ),

    # Get activities for a lead
    path(
        "lead/<int:lead_id>/activities/",
        views.get_lead_activities,
        name="get_lead_activities",
    ),
    
    # Admin lead assignment
    path(
        "assign-lead/",
        views.assign_lead,
        name="assign_lead",
    ),
    
    # CSV import
    path(
        "import-csv/",
        views.import_csv,
        name="import_csv",
    ),
    
    # User role management
    path(
        "toggle-user-role/",
        views.toggle_user_role,
        name="toggle_user_role",
    ),
]
