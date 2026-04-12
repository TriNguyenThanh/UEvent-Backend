---
description: UEvent Backend Antigravity Guidelines & Rules
---

# Antigravity Rules - UEvent Backend Architecture

This document contains mandatory guidelines for Antigravity (and human devs) when building or modifying the UEvent Backend project. **You MUST adhere strictly to these rules in every file you read, edit, or create.** 

## 1. Kiến trúc Feature-First (Domain-Driven)
- Thư mục gốc chứa logic phải là `apps/<tên_app>/`.
- Tuyệt đối **KHÔNG** dùng kiến trúc App hỗn hợp (Ví dụ không tạo thư mục `views/` ở root gom chung mọi App).
- File/Folder phải được đặt tên kiểu `snake_case`.

## 2. Quy tắc 3 Lớp: Views - Services - Models
*Logic nghiệp vụ nặng (Fat logic) KHÔNG ĐƯỢC đặt trong View hay Model.*

- **Views (`views.py`)**: 
  - Chỉ làm nhiệm vụ điều phối: Nhận Request -> Đưa vào Serializer Validate -> Gọi Service xử lý -> Trả về Response.
  - Sử dụng DRF `APIView`, `GenericAPIView` hoặc `ViewSet`. Không code SQL/ORM phức tạp tại đây.

- **Services (`services.py` - Tự tạo thêm ở mỗi app)**:
  - Tất cả Business Logic quan trọng (ví dụ: cấp phát vé, lock database khi check-in, rotate QR, quản lý Waitlist) đều phải đưa vào class/hàm trong file `services.py`.
  - Luôn ưu tiên dùng `transaction.atomic()` tại Service layer đối với thao tác ghi.

- **Models (`models/`)**:
  - Mỗi class một file theo chuẩn đang có. 
  - KHÔNG thay đổi schema đã được duyệt từ ERD Final mà không có approval.
  - Luôn extends từ `common.models.BaseModel` để kế thừa ID (UUID), `created_at`, `updated_at`, và tính năng Soft Delete (`deleted_at`).

## 3. Quy tắc viết API & Serializers
- Tạo file `serializers.py` cho từng app.
- Tách biệt rõ ràng **Input Serializer** (dành cho Request Validation) và **Output Serializer** (dành cho Response). 
  - Dùng tiền tố/hậu tố rõ ràng: `CreateEventInputSerializer`, `EventDetailOutputSerializer`.
- **Naming Contract**: Luôn trả về `snake_case` ở API Response (chuẩn Python + DRF). 
- Các biến alias đổi tên từ ver cũ (nếu có) phải khai báo dùng chung `source='new_field_name', read_only=True` theo tài liệu ERD alignment.

## 4. Xử lý Lỗi & Exception (Exception Handling)
- Views hoặc Services phải raise các Exception có ý nghĩa. Không return tuple `(error, status)` thủ công.
- Dùng cơ chế `custom_exception_handler` ở `common/exceptions.py`. Lỗi sẽ tự động map ra thông báo Response chuẩn hóa.

## 5. Quy định Migrations
- Migration chạy theo nguyên lý **Tịnh tiến tăng dần**. Không xóa và remake file migration lịch sử khi đã lên staging/production.
- Hạn chế để Null constraint đụng độ khi `makemigrations` trên dev env (Tuân thủ rule Add_Null -> Backfill_Data -> Set_NotNull).

## 6. Lệnh Terminal Dành Cho Antigravity
Khi được yêu cầu chạy lệnh terminal, Antigravity lưu ý:
- Lệnh Python: Phải luôn chạy thông qua virtual environment `venv/Scripts/python manage.py` (Windows OS).
- Tuyệt đối KHÔNG tự ý xóa file DB sqlite/postgres nếu user chưa approve rủi ro mất dữ liệu.

---
// Tóm tắt cho Antigravity AI Command Execute Rule:
// Bất kể khi nào user yêu cầu tạo CRUD cho một Model X, luôn tuân theo các bước:
// 1. Tạo file serializer `apps/[app]/serializers.py`
// 2. Tạo file business logic `apps/[app]/services.py` 
// 3. Tạo controller `apps/[app]/views.py` và gọi qua Service.
// 4. Tạo router `apps/[app]/urls.py` và đính kèm vào `core/urls.py`
