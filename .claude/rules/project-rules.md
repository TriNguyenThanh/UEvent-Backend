---
description: UEvent Backend Guidelines & Rules
---

# UEvent Backend Architecture Rules

This document contains mandatory guidelines for agents and developers when building or modifying the UEvent Backend project. **You MUST adhere strictly to these rules in every file you read, edit, or create.** 

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

### 3.1. Quy tắc API Response Envelope dùng chung
- Tất cả JSON API response mới hoặc API admin được chỉnh sửa phải dùng envelope chung:
  - Success: `{ "success": true, "code": "success", "message": "...", "data": ..., "errors": null, "meta": {...} }`
  - Error: `{ "success": false, "code": "validation_error", "message": "...", "data": null, "errors": ..., "meta": {...} }`
- View không được trả trực tiếp `Response(serializer.data)` hoặc tự build dict response thủ công. Phải dùng helper trong `common.responses`:
  - `success_response(data=..., message="...")` cho response thành công.
  - `created_response(data=..., message="...")` cho tạo mới.
  - `deleted_response(message="...")` cho xóa mềm/xóa thành công.
  - `error_response(...)` chỉ dùng khi thật sự cần trả lỗi thủ công; ưu tiên raise exception để `custom_exception_handler` xử lý.
- Mọi response success trong View phải ghi rõ `message` theo từng hành động, bằng tiếng Việt có dấu, ngắn gọn và an toàn để hiển thị cho client. Không dựa vào message mặc định nếu View đã biết ngữ cảnh nghiệp vụ.
- Mọi mã response/error phải dùng `common.response_codes.ResponseCode`; không hardcode string code như `"validation_error"`, `"unauthorized"`, `"invalid_credentials"` trong View/Service/Middleware.
- Pagination list endpoint phải dùng pagination envelope chung từ `common.pagination.EnvelopePageNumberPagination` hoặc class feature kế thừa nó. Dữ liệu list nằm trong `data`, pagination nằm trong `meta.pagination`.
- Swagger/ReDoc serializer cho response envelope phải dùng serializer dùng chung trong `common.serializers` hoặc serializer feature kế thừa chúng; không mô tả schema lỗi cũ `{code, message, details, request_id}`.
- `request_id` phải nằm trong `meta.request_id`; không trả `request_id` ở top-level.

## 4. Xử lý Lỗi & Exception (Exception Handling)
- Views hoặc Services phải raise các Exception có ý nghĩa. Không return tuple `(error, status)` thủ công.
- Dùng cơ chế `custom_exception_handler` ở `common/exceptions.py`. Lỗi sẽ tự động map ra thông báo Response chuẩn hóa.

## 5. Quy định Migrations
- Migration chạy theo nguyên lý **Tịnh tiến tăng dần**. Không xóa và remake file migration lịch sử khi đã lên staging/production.
- Hạn chế để Null constraint đụng độ khi `makemigrations` trên dev env (Tuân thủ rule Add_Null -> Backfill_Data -> Set_NotNull).

## 6. Lệnh Terminal
Khi được yêu cầu chạy lệnh terminal, agent cần lưu ý:
- Lệnh Python: Phải luôn chạy thông qua virtual environment `venv/Scripts/python manage.py` (Windows OS).
- Tuyệt đối KHÔNG tự ý xóa file DB sqlite/postgres nếu user chưa approve rủi ro mất dữ liệu.

---
// Tóm tắt quy tắc thực thi lệnh/tạo CRUD:
// Bất kể khi nào user yêu cầu tạo CRUD cho một Model X, luôn tuân theo các bước:
// 1. Tạo file serializer `apps/[app]/serializers.py`
// 2. Tạo file business logic `apps/[app]/services.py` 
// 3. Tạo controller `apps/[app]/views.py` và gọi qua Service.
// 4. Tạo router `apps/[app]/urls.py` và đính kèm vào `core/urls.py`

## 7. Quy định Build & Verify trước khi hoàn tất Phase
- Sau khi hoàn thành mỗi phase hoặc plan, agent **BẮT BUỘC** phải chạy `python manage.py check` (và `python manage.py test` nếu có test) và đảm bảo **THÀNH CÔNG** (0 errors) trước khi tuyên bố phase hoàn tất.
- Nếu check hoặc test thất bại, agent phải tự sửa lỗi cho đến khi pass rồi mới được báo hoàn tất.

## 8. Quy định Git — Agent KHÔNG được commit
- Agent **TUYỆT ĐỐI KHÔNG** được tự ý thực hiện lệnh `git commit`, `git push`, `git merge`, hoặc bất kỳ lệnh git ghi nào.
- Chỉ có chủ dự án (user) mới được phép thực hiện commit và push.
- Agent chỉ được phép chạy các lệnh git **đọc** (ví dụ: `git status`, `git log`, `git branch`, `git diff`).
- Khi cần tạo nhánh mới (`git checkout -b`), agent phải **hỏi user** trước khi thực hiện.

## 9. Báo cáo hoàn thành Phase
- Chỉ được báo phase hoàn thành khi toàn bộ điều kiện Definition of Done của phase đạt hoặc deferred item đã được user chấp thuận.
- Báo cáo cuối phase phải có: danh sách việc đã làm, file/khu vực đã sửa, lệnh kiểm tra đã chạy, kết quả kiểm tra, rủi ro còn lại, deferred items và bước tiếp theo.
- Không được tự ý `git commit`, `git push`, `git merge`; chỉ đề xuất commit message/branch theo plan để user tự thực hiện.
