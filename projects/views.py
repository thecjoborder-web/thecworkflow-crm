import json
from datetime import datetime
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
    
    # Filter by created_by (only my projects)
    my_projects_only = request.GET.get('my_projects') == 'on'
    if my_projects_only:
        projects = projects.filter(created_by=request.user)
    
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
        'my_projects_only': my_projects_only,
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
    
    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        projects = projects.filter(status=status_filter)
    
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
        'status_filter': status_filter,
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
        'can_download': is_production_staff(request.user) and project.sent_to_production,
    }
    
    return render(request, 'projects/project_detail.html', context)


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
        binding_type = request.POST.get('binding_type', 'perfect')
        special_instructions = request.POST.get('special_instructions', '')
        budget = request.POST.get('budget', None)
        
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
            project_date=project_date,
            deadline=deadline,
            number_of_copies=int(number_of_copies),
            font_type=font_type,
            color_requirement=color_requirement,
            paper_type=paper_type,
            binding_type=binding_type,
            special_instructions=special_instructions,
            budget=budget if budget else None,
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
@user_passes_test(is_production_staff)
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
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{project.project_title}_manuscript"'
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
