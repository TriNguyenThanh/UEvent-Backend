# UEvent Database – Entity Relationship Diagram

> All entities are derived from the system description in `README.md`.

```mermaid
erDiagram

    %% ──────────────────────────────────────────
    %%  CORE ENTITIES
    %% ──────────────────────────────────────────

    USER {
        uuid        id              PK
        string      username
        string      email
        string      password_hash
        enum        role            "admin | organizer | attendee"
        boolean     is_active
        datetime    created_at
        datetime    updated_at
    }

    EVENT {
        uuid        id              PK
        uuid        organizer_id    FK
        string      title
        text        description
        string      location
        datetime    start_time
        datetime    end_time
        enum        status          "draft | published | ongoing | completed | cancelled"
        datetime    created_at
        datetime    updated_at
    }

    %% ──────────────────────────────────────────
    %%  ROLE ASSIGNMENT
    %% ──────────────────────────────────────────

    EVENT_OPERATOR {
        uuid        id              PK
        uuid        event_id        FK
        uuid        user_id         FK
        datetime    assigned_at
    }

    %% ──────────────────────────────────────────
    %%  SESSION (sub-unit of an event)
    %% ──────────────────────────────────────────

    SESSION {
        uuid        id              PK
        uuid        event_id        FK
        string      title
        text        description
        string      speaker
        datetime    start_time
        datetime    end_time
        datetime    created_at
    }

    %% ──────────────────────────────────────────
    %%  REGISTRATION / BOOKING
    %% ──────────────────────────────────────────

    REGISTRATION {
        uuid        id              PK
        uuid        event_id        FK
        uuid        attendee_id     FK
        enum        status          "pending | confirmed | cancelled"
        datetime    registered_at
        datetime    updated_at
    }

    %% ──────────────────────────────────────────
    %%  TICKET  (carries the QR code)
    %% ──────────────────────────────────────────

    TICKET {
        uuid        id              PK
        uuid        registration_id FK
        string      qr_code_data    "unique encrypted token"
        boolean     is_used
        datetime    issued_at
    }

    %% ──────────────────────────────────────────
    %%  CHECK-IN  (QR validation record)
    %% ──────────────────────────────────────────

    CHECKIN {
        uuid        id              PK
        uuid        ticket_id       FK
        uuid        operator_id     FK
        datetime    checked_in_at
    }

    %% ──────────────────────────────────────────
    %%  Q&A MODULE
    %% ──────────────────────────────────────────

    QUESTION {
        uuid        id              PK
        uuid        session_id      FK
        uuid        author_id       FK
        text        content
        integer     upvotes
        boolean     is_answered
        datetime    created_at
    }

    ANSWER {
        uuid        id              PK
        uuid        question_id     FK
        uuid        author_id       FK
        text        content
        datetime    created_at
    }

    %% ──────────────────────────────────────────
    %%  RATING & REVIEW
    %% ──────────────────────────────────────────

    REVIEW {
        uuid        id              PK
        uuid        event_id        FK
        uuid        reviewer_id     FK
        integer     rating          "1 – 5"
        text        comment
        datetime    created_at
    }

    %% ══════════════════════════════════════════
    %%  RELATIONSHIPS
    %% ══════════════════════════════════════════

    USER            ||--o{ EVENT            : "organizes"
    USER            ||--o{ EVENT_OPERATOR   : "is assigned as operator"
    EVENT           ||--o{ EVENT_OPERATOR   : "has operators"
    EVENT           ||--o{ SESSION          : "contains"
    EVENT           ||--o{ REGISTRATION     : "receives"
    USER            ||--o{ REGISTRATION     : "makes"
    REGISTRATION    ||--||  TICKET          : "generates"
    TICKET          ||--o|  CHECKIN         : "validated by"
    USER            ||--o{ CHECKIN          : "performed by operator"
    SESSION         ||--o{ QUESTION         : "has"
    USER            ||--o{ QUESTION         : "asks"
    QUESTION        ||--o{ ANSWER           : "receives"
    USER            ||--o{ ANSWER           : "provides"
    EVENT           ||--o{ REVIEW           : "receives"
    USER            ||--o{ REVIEW           : "writes"
```

---

## Entity Descriptions

| Entity | Description |
|---|---|
| **USER** | Platform account. The `role` field (`admin`, `organizer`, `attendee`) governs system-wide permissions. Per-event operator rights are managed separately via `EVENT_OPERATOR`. |
| **EVENT** | The central aggregate. Created by an organizer and progressed through a lifecycle (`draft → published → ongoing → completed`). |
| **EVENT_OPERATOR** | Join table granting a `USER` operator privileges on a specific `EVENT` (e.g. running check-in desks). |
| **SESSION** | A timed sub-unit within an `EVENT` (e.g. a talk or workshop). Hosts Q&A interactions. |
| **REGISTRATION** | An attendee's booking record for an event. A confirmed registration triggers ticket issuance. |
| **TICKET** | Holds a unique, encrypted `qr_code_data` token used for physical entry validation. |
| **CHECKIN** | Immutable audit record created when an operator scans and validates a `TICKET`. |
| **QUESTION** | A question submitted by an attendee inside a `SESSION`. Can be upvoted by peers. |
| **ANSWER** | A response to a `QUESTION`, posted by an organizer, operator, or speaker. |
| **REVIEW** | Post-event feedback submitted by an attendee, including a numeric `rating` (1–5) and optional comment. |
