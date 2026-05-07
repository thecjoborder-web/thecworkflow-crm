import json
import csv
import io
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Prefetch, Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from crm_leads.models import Lead, LeadActivity, Note, JobOrder
from crm_leads.forms import JobOrderForm
from projects.models import Project, ProjectStatusLog, ProjectDownloadLog

User = get_user_model()


# --------------------------
# Admin Check
# --------------------------
def is_admin(user):
    return user.is_staff or user.is_superuser


# --------------------------
# Admin Dashboard (FULL 4-LAYER STRUCTURE)
# --------------------------
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    4-Layer Admin Dashboard:
    Layer 1: Executive Overview (KPI Cards)
    Layer 2: Agent Performance Table
    Layer 3: Lead Assignment Engine
    Layer 4: Global Lead Management
    """
    
    # ===== LAYER 1: EXECUTIVE OVERVIEW =====
    total_leads = Lead.objects.count()
    active_leads = Lead.objects.exclude(status__in=["closed", "lost"]).count()
    closed_leads = Lead.objects.filter(status="closed").count()
    lost_leads = Lead.objects.filter(status="lost").count()
    
    conversion_rate = (
        (closed_leads / total_leads) * 100
        if total_leads > 0 else 0
    )
    
    leads_added_today = Lead.objects.filter(
        created_at__date=date.today()
    ).count()
    
    activities_today = LeadActivity.objects.filter(
        created_at__date=date.today()
    ).count()
    
    # ===== LAYER 2: AGENT PERFORMANCE TABLE =====
    sales_agents = User.objects.filter(groups__name='sales_agent')
    agent_stats = []
    
    for agent in sales_agents:
        agent_leads = Lead.objects.filter(assigned_to=agent)
        assigned_count = agent_leads.count()
        active_count = agent_leads.exclude(status__in=["closed", "lost"]).count()
        awaiting_count = agent_leads.filter(status="awaiting").count()
        closed_count = agent_leads.filter(status="closed").count()
        lost_count = agent_leads.filter(status="lost").count()
        
        agent_conversion = (
            (closed_count / assigned_count) * 100
            if assigned_count > 0 else 0
        )
        
        agent_activities = LeadActivity.objects.filter(
            user=agent,
            created_at__date=date.today()
        ).count()
        
        agent_stats.append({
            'agent': agent,
            'assigned': assigned_count,
            'active': active_count,
            'awaiting': awaiting_count,
            'closed': closed_count,
            'lost': lost_count,
            'conversion_rate': round(agent_conversion, 2),
            'activities_today': agent_activities,
        })
    
    # ===== LAYER 3: LEAD ASSIGNMENT ENGINE =====
    unassigned_leads = Lead.objects.filter(assigned_to__isnull=True).order_by('-created_at')
    
    # ===== LAYER 4: GLOBAL LEAD MANAGEMENT =====
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    agent_filter = request.GET.get('agent', '')
    source_filter = request.GET.get('source', '')
    search_query = request.GET.get('search', '')
    
    # Build global leads queryset with filters
    global_leads = Lead.objects.all().order_by('-created_at')
    
    if status_filter:
        global_leads = global_leads.filter(status=status_filter)
    
    if agent_filter:
        global_leads = global_leads.filter(assigned_to__id=agent_filter)
    
    if source_filter:
        global_leads = global_leads.filter(source=source_filter)
    
    if search_query:
        global_leads = global_leads.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Get unique sources for filter dropdown
    sources = Lead.objects.values_list('source', flat=True).distinct()
    
    context = {
        # Layer 1: Executive Overview
        'total_leads': total_leads,
        'active_leads': active_leads,
        'closed_leads': closed_leads,
        'lost_leads': lost_leads,
        'conversion_rate': round(conversion_rate, 2),
        'leads_added_today': leads_added_today,
        'activities_today': activities_today,
        
        # Layer 2: Agent Performance
        'agent_stats': agent_stats,
        
        # Layer 3: Lead Assignment
        'unassigned_leads': unassigned_leads,
        'all_agents': sales_agents,
        
        # Layer 4: Global Lead Management
        'global_leads': global_leads,
        'sources': sources,
        'status_filter': status_filter,
        'agent_filter': agent_filter,
        'source_filter': source_filter,
        'search_query': search_query,
        
        # User Management
        'all_users': User.objects.filter(is_staff=False).order_by('username'),
        'sales_agent_group': Group.objects.filter(name='sales_agent').first(),
    }
    
    return render(request, 'dashboards/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def assign_lead(request):
    """
    AJAX endpoint for assigning leads to agents.
    Expects JSON: { lead_id, agent_id }
    """
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        agent_id = data.get('agent_id')
        
        if not lead_id or not agent_id:
            return JsonResponse(
                {'error': 'Missing lead_id or agent_id'},
                status=400
            )
        
        lead = get_object_or_404(Lead, id=lead_id)
        agent = get_object_or_404(User, id=agent_id)
        
        # Assign lead
        old_agent = lead.assigned_to
        lead.assigned_to = agent
        lead.status = 'assigned'
        lead.assigned_at = timezone.now()
        lead.save()
        
        # Log activity
        message = f"Lead assigned to {agent.first_name} {agent.last_name}"
        if old_agent:
            message = f"Lead reassigned from {old_agent.first_name} {old_agent.last_name} to {agent.first_name} {agent.last_name}"
        
        LeadActivity.objects.create(
            lead=lead,
            user=request.user,
            activity_type='status',
            message=message
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Lead assigned to {agent.first_name} {agent.last_name}',
            'lead_id': lead_id,
            'agent_name': f'{agent.first_name} {agent.last_name}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f'🚨 Error in assign_lead: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


# --------------------------
# CSV Import
# --------------------------
@login_required
@user_passes_test(is_admin)
@require_POST
def import_csv(request):
    """
    AJAX endpoint for importing leads from CSV.
    Expects form data with 'csv_file' field.
    CSV format: full_name, email, phone, source (optional)
    """
    try:
        if 'csv_file' not in request.FILES:
            return JsonResponse({'error': 'No CSV file provided'}, status=400)
        
        csv_file = request.FILES['csv_file']
        
        # Read CSV file
        csv_data = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        created_count = 0
        error_count = 0
        errors = []
        
        for row in csv_reader:
            try:
                full_name = row.get('full_name', '').strip()
                email = row.get('email', '').strip()
                phone = row.get('phone', '').strip()
                source = row.get('source', 'manual').strip().lower()
                
                # Validate required fields
                if not full_name or not phone:
                    error_count += 1
                    errors.append(f"Row skipped: missing name or phone")
                    continue
                
                # Validate source
                valid_sources = ['whatsapp', 'website', 'manual']
                if source not in valid_sources:
                    source = 'manual'
                
                # Check if lead already exists
                if Lead.objects.filter(phone=phone).exists():
                    error_count += 1
                    errors.append(f"Lead with phone {phone} already exists")
                    continue
                
                # Create lead
                Lead.objects.create(
                    full_name=full_name,
                    email=email if email else None,
                    phone=phone,
                    source=source,
                    status='new'
                )
                created_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing row: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'created_count': created_count,
            'error_count': error_count,
            'errors': errors[:10] if errors else []
        })
        
    except Exception as e:
        print(f'🚨 Error in import_csv: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


# --------------------------
# User Management Endpoints
# --------------------------
@login_required
@user_passes_test(is_admin)
@require_POST
def toggle_user_role(request):
    """
    AJAX endpoint to toggle sales_agent role for a user.
    Expects JSON: { user_id, action } where action is 'add' or 'remove'
    """
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        action = data.get('action')
        
        if not user_id or action not in ['add', 'remove']:
            return JsonResponse({'error': 'Invalid parameters'}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        sales_agent_group, created = Group.objects.get_or_create(name='sales_agent')
        
        if action == 'add':
            user.groups.add(sales_agent_group)
            message = f"✅ {user.username} added to sales_agent group"
        else:
            user.groups.remove(sales_agent_group)
            message = f"❌ {user.username} removed from sales_agent group"
        
        return JsonResponse({
            'success': True,
            'message': message,
            'user_id': user_id,
            'action': action
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f'🚨 Error in toggle_user_role: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


# --------------------------
# CEO Check
# --------------------------
def is_ceo(user):
    return user.groups.filter(name='ceo').exists() or user.is_superuser


@login_required
@user_passes_test(is_ceo)
def ceo_dashboard(request):
    """
    CEO Dashboard with comprehensive metrics:
    1. Real-time metrics: Total leads, Completed vs Pending, Delayed, Per-user
    2. Staff Performance: Projects per user, Completion rate, Activity frequency
    3. Activity Feed: Recent actions, Who did what
    4. Alerts: Missed deadlines, Inactive users, Bottlenecks
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # ===== 📊 REAL-TIME METRICS =====
    
    # Total Project Metrics
    total_leads = Lead.objects.count()
    completed_leads = Lead.objects.filter(status__in=['closed']).count()
    pending_leads = Lead.objects.exclude(status__in=['closed', 'lost']).count()
    lost_leads = Lead.objects.filter(status='lost').count()
    
    # Calculate completion percentage
    completion_rate = (
        (completed_leads / total_leads) * 100 if total_leads > 0 else 0
    )
    
    # Delayed projects (awaiting for more than 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    delayed_leads = Lead.objects.filter(
        status='awaiting',
        awaiting_at__lt=seven_days_ago
    ).count()

    # ===== 📂 PROJECT METRICS =====
    total_projects = Project.objects.count()
    sent_to_production_projects = Project.objects.filter(sent_to_production=True).count()
    in_production_projects = Project.objects.filter(status='in_production').count()
    completed_projects = Project.objects.filter(status='completed').count()
    ready_for_pickup_projects = Project.objects.filter(status='ready_for_pickup').count()
    latest_projects = Project.objects.order_by('-created_at')[:6]

    project_status_logs = ProjectStatusLog.objects.select_related('project', 'changed_by').order_by('-created_at')[:5]
    project_downloads = ProjectDownloadLog.objects.select_related('project', 'downloaded_by').order_by('-downloaded_at')[:5]
    project_activity_feed = []

    for log in project_status_logs:
        notes_text = log.notes or ''
        project_activity_feed.append({
            'user': log.changed_by.username if log.changed_by else 'Unknown',
            'action': '🔄 Status Change',
            'project': log.project.project_title,
            'message': notes_text[:80] + ('...' if len(notes_text) > 80 else ''),
            'time': log.created_at,
        })

    for download in project_downloads:
        project_activity_feed.append({
            'user': download.downloaded_by.username if download.downloaded_by else 'Unknown',
            'action': '📥 Download',
            'project': download.project.project_title,
            'message': f'Downloaded by {download.downloaded_by.username if download.downloaded_by else "Unknown"}',
            'time': download.downloaded_at,
        })

    project_activity_feed.sort(key=lambda item: item['time'], reverse=True)
    
    # ===== 👥 STAFF PERFORMANCE =====
    
    # Get all sales agents
    sales_agents = User.objects.filter(groups__name='sales_agent')
    
    staff_performance = []
    total_activities_all_users = 0
    
    for agent in sales_agents:
        # Leads handled by this agent
        agent_leads = Lead.objects.filter(assigned_to=agent)
        agent_completed = agent_leads.filter(status__in=['closed']).count()
        agent_total = agent_leads.count()
        agent_completion_rate = (
            (agent_completed / agent_total) * 100 if agent_total > 0 else 0
        )
        
        # Activity frequency (activities in last 7 days)
        last_week = timezone.now() - timedelta(days=7)
        agent_activities = LeadActivity.objects.filter(
            user=agent,
            created_at__gte=last_week
        ).count()
        total_activities_all_users += agent_activities
        
        # Last activity timestamp
        last_activity = LeadActivity.objects.filter(user=agent).order_by('-created_at').first()
        last_activity_time = last_activity.created_at if last_activity else None
        
        staff_performance.append({
            'agent': agent,
            'full_name': f"{agent.first_name} {agent.last_name}" if agent.first_name else agent.username,
            'leads_handled': agent_total,
            'completed': agent_completed,
            'completion_rate': round(agent_completion_rate, 1),
            'activities_7days': agent_activities,
            'last_activity': last_activity_time,
        })
    
    # ===== 🧾 ACTIVITY FEED (Recent Actions) =====
    
    recent_activities = LeadActivity.objects.select_related('user', 'lead').order_by('-created_at')[:10]
    
    activity_feed = []
    for activity in recent_activities:
        display_type = {
            'call': '☎️ Call',
            'whatsapp': '💬 WhatsApp',
            'email': '✉️ Email',
            'note': '📝 Note',
            'status': '🔄 Status Change'
        }.get(activity.activity_type, activity.activity_type)
        
        activity_feed.append({
            'user': activity.user.username if activity.user else 'Unknown',
            'action': display_type,
            'lead': activity.lead.full_name,
            'message': activity.message[:50] + ('...' if len(activity.message) > 50 else ''),
            'time': activity.created_at,
        })
    
    # ===== 🚨 ALERTS & BOTTLENECKS =====
    
    # 1. Missed Deadlines: Leads in awaiting status for more than 7 days
    alerts = []
    
    bottleneck_leads = Lead.objects.filter(
        status='awaiting',
        awaiting_at__lte=seven_days_ago
    ).select_related('assigned_to').order_by('awaiting_at')
    
    for lead in bottleneck_leads[:5]:  # Show top 5
        days_stuck = (timezone.now() - lead.awaiting_at).days
        alerts.append({
            'type': 'bottleneck',
            'icon': '⚠️',
            'title': f'Bottleneck: {lead.full_name}',
            'description': f'Stuck in awaiting for {days_stuck} days',
            'assigned_to': f"{lead.assigned_to.first_name} {lead.assigned_to.last_name}" if lead.assigned_to and lead.assigned_to.first_name else (lead.assigned_to.username if lead.assigned_to else 'Unassigned'),
        })
    
    # 2. Inactive Users: No activity in last 7 days
    for agent in sales_agents:
        last_activity_time = LeadActivity.objects.filter(user=agent).order_by('-created_at').first()
        
        if not last_activity_time or (timezone.now() - last_activity_time.created_at).days > 7:
            if last_activity_time:
                days_inactive = (timezone.now() - last_activity_time.created_at).days
            else:
                days_inactive = 999  # Never had activity
            
            alerts.append({
                'type': 'inactive',
                'icon': '😴',
                'title': f'Inactive: {agent.first_name} {agent.last_name}' if agent.first_name else f'Inactive: {agent.username}',
                'description': f'No activity for {days_inactive} days',
                'assigned_to': agent.username,
            })
    
    # ===== 📈 ADDITIONAL METRICS =====
    
    # Leads created today
    today = timezone.now().date()
    leads_created_today = Lead.objects.filter(created_at__date=today).count()
    
    # Activities today
    activities_today = LeadActivity.objects.filter(created_at__date=today).count()
    
    # Most active user (by activity count today)
    most_active_user = None
    most_active_count = 0
    for agent in sales_agents:
        today_activities = LeadActivity.objects.filter(user=agent, created_at__date=today).count()
        if today_activities > most_active_count:
            most_active_count = today_activities
            most_active_user = agent
    
    context = {
        # Real-time metrics
        'total_leads': total_leads,
        'completed_leads': completed_leads,
        'pending_leads': pending_leads,
        'lost_leads': lost_leads,
        'completion_rate': round(completion_rate, 1),
        'delayed_leads': delayed_leads,
        
        # Staff performance
        'staff_performance': staff_performance,
        'total_agents': sales_agents.count(),
        'total_activities_7days': total_activities_all_users,
        
        # Activity feed
        'activity_feed': activity_feed,
        
        # Alerts
        'alerts': alerts,
        'alert_count': len(alerts),
        
        # Today's stats
        'leads_created_today': leads_created_today,
        'activities_today': activities_today,
        'most_active_user': most_active_user,
        'most_active_count': most_active_count,
        'total_projects': total_projects,
        'sent_to_production_projects': sent_to_production_projects,
        'in_production_projects': in_production_projects,
        'completed_projects': completed_projects,
        'ready_for_pickup_projects': ready_for_pickup_projects,
        'latest_projects': latest_projects,
        'project_activity_feed': project_activity_feed,
    }
    
    return render(request, 'dashboards/ceo_dashboard.html', context)


# --------------------------
# Sales Dashboard
# --------------------------
def is_sales_agent(user):
    return user.groups.filter(name='sales_agent').exists() or user.is_superuser


@login_required
@user_passes_test(is_sales_agent)
def sales_dashboard(request):
    user = request.user

    user_leads = Lead.objects.filter(assigned_to=user)
    total_leads = user_leads.count()
    active_leads = user_leads.exclude(status__in=['closed', 'lost']).count()
    awaiting_count = user_leads.filter(status='awaiting').count()
    closed_count = user_leads.filter(status='closed').count()
    conversion_rate = (closed_count / total_leads * 100) if total_leads > 0 else 0
    activities_today = LeadActivity.objects.filter(
        user=user,
        created_at__date=date.today()
    ).count()

    date_filter = request.GET.get('date_filter', 'all')
    job_orders = JobOrder.objects.filter(created_by=user).order_by('-created_at')

    if date_filter == 'today':
        job_orders = job_orders.filter(created_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        job_orders = job_orders.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        job_orders = job_orders.filter(created_at__date__gte=month_start)

    total_job_orders = job_orders.count()
    active_job_orders = job_orders.exclude(status='closed').count()
    sent_job_orders = job_orders.filter(status='sent_to_project').count()
    closed_job_orders = job_orders.filter(status='closed').count()

    context = {
        'total_leads': total_leads,
        'active_leads': active_leads,
        'awaiting_count': awaiting_count,
        'closed_count': closed_count,
        'conversion_rate': round(conversion_rate, 1),
        'activities_today': activities_today,
        'job_orders': job_orders,
        'total_job_orders': total_job_orders,
        'active_job_orders': active_job_orders,
        'sent_job_orders': sent_job_orders,
        'closed_job_orders': closed_job_orders,
        'date_filter': date_filter,
        'assigned_leads': user_leads.filter(status='assigned'),
        'contacted_leads': user_leads.filter(status='contacted'),
        'awaiting_leads': user_leads.filter(status='awaiting'),
        'closed_leads': user_leads.filter(status='closed'),
        'lost_leads': user_leads.filter(status='lost'),
    }

    return render(request, 'dashboards/sales_dashboard.html', context)


@login_required
@user_passes_test(is_sales_agent)
def job_order_dashboard(request):
    user = request.user
    job_orders = JobOrder.objects.filter(created_by=user).order_by('-created_at')

    status_filter = request.GET.get('status', 'all')
    date_filter = request.GET.get('date_filter', 'all')

    if status_filter != 'all':
        job_orders = job_orders.filter(status=status_filter)

    if date_filter == 'today':
        job_orders = job_orders.filter(created_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        job_orders = job_orders.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        job_orders = job_orders.filter(created_at__date__gte=month_start)

    draft_orders = job_orders.filter(status='draft')
    sent_orders = job_orders.filter(status='sent_to_project')
    closed_orders = job_orders.filter(status='closed')

    context = {
        'job_orders': job_orders,
        'total_job_orders': job_orders.count(),
        'draft_orders': draft_orders.count(),
        'sent_job_orders': sent_orders.count(),
        'closed_job_orders': closed_orders.count(),
        'status_filter': status_filter,
        'date_filter': date_filter,
    }

    return render(request, 'dashboards/job_order_dashboard.html', context)


# --------------------------
# Job Order Creation
# --------------------------
@login_required
@user_passes_test(is_sales_agent)
def create_job_order(request):
    if request.method == 'POST':
        form = JobOrderForm(request.POST, request.FILES)
        if form.is_valid():
            job_order = form.save(commit=False)
            job_order.created_by = request.user
            job_order.save()
            return redirect('dashboards:job_order_detail', order_id=job_order.id)
    else:
        form = JobOrderForm()

    return render(request, 'dashboards/job_order_form.html', {
        'form': form,
    })


# --------------------------
# Job Order Detail
# --------------------------
@login_required
@user_passes_test(is_sales_agent)
def job_order_detail(request, order_id):
    job_order = get_object_or_404(JobOrder, id=order_id, created_by=request.user)
    return render(request, 'dashboards/job_order_detail.html', {
        'job_order': job_order,
    })


# --------------------------
# Print Job Order
# --------------------------
@login_required
@user_passes_test(is_sales_agent)
def print_job_order(request, order_id):
    job_order = get_object_or_404(JobOrder, id=order_id, created_by=request.user)
    return render(request, 'dashboards/job_order_print.html', {
        'job_order': job_order,
    })


# --------------------------
# Send Job Order to Project
# --------------------------
@login_required
@user_passes_test(is_sales_agent)
@require_POST
def send_job_order_to_project(request, order_id):
    job_order = get_object_or_404(JobOrder, id=order_id, created_by=request.user)

    if job_order.status == 'closed':
        return JsonResponse({'error': 'Cannot send a closed order.'}, status=400)
    if job_order.status == 'sent_to_project':
        return JsonResponse({'error': 'This order has already been sent to project.'}, status=400)

    project = Project.objects.create(
        project_title=job_order.title_description or job_order.get_product_service_display(),
        project_description=job_order.special_instructions or job_order.title_description or job_order.get_product_service_display(),
        client_name=job_order.customer_name,
        client_contact=job_order.phone or job_order.email or '',
        project_date=job_order.date or timezone.now().date(),
        deadline=job_order.expected_delivery_date or job_order.date or timezone.now().date(),
        number_of_copies=job_order.quantity,
        font_type=job_order.font_type or 'Times New Roman',
        color_requirement=job_order.color_mode or 'b&w',
        paper_type=job_order.paper_type or 'A4',
        binding_type=job_order.binding or 'perfect',
        special_instructions=job_order.special_instructions or '',
        estimated_budget=job_order.estimated_budget or 0.00,
        agreed_amount=job_order.agreed_amount or 0.00,
        part_payment=job_order.part_payment or 0.00,
        balance_due=job_order.balance_due or 0.00,
        manuscript_file=job_order.manuscript_file if job_order.manuscript_file else None,
        created_by=request.user,
        source_job_order=job_order,
        status='submitted',
    )

    ProjectStatusLog.objects.create(
        project=project,
        old_status='submitted',
        new_status='submitted',
        changed_by=request.user,
        notes='Created from sales job order'
    )

    job_order.status = 'sent_to_project'
    job_order.sent_at = timezone.now()
    job_order.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Job order successfully sent to project management.',
            'project_id': project.id,
        })

    return redirect('dashboards:job_order_detail', order_id=job_order.id)


# --------------------------
# Export Job Orders
# --------------------------
@login_required
@user_passes_test(is_sales_agent)
def export_job_orders_csv(request):
    job_orders = JobOrder.objects.filter(created_by=request.user)
    date_filter = request.GET.get('date_filter', 'all')
    if date_filter == 'today':
        job_orders = job_orders.filter(created_at__date=date.today())
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        job_orders = job_orders.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = date.today().replace(day=1)
        job_orders = job_orders.filter(created_at__date__gte=month_start)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="job_orders.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Order No',
        'Date',
        'Customer Name',
        'Phone',
        'Email',
        'Product/Service',
        'Quantity',
        'Status',
        'Agreed Amount',
        'Part Payment',
        'Balance Due',
        'Created At',
    ])

    for job in job_orders.order_by('-created_at'):
        writer.writerow([
            job.order_no,
            job.date,
            job.customer_name,
            job.phone,
            job.email,
            job.get_product_service_display(),
            job.quantity,
            job.get_status_display(),
            job.agreed_amount,
            job.part_payment,
            job.balance_due,
            job.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


# --------------------------
# Lead Action (Mark Contacted)
# --------------------------
@login_required
@require_POST
def mark_lead_contacted(request, lead_id):
    lead = get_object_or_404(
        Lead,
        id=lead_id,
        assigned_to=request.user
    )

    lead.status = "contacted"
    lead.save()

    LeadActivity.objects.create(
        lead=lead,
        activity_type="status",
        message="Lead was contacted",
        user=request.user
    )

    return JsonResponse({"success": True})


# --------------------------
# Add Note
# --------------------------
@login_required
@require_POST
def add_lead_note(request, lead_id):
    lead = get_object_or_404(
        Lead,
        id=lead_id,
        assigned_to=request.user
    )

    note_text = request.POST.get("note_text")

    if note_text:
        Note.objects.create(
            lead=lead,
            user=request.user,
            content=note_text
        )

        LeadActivity.objects.create(
            lead=lead,
            activity_type="note",
            message=note_text,
            user=request.user
        )

    return redirect("dashboards:sales_dashboard")


# --------------------------
# Log Activity (AJAX)
# --------------------------
@login_required
@user_passes_test(is_sales_agent)
@require_POST
def log_activity(request):
    """
    Handle AJAX POST requests for logging lead activities and stage progression.
    Expects JSON body with: lead_id, activity_type, message, new_stage (optional)
    
    Supports stage progression:
    - assigned -> contacted
    - contacted -> awaiting
    - awaiting -> closed or lost
    - closed/lost -> no progression
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        print(f"\n📨 Received log_activity request: {data}")

        lead_id = data.get("lead_id")
        activity_type = data.get("activity_type")
        message = data.get("message", "")
        new_stage = data.get("new_stage")  # For stage progression

        # Validate required fields
        if not lead_id or not activity_type:
            return JsonResponse(
                {"error": "Missing required fields: lead_id, activity_type"},
                status=400
            )

        # Valid activity types
        valid_types = [choice[0] for choice in LeadActivity.ACTIVITY_TYPES]
        if activity_type not in valid_types and activity_type not in ["contacted"]:
            return JsonResponse(
                {"error": f"Invalid activity type. Must be one of: {', '.join(valid_types)}"},
                status=400
            )

        # Ensure lead belongs to logged-in user
        lead = get_object_or_404(
            Lead,
            id=lead_id,
            assigned_to=request.user
        )
        print(f"✅ Lead {lead_id} found and belongs to {request.user}")

        # Handle stage progression
        if new_stage:
            valid_stages = [choice[0] for choice in Lead.STATUS_CHOICES]
            if new_stage not in valid_stages:
                return JsonResponse(
                    {"error": f"Invalid stage. Must be one of: {', '.join(valid_stages)}"},
                    status=400
                )
            
            # Enforce strict stage progression rules
            current_stage = lead.status
            allowed_transitions = {
                "assigned": ["contacted"],
                "contacted": ["awaiting"],
                "awaiting": ["closed", "lost"],
                "closed": [],  # Final state
                "lost": [],    # Final state
            }
            
            if new_stage not in allowed_transitions.get(current_stage, []):
                return JsonResponse(
                    {"error": f"Cannot move from '{current_stage}' to '{new_stage}'"},
                    status=400
                )
            
            old_stage = lead.status
            lead.status = new_stage
            lead.save()
            print(f"🔄 Stage changed: {old_stage} → {new_stage}")
            
            # Log the status change activity
            LeadActivity.objects.create(
                lead=lead,
                activity_type="status",
                message=f"Stage changed from {old_stage} to {new_stage}",
                user=request.user
            )

        # Create activity log for the action
        activity = LeadActivity.objects.create(
            lead=lead,
            activity_type=activity_type,
            message=message,
            user=request.user
        )
        print(f"✅ Activity created: {activity.id} ({activity_type})")

        return JsonResponse({"success": True, "message": "Activity logged successfully", "activity_id": activity.id})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Lead.DoesNotExist:
        print(f"❌ Lead {lead_id} not found or not assigned to {request.user}")
        return JsonResponse(
            {"error": "Lead not found or not assigned to you"},
            status=403
        )
    except Exception as e:
        print(f"🚨 Exception in log_activity: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"error": f"Server error: {str(e)}"},
            status=500
        )


# --------------------------
# Get Lead Activities (AJAX)
# --------------------------
@login_required
def get_lead_activities(request, lead_id):
    """
    Fetch all activities for a lead as JSON with optional filtering.
    Supports filter parameter: ?type=call|whatsapp|email|note|status
    """
    try:
        # Debug logging
        print(f"\n🔍 Loading activities for lead {lead_id}, user: {request.user}")
        
        lead = get_object_or_404(
            Lead,
            id=lead_id,
            assigned_to=request.user
        )

        activities = LeadActivity.objects.filter(lead=lead).order_by('-created_at')
        print(f"📋 Found {activities.count()} activities for lead {lead_id}")
        
        # Filter by activity type if provided
        filter_type = request.GET.get("type")
        if filter_type:
            valid_types = [choice[0] for choice in LeadActivity.ACTIVITY_TYPES]
            if filter_type in valid_types:
                activities = activities.filter(activity_type=filter_type)
                print(f"🔽 Filtered to {activities.count()} activities of type '{filter_type}'")

        activities_data = [
            {
                'id': activity.id,
                'activity_type': activity.activity_type,
                'message': activity.message,
                'created_by': activity.user.username if activity.user else 'Unknown',
                'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for activity in activities
        ]

        print(f"✅ Returning {len(activities_data)} activities\n")
        return JsonResponse({'activities': activities_data})
        
    except Lead.DoesNotExist:
        print(f"❌ Lead {lead_id} not found or not assigned to {request.user}\n")
        return JsonResponse(
            {'error': f'Lead not found or not assigned to you'},
            status=403
        )
    except Exception as e:
        print(f"🚨 Exception in get_lead_activities: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': f'Failed to load activities: {str(e)}'},
            status=500
        )
