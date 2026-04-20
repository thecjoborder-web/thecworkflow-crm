# Project Management System - API Reference

## Overview
All project management endpoints are in the `projects/` app. Most operations use AJAX calls and return JSON responses.

---

## 🎯 Dashboard Endpoints

### Project Supervisor Dashboard
**URL**: `/projects/supervisor/`  
**Method**: GET  
**Permission**: User must be in `project_supervisor` group or staff  
**Query Parameters**:
- `client` (optional): Filter by client name (case-insensitive partial match)
- `my_projects` (optional): If `on`, show only projects created by current user

**Response**: HTML page with:
- KPI cards (total, mine, sent, in production)
- Upload form for new projects
- Projects table with filtering options

---

### Production Room Dashboard
**URL**: `/projects/production/`  
**Method**: GET  
**Permission**: User must be in `production_staff` group or staff  
**Query Parameters**:
- `client` (optional): Filter by client name
- `status` (optional): Filter by project status

**Response**: HTML page with:
- KPI cards (available, in production, completed, ready)
- Project cards showing sent projects only
- Status update modal

---

### Project Detail
**URL**: `/projects/<project_id>/`  
**Method**: GET  
**Permission**: 
- Project Supervisors: Can see all projects
- Production Staff: Can only see projects where `sent_to_production=True`

**Response**: HTML page showing:
- Full project information
- All specifications
- Status history/timeline
- Download option (production staff only)

---

## 📤 Create/Upload Endpoints

### Upload Project
**URL**: `/projects/upload/`  
**Method**: POST  
**Permission**: User must be in `project_supervisor` group or staff  
**Content-Type**: `multipart/form-data`

**Request Body** (form data):
```
project_title: (required) string
client_name: (required) string
client_contact: (optional) string
project_date: (required) YYYY-MM-DD
deadline: (required) YYYY-MM-DD
number_of_copies: (optional) integer, default=1
font_type: (optional) string
color_requirement: (optional) b&w or color
paper_type: (optional) string
binding_type: (optional) spiral, perfect, comb, saddle_stitch, none
budget: (optional) decimal
project_description: (optional) text
special_instructions: (optional) text
manuscript_file: (required) file upload
```

**Response** (JSON):
```json
{
    "success": true,
    "message": "Project uploaded successfully",
    "project_id": 123
}
```

**Error Response**:
```json
{
    "success": false,
    "error": "Error message here"
}
```

---

## ✈️ Workflow Endpoints

### Send Project to Production
**URL**: `/projects/<project_id>/send-to-production/`  
**Method**: POST  
**Permission**: User must be in `project_supervisor` group or staff (must be project creator)  
**Content-Type**: `application/json`

**Request Body**:
```json
{}
```

**Response** (JSON):
```json
{
    "success": true,
    "message": "Project sent to production",
    "sent_at": "2024-01-15 14:30:00"
}
```

**Behavior**:
- Sets `sent_to_production = True`
- Records timestamp in `sent_to_production_at`
- Creates notification for creator
- Production staff can now see this project

---

## ⬇️ Download Endpoints

### Download Project File
**URL**: `/projects/<project_id>/download/`  
**Method**: GET  
**Permission**: User must be in `production_staff` group or staff AND project must have `sent_to_production=True`

**Response**: File stream (binary)  
**Headers**: Sets `Content-Disposition: attachment; filename="..."`

**Side Effects**:
- Logs download in `ProjectDownloadLog`
- Creates notification for project creator
- Records timestamp and user

**Error**: HTTP 403 if not authorized

---

## 🔄 Status Update Endpoints

### Update Project Status
**URL**: `/projects/<project_id>/update-status/`  
**Method**: POST  
**Permission**: User must be in `production_staff` group or staff (only if sent_to_production=True)  
**Content-Type**: `application/json`

**Request Body**:
```json
{
    "status": "in_production",  // or: submitted, quality_check, completed, ready_for_pickup, cancelled
    "notes": "Optional status change notes"
}
```

**Response** (JSON):
```json
{
    "success": true,
    "message": "Status updated successfully",
    "old_status": "submitted",
    "new_status": "in_production"
}
```

**Behavior**:
- Updates `Project.status`
- Creates entry in `ProjectStatusLog` with old/new status, user, timestamp, notes
- Creates notification for project creator
- Visible in status history/timeline on detail page

---

## 🔔 Notification Endpoints

### Get Notifications
**URL**: `/projects/notifications/get/`  
**Method**: GET  
**Permission**: User must be logged in  
**Query Parameters**:
- `limit` (optional): Number of notifications to return, default=10
- `unread_only` (optional): If `true`, return only unread notifications

**Response** (JSON):
```json
{
    "notifications": [
        {
            "id": 1,
            "type": "downloaded",  // or: status_changed, production_complete
            "message": "Production Room downloaded your project",
            "project_id": 123,
            "is_read": false,
            "created_at": "2024-01-15 14:30:00"
        }
    ],
    "total_unread": 2
}
```

---

### Mark Notification Read
**URL**: `/projects/notifications/<notification_id>/read/`  
**Method**: POST  
**Permission**: User must be logged in (and notification belongs to them)  
**Content-Type**: `application/json`

**Request Body**:
```json
{}
```

**Response** (JSON):
```json
{
    "success": true,
    "message": "Notification marked as read"
}
```

---

## 📊 Query Status Codes

### Success Responses
- **200 OK**: Standard successful request
- **201 Created**: New resource created (rare in this API; usually returns 200)

### Error Responses
- **400 Bad Request**: Invalid form data (JSON response with error details)
- **403 Forbidden**: User doesn't have permission or workflow restriction violated
- **404 Not Found**: Project doesn't exist
- **405 Method Not Allowed**: Wrong HTTP method used

---

## 🔐 Security Features

### CSRF Protection
All POST requests require CSRF token in headers:
```javascript
headers: {
    'X-CSRFToken': csrftoken
}
```

Token can be obtained from:
1. `<input name="csrfmiddlewaretoken">` in forms
2. `document.cookie` (look for `csrftoken`)
3. Response header `X-CSRFToken` (in some cases)

### Permission Checks
All endpoints check:
1. User is authenticated (`@login_required`)
2. User is in correct group (`@user_passes_test(is_project_supervisor)` or `is_production_staff`)
3. Access control rules:
   - PS: Can see all projects, upload, send to production
   - Production: Can only see projects with `sent_to_production=True`, can download and update status
   - Admins: Full access to everything

### Workflow Restrictions
- Production can ONLY download projects if `sent_to_production=True` (enforced at view level)
- Production can ONLY update status if `sent_to_production=True`
- Only PS can send project to production

---

## 📝 Example AJAX Calls

### Example 1: Upload Project
```javascript
const formData = new FormData();
formData.append('project_title', 'New Product Brochure');
formData.append('client_name', 'Acme Corp');
formData.append('deadline', '2024-02-01');
formData.append('manuscript_file', fileInput.files[0]);

const response = await fetch('/projects/upload/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken
    },
    body: formData
});

const data = await response.json();
console.log(data.message); // "Project uploaded successfully"
```

### Example 2: Send to Production
```javascript
const response = await fetch(`/projects/123/send-to-production/`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({})
});

const data = await response.json();
console.log(data.message); // "Project sent to production"
```

### Example 3: Update Status
```javascript
const response = await fetch(`/projects/123/update-status/`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
        status: 'in_production',
        notes: 'Started printing today'
    })
});

const data = await response.json();
console.log(data.message); // "Status updated successfully"
```

### Example 4: Get Notifications
```javascript
const response = await fetch('/projects/notifications/get/?unread_only=true', {
    method: 'GET'
});

const data = await response.json();
console.log(data.total_unread); // Number of unread notifications
data.notifications.forEach(n => console.log(n.message));
```

---

## 🐛 Debugging Tips

### Check if migration ran
```bash
python manage.py showmigrations projects
# Should show: [X] 0001_initial
```

### Check if groups exist
```bash
python manage.py shell
>>> from django.contrib.auth.models import Group
>>> Group.objects.filter(name__in=['project_supervisor', 'production_staff']).values_list('name')
```

### Check user's groups
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='admin')
>>> list(user.groups.values_list('name', flat=True))
```

### Check uploaded files
```bash
# Navigate to: media/projects/manuscripts/
# Files are organized by date: YYYY/MM/DD/
```

### View database directly
```python
# For SQLite:
python manage.py shell
>>> from projects.models import Project
>>> Project.objects.all().values('project_title', 'client_name', 'status')
```

---

## 🔄 Typical User Flows

### Project Supervisor Workflow
1. Login
2. Go to `/projects/supervisor/`
3. Fill upload form
4. Submit (POST to `/projects/upload/`)
5. See project in table
6. Click "Send" (POST to `/projects/<id>/send-to-production/`)
7. Project now visible to production staff

### Production Staff Workflow
1. Login
2. Go to `/projects/production/`
3. See only projects with `sent_to_production=True`
4. Click "Download" (GET from `/projects/<id>/download/`)
5. Click "Update Status" (POST to `/projects/<id>/update-status/`)
6. Project Supervisor gets notification

### Both Roles
- Can see project details at `/projects/<id>/`
- Can view status history
- Can search by client name

---

## 📚 Related Files

- **Models Definition**: `projects/models.py`
- **Views Implementation**: `projects/views.py`
- **Templates**: `projects/templates/projects/`
- **URL Routing**: `projects/urls.py`
- **Permission Functions**: `projects/views.py` (top of file)
