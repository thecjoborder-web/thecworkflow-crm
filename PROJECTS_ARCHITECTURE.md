# Project Management System - Architecture Overview

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Django Application                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              URL Router (config/urls.py)                 │   │
│  │  /projects/supervisor/      →  project_supervisor_...   │   │
│  │  /projects/production/      →  production_dashboard     │   │
│  │  /projects/<id>/            →  project_detail           │   │
│  │  /projects/upload/          →  upload_project (AJAX)    │   │
│  │  /projects/<id>/send-to-... →  send_to_production       │   │
│  │  /projects/<id>/download/   →  download_project         │   │
│  │  /projects/<id>/update-...  →  update_project_status    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          Views (projects/views.py)                       │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ Permission Checks                               │    │   │
│  │  │ - is_project_supervisor(): group check          │    │   │
│  │  │ - is_production_staff(): group check            │    │   │
│  │  │ - sent_to_production flag check                 │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ↓                                                       │   │
│  │  Dashboard Views: Display filtered project lists        │   │
│  │  Upload View: Create new Project with file upload       │   │
│  │  Send View: Mark project for production                 │   │
│  │  Download View: Stream file with logging                │   │
│  │  Status Update View: Change project status + log        │   │
│  │  Notification Views: Get & mark notifications read      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │        Models (projects/models.py)                       │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ Project Model                                   │    │   │
│  │  │ - project_title, client_name                    │    │   │
│  │  │ - specifications (font, color, paper, binding)  │    │   │
│  │  │ - status (submitted, in_production, etc)        │    │   │
│  │  │ - sent_to_production (workflow gate)            │    │   │
│  │  │ - created_by (ForeignKey to User)               │    │   │
│  │  │ - Microsoft file (FileField)                    │    │   │
│  │  │ - Meta properties: is_overdue, days_until_...   │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ↓                                                       │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ProjectStatusLog Model (Audit Trail)            │    │   │
│  │  │ - old_status, new_status                        │    │   │
│  │  │ - changed_by (ForeignKey to User)               │    │   │
│  │  │ - notes, changed_at                             │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ↓                                                       │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ProjectDownloadLog Model (Audit Trail)          │    │   │
│  │  │ - project (ForeignKey)                          │    │   │
│  │  │ - downloaded_by (ForeignKey to User)            │    │   │
│  │  │ - downloaded_at (DateTimeField)                 │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ↓                                                       │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ProductionNotification Model (Alerts)           │    │   │
│  │  │ - notification_type (downloaded, status_...)    │    │   │
│  │  │ - recipient (ForeignKey to User)                │    │   │
│  │  │ - project (ForeignKey)                          │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          Database (SQLite / PostgreSQL)                 │   │
│  │  projects_project                                       │   │
│  │  projects_projectstatuslog                              │   │
│  │  projects_projectdownloadlog                            │   │
│  │  projects_productionnotification                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│              Frontend (Templates + JavaScript)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  project_supervisor_dashboard.html                       │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ KPI Cards (Total, Mine, Sent, In Production)     │  │   │
│  │  │ Upload Form (AJAX POST to /projects/upload/)     │  │   │
│  │  │ Projects Table (Client Filter, My Projects Filter)│  │   │
│  │  │ Send to Production Button (AJAX POST)            │  │   │
│  │  │ View Details Links (to project detail page)      │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  production_dashboard.html                               │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ KPI Cards (Available, In Prod, Complete, Ready)  │  │   │
│  │  │ Project Cards (sent_to_production=True only)     │  │   │
│  │  │ Download Button (AJAX to /projects/<id>/download)│  │   │
│  │  │ Update Status Button (Modal with AJAX POST)      │  │   │
│  │  │ View Details Links (to project detail page)      │  │   │
│  │  │ Search/Filter (Client name, Status)             │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  project_detail.html                                     │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ Project Information (title, client, dates)       │  │   │
│  │  │ Specifications Grid (all spec fields)            │  │   │
│  │  │ Timeline with Deadline Status                    │  │   │
│  │  │ File Download (if production_staff)              │  │   │
│  │  │ Status History (all status changes with notes)   │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Diagrams

### Flow 1: Project Upload & Send Workflow

```
Project Supervisor
    │
    ├─→ Fills Upload Form (client, specs, file)
    │       └─→ AJAX POST /projects/upload/
    │           (FormData with CSRF token)
    │
    ├─→ View: upload_project()
    │   ├─ Validates form data
    │   ├─ Creates Project record
    │   │   └─ status = 'submitted'
    │   │   └─ created_by = current_user
    │   │   └─ sent_to_production = False
    │   ├─ Saves file to media/projects/manuscripts/{Y}/{M}/{D}/
    │   └─ Returns JSON { success: true, project_id: X }
    │
    ├─→ Modal shows: "Project uploaded successfully"
    │       └─→ Page reloads, sees new project in table
    │
    ├─→ Clicks "Send to Production" button
    │       └─→ AJAX POST /projects/<id>/send-to-production/
    │           (JSON body with CSRF token)
    │
    ├─→ View: send_to_production()
    │   ├─ Validates user is creator
    │   ├─ Sets sent_to_production = True
    │   ├─ Records sent_to_production_at = now()
    │   ├─ Creates ProductionNotification
    │   │   └─ notification_type = 'ready_for_production'
    │   └─ Returns JSON { success: true, message: '...' }
    │
    ├─→ Button changes to "✅ Sent" (disabled)
    │
    └─→ Project is now visible to Production Staff
```

### Flow 2: Production Download & Status Update Workflow

```
Production Staff
    │
    ├─→ Accesses /projects/production/
    │       └─ View: production_dashboard()
    │           ├─ Filters Project.objects.filter(sent_to_production=True)
    │           ├─ Only sees sent projects (others hidden)
    │           └─ Returns HTML with project cards
    │
    ├─→ Clicks "Download" button
    │       └─→ GET /projects/<id>/download/
    │           (No AJAX needed, direct file stream)
    │
    ├─→ View: download_project()
    │   ├─ Permission check: is_production_staff()
    │   ├─ Permission check: sent_to_production == True
    │   ├─ Returns FileResponse (file streaming)
    │   └─ Side effect: Creates ProjectDownloadLog
    │       ├─ project_id = X
    │       ├─ downloaded_by = production_user
    │       └─ downloaded_at = now()
    │
    ├─→ File downloads to user's computer
    │
    ├─→ Clicks "Update Status" button
    │       └─→ Modal appears with status dropdown
    │
    ├─→ Selects new status (e.g., "In Production") + optional notes
    │   │
    │   └─→ AJAX POST /projects/<id>/update-status/
    │       (JSON: { status: '...', notes: '...' })
    │
    ├─→ View: update_project_status()
    │   ├─ Permission check: is_production_staff()
    │   ├─ Permission check: sent_to_production == True
    │   ├─ Updates Project.status = new_status
    │   ├─ Creates ProjectStatusLog
    │   │   ├─ old_status = previous value
    │   │   ├─ new_status = new value
    │   │   ├─ changed_by = production_user
    │   │   ├─ notes = user provided notes
    │   │   └─ created_at = now()
    │   ├─ Creates ProductionNotification
    │   │   └─ Sent to project creator (PS)
    │   └─ Returns JSON { success: true, message: '...' }
    │
    └─→ Status updates on page
        Project Supervisor gets in-app notification (ProductionNotification)
```

### Flow 3: Access Control & Workflow Restriction

```
User Access Attempt
    │
    ├─ Is user authenticated?
    │  └─ No → Redirect to login
    │
    ├─ Accessing /projects/supervisor/?
    │  └─ View: @user_passes_test(is_project_supervisor)
    │     ├─ Check: user.groups.filter(name='project_supervisor').exists()
    │     ├─ OR: user.is_staff or user.is_superuser
    │     ├─ Yes → Allow access, show all projects
    │     └─ No → 403 Forbidden
    │
    ├─ Accessing /projects/production/?
    │  └─ View: @user_passes_test(is_production_staff)
    │     ├─ Check: user.groups.filter(name='production_staff').exists()
    │     ├─ OR: user.is_staff or user.is_superuser
    │     ├─ Yes → Allow access, show only sent projects
    │     └─ No → 403 Forbidden
    │
    ├─ Production staff tries to access unsent project?
    │  └─ View: project_detail()
    │     ├─ Check: is_production_staff(user) AND NOT sent_to_production
    │     └─ Return: HTTP 403 (Access Denied)
    │
    ├─ Production staff tries to download unsent project?
    │  └─ View: download_project()
    │     ├─ Check: is_production_staff(user) AND NOT sent_to_production
    │     └─ Return: HTTP 403 (Access Denied)
    │
    ├─ Production staff tries to update status of unsent project?
    │  └─ View: update_project_status()
    │     ├─ Check: is_production_staff(user) AND NOT sent_to_production
    │     └─ Return: HTTP 403 (Access Denied)
    │
    └─ Invalid user can't bypass workflow restrictions even with direct URL
```

---

## 🗂️ File Organization

```
projects/
├── __init__.py
├── admin.py                         # ModelAdmin registrations
├── apps.py                          # App configuration
├── models.py                        # 4 Models: Project, StatusLog, DownloadLog, Notification
├── views.py                         # 11 Views with permission checks
├── urls.py                          # 7 URL patterns
├── tests.py                         # (empty, can add tests here)
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── setup_groups.py          # Management command to create groups
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py              # Initial migration (run with `migrate`)
└── templates/
    └── projects/
        ├── project_supervisor_dashboard.html    # PS Dashboard (500+ lines)
        ├── production_dashboard.html            # Production Dashboard (450+ lines)
        └── project_detail.html                  # Project Detail View (300+ lines)
```

---

## 🔐 Security Architecture

### Permission Layers

```
Layer 1: Authentication
  └─ @login_required decorator on all views
     └─ User must be logged in

Layer 2: Group-based Authorization
  └─ @user_passes_test(is_project_supervisor)
     └─ @user_passes_test(is_production_staff)
     └─ Check: user.groups.filter(name='...')

Layer 3: Workflow-based Access Control
  └─ In views, check sent_to_production flag
     └─ Production can ONLY see/download if sent_to_production=True

Layer 4: CSRF Protection
  └─ All POST requests require CSRF token
     └─ Either in form field or X-CSRFToken header
```

### Unrestricted Access
- ❌ Unknown users cannot access dashboards (401 Unauthorized)
- ❌ Authenticated users without groups cannot access dashboards (403 Forbidden)
- ❌ Production staff cannot see unsent projects (filtered in query + 403 check)
- ❌ Production staff cannot download unsent projects (403 check in view)
- ❌ Production staff cannot directly access supervisor endpoints (403 check)

---

## 💾 Database Schema Summary

### Project (24 fields)
```
Identifiers:
  - id (Primary Key, auto-increment)

Basic Information:
  - project_title (CharField, max_length=255)
  - project_description (TextField, nullable)
  - client_name (CharField, max_length=255)
  - client_contact (CharField, max_length=100, nullable)

Specifications:
  - number_of_copies (PositiveIntegerField, default=1)
  - font_type (CharField, default='Times New Roman')
  - color_requirement (CharField, choices=['b&w', 'color'])
  - paper_type (CharField, default='A4')
  - binding_type (CharField, choices=['spiral', 'perfect', 'comb', 'saddle_stitch', 'none'])
  - special_instructions (TextField, nullable)
  - budget (DecimalField, max_digits=10, decimal_places=2, nullable)

Dates:
  - project_date (DateField - when project starts)
  - deadline (DateField - when project is due)

File:
  - manuscript_file (FileField, upload_to='projects/manuscripts/%Y/%m/%d/')

Status:
  - status (CharField, choices=['submitted', 'in_production', 'quality_check', 'completed', 'ready_for_pickup', 'cancelled'])

Workflow:
  - sent_to_production (BooleanField, default=False) ← CRITICAL GATE
  - sent_to_production_at (DateTimeField, nullable)

Creator:
  - created_by (ForeignKey to User)

Timestamps:
  - created_at (DateTimeField, auto_now_add=True)
  - updated_at (DateTimeField, auto_now=True)

Computed Properties (@property):
  - is_overdue: Boolean (deadline < today())
  - days_until_deadline: Integer (deadline - today())
```

### ProjectStatusLog (Audit Trail)
```
- id (Primary Key)
- project (ForeignKey to Project)
- old_status (CharField)
- new_status (CharField)
- changed_by (ForeignKey to User)
- notes (TextField, optional)
- created_at (DateTimeField, auto_now_add=True)
```

### ProjectDownloadLog (Audit Trail)
```
- id (Primary Key)
- project (ForeignKey to Project)
- downloaded_by (ForeignKey to User)
- downloaded_at (DateTimeField, auto_now_add=True)
```

### ProductionNotification (In-app Alerts)
```
- id (Primary Key)
- project (ForeignKey to Project)
- recipient (ForeignKey to User)
- notification_type (CharField, choices=['downloaded', 'status_changed', 'production_complete'])
- message (TextField)
- is_read (BooleanField, default=False)
- created_at (DateTimeField, auto_now_add=True)
```

---

## 🚀 Deployment Considerations

### Local Development
- ✅ SQLite database
- ✅ DEBUG=True (detailed error pages)
- ✅ Media files stored in `media/` folder
- ✅ Static files served by Django dev server

### Production (Render)
- ⚠️ PostgreSQL database
- ⚠️ DEBUG=False (no error details)
- ⚠️ Media files on ephemeral filesystem (temporary storage)
  - ✅ Solution: Use AWS S3 or similar cloud storage for media files
- ✅ Static files collected with `collectstatic`
- ✅ CSRF protection enabled
- ✅ Secure cookies with SECURE=True

---

## 📊 Typical Usage Statistics

### Database Queries per User Action

| Action | Queries | Notes |
|--------|---------|-------|
| Load Supervisor Dashboard | 5-7 | Get all projects, user groups, project counts |
| Upload Project | 3-4 | Create project, check auth, create status log |
| Send to Production | 3-4 | Update project, create notification, check auth |
| Load Production Dashboard | 5-7 | Get sent projects only, user groups, project counts |
| Download File | 2-3 | Get project, create download log, stream file |
| Update Status | 4-5 | Update project, create status log, create notification |
| Load Project Detail | 2-4 | Get project, get status history, check auth |

---

## 🔧 Extension Points

### Adding Email Notifications
- Currently: In-app notifications only
- To Add: Use Django signals on ProductionNotification/ProjectStatusLog post_save
- Example: Send email when Project Supervisor gets notification

### Adding Dashboard Admin Metrics
- Query ProjectStatusLog for average time in each status
- Query ProjectDownloadLog for download frequency
- Query Project for completion rate

### Adding File Versioning
- Currently: One file per project
- To Add: Create ProjectFile model (one-to-many with Project)
- Add version tracking and history

### Adding User Roles
- Currently: 2 roles (PS, Production Staff)
- To Add: QA Department, Accounts Department, etc.
- Add new groups and permission checks in views

### Adding Notifications Dashboard Widget
- Create notification center view
- Display in base template
- Real-time updates with WebSockets (Django Channels)

---

## 🎓 Learning Resources

### Django Concepts Used
- Models (ForeignKey relationships)
- Views (@login_required, @user_passes_test)
- Templates (for loops, conditionals, static files)
- Forms (FileField, form validation)
- Admin interface (ModelAdmin)
- Migrations (schema management)
- Management commands (custom CLI tools)

### Frontend Concepts Used
- HTML5 (semantic markup)
- CSS3 (Grid, Flexbox, responsive design)
- JavaScript (AJAX, FormData, fetch API)
- CSRF tokens (security)
- Modal dialogs
- Responsive design patterns

---

**This architecture is designed to scale from local development to production deployment with minimal changes.**
