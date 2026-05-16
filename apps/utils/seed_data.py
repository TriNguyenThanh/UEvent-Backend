SEED_PASSWORD = "password123"

SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@uevents.local",
        "full_name": "System Admin",
        "role": "system_admin",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "organizer",
        "email": "organizer@uevents.local",
        "full_name": "Event Organizer",
        "role": "organizer",
        "faculty": "Information Technology",
    },
    {
        "username": "student01",
        "email": "student01@uevents.local",
        "full_name": "Nguyen Van An",
        "role": "student",
        "student_code": "SEED001",
        "faculty": "Information Technology",
        "class_name": "SE18A",
    },
    {
        "username": "student02",
        "email": "student02@uevents.local",
        "full_name": "Tran Thi Binh",
        "role": "student",
        "student_code": "SEED002",
        "faculty": "Business Administration",
        "class_name": "BA18B",
    },
    {
        "username": "student03",
        "email": "student03@uevents.local",
        "full_name": "Le Minh Chau",
        "role": "student",
        "student_code": "SEED003",
        "faculty": "Graphic Design",
        "class_name": "GD18C",
    },
]

SEED_CATEGORIES = [
    {
        "name": "Workshop",
        "slug": "workshop",
        "description": "Hands-on sessions and skill-building events.",
        "icon": "briefcase",
        "color": "#2563EB",
    },
    {
        "name": "Seminar",
        "slug": "seminar",
        "description": "Talks, panels, and academic sharing sessions.",
        "icon": "presentation",
        "color": "#16A34A",
    },
    {
        "name": "Club Activity",
        "slug": "club-activity",
        "description": "Student club activities and community events.",
        "icon": "users",
        "color": "#F97316",
    },
]

SEED_LOCATIONS = [
    {
        "campus": {"name": "Main Campus", "code": "MAIN", "address": "123 University Street"},
        "buildings": [
            {
                "name": "Innovation Hall",
                "code": "INNO",
                "rooms": [
                    {"name": "Auditorium A", "code": "A101", "capacity": 150},
                    {"name": "Workshop Lab", "code": "A202", "capacity": 45},
                ],
            },
            {
                "name": "Learning Center",
                "code": "LC",
                "rooms": [{"name": "Seminar Room", "code": "S301", "capacity": 80}],
            },
        ],
    }
]

SEED_EVENTS = [
    {
        "title": "AI Career Workshop",
        "slug": "ai-career-workshop",
        "category_slug": "workshop",
        "room_code": "A202",
        "description": "Explore AI career paths and practice with real project scenarios.",
        "status": "approved",
        "starts_in_days": 7,
        "duration_hours": 3,
        "max_capacity": 2,
        "fields": [
            {
                "field_key": "skill_level",
                "label": "Skill level",
                "field_type": "select",
                "is_required": True,
                "options_json": ["Beginner", "Intermediate", "Advanced"],
                "sort_order": 1,
            },
            {
                "field_key": "expectation",
                "label": "Expectation",
                "field_type": "text",
                "is_required": False,
                "sort_order": 2,
            },
        ],
    },
    {
        "title": "Startup Seminar 2026",
        "slug": "startup-seminar-2026",
        "category_slug": "seminar",
        "room_code": "S301",
        "description": "Founders and mentors share practical startup lessons.",
        "status": "active",
        "starts_in_days": 14,
        "duration_hours": 2,
        "max_capacity": 80,
        "fields": [],
    },
    {
        "title": "Design Club Meetup",
        "slug": "design-club-meetup",
        "category_slug": "club-activity",
        "room_code": "A101",
        "description": "A casual meetup for portfolio reviews and creative networking.",
        "status": "draft",
        "starts_in_days": 21,
        "duration_hours": 2,
        "max_capacity": 120,
        "fields": [],
    },
]

SEED_REGISTRATIONS = [
    {
        "event_slug": "ai-career-workshop",
        "username": "student01",
        "status": "registered",
        "answers": {"skill_level": "Intermediate", "expectation": "Build a demo"},
    },
    {
        "event_slug": "ai-career-workshop",
        "username": "student02",
        "status": "registered",
        "answers": {"skill_level": "Beginner", "expectation": "Learn AI basics"},
    },
    {
        "event_slug": "ai-career-workshop",
        "username": "student03",
        "status": "waitlisted",
        "answers": {"skill_level": "Advanced", "expectation": "Meet mentors"},
    },
    {
        "event_slug": "startup-seminar-2026",
        "username": "student01",
        "status": "registered",
        "answers": {},
    },
]

SEED_EVENT_SLUGS = [item["slug"] for item in SEED_EVENTS]
SEED_CATEGORY_SLUGS = [item["slug"] for item in SEED_CATEGORIES]
SEED_USERNAMES = [item["username"] for item in SEED_USERS]
SEED_CAMPUS_CODES = [item["campus"]["code"] for item in SEED_LOCATIONS]
SEED_BUILDING_CODES = [
    building["code"]
    for location in SEED_LOCATIONS
    for building in location["buildings"]
]
SEED_ROOM_CODES = [
    room["code"]
    for location in SEED_LOCATIONS
    for building in location["buildings"]
    for room in building["rooms"]
]
