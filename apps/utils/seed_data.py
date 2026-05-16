SEED_PASSWORD = "password123"

SEED_ROLES = [
    {
        "code": "STUDENT",
        "name": "Sinh viên / Người tham gia",
        "description": "Người dùng sinh viên, có thể khám phá và đăng ký tham gia sự kiện.",
    },
    {
        "code": "ORGANIZER",
        "name": "Người tổ chức / Ban tổ chức",
        "description": "Người tổ chức sự kiện, có quyền tạo và quản lý sự kiện được phân công.",
    },
    {
        "code": "ADMIN",
        "name": "Quản trị viên hệ thống",
        "description": "Quản trị viên hệ thống, có quyền quản lý người dùng và kiểm duyệt sự kiện.",
    },
]
SEED_ROLE_CODES = [item["code"] for item in SEED_ROLES]
LEGACY_SEED_ROLE_CODES = ["student", "organizer", "admin", "faculty_admin", "system_admin"]

SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@utc2.edu.vn",
        "full_name": "UTC2 System Admin",
        "role": "ADMIN",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "organizer",
        "email": "organizer@utc2.edu.vn",
        "full_name": "Ban To Chuc UTC2",
        "role": "ORGANIZER",
        "faculty": "Phong Cong tac Sinh vien",
    },
    {
        "username": "student01",
        "email": "2251050001@st.utc2.edu.vn",
        "full_name": "Nguyen Van An",
        "role": "STUDENT",
        "student_code": "2251050001",
        "faculty": "Cong nghe Thong tin",
        "class_name": "22DTHA1",
    },
    {
        "username": "student02",
        "email": "2251050002@st.utc2.edu.vn",
        "full_name": "Tran Thi Binh",
        "role": "STUDENT",
        "student_code": "2251050002",
        "faculty": "Kinh te Van tai",
        "class_name": "22DKTA1",
    },
    {
        "username": "student03",
        "email": "2251050003@st.utc2.edu.vn",
        "full_name": "Le Minh Chau",
        "role": "STUDENT",
        "student_code": "2251050003",
        "faculty": "Xay dung Cau duong",
        "class_name": "22DCDA1",
    },
]

SEED_CATEGORIES = [
    {
        "name": "Hoc thuat",
        "slug": "hoc-thuat",
        "description": "Hoi thao, workshop va cac hoat dong hoc thuat tai UTC2.",
        "icon": "graduation-cap",
        "color": "#2563EB",
    },
    {
        "name": "Am nhac",
        "slug": "am-nhac",
        "description": "Su kien van nghe, giao luu am nhac va cau lac bo nghe thuat.",
        "icon": "music",
        "color": "#16A34A",
    },
    {
        "name": "The thao",
        "slug": "the-thao",
        "description": "Giai dau va hoat dong ren luyen suc khoe cho sinh vien.",
        "icon": "trophy",
        "color": "#F97316",
    },
]

SEED_LOCATIONS = [
    {
        "campus": {
            "name": "UTC2 Campus",
            "code": "UTC2",
            "address": "450-451 Le Van Viet, Tang Nhon Phu A, TP Thu Duc, TP HCM",
        },
        "buildings": [
            {
                "name": "Khu A",
                "code": "A",
                "rooms": [
                    {"name": "Hoi truong A", "code": "A-HALL", "capacity": 300},
                    {"name": "Phong hoc A202", "code": "A202", "capacity": 60},
                ],
            },
            {
                "name": "Khu B",
                "code": "B",
                "rooms": [{"name": "San the thao", "code": "B-SPORT", "capacity": 500}],
            },
        ],
    }
]

SEED_EVENTS = [
    {
        "title": "Workshop AI va Dinh huong Nghe nghiep",
        "slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "category_slug": "hoc-thuat",
        "room_code": "A202",
        "description": "Workshop danh cho sinh vien UTC2 ve ung dung AI va lo trinh nghe nghiep.",
        "status": "approved",
        "starts_in_days": 7,
        "duration_hours": 3,
        "max_capacity": 2,
        "fields": [
            {
                "field_key": "skill_level",
                "label": "Muc do kinh nghiem",
                "field_type": "select",
                "is_required": True,
                "options_json": ["Moi bat dau", "Da co kien thuc co ban", "Da tung lam du an"],
                "sort_order": 1,
            },
            {
                "field_key": "expectation",
                "label": "Mong doi khi tham gia",
                "field_type": "text",
                "is_required": False,
                "sort_order": 2,
            },
        ],
    },
    {
        "title": "Dem nhac Chao Tan Sinh vien UTC2",
        "slug": "dem-nhac-chao-tan-sinh-vien-utc2",
        "category_slug": "am-nhac",
        "room_code": "A-HALL",
        "description": "Chuong trinh giao luu am nhac va ket noi cau lac bo UTC2.",
        "status": "active",
        "starts_in_days": 14,
        "duration_hours": 2,
        "max_capacity": 300,
        "fields": [],
    },
    {
        "title": "Giai Bong da Sinh vien UTC2",
        "slug": "giai-bong-da-sinh-vien-utc2",
        "category_slug": "the-thao",
        "room_code": "B-SPORT",
        "description": "Giai dau bong da noi bo danh cho cac lop va cau lac bo sinh vien UTC2.",
        "status": "draft",
        "starts_in_days": 21,
        "duration_hours": 4,
        "max_capacity": 500,
        "fields": [],
    },
]

SEED_REGISTRATIONS = [
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student01",
        "status": "registered",
        "answers": {
            "skill_level": "Da co kien thuc co ban",
            "expectation": "Muon hieu cach ung dung AI vao do an",
        },
    },
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student02",
        "status": "registered",
        "answers": {
            "skill_level": "Moi bat dau",
            "expectation": "Tim hieu tong quan ve AI",
        },
    },
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student03",
        "status": "waitlisted",
        "answers": {
            "skill_level": "Da tung lam du an",
            "expectation": "Muon gap mentor va trao doi y tuong",
        },
    },
    {
        "event_slug": "dem-nhac-chao-tan-sinh-vien-utc2",
        "username": "student01",
        "status": "registered",
        "answers": {},
    },
]

SEED_EVENT_INVITATIONS = [
    {
        "event_slug": "dem-nhac-chao-tan-sinh-vien-utc2",
        "email": "2251050002@student.utc2.edu.vn",
        "invited_username": "student02",
        "inviter_username": "organizer",
        "token": "seed-invite-dem-nhac-student02",
        "invite_channel": "email",
        "status": "pending",
    },
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "email": "2251050003@student.utc2.edu.vn",
        "invited_username": "student03",
        "inviter_username": "organizer",
        "token": "seed-invite-ai-student03",
        "invite_channel": "email",
        "status": "accepted",
    },
]

SEED_CANCELLATION_REQUESTS = [
    {
        "event_slug": "dem-nhac-chao-tan-sinh-vien-utc2",
        "username": "student01",
        "reason": "Trung lich hoc buoi toi.",
        "status": "pending",
    }
]

SEED_CHECKIN_LOGS = [
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student01",
        "scanner_username": "organizer",
        "result": "success",
        "note": "Seed check-in thanh cong cho workshop AI.",
        "mark_ticket_used": True,
    },
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student02",
        "scanner_username": "organizer",
        "result": "already_checked_in",
        "note": "Seed log minh hoa ve truong hop da check-in.",
        "mark_ticket_used": False,
    },
]

SEED_QUESTIONS = [
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student01",
        "question_text": "Sinh vien nam nhat co can chuan bi kien thuc lap trinh truoc khong?",
        "is_anonymous": False,
        "is_pinned": True,
        "answer_text": "Ban chi can mang laptop, BTC se huong dan tu phan co ban.",
        "answered_by_username": "organizer",
        "moderation_status": "visible",
    },
    {
        "event_slug": "dem-nhac-chao-tan-sinh-vien-utc2",
        "username": "student02",
        "question_text": "Sinh vien co the dang ky bieu dien theo nhom khong?",
        "is_anonymous": True,
        "is_pinned": False,
        "answer_text": "",
        "answered_by_username": None,
        "moderation_status": "visible",
    },
]

SEED_FEEDBACKS = [
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student01",
        "rating": 5,
        "content": "Noi dung thuc te va phu hop voi sinh vien UTC2.",
        "is_anonymous": False,
    },
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "username": "student02",
        "rating": 4,
        "content": "Muon co them thoi gian thuc hanh o phan demo.",
        "is_anonymous": True,
    },
]

SEED_NOTIFICATION_TEMPLATES = [
    {
        "code": "EVENT_REMINDER",
        "name": "Nhac lich su kien",
        "title_template": "Sap dien ra: {event_title}",
        "message_template": "Su kien {event_title} se bat dau luc {start_at}.",
        "channel": "in_app",
    },
    {
        "code": "REGISTRATION_CONFIRMED",
        "name": "Xac nhan dang ky",
        "title_template": "Dang ky thanh cong",
        "message_template": "Ban da dang ky thanh cong su kien {event_title}.",
        "channel": "in_app",
    },
]

SEED_NOTIFICATIONS = [
    {
        "title": "Nhac lich Workshop AI",
        "message": "Workshop AI va Dinh huong Nghe nghiep se dien ra trong 7 ngay toi.",
        "template_code": "EVENT_REMINDER",
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "created_by_username": "organizer",
        "type": "reminder",
        "audience_type": "students",
        "status": "sent",
        "recipient_usernames": ["student01", "student02", "student03"],
        "read_by_usernames": ["student01"],
    },
    {
        "title": "Thong bao mo dang ky Dem nhac",
        "message": "Dem nhac Chao Tan Sinh vien UTC2 da mo dang ky cho sinh vien.",
        "template_code": None,
        "event_slug": "dem-nhac-chao-tan-sinh-vien-utc2",
        "created_by_username": "admin",
        "type": "announcement",
        "audience_type": "all",
        "status": "sent",
        "recipient_usernames": ["organizer", "student01", "student02"],
        "read_by_usernames": ["organizer"],
    },
]

SEED_SUPPORT_TICKETS = [
    {
        "subject": "Khong thay ve QR sau khi dang ky",
        "username": "student02",
        "assigned_to_username": "admin",
        "category": "technical",
        "description": "Sinh vien da dang ky workshop nhung muon duoc huong dan cach xem ve QR.",
        "status": "in_progress",
        "priority": "medium",
        "messages": [
            {
                "author_username": "student02",
                "content": "Em da dang ky nhung chua biet xem ve QR o dau.",
                "is_staff": False,
            },
            {
                "author_username": "admin",
                "content": "Em vao muc Ve cua toi de xem ma QR cua su kien da dang ky.",
                "is_staff": True,
            },
        ],
    }
]

SEED_MODERATION_LOGS = [
    {
        "event_slug": "workshop-ai-dinh-huong-nghe-nghiep",
        "admin_username": "admin",
        "action": "approve",
        "report_type": "event_review",
        "reason": "Noi dung phu hop voi quy dinh to chuc su kien UTC2.",
    },
    {
        "event_slug": "giai-bong-da-sinh-vien-utc2",
        "admin_username": "admin",
        "action": "request_revision",
        "report_type": "event_review",
        "reason": "Can bo sung ke hoach y te va an toan san bai truoc khi duyet.",
    },
]

SEED_APP_SETTINGS = [
    {
        "key": "allowed_email_domains",
        "value": '["utc2.edu.vn", "student.utc2.edu.vn"]',
        "description": "Danh sach domain email duoc phep dang ky tai he thong UEvent UTC2.",
        "updated_by_username": "admin",
    },
    {
        "key": "require_admin_approval",
        "value": "true",
        "description": "Bat buoc admin duyet su kien truoc khi cong khai.",
        "updated_by_username": "admin",
    },
    {
        "key": "cancel_registration_before_hours",
        "value": "24",
        "description": "So gio toi thieu truoc su kien de sinh vien duoc huy dang ky.",
        "updated_by_username": "admin",
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
SEED_INVITATION_TOKENS = [item["token"] for item in SEED_EVENT_INVITATIONS]
SEED_NOTIFICATION_TEMPLATE_CODES = [item["code"] for item in SEED_NOTIFICATION_TEMPLATES]
SEED_NOTIFICATION_TITLES = [item["title"] for item in SEED_NOTIFICATIONS]
SEED_SUPPORT_TICKET_SUBJECTS = [item["subject"] for item in SEED_SUPPORT_TICKETS]
SEED_APP_SETTING_KEYS = [item["key"] for item in SEED_APP_SETTINGS]
