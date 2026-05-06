from django.urls import path
from . import views
app_name = "dashboards"
urlpatterns = [
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("ceo/", views.ceo_dashboard, name="ceo_dashboard"),
    path("sales/", views.sales_dashboard, name="sales_dashboard"),
    path("job-order/", views.sales_dashboard, name="job_order_home"),
    path("job-order/new/", views.create_job_order, name="create_job_order"),
    path("job-order/<int:order_id>/", views.job_order_detail, name="job_order_detail"),
    path("job-order/<int:order_id>/send-to-project/", views.send_job_order_to_project, name="send_job_order_to_project"),
    path("job-order/<int:order_id>/print/", views.print_job_order, name="print_job_order"),
    path("job-orders/export/", views.export_job_orders_csv, name="export_job_orders_csv"),

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
