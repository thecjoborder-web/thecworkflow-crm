import json
import csv
import io
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Prefetch, Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from crm_leads.models import Lead, LeadActivity, Note

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
    total_leads = Lead.objects.count()
    assigned_leads = Lead.objects.exclude(assigned_to=None).count()
    unassigned_leads = Lead.objects.filter(assigned_to=None).count()

    context = {
        'total_leads': total_leads,
        'assigned_leads': assigned_leads,
        'unassigned_leads': unassigned_leads,
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
    """
    Sales dashboard with pipeline stages, KPI metrics, and activity tracking.
    """
    user = request.user
    
    # Get all leads assigned to this user
    leads = Lead.objects.filter(assigned_to=user)
    
    # Filter leads by status (pipeline stages)
    assigned_leads = leads.filter(status="assigned")
    contacted_leads = leads.filter(status="contacted")
    awaiting_leads = leads.filter(status="awaiting")
    closed_leads = leads.filter(status="closed")
    lost_leads = leads.filter(status="lost")
    
    # KPI Metrics
    total_leads = leads.count()
    active_leads = leads.exclude(status__in=["closed", "lost"]).count()
    awaiting_count = awaiting_leads.count()
    closed_count = closed_leads.count()
    
    # Conversion rate calculation
    conversion_rate = (
        (closed_count / total_leads) * 100
        if total_leads > 0 else 0
    )
    
    # Daily activity tracking
    activities_today = LeadActivity.objects.filter(
        user=user,
        created_at__date=date.today()
    ).count()
    
    # Activity filtering (optional filter_type parameter)
    filter_type = request.GET.get("type")
    all_activities = LeadActivity.objects.filter(user=user).order_by('-created_at')
    if filter_type:
        all_activities = all_activities.filter(activity_type=filter_type)
    
    context = {
        # Pipeline stages
        "assigned_leads": assigned_leads,
        "contacted_leads": contacted_leads,
        "awaiting_leads": awaiting_leads,
        "closed_leads": closed_leads,
        "lost_leads": lost_leads,
        
        # KPI metrics
        "total_leads": total_leads,
        "active_leads": active_leads,
        "awaiting_count": awaiting_count,
        "closed_count": closed_count,
        "conversion_rate": round(conversion_rate, 2),
        "activities_today": activities_today,
        
        # All activities for filtering
        "activities": all_activities,
        "selected_filter": filter_type or "",
    }
    
    return render(request, "dashboards/sales_dashboard.html", context)


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
