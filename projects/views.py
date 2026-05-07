import json
import os
from datetime import datetime, date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Project, ProjectStatusLog, ProductionNotification, ProjectDownloadLog

User = get_user_model()


# ==================== PERMISSION CHECKS ====================

def is_project_supervisor(user):
    """Check if user is Project Supervisor or Admin"""
    return user.groups.filter(name='project_supervisor').exists() or user.is_staff or user.is_superuser


def is_production_staff(user):
    """Check if user is Production Staff or Admin"""
    return user.groups.filter(name='production_staff').exists() or user.is_staff or user.is_superuser


# ==================== PROJECT SUPERVISOR DASHBOARD ====================

@login_required
@user_passes_test(is_project_supervisor)
def project_supervisor_dashboard(request):
    """
    Project Supervisor Dashboard
    - View all projects (own + others)
    - Upload new projects
    - Send to production
    - Track status
    - Search by client
    """
    
    # Get all projects (all PSs see all projects)
    projects = Project.objects.all().select_related('created_by').order_by('-created_at')
    
    # Search by client name
    client_search = request.GET.get('client', '').strip()
    if client_search:
        projects = projects.filter(Q(client_name__icontains=client_search))
    
    # Search by creator name
    created_by_search = request.GET.get('created_by', '').strip()
    if created_by_search:
        projects = projects.filter(
            Q(created_by__first_name__icontains=created_by_search) |
            Q(created_by__last_name__icontains=created_by_search) |
            Q(created_by__username__icontains=created_by_search)
        )
    
    # Filter by created_by (only my projects)
    my_projects_only = request.GET.get('my_projects') == 'on'
    if my_projects_only:
        projects = projects.filter(created_by=request.user)

    # Date filter for project uploads
    date_filter = request.GET.get('date_filter', 'all')
    if date_filter == 'today':
        projects = projects.filter(created_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        projects = projects.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        projects = projects.filter(created_at__date__gte=month_start)
    
    # Get stats
    total_projects = Project.objects.count()
    my_projects = Project.objects.filter(created_by=request.user).count()
    sent_to_production = Project.objects.filter(sent_to_production=True).count()
    in_production = Project.objects.filter(status='in_production').count()
    
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'my_projects': my_projects,
        'sent_to_production': sent_to_production,
        'in_production': in_production,
        'client_search': client_search,
        'created_by_search': created_by_search,
        'my_projects_only': my_projects_only,
        'date_filter': date_filter,
    }
    
    return render(request, 'projects/project_supervisor_dashboard.html', context)


# ==================== PRODUCTION DASHBOARD ====================

@login_required
@user_passes_test(is_production_staff)
def production_dashboard(request):
    """
    Production Room Dashboard
    - View ONLY projects sent to production (sent_to_production=True)
    - Download project files
    - Update status
    - Track progress
    - Search by client
    """
    
    # Get ONLY projects sent to production (WORKFLOW RESTRICTION)
    projects = Project.objects.filter(
        sent_to_production=True
    ).select_related('created_by').order_by('-sent_to_production_at')
    
    # Search by client name
    client_search = request.GET.get('client', '').strip()
    if client_search:
        projects = projects.filter(Q(client_name__icontains=client_search))

    # Search by creator name
    created_by_search = request.GET.get('created_by', '').strip()
    if created_by_search:
        projects = projects.filter(
            Q(created_by__first_name__icontains=created_by_search) |
            Q(created_by__last_name__icontains=created_by_search) |
            Q(created_by__username__icontains=created_by_search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        projects = projects.filter(status=status_filter)

    # Date filter for production projects
    date_filter = request.GET.get('date_filter', 'all')
    if date_filter == 'today':
        projects = projects.filter(sent_to_production_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        projects = projects.filter(sent_to_production_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        projects = projects.filter(sent_to_production_at__date__gte=month_start)
    
    # Get stats
    total_projects = Project.objects.filter(sent_to_production=True).count()
    in_production = projects.filter(status='in_production').count()
    completed = projects.filter(status='completed').count()
    ready_for_pickup = projects.filter(status='ready_for_pickup').count()
    
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'in_production': in_production,
        'completed': completed,
        'ready_for_pickup': ready_for_pickup,
        'client_search': client_search,
        'created_by_search': created_by_search,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'project_statuses': Project.PROJECT_STATUSES,
    }
    
    return render(request, 'projects/production_dashboard.html', context)


# ==================== PROJECT DETAIL VIEW ====================

@login_required
def project_detail(request, project_id):
    """View full project details"""
    project = get_object_or_404(Project, id=project_id)
    
    # Check access: PS sees all, Production sees only sent projects
    if not (is_project_supervisor(request.user) or (is_production_staff(request.user) and project.sent_to_production)):
        return HttpResponse("Access Denied", status=403)
    
    # Get status history
    status_logs = project.status_logs.all()
    
    context = {
        'project': project,
        'status_logs': status_logs,
        'can_edit': is_project_supervisor(request.user),
        'can_download': (is_project_supervisor(request.user) or is_production_staff(request.user)) and project.sent_to_production,
        'source_job_order': project.source_job_order,
    }
    
    return render(request, 'projects/project_detail.html', context)


# ==================== PROJECT PRINT VIEW ====================

@login_required
def print_project_order(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if not (is_project_supervisor(request.user) or (is_production_staff(request.user) and project.sent_to_production)):
        return HttpResponse('Access Denied', status=403)

    return render(request, 'projects/project_print.html', {
        'project': project,
        'source_job_order': project.source_job_order,
    })


# ==================== UPLOAD PROJECT (AJAX) ====================

@login_required
@user_passes_test(is_project_supervisor)
@require_POST
def upload_project(request):
    """
    AJAX endpoint for uploading new projects
    Expects form data with file upload
    """
    try:
        # Get all form data
        project_title = request.POST.get('project_title')
        project_description = request.POST.get('project_description', '')
        client_name = request.POST.get('client_name')
        client_contact = request.POST.get('client_contact', '')
        project_date = request.POST.get('project_date')
        deadline = request.POST.get('deadline')
        number_of_copies = request.POST.get('number_of_copies', 1)
        font_type = request.POST.get('font_type', 'Times New Roman')
        color_requirement = request.POST.get('color_requirement', 'b&w')
        paper_type = request.POST.get('paper_type', 'A4')
        paper_size = request.POST.get('paper_size', '')
        paper_weight = request.POST.get('paper_weight', '')
        binding_type = request.POST.get('binding_type', 'perfect')
        line_spacing = request.POST.get('line_spacing', '')
        isbn_required = request.POST.get('isbn_required', 'off') == 'on'
        special_instructions = request.POST.get('special_instructions', '')
        estimated_budget = request.POST.get('estimated_budget', None)
        agreed_amount = request.POST.get('agreed_amount', None)
        part_payment_raw = request.POST.get('part_payment', '')
        balance_due_raw = request.POST.get('balance_due', '')
        
        try:
            part_payment = float(part_payment_raw) if part_payment_raw else 0.00
        except ValueError:
            part_payment = 0.00

        try:
            balance_due = float(balance_due_raw) if balance_due_raw else 0.00
        except ValueError:
            balance_due = 0.00
        
        # Validate file
        if 'manuscript_file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        manuscript_file = request.FILES['manuscript_file']
        
        # Validate required fields
        if not all([project_title, client_name, project_date, deadline]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Create project
        project = Project.objects.create(
            project_title=project_title,
            project_description=project_description,
            client_name=client_name,
            client_contact=client_contact,
            client_location=request.POST.get('client_location', ''),
            delivery_location=request.POST.get('delivery_location', ''),
            project_date=project_date,
            deadline=deadline,
            number_of_copies=int(number_of_copies),
            font_type=font_type,
            color_requirement=color_requirement,
            paper_type=paper_type,
            paper_size=paper_size,
            paper_weight=paper_weight,
            line_spacing=line_spacing,
            isbn_required=isbn_required,
            binding_type=binding_type,
            special_instructions=special_instructions,
            estimated_budget=estimated_budget if estimated_budget else None,
            agreed_amount=agreed_amount if agreed_amount else None,
            part_payment=float(part_payment or 0.00),
            balance_due=float(balance_due or 0.00),
            manuscript_file=manuscript_file,
            created_by=request.user,
            status='submitted'
        )
        
        # Log initial status
        ProjectStatusLog.objects.create(
            project=project,
            old_status='submitted',
            new_status='submitted',
            changed_by=request.user,
            notes='Project created'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Project "{project_title}" uploaded successfully!',
            'project_id': project.id
        })
        
    except Exception as e:
        print(f'🚨 Error uploading project: {str(e)}')
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)


# ==================== SEND TO PRODUCTION (AJAX) ====================

@login_required
@user_passes_test(is_project_supervisor)
@require_POST
def send_to_production(request, project_id):
    """
    AJAX: Send project to Production Room
    """
    try:
        project = get_object_or_404(Project, id=project_id, created_by=request.user)
        
        project.sent_to_production = True
        project.sent_to_production_at = timezone.now()
        project.status = 'submitted'  # Ensure status is submitted when sent
        project.save()
        
        # Create notification for PS
        ProductionNotification.objects.create(
            project=project,
            notification_type='production_complete',
            title=f'Project sent to production',
            message=f'Your project "{project.project_title}" has been sent to production room',
            recipient=project.created_by
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Project sent to production!',
        })
        
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        print(f'🚨 Error sending to production: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


# ==================== DOWNLOAD PROJECT (FILE SERVE) ====================

@login_required
@user_passes_test(lambda user: is_production_staff(user) or is_project_supervisor(user))
def download_project(request, project_id):
    """
    Download project manuscript file
    Only if sent_to_production=True
    Logs download activity
    """
    try:
        project = get_object_or_404(Project, id=project_id)
        
        # WORKFLOW RESTRICTION: Only download if sent to production
        if not project.sent_to_production:
            return HttpResponse("This project has not been sent to production yet.", status=403)
        
        # Log download
        ProjectDownloadLog.objects.create(
            project=project,
            downloaded_by=request.user
        )
        
        # Create notification for PS
        ProductionNotification.objects.create(
            project=project,
            notification_type='downloaded',
            title=f'Project downloaded',
            message=f'Production staff downloaded "{project.project_title}"',
            recipient=project.created_by
        )
        
        # Serve the file
        if project.manuscript_file:
            file_path = project.manuscript_file.path
            filename = os.path.basename(file_path)
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return HttpResponse("File not found", status=404)
            
    except Exception as e:
        print(f'🚨 Error downloading project: {str(e)}')
        return HttpResponse(f'Error occurred: {str(e)}', status=500)


# ==================== UPDATE PROJECT STATUS (AJAX) ====================

@login_required
@user_passes_test(is_production_staff)
@require_POST
def update_project_status(request, project_id):
    """
    AJAX: Update project status (Production staff only)
    Only for projects sent to production
    """
    try:
        project = get_object_or_404(Project, id=project_id)
        
        # WORKFLOW RESTRICTION: Only update if sent to production
        if not project.sent_to_production:
            return JsonResponse({'error': 'Cannot update - project not sent to production'}, status=403)
        
        data = json.loads(request.body)
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        # Validate status
        valid_statuses = [choice[0] for choice in Project.PROJECT_STATUSES]
        if new_status not in valid_statuses:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        old_status = project.status
        project.status = new_status
        project.save()
        
        # Log status change
        ProjectStatusLog.objects.create(
            project=project,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            notes=notes
        )
        
        # Create notification for PS
        ProductionNotification.objects.create(
            project=project,
            notification_type='status_changed',
            title=f'Status changed: {new_status}',
            message=f'Project "{project.project_title}" status changed to {new_status}',
            recipient=project.created_by
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f'🚨 Error updating status: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


# ==================== GET NOTIFICATIONS (AJAX) ====================

@login_required
def get_notifications(request):
    """
    AJAX: Get unread notifications for current user
    Used to show notification badge
    """
    notifications = ProductionNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).values('id', 'title', 'message', 'notification_type', 'created_at')[:5]
    
    unread_count = ProductionNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'notifications': list(notifications),
        'unread_count': unread_count
    })


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = get_object_or_404(ProductionNotification, id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==================== REPORT GENERATION ====================

@login_required
@user_passes_test(is_project_supervisor)
def project_supervisor_report(request):
    """
    Generate HTML report for Project Supervisor Dashboard
    - Shows projects uploaded + job orders
    - Respects current filters (client, creator, date)
    - Can be viewed/printed in browser
    """
    from crm_leads.models import JobOrder
    
    # Get filtered projects
    projects = Project.objects.all().select_related('created_by').order_by('-created_at')
    
    # Apply filters
    client_search = request.GET.get('client', '').strip()
    if client_search:
        projects = projects.filter(Q(client_name__icontains=client_search))
    
    created_by_search = request.GET.get('created_by', '').strip()
    if created_by_search:
        projects = projects.filter(
            Q(created_by__first_name__icontains=created_by_search) |
            Q(created_by__last_name__icontains=created_by_search) |
            Q(created_by__username__icontains=created_by_search)
        )
    
    my_projects_only = request.GET.get('my_projects') == 'on'
    if my_projects_only:
        projects = projects.filter(created_by=request.user)
    
    date_filter = request.GET.get('date_filter', 'all')
    if date_filter == 'today':
        projects = projects.filter(created_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        projects = projects.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        projects = projects.filter(created_at__date__gte=month_start)
    
    # Get job orders (for separate section)
    job_orders = JobOrder.objects.all().select_related('created_by').order_by('-date')
    
    if date_filter == 'today':
        job_orders = job_orders.filter(date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        job_orders = job_orders.filter(date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        job_orders = job_orders.filter(date__gte=month_start)
    
    # Get date range label for title
    date_range_label = 'All Time'
    if date_filter == 'today':
        date_range_label = f'Today ({date.today().strftime("%B %d, %Y")})'
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)
        date_range_label = f'Week of {week_start.strftime("%B %d")} - {week_end.strftime("%B %d, %Y")}'
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        date_range_label = month_start.strftime('%B %Y')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Project Supervisor Report - {date_range_label}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                border-bottom: 3px solid #D32F2F;
                padding-bottom: 20px;
            }}
            .header h1 {{
                font-size: 28px;
                color: #D32F2F;
                margin-bottom: 10px;
            }}
            .header p {{
                color: #666;
                font-size: 14px;
            }}
            .section {{
                margin-bottom: 40px;
                break-inside: avoid;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: 700;
                color: #1a1a1a;
                border-bottom: 2px solid #D32F2F;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            thead {{
                background-color: #f5f5f5;
                border-bottom: 2px solid #2196F3;
            }}
            th {{
                padding: 12px;
                text-align: left;
                font-weight: 600;
                color: #333;
                font-size: 12px;
                text-transform: uppercase;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e0e0e0;
                font-size: 13px;
                color: #666;
            }}
            tbody tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .empty {{
                padding: 20px;
                text-align: center;
                color: #999;
                background: #f9f9f9;
                border-radius: 4px;
            }}
            .filter-info {{
                background: #E3F2FD;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 13px;
                color: #1565C0;
            }}
            .badge {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .badge-submitted {{
                background: #E3F2FD;
                color: #1565C0;
            }}
            .badge-sent_to_project {{
                background: #FFF3E0;
                color: #E65100;
            }}
            .badge-in_production {{
                background: #FCE4EC;
                color: #880E4F;
            }}
            .badge-completed {{
                background: #E8F5E9;
                color: #1B5E20;
            }}
            .amount {{
                text-align: right;
                font-weight: 600;
                color: #D32F2F;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                color: #999;
                font-size: 12px;
            }}
            @media print {{
                body {{
                    padding: 0;
                }}
                .container {{
                    padding: 20px;
                }}
                .section {{
                    page-break-inside: avoid;
                }}
                .no-print {{
                    display: none !important;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 Project Supervisor Report</h1>
                <p>Report Period: {date_range_label}</p>
                <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            {f'<div class="filter-info">Applied Filters: Client: {client_search or "None"} | Creator: {created_by_search or "None"} | My Projects Only: {"Yes" if my_projects_only else "No"}</div>' if (client_search or created_by_search or my_projects_only) else ''}
            
            <!-- Projects Section -->
            <div class="section">
                <div class="section-title">📤 Projects Uploaded ({projects.count()})</div>
                {'<table><thead><tr><th>Project Title</th><th>Client</th><th>Created By</th><th>Status</th><th>Deadline</th><th>Description</th></tr></thead><tbody>' + ''.join(f'''<tr>
                    <td><strong>{p.project_title}</strong></td>
                    <td>{p.client_name}</td>
                    <td>{p.created_by.first_name or p.created_by.username}</td>
                    <td><span class="badge badge-{p.status}">{p.get_status_display()}</span></td>
                    <td>{p.deadline.strftime("%b %d, %Y") if p.deadline else "N/A"}</td>
                    <td>{(p.project_description[:50] + "...") if p.project_description else "—"}</td>
                </tr>''' for p in projects) + '</tbody></table>' if projects else '<div class="empty">No projects found</div>'}
            </div>
            
            <!-- Job Orders Section -->
            <div class="section">
                <div class="section-title">📑 Job Orders ({job_orders.count()})</div>
                {'<table><thead><tr><th>Order #</th><th>Customer</th><th>Service</th><th>Quantity</th><th>Amount</th><th>Status</th><th>Expected Delivery</th></tr></thead><tbody>' + ''.join(f'''<tr>
                    <td><strong>{jo.order_no}</strong></td>
                    <td>{jo.customer_name}</td>
                    <td>{jo.get_product_service_display()}</td>
                    <td>{jo.quantity}</td>
                    <td class="amount">₦{jo.agreed_amount:,.2f}</td>
                    <td><span class="badge badge-{jo.status}">{jo.get_status_display()}</span></td>
                    <td>{jo.expected_delivery_date.strftime("%b %d, %Y") if jo.expected_delivery_date else "N/A"}</td>
                </tr>''' for jo in job_orders) + '</tbody></table>' if job_orders else '<div class="empty">No job orders found</div>'}
            </div>
            
            <div class="footer">
                <p>This report was generated from the Project Management System</p>
                <p style="margin-top: 10px;"><strong>Note:</strong> Print this page using Ctrl+P or the browser Print option. Choose "Print to PDF" for digital archiving.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_content, content_type='text/html')


@login_required
@user_passes_test(is_production_staff)
def production_report(request):
    """
    Generate HTML report for Production Dashboard
    - Shows projects sent to production
    - Respects current filters (client, creator, status, date)
    - Can be viewed/printed in browser
    """
    # Get filtered projects sent to production
    projects = Project.objects.filter(
        sent_to_production=True
    ).select_related('created_by').order_by('-sent_to_production_at')
    
    # Apply filters
    client_search = request.GET.get('client', '').strip()
    if client_search:
        projects = projects.filter(Q(client_name__icontains=client_search))
    
    created_by_search = request.GET.get('created_by', '').strip()
    if created_by_search:
        projects = projects.filter(
            Q(created_by__first_name__icontains=created_by_search) |
            Q(created_by__last_name__icontains=created_by_search) |
            Q(created_by__username__icontains=created_by_search)
        )
    
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    date_filter = request.GET.get('date_filter', 'all')
    if date_filter == 'today':
        projects = projects.filter(sent_to_production_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        projects = projects.filter(sent_to_production_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        projects = projects.filter(sent_to_production_at__date__gte=month_start)
    
    # Get date range label for title
    date_range_label = 'All Time'
    if date_filter == 'today':
        date_range_label = f'Today ({date.today().strftime("%B %d, %Y")})'
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)
        date_range_label = f'Week of {week_start.strftime("%B %d")} - {week_end.strftime("%B %d, %Y")}'
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        date_range_label = month_start.strftime('%B %Y')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Production Report - {date_range_label}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                border-bottom: 3px solid #FF9800;
                padding-bottom: 20px;
            }}
            .header h1 {{
                font-size: 28px;
                color: #FF9800;
                margin-bottom: 10px;
            }}
            .header p {{
                color: #666;
                font-size: 14px;
            }}
            .section {{
                margin-bottom: 40px;
                break-inside: avoid;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: 700;
                color: #1a1a1a;
                border-bottom: 2px solid #FF9800;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            .project-item {{
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 15px;
                background: white;
            }}
            .project-item:hover {{
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .project-header {{
                display: flex;
                justify-content: space-between;
                align-items: start;
                margin-bottom: 10px;
            }}
            .project-title {{
                font-size: 16px;
                font-weight: 700;
                color: #333;
            }}
            .project-meta {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                font-size: 13px;
                margin-bottom: 10px;
            }}
            .meta-item {{
                color: #666;
            }}
            .meta-label {{
                font-weight: 600;
                color: #333;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .badge-in_production {{
                background: #FFF3E0;
                color: #E65100;
            }}
            .badge-completed {{
                background: #E8F5E9;
                color: #1B5E20;
            }}
            .badge-ready_for_pickup {{
                background: #FCE4EC;
                color: #880E4F;
            }}
            .badge-submitted {{
                background: #E3F2FD;
                color: #1565C0;
            }}
            .specs {{
                background: #f9f9f9;
                padding: 10px;
                border-radius: 4px;
                font-size: 12px;
                margin-top: 10px;
            }}
            .specs-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
            }}
            .spec {{
                padding: 5px;
            }}
            .spec-label {{
                font-weight: 600;
                color: #333;
                font-size: 11px;
            }}
            .spec-value {{
                color: #666;
                font-size: 12px;
            }}
            .empty {{
                padding: 30px;
                text-align: center;
                color: #999;
                background: #f9f9f9;
                border-radius: 4px;
                border: 1px dashed #ddd;
            }}
            .filter-info {{
                background: #FFF3E0;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 13px;
                color: #E65100;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                color: #999;
                font-size: 12px;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #f5f5f5;
                padding: 15px;
                border-radius: 4px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: 700;
                color: #FF9800;
            }}
            .stat-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }}
            @media print {{
                body {{
                    padding: 0;
                }}
                .container {{
                    padding: 20px;
                }}
                .project-item {{
                    page-break-inside: avoid;
                }}
                .no-print {{
                    display: none !important;
                }}
            }}
            @media (max-width: 768px) {{
                .project-meta {{
                    grid-template-columns: 1fr;
                }}
                .stats {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏭 Production Report</h1>
                <p>Report Period: {date_range_label}</p>
                <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            {f'<div class="filter-info">Applied Filters: Client: {client_search or "All"} | Creator: {created_by_search or "All"} | Status: {status_filter or "All"}</div>' if (client_search or created_by_search or status_filter) else ''}
            
            <!-- Statistics -->
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{projects.filter(status="in_production").count()}</div>
                    <div class="stat-label">In Production</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{projects.filter(status="completed").count()}</div>
                    <div class="stat-label">Completed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{projects.filter(status="ready_for_pickup").count()}</div>
                    <div class="stat-label">Ready for Pickup</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{projects.count()}</div>
                    <div class="stat-label">Total Projects</div>
                </div>
            </div>
            
            <!-- Projects Section -->
            <div class="section">
                <div class="section-title">📦 Production Projects Received ({projects.count()})</div>
                {'<div>' + ''.join(f'''<div class="project-item">
                    <div class="project-header">
                        <div>
                            <div class="project-title">{p.project_title}</div>
                            <div style="font-size: 12px; color: #999; margin-top: 3px;">Order: {p.source_job_order.order_no if p.source_job_order else "N/A"}</div>
                        </div>
                        <span class="badge badge-{p.status}">{p.get_status_display()}</span>
                    </div>
                    <div class="project-meta">
                        <div class="meta-item"><span class="meta-label">👤 Client:</span> {p.client_name}</div>
                        <div class="meta-item"><span class="meta-label">👨‍💼 Created By:</span> {p.created_by.first_name or p.created_by.username}</div>
                        <div class="meta-item"><span class="meta-label">📅 Deadline:</span> {p.deadline.strftime("%b %d, %Y") if p.deadline else "N/A"}</div>
                        <div class="meta-item"><span class="meta-label">📧 Sent to Production:</span> {p.sent_to_production_at.strftime("%b %d, %Y %I:%M %p") if p.sent_to_production_at else "N/A"}</div>
                    </div>
                    <div class="specs">
                        <div class="specs-grid">
                            <div class="spec"><div class="spec-label">Copies:</div><div class="spec-value">{p.number_of_copies}</div></div>
                            <div class="spec"><div class="spec-label">Font:</div><div class="spec-value">{p.font_type or "N/A"}</div></div>
                            <div class="spec"><div class="spec-label">Paper:</div><div class="spec-value">{p.paper_type or "N/A"}</div></div>
                            <div class="spec"><div class="spec-label">Binding:</div><div class="spec-value">{p.get_binding_type_display() if p.binding_type else "None"}</div></div>
                            <div class="spec"><div class="spec-label">Color:</div><div class="spec-value">{p.get_color_requirement_display() if p.color_requirement else "N/A"}</div></div>
                        </div>
                    </div>
                    {f'<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #666;">📝 {p.project_description}</div>' if p.project_description else ''}
                </div>''' for p in projects) + '</div>' if projects else '<div class="empty">📭 No production projects found for this period</div>'}
            </div>
            
            <div class="footer">
                <p>This report was generated from the Production Management System</p>
                <p style="margin-top: 10px;"><strong>Note:</strong> Print this page using Ctrl+P or the browser Print option. Choose "Print to PDF" for digital archiving.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_content, content_type='text/html')
