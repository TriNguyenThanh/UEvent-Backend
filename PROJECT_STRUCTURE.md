# UEvent Backend - Project Structure

## Overview

**UEvent Backend** is a Django REST Framework-based API designed for comprehensive event management. The project follows a **feature-first modular architecture**, where each app represents a distinct business domain with its own models, views, and business logic.

## Technology Stack

- **Framework:** Django 6.0.3 + Django REST Framework
- **Database:** PostgreSQL (with JSONB support)
- **Python:** 3.10+
- **API Documentation:** drf-yasg (Swagger/OpenAPI)
- **Architecture Pattern:** Feature-based modules (Microservice-ready monolith)

## Project Root Structure

```
UEvent-backend/
├── apps/                    # Django applications (feature modules)
├── common/                  # Shared utilities and base classes
├── core/                    # Django project configuration
├── Docs/                    # Documentation and diagrams
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── venv/                   # Virtual environment
```

## Core Configuration (`core/`)

```
core/
├── __init__.py
├── settings.py             # Django settings (DB, apps, middleware)
├── urls.py                 # Root URL configuration
├── asgi.py                 # ASGI entry point
└── wsgi.py                 # WSGI entry point
```

### Key Settings

- **Database:** PostgreSQL with JSONB field support
- **Timezone:** UTC (all timestamps stored in UTC)
- **Authentication:** Custom User model (`users.User`)
- **Apps Installed:** 8 feature apps + Django defaults + DRF

## Common Module (`common/`)

Shared utilities used across all apps.

```
common/
├── models.py               # BaseModel with UUID PK + soft delete
├── exceptions.py           # Custom exception handlers
├── permissions.py          # DRF permission classes
└── utils.py               # Helper functions
```

### BaseModel Features

- **Primary Key:** UUID (prevents enumeration attacks)
- **Timestamps:** `created_at`, `updated_at` (auto-managed)
- **Soft Delete:** `deleted_at` field with custom manager
- **Managers:**
  - `objects` - Returns only non-deleted records
  - `all_objects` - Returns all records including soft-deleted

## Apps Architecture (`apps/`)

### 1. Users (`apps/users/`)

**Purpose:** Identity, authentication, and access control

```
users/
├── models/
│   ├── user.py                    # Custom User (extends AbstractUser)
│   ├── role.py                    # System roles (student, organizer, admin)
│   ├── user_role.py               # User-Role mapping (many-to-many with primary flag)
│   ├── user_auth_identity.py     # Auth providers (email, Google, passkey)
│   └── user_session.py           # Session management with refresh tokens
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Key Models:**
- **User:** Extends Django's AbstractUser with `student_code`, `phone_number`, `avatar_url`
- **UserRole:** Enforces single primary role per user via constraint
- **UserAuthIdentity:** Multi-provider authentication support

**Constraints:**
- Unique `(user, role)` pair
- Single primary role per user (`is_primary=True`)

---

### 2. Locations (`apps/locations/`)

**Purpose:** Physical venue hierarchy management

```
locations/
├── models/
│   ├── campus.py                  # University campuses
│   ├── building.py                # Buildings within campus
│   └── room.py                    # Rooms/halls with capacity
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Hierarchy:** Campus → Building → Room

**Key Features:**
- Unique `(campus, code)` for buildings
- Unique `(building, code)` for rooms
- Capacity tracking at room level

---

### 3. Events (`apps/events/`)

**Purpose:** Core event lifecycle and organization

```
events/
├── models/
│   ├── event_category.py          # Event categories (music, academic, sports)
│   ├── event.py                   # Event core (title, dates, status, capacity)
│   ├── event_organizer.py         # Organizer roles (owner, co-host, staff, checkin)
│   ├── registration_form_field.py # Custom registration form builder
│   └── event_invitation.py        # Email-based invitations
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Event Status Flow:**
```
draft → pending → approved → active → finished
                     ↓
                 rejected / cancelled / archived
```

**Key Features:**
- Dynamic registration forms via JSONB
- Multi-organizer support with role hierarchy
- Deadline enforcement (`registration_close_at`, `cancellation_deadline_at`)

---

### 4. Registrations (`apps/registrations/`)

**Purpose:** Event registration, ticketing, and check-in

```
registrations/
├── models/
│   ├── event_registration.py              # User event registrations
│   ├── registration_cancellation_request.py # Cancellation workflow
│   ├── ticket.py                          # E-tickets with QR codes
│   ├── ticket_qr_token.py                 # Rotating QR tokens (15s validity)
│   └── checkin_log.py                     # Check-in audit trail
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Registration Status Flow:**
```
pending → registered → checked_in
    ↓         ↓
waitlisted  cancel_requested → cancelled
```

**Key Features:**
- **JSONB Form Answers:** Custom field responses stored as JSON
- **1-to-1 Ticket Relationship:** Each registration gets exactly one ticket
- **QR Security:** 
  - Rotating tokens every 15 seconds (prevents screenshot replay)
  - Digital signature verification
- **Race Condition Protection:** `Ticket.lock_for_checkin()` uses `select_for_update()`

**Constraints:**
- Unique `(event, user)` - One registration per user per event

---

### 5. Interactions (`apps/interactions/`)

**Purpose:** Attendee engagement (Q&A, feedback)

```
interactions/
├── models/
│   ├── event_question.py          # Q&A with moderation
│   └── event_feedback.py          # Post-event ratings/reviews
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Key Features:**
- **Question Moderation:** Status (visible, hidden, flagged)
- **Anonymous Feedback:** Optional `is_anonymous` flag
- **One Feedback Per Event:** Constraint on `(event, user)`

---

### 6. Notifications (`apps/notifications/`)

**Purpose:** Multi-channel notification system

```
notifications/
├── models/
│   ├── notification_template.py   # Reusable message templates
│   ├── notification.py            # Notification instances
│   └── notification_recipient.py  # Delivery tracking per user
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Notification Flow:**
```
queued → sent (delivered to recipients)
   ↓
failed
```

**Key Features:**
- Template-based content generation
- Per-recipient delivery tracking (`delivered_at`, `read_at`)
- Scheduled notifications support

---

### 7. Moderation (`apps/moderation/`)

**Purpose:** Content moderation and system audit logging

```
moderation/
├── models/
│   ├── moderation_log.py          # Content moderation actions
│   └── audit_log.py               # System-wide audit trail
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Moderation Actions:**
- `approve`, `reject`, `hide`, `flag`, `reopen`, `escalate`

**Audit Log:**
- Tracks all CRUD operations
- Stores metadata as JSONB
- Polymorphic resource tracking (`resource_type`, `resource_id`)

---

### 8. Support (`apps/support/`)

**Purpose:** User support ticket system

```
support/
├── models/
│   ├── support_ticket.py          # Ticket management
│   └── support_message.py         # Threaded conversations
├── admin.py
├── apps.py
├── views.py
└── tests.py
```

**Ticket Status Flow:**
```
open → in_progress → resolved → closed
```

**Key Features:**
- Priority levels (low, medium, high, urgent)
- Assignment to support staff
- Internal notes support (`is_internal` flag)

---

## Database Design

### Naming Conventions

- **Tables:** `snake_case` (e.g., `event_registrations`)
- **Foreign Keys:** Auto-generated `{field}_id` (e.g., `event_id`)
- **Constraints:** Prefixed with type:
  - `uq_` for unique constraints
  - `fk_` for foreign keys (implicit)
  - `idx_` for indexes (implicit)

### Key Relationships

```
User ──< UserRole >── Role
User ──< Event.created_by
User ──< EventOrganizer >── Event
User ──< EventRegistration >── Event
EventRegistration ─── Ticket (1-to-1)
Ticket ──< TicketQrToken
Ticket ──< CheckinLog
Event ──< EventQuestion
Event ──< EventFeedback
```

### Soft Delete Pattern

All models inherit `BaseModel` which implements:
- Logical deletion via `deleted_at` timestamp
- `delete()` sets timestamp (soft)
- `hard_delete()` permanently removes record
- `restore()` clears `deleted_at`

### JSONB Fields

Used for flexible schema storage:
- `EventRegistration.form_answers_jsonb` - Custom field responses
- `RegistrationFormField.options_json` - Field options (e.g., dropdown values)
- `AuditLog.metadata_json` - Contextual action metadata

---

## Security Features

### 1. Authentication
- Multi-provider support (email, Google OAuth, passkey)
- Session-based refresh token management
- Device tracking (`user_agent`, `ip_address`)

### 2. Authorization
- Role-based access control (RBAC)
- Event-level organizer permissions
- Primary role enforcement

### 3. QR Code Security
- Rotating tokens (15-second validity window)
- Digital signature verification
- Replay attack prevention

### 4. Audit Trail
- All moderation actions logged
- System-wide audit log with metadata
- Check-in logs (success and failure)

---

## API Design (Planned)

### Versioning
- URL-based: `/api/v1/`

### Documentation
- Auto-generated Swagger UI
- ReDoc alternative view

### Standards
- RESTful endpoints
- JSON request/response
- Pagination (10 items per page default)

---

## Development Workflow

### Running Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating Superuser

```bash
python manage.py createsuperuser
```

### Running Development Server

```bash
python manage.py runserver
```

### Running Tests

```bash
python manage.py test
```

---

## Future Roadmap

### Infrastructure
- [ ] Redis caching for event listings
- [ ] Apache Kafka for asynchronous notifications
- [ ] Celery for background tasks
- [ ] Docker containerization

### Features
- [ ] Payment integration (abstract gateway)
- [ ] Analytics dashboard
- [ ] WebSocket support for live Q&A
- [ ] Push notifications (FCM/APNs)

### Security Enhancements
- [ ] OAuth2 server for third-party integrations
- [ ] WebAuthn passkey implementation
- [ ] Rate limiting
- [ ] CORS configuration

---

## File Organization Best Practices

### Models
- **One class per file** in `models/` directory
- Filename matches class name in `snake_case`
- `__init__.py` imports all models for app-level access

### Views
- Group by resource (e.g., `EventViewSet`, `RegistrationViewSet`)
- Use DRF generic views/viewsets

### Serializers
- Create in `serializers.py` or `serializers/` module
- Nested serializers for related data

---

## Dependencies

### Core
- `django` - Web framework
- `djangorestframework` - REST API toolkit
- `psycopg2-binary` - PostgreSQL adapter

### Documentation
- `drf-yasg` - Swagger/OpenAPI generator

### Future
- `celery` - Task queue
- `redis` - Caching layer
- `gunicorn` - Production WSGI server

---

## Contact & Contribution

**Project:** UEvent Backend  
**Repository:** [GitHub](https://github.com/TriNguyenThanh/UEvent-backend-Django)  
**License:** MIT

For detailed API documentation, visit `/api/v1/swagger/` when the server is running.
