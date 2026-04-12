# UEvent Backend - Kế Hoạch Sprint (Sprint Plan for Trello)

Cơ sở dữ liệu (Database Schema) & Models của dự án đã được đồng bộ chuẩn 100% theo ERD. Kế hoạch dưới đây hướng đến việc xây dựng toàn bộ Logic (Services), Tầng API (Serializers, Views) và Hoàn thiện hệ thống, sẵn sàng tích hợp với Frontend (Flutter/Stitch).

*Ước tính mỗi Sprint kéo dài 2 tuần. Phân nhỏ các Task để dễ quản lý trên Trello/Jira.*

---

## Sprint 1: Setup Backend & Identity - Access APIs
**Mục tiêu**: Làm sạch luồng Migration, dựng Admin UI cơ sở, và hoàn tất toàn bộ quy trình Xác thực (Auth), Quản lý tài khoản (Users) cùng vị trí (Locations) tĩnh.

### Trello Tasks
- [ ] **Task 1: Dọn dẹp Migration & Seed Data**
  - Xóa/Reset db cũ, run `makemigrations` từ đầu cho các app. Tạo script cấp sẵn dữ liệu (Fixtures) cho: `roles`, `campuses`, `buildings`, `rooms`, `event_categories`.
- [ ] **Task 2: Core Admin Dashboard**
  - Xây dựng `admin.py` cho quản trị viên Django để CRUD thủ công nhanh các Model (chuẩn bị UI test cho PO/QA).
- [ ] **Task 3: Auth Services (Xác thực)**
  - Viết API Đăng ký, Đăng nhập (Email/Password).
  - Viết luồng cấp đổi Session/Refresh token. (Bao gồm bảo vệ giới hạn tối đa 5 sessions/user).
- [ ] **Task 4: User/Profile APIs**
  - Viết API Lấy/Sửa thông tin cá nhân.
  - Viết API phân Role (xử lý logic 1 Primary Role).
- [ ] **Task 5: Location APIs (Public)**
  - Cung cấp API GET (Read-only) cho `campuses`, `buildings`, `rooms` để frontend đổ data vào Lookup Dropdown.

---

## Sprint 2: Event Core Lifecycle & Dynamic Configs
**Mục tiêu**: Xây dựng toàn bộ hệ thống quản lý Vòng đời sự kiện (Tạo, Sửa, Duyệt) và các thiết lập Custom (Form, BTC, Categories).

### Trello Tasks
- [ ] **Task 1: System Config & Event Category APIs**
  - Viết API quản trị `core.AppSetting` và `event_categories`.
- [ ] **Task 2: Event Management APIs (Quản lý sự kiện cơ bản)**
  - Xây dựng API Tạo, Sửa, Xóa sự kiện (chỉ dành cho Organizer/Admin).
  - Áp dụng Workflow chuyển status (Draft → Pending → Approved → Active).
- [ ] **Task 3: Organizer Role APIs (Phân quyền người tổ chức)**
  - Viết logic và API để Owner gán/thêm/bớt Co-host, Staff, Check-in staff vào Event.
- [ ] **Task 4: Dynamic Registration Form API (Custom Form)**
  - Viết API để Organizer định nghĩa các field đăng ký (JSON schema, Text/Option fields) cho Event đó.
- [ ] **Task 5: Private Event Invitations**
  - Viết Service + API gửi Email Lời mời. End-point chấp nhận/từ chối lời mời.

---

## Sprint 3: Đăng ký vé (Ticketing) & Check-in Anti-Fraud
**Mục tiêu**: Đóng gói luồng mua/nhận vé, Gen QRCode chống giả mạo, giải quyết bài toán Data lớn & Transaction Lock khi Check-in.

### Trello Tasks
- [ ] **Task 1: User Registration APIs**
  - Viết API User submit form tham gia (lưu Data dưới dạng JSONB). Xử lý tự động gán trạng thái `Waitlisted` nếu vượt quá `max_capacity`.
- [ ] **Task 2: Cancellation Workflow (Hủy vé)**
  - Viết API Yêu cầu hủy đăng ký (Kiểm tra deadline `cancellation_deadline_at`). Luồng duyệt hủy và Rollback Capacity/Refund.
- [ ] **Task 3: Ticket Issuing & QR Generator Service**
  - Viết Service xuất vé Điện tử, Gen `Ticket` cho user.
  - Thiết lập API Request QR Token xoay vòng 15 giây (Security layer).
- [ ] **Task 4: Check-in API (Strict Check)**
  - Viết Endpoint cho máy quét QR của Event Organizer: Verify payload/signature, kiểm tra hiệu lực thời gian. Quản lý đồng bộ tranh chấp (Database Transaction Locking `select_for_update`).
- [ ] **Task 5: Check-in Logs API**
  - Ghi Audit Logs những lần Check-in thất bại/thành công. API Dashboard cho Admin hiển thị Real-time Analytics check-in.

---

## Sprint 4: Tương tác sự kiện, Thông báo & Hỗ Trợ 
**Mục tiêu**: Hoàn thiện các tính năng sau sự kiện như Q&A, Feedback, Push Notifications, Moderation của System Admin.

### Trello Tasks
- [ ] **Task 1: Q&A Service APIs**
  - Viết API Khán giả gửi câu hỏi (ẩn danh/công khai).
  - API BTC Duyệt, đánh dấu hiển thị `visible/hidden` và trả lời câu hỏi trực tiếp.
- [ ] **Task 2: Feedback & Rating APIs**
  - Xây dựng API Review/Rating (có Constraints mỗi user 1 Feedback).
- [ ] **Task 3: Notifications Service Component**
  - Cấu hình Email Dispatcher/FCM Push Token.
  - Viết Service nội bộ để hệ thống tự bắn cảnh báo dựa vào `NotificationTemplate`.
- [ ] **Task 4: User Notification Endpoint**
  - API Load chuông thông báo (Paginated) của user từ `NotificationRecipient`. Đánh dấu `read_at`.
- [ ] **Task 5: Moderation & Support Ticket Flow**
  - Tích hợp `Event Moderation Logs`.
  - Viết hệ thống Support Ticket APIs cho User báo lỗi (Open, Reply message, Close ticket). 
- [ ] **Task 6: API Swagger/OpenAPI Finalization**
  - Format/Document lại toàn bộ chuẩn `drf-yasg` Swagger cho Frontend test. Verify lại Naming Convention (alias cũ, field mới).

---
*Ghi chú cho đội thi công:*
- Hệ thống cần bổ sung folder mô-đun `serializers/`, `views/`, `services/` tương ứng vào cấu trúc mỗi App theo từng tuần rải vụ.
- Ưu tiên Test luồng Data Model và Relation Constraints chặt chẽ ngay từ Sprint 1 & 2.
