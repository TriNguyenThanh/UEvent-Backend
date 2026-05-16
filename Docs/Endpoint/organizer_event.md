# Organizer Event API Contract

## Base URL
```
/api/v1/organizer/events/
```

## Authentication
All endpoints require `Authorization: Bearer <token>` header.

## Endpoints

### List Organizer Events
```
GET /api/v1/organizer/events/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by event status (draft, pending, approved, active, finished, cancelled, rejected, archived) |
| `category` | UUID | Filter by category ID |
| `visibility` | string | Filter by visibility (public, private) |
| `search` | string | Search in title and description |
| `ordering` | string | Order by: start_at, created_at, updated_at, status |
| `page` | integer | Page number |
| `page_size` | integer | Items per page (max 100) |

**Response (200 OK):**
```json
{
  "success": true,
  "code": "success",
  "message": "Lấy danh sách dữ liệu thành công.",
  "data": [
    {
      "id": "uuid",
      "title": "Event Title",
      "slug": "event-title",
      "status": "draft",
      "visibility": "public",
      "category": {
        "id": "uuid",
        "name": "Workshop",
        "slug": "workshop",
        "color": "#FF5733",
        "icon": "school"
      },
      "start_at": "2026-05-20T09:00:00Z",
      "end_at": "2026-05-20T11:00:00Z",
      "max_capacity": 50,
      "cover_image_url": "https://...",
      "created_at": "2026-05-15T10:00:00Z",
      "updated_at": "2026-05-15T10:00:00Z"
    }
  ],
  "errors": null,
  "meta": {
    "pagination": {
      "count": 10,
      "next": "/api/v1/organizer/events/?page=2",
      "previous": null,
      "page": 1,
      "page_size": 10,
      "total_pages": 1
    }
  }
}
```

---

### Create Event
```
POST /api/v1/organizer/events/
```

**Request Body:**
```json
{
  "title": "Workshop Title",
  "category": "uuid-of-category",
  "start_at": "2026-05-20T09:00:00Z",
  "end_at": "2026-05-20T11:00:00Z",
  "description": "Optional description",
  "visibility": "public",
  "room": "uuid-of-room (optional)",
  "registration_open_at": "2026-05-15T00:00:00Z (optional)",
  "registration_close_at": "2026-05-19T23:59:59Z (optional)",
  "cancellation_deadline_at": "2026-05-19T12:00:00Z (optional)",
  "max_capacity": 50 (optional),
  "location_snapshot": "Building A, Room 101 (optional)",
  "cover_image_url": "https://... (optional)",
  "deep_link": "https://... (optional)"
}
```

**Required Fields on Create:**
- `title`
- `category`
- `start_at`
- `end_at`

**Response (201 Created):**
```json
{
  "success": true,
  "code": "created",
  "message": "Tạo sự kiện thành công.",
  "data": {
    "id": "uuid",
    "title": "Workshop Title",
    "slug": "workshop-title",
    "status": "draft",
    "visibility": "public",
    "category": {...},
    "room": null,
    "description": "Optional description",
    "start_at": "2026-05-20T09:00:00Z",
    "end_at": "2026-05-20T11:00:00Z",
    "max_capacity": 50,
    "cover_image_url": "https://...",
    "created_at": "2026-05-15T10:00:00Z",
    "updated_at": "2026-05-15T10:00:00Z",
    "registration_open_at": "2026-05-15T00:00:00Z",
    "registration_close_at": "2026-05-19T23:59:59Z",
    "cancellation_deadline_at": "2026-05-19T12:00:00Z",
    "location_snapshot": "Building A, Room 101",
    "deep_link": "https://...",
    "created_by": {
      "id": "uuid",
      "username": "organizer",
      "email": "organizer@example.com",
      "full_name": "Organizer Name"
    },
    "organizers": [...],
    "registration_fields": [...]
  },
  "errors": null,
  "meta": {}
}
```

---

### Get Event Detail
```
GET /api/v1/organizer/events/{event_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "code": "success",
  "message": "Success.",
  "data": {
    "id": "uuid",
    "title": "Event Title",
    "slug": "event-title",
    "status": "draft",
    "visibility": "public",
    "category": {...},
    "description": "Full description",
    "room": {
      "id": "uuid",
      "name": "Room 101",
      "code": "R101",
      "building_name": "Building A",
      "campus_name": "Main Campus"
    },
    "created_by": {...},
    "organizers": [
      {
        "id": "uuid",
        "user": {...},
        "organizer_role": "owner",
        "joined_at": "2026-05-15T10:00:00Z"
      }
    ],
    "registration_fields": [...],
    "registration_open_at": "...",
    "registration_close_at": "...",
    "cancellation_deadline_at": "...",
    "location_snapshot": "...",
    "deep_link": "...",
    "start_at": "...",
    "end_at": "...",
    "max_capacity": 50,
    "cover_image_url": "...",
    "created_at": "...",
    "updated_at": "..."
  },
  "errors": null,
  "meta": {}
}
```

---

### Update Event
```
PATCH /api/v1/organizer/events/{event_id}/
```

**Request Body:**
All fields optional. Only provided fields will be updated.

```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "visibility": "private",
  "max_capacity": 100
}
```

**Organizer-Writable Fields:**
- `title`
- `category`
- `room`
- `description`
- `visibility`
- `registration_open_at`
- `registration_close_at`
- `cancellation_deadline_at`
- `start_at`
- `end_at`
- `max_capacity`
- `location_snapshot`
- `cover_image_url`
- `deep_link`
- `status` (only: draft, cancelled)

**Non-Writable Fields:**
- `slug`
- Admin statuses (approved, rejected, archived, pending, active, finished)

**Response (200 OK):**
```json
{
  "success": true,
  "code": "success",
  "message": "Cập nhật sự kiện thành công.",
  "data": {...},
  "errors": null,
  "meta": {}
}
```

---

### Delete Event (Soft Delete)
```
DELETE /api/v1/organizer/events/{event_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "code": "deleted",
  "message": "Xóa sự kiện thành công.",
  "data": null,
  "errors": null,
  "meta": {}
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "code": "validation_error",
  "message": "Validation error.",
  "data": null,
  "errors": {
    "title": ["This field is required."],
    "end_at": ["End time must be after start time."]
  },
  "meta": {}
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "code": "unauthorized",
  "message": "Authentication credentials were not provided.",
  "data": null,
  "errors": null,
  "meta": {}
}
```

### 403 Forbidden
```json
{
  "success": false,
  "code": "forbidden",
  "message": "You do not have organizer access to this event.",
  "data": null,
  "errors": null,
  "meta": {}
}
```

### 404 Not Found
```json
{
  "success": false,
  "code": "not_found",
  "message": "Resource not found.",
  "data": null,
  "errors": null,
  "meta": {}
}
```

---

## Validation Rules

1. **Date Constraints:**
   - `start_at` must be before `end_at`
   - `registration_open_at` must be before or equal to `registration_close_at`
   - `registration_close_at` must be before or equal to `start_at`
   - `cancellation_deadline_at` must be before or equal to `start_at`

2. **Category:**
   - Must exist
   - Must be active (is_active=true)

3. **Room:**
   - Must exist if provided

4. **Capacity:**
   - Must be positive if provided

5. **Status Transitions:**
   - Organizers can only set: `draft`, `cancelled`
   - Cannot directly set: `pending`, `active`, `finished`, `approved`, `rejected`, `archived`

---

## Notes

- Slug is auto-generated from title if not provided
- Creating an event automatically creates an OWNER EventOrganizer record for the creator
- Soft delete preserves event data (deleted_at timestamp set)
- All list/detail queries are scoped to events the user created or is an organizer of