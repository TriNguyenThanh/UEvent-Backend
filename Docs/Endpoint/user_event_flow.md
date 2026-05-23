# API xem chi tiet event, dang ky, feedback, question va co-host

Prefix chung: `/api/v1/`

Nhieu endpoint tra ve theo envelope chung:

```json
{
  "success": true,
  "code": "success",
  "message": "Success.",
  "data": {},
  "errors": null,
  "meta": {}
}
```

## 1. Xem chi tiet event

### Public/user event detail

```http
GET /api/v1/events/{event_id}/
```

Endpoint cho user/public xem chi tiet event. Khong yeu cau dang nhap.

Dieu kien event duoc tra ve:

- `visibility = public`
- `status = approved` hoac `active`
- Event ton tai va khong bi an boi default manager

Response `200`:

```json
{
  "success": true,
  "code": "success",
  "message": "Success.",
  "data": {
    "id": "uuid",
    "title": "Public Detail Event",
    "slug": "public-detail-event",
    "status": "active",
    "visibility": "public",
    "category": {
      "id": "uuid",
      "name": "Workshop",
      "slug": "workshop",
      "color": "#...",
      "icon": "..."
    },
    "start_at": "2026-...",
    "end_at": "2026-...",
    "max_capacity": 100,
    "cover_image_url": "https://...",
    "created_at": "...",
    "updated_at": "...",
    "description": "Detail page content",
    "registration_open_at": "...",
    "registration_close_at": "...",
    "location_snapshot": "...",
    "deep_link": "...",
    "room": {
      "id": "uuid",
      "name": "Auditorium",
      "code": "A1",
      "building_name": "Main Building",
      "campus_name": "Main Campus"
    },
    "registration_fields": [
      {
        "id": "uuid",
        "field_key": "shirt_size",
        "label": "Shirt size",
        "field_type": "select",
        "is_required": true,
        "is_editable_after_submit": false,
        "options_json": ["S", "M", "L"],
        "sort_order": 1
      }
    ],
    "cancellation_deadline_at": "..."
  },
  "errors": null,
  "meta": {}
}
```

Neu event la `draft`, `private`, `cancelled`, khong ton tai, v.v. thi tra `404`.

### Organizer event detail

#### Danh sach event cua organizer

```http
GET /api/v1/organizer/events/
```

Endpoint cho organizer xem danh sach event ma minh co quyen quan ly.

Yeu cau dang nhap.

Dieu kien event duoc tra ve:

- User co record trong `EventOrganizer` cua event do.
- Role nam trong cac role duoc xem danh sach: `owner`, `co_host`, `staff`.
- Role `checkin` khong nam trong danh sach role duoc list event o endpoint nay.

Query params:

| Param | Type | Bat buoc | Mo ta |
|---|---|---:|---|
| `status` | string | No | Loc theo status event, vi du `draft`, `approved`, `active`, `finished`, `cancelled` |
| `category` | uuid | No | Loc theo id danh muc event |
| `visibility` | string | No | Loc theo `public` hoac `private` |
| `search` | string | No | Tim theo `title` hoac `description` |
| `ordering` | string | No | Sap xep theo `start_at`, `created_at`, `updated_at`, `status`; co the them dau `-` de sort giam dan |
| `page` | integer | No | Trang hien tai |
| `page_size` | integer | No | So item moi trang, toi da 100 |

Response `200`:

```json
{
  "success": true,
  "code": "success",
  "message": "Lay danh sach du lieu thanh cong.",
  "data": [
    {
      "id": "uuid",
      "title": "Organizer Event",
      "slug": "organizer-event",
      "status": "draft",
      "visibility": "public",
      "category": {
        "id": "uuid",
        "name": "Workshop",
        "slug": "workshop",
        "color": "#...",
        "icon": "..."
      },
      "start_at": "2026-...",
      "end_at": "2026-...",
      "max_capacity": 100,
      "cover_image_url": "https://...",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "errors": null,
  "meta": {
    "pagination": {
      "count": 1,
      "next": null,
      "previous": null,
      "page": 1,
      "page_size": 10,
      "total_pages": 1
    }
  }
}
```

#### Chi tiet event cua organizer

```http
GET /api/v1/organizer/events/{event_id}/
```

Endpoint cho organizer xem chi tiet event. Yeu cau dang nhap va user phai la organizer cua event.

Quyen truy cap:

- User la `created_by` cua event, hoac
- User co record trong `EventOrganizer` cua event.

Khac voi public event detail, endpoint nay co the xem event nhap/quan tri nhu `draft`, `private`, `cancelled`, mien la user co quyen organizer voi event do.

Response `200`:

```json
{
  "success": true,
  "code": "success",
  "message": "Success.",
  "data": {
    "id": "uuid",
    "title": "Organizer Event",
    "slug": "organizer-event",
    "status": "draft",
    "visibility": "private",
    "category": {
      "id": "uuid",
      "name": "Workshop",
      "slug": "workshop",
      "color": "#...",
      "icon": "..."
    },
    "start_at": "2026-...",
    "end_at": "2026-...",
    "max_capacity": 100,
    "cover_image_url": "https://...",
    "created_at": "...",
    "updated_at": "...",
    "description": "Noi dung chi tiet event",
    "room": {
      "id": "uuid",
      "name": "Auditorium",
      "code": "A1",
      "building_name": "Main Building",
      "campus_name": "Main Campus"
    },
    "created_by": {
      "id": "uuid",
      "username": "organizer",
      "email": "organizer@example.com",
      "full_name": "Organizer User"
    },
    "organizers": [
      {
        "id": "uuid",
        "user": {
          "id": "uuid",
          "username": "organizer",
          "email": "organizer@example.com",
          "full_name": "Organizer User"
        },
        "organizer_role": "owner",
        "joined_at": "..."
      },
      {
        "id": "uuid",
        "user": {
          "id": "uuid",
          "username": "cohost",
          "email": "cohost@example.com",
          "full_name": "Co Host"
        },
        "organizer_role": "co_host",
        "joined_at": "..."
      }
    ],
    "registration_fields": [
      {
        "id": "uuid",
        "field_key": "student_code",
        "label": "Student code",
        "field_type": "text",
        "is_required": true,
        "is_editable_after_submit": false,
        "options_json": [],
        "sort_order": 1
      }
    ],
    "registration_open_at": "...",
    "registration_close_at": "...",
    "cancellation_deadline_at": "...",
    "location_snapshot": "...",
    "deep_link": "..."
  },
  "errors": null,
  "meta": {}
}
```

Loi thuong gap:

- `401`: Chua dang nhap.
- `403`: User khong co quyen organizer voi event.
- `404`: Event khong ton tai.

#### Cap nhat event cua organizer

```http
PATCH /api/v1/organizer/events/{event_id}/
```

Organizer cap nhat cac field cua event. Yeu cau dang nhap va co quyen organizer.

Request body co the gui partial:

```json
{
  "title": "Ten event moi",
  "description": "Mo ta moi",
  "visibility": "public",
  "category": "uuid",
  "room": "uuid",
  "registration_open_at": "2026-...",
  "registration_close_at": "2026-...",
  "cancellation_deadline_at": "2026-...",
  "start_at": "2026-...",
  "end_at": "2026-...",
  "max_capacity": 100,
  "location_snapshot": "...",
  "cover_image_url": "https://...",
  "deep_link": "...",
  "status": "draft"
}
```

Response `200` tra ve format giong organizer event detail.

#### Xoa event cua organizer

```http
DELETE /api/v1/organizer/events/{event_id}/
```

Organizer soft-delete event. Yeu cau dang nhap va co quyen organizer.

Response `200`:

```json
{
  "success": true,
  "code": "deleted",
  "message": "Xoa su kien thanh cong.",
  "data": null,
  "errors": null,
  "meta": {}
}
```

## 2. Dang ky event

```http
POST /api/v1/events/{event_id}/registrations/
```

Yeu cau dang nhap.

Request body:

```json
{
  "answers": [
    {
      "fieldId": "shirt_size",
      "value": "L"
    }
  ]
}
```

`answers` la optional, dung de luu cau tra loi form dang ky vao `form_answers_jsonb`.

Dieu kien dang ky:

- Event ton tai.
- Event status phai la `approved` hoac `active`.
- Neu co `registration_open_at`, thoi diem hien tai phai sau hoac bang thoi diem mo dang ky.
- Neu co `registration_close_at`, thoi diem hien tai phai truoc hoac bang thoi diem dong dang ky.
- Event chua ket thuc.
- User chua tung dang ky event nay.
- Neu event con capacity, registration status la `registered`.
- Neu event het capacity, registration status la `waitlisted`.

Response `201`:

```json
{
  "id": "uuid",
  "status": "registered",
  "registered_at": "...",
  "cancelled_at": null,
  "cancel_reason": null,
  "answers": [
    {
      "fieldId": "shirt_size",
      "value": "L"
    }
  ],
  "event": {
    "id": "uuid",
    "title": "Event title",
    "slug": "event-title",
    "status": "active",
    "visibility": "public",
    "start_at": "...",
    "end_at": "...",
    "location_snapshot": "...",
    "cover_image_url": "..."
  },
  "user": {
    "id": "uuid",
    "username": "attendee",
    "full_name": "Attendee Name",
    "email": "attendee@example.com"
  },
  "ticket": {
    "id": "uuid",
    "ticket_code": "TK-...",
    "status": "valid",
    "issued_at": "...",
    "expires_at": "..."
  }
}
```

Neu bi waitlist thi `ticket` se la `null`.

### Cac API lien quan registration

```http
GET /api/v1/registrations/me/
```

User xem danh sach dang ky cua minh.

```http
DELETE /api/v1/events/{event_id}/registrations/me/
```

User huy dang ky cua chinh minh.

```http
GET /api/v1/events/{event_id}/registrations/
```

Organizer xem danh sach dang ky cua event.

```http
GET /api/v1/events/{event_id}/registrations/{registration_id}/
```

Organizer xem chi tiet mot registration.

```http
PATCH /api/v1/events/{event_id}/registrations/{registration_id}/cancel/
```

Organizer huy registration cua user.

Request:

```json
{
  "reason": "Capacity changed"
}
```

## 3. Quan ly feedback

### Tao feedback

```http
POST /api/v1/events/{event_id}/feedbacks/
```

User gui feedback sau su kien. Yeu cau dang nhap.

Request:

```json
{
  "rating": 5,
  "content": "Su kien rat huu ich",
  "is_anonymous": false
}
```

Co ho tro alias:

```json
{
  "rating": 5,
  "comment": "Su kien rat huu ich",
  "isAnonymous": false
}
```

Dieu kien gui feedback:

- Event phai co status `finished`.
- User phai co registration voi status `registered` hoac `checked_in`.
- Moi user chi gui feedback mot lan cho mot event.

Response:

```json
{
  "id": "uuid",
  "event": {
    "id": "uuid",
    "title": "Event title",
    "slug": "event-title",
    "status": "finished"
  },
  "user": {
    "id": "uuid",
    "username": "attendee",
    "full_name": "Attendee Name"
  },
  "rating": 5,
  "content": "Su kien rat huu ich",
  "comment": "Su kien rat huu ich",
  "is_anonymous": false,
  "isAnonymous": false,
  "created_at": "...",
  "updated_at": "..."
}
```

### Organizer feedback APIs

```http
GET /api/v1/events/{event_id}/feedbacks/
```

Organizer xem danh sach feedback.

```http
GET /api/v1/events/{event_id}/feedbacks/summary/
```

Organizer xem thong ke rating.

Response summary:

```json
{
  "event_id": "uuid",
  "total": 12,
  "average_rating": 4.5,
  "rating_counts": {
    "1": 0,
    "2": 1,
    "3": 1,
    "4": 3,
    "5": 7
  }
}
```

### Feedback detail APIs

```http
GET /api/v1/feedbacks/{feedback_id}/
PATCH /api/v1/feedbacks/{feedback_id}/
PUT /api/v1/feedbacks/{feedback_id}/
DELETE /api/v1/feedbacks/{feedback_id}/
```

Quyen sua/xoa: owner cua feedback, superuser, hoac organizer cua event.

## 4. Quan ly question

### Tao question

```http
POST /api/v1/events/{event_id}/questions/
```

User gui cau hoi cho event. Yeu cau dang nhap.

Request:

```json
{
  "question_text": "Su kien co cap certificate khong?",
  "is_anonymous": false
}
```

Response:

```json
{
  "id": "uuid",
  "event": {
    "id": "uuid",
    "title": "Event title",
    "slug": "event-title",
    "status": "active"
  },
  "user": {
    "id": "uuid",
    "username": "attendee",
    "full_name": "Attendee Name"
  },
  "question_text": "Su kien co cap certificate khong?",
  "is_anonymous": false,
  "is_pinned": false,
  "answer_text": null,
  "answered_by": null,
  "moderation_status": "visible",
  "asked_at": "...",
  "answered_at": null,
  "created_at": "...",
  "updated_at": "..."
}
```

### Question list APIs

```http
GET /api/v1/events/{event_id}/questions/
```

Organizer xem toan bo cau hoi cua event.

```http
GET /api/v1/events/{event_id}/questions/public/
```

User xem cac cau hoi public. Chi tra question co `moderation_status = visible`.

### Question detail/update APIs

```http
GET /api/v1/questions/{question_id}/
PATCH /api/v1/questions/{question_id}/
PUT /api/v1/questions/{question_id}/
DELETE /api/v1/questions/{question_id}/
```

Owner hoac organizer duoc cap nhat/xoa question.

### Organizer action APIs

```http
PATCH /api/v1/questions/{question_id}/answer/
```

Organizer tra loi cau hoi.

Request:

```json
{
  "answer_text": "Co, certificate se duoc gui sau su kien."
}
```

```http
PATCH /api/v1/questions/{question_id}/pin/
```

Organizer ghim cau hoi. Set `is_pinned = true`.

```http
PATCH /api/v1/questions/{question_id}/hide/
```

Organizer an cau hoi khoi danh sach public. Set `moderation_status = hidden`.

## 5. Them role co-host cho user

```http
POST /api/v1/organizer/events/{event_id}/registrations/{registration_id}/cohost/
```

Yeu cau dang nhap. Chi event owner duoc cap co-host.

Owner hop le la:

- User tao event, tuc `event.created_by`
- Hoac user co record `EventOrganizer` voi `organizer_role = owner`

Dieu kien:

- Registration phai thuoc event do.
- Registration khong duoc co status `cancelled` hoac `rejected`.
- User duoc cap co-host chinh la `registration.user`.
- Neu user da co role organizer trong event, he thong update role thanh `co_host`.
- Neu chua co, he thong tao moi `EventOrganizer`.

Response:

```json
{
  "id": "uuid",
  "event_id": "uuid",
  "user": {
    "id": "uuid",
    "username": "attendee",
    "full_name": "Attendee Name",
    "email": "attendee@example.com"
  },
  "organizer_role": "co_host",
  "joined_at": "..."
}
```

Luu y: hien tai chua co endpoint cap co-host truc tiep bang `user_id`. Muon cap co-host, user do phai dang ky event truoc, sau do owner dung `registration_id` de cap quyen.
