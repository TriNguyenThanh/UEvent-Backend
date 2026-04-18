Created serializers.py
Created services.py
Edited views.py
Created urls.py
Edited urls.py

Tuyệt vời! Bạn đã tạo xong toàn bộ 4 file rồi. Bây giờ tôi sẽ giải thích từ đầu để bạn hiểu **tại sao** code được tổ chức như vậy.

---

## Django hoạt động như thế nào? – Bức tranh toàn cảnh

Hãy hình dung một request từ client đi qua hệ thống như sau:

```
Client (app/browser)
    │
    ▼
[core/urls.py]          ← "Tổng đài" điều hướng
    │
    ▼
[apps/registrations/urls.py]  ← Điều hướng trong app
    │
    ▼
[views.py]              ← "Receptionist" nhận & trả request
    │
    ├──► [serializers.py]  ← Validate input / Format output
    │
    └──► [services.py]     ← Xử lý business logic
              │
              ▼
         [models.py]       ← Đại diện data trong database
```

---

## Giải thích từng tầng

### 🗄️ 1. Model – "Bản đồ database"

```python
# models/ticket.py
class Ticket(BaseModel):
    ticket_code = models.CharField(max_length=50, unique=True)
    status = models.CharField(choices=TicketStatus.choices, ...)
    registration = models.OneToOneField("registrations.EventRegistration", ...)
```

- **Model = ánh xạ 1-1 với bảng trong database.**
- Bạn không cần viết SQL. Django tự dịch `Ticket.objects.create(...)` thành `INSERT INTO tickets ...`
- `OneToOneField` nghĩa là mỗi `EventRegistration` chỉ có đúng 1 `Ticket`. Django tự tạo constraint ở DB.
- `BaseModel` là class cha dự án này tự tạo, cung cấp sẵn `id` (UUID), `created_at`, `updated_at`, và **soft delete** (`deleted_at` thay vì xóa thật).

---

### 🔌 2. URLs – "Bảng điều hướng"

Có **2 cấp** URL:

**Cấp 1 – `core/urls.py` (cổng chính):**
```python
path("api/v1/registrations/", include("apps.registrations.urls")),
```
Ý nghĩa: *"Bất kỳ request nào bắt đầu bằng `/api/v1/registrations/` thì chuyển tiếp cho `apps.registrations.urls` xử lý."*

**Cấp 2 – `apps/registrations/urls.py` (nội bộ app):**
```python
router = DefaultRouter()
router.register(r"tickets", TicketViewSet, basename="ticket")
```
`DefaultRouter` tự động sinh ra 5 URL từ 1 dòng:

| URL | Method | Gọi hàm nào trong ViewSet |
|-----|--------|---------------------------|
| `/api/v1/registrations/tickets/` | GET | `list()` |
| `/api/v1/registrations/tickets/` | POST | `create()` |
| `/api/v1/registrations/tickets/{id}/` | GET | `retrieve()` |
| `/api/v1/registrations/tickets/{id}/` | PATCH | `partial_update()` |
| `/api/v1/registrations/tickets/{id}/` | DELETE | `destroy()` |

> **Router = "phép màu" của DRF** – bạn đăng ký 1 ViewSet là có đủ 5 endpoint CRUD.

---

### 📋 3. Serializer – "Cửa khẩu kiểm soát"

Có **2 loại serializer** với vai trò khác nhau:

**Input Serializer** – Kiểm tra dữ liệu *đầu vào* từ client:
```python
class CreateTicketInputSerializer(serializers.Serializer):
    registration_id = serializers.PrimaryKeyRelatedField(
        queryset=EventRegistration.objects.all()  # ← Tự động check ID có tồn tại không
    )
    expires_at = serializers.DateTimeField()  # ← Tự validate đúng định dạng datetime
```
Khi gọi `.is_valid(raise_exception=True)`, nếu client gửi `registration_id` sai → DRF tự động trả về `400 Bad Request` với thông báo lỗi rõ ràng, **bạn không cần tự viết if-else kiểm tra.**

**Output Serializer** – Format dữ liệu *trả ra* cho client:
```python
class TicketOutputSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="registration.event.title", read_only=True)
```
`source="registration.event.title"` nghĩa là: *"Lấy trường `title` từ object `event`, là ForeignKey của `registration`, là ForeignKey của `ticket`."* DRF tự navigate qua các quan hệ.

---

### ⚙️ 4. Service – "Kỹ sư xử lý"

Đây là tầng **quan trọng nhất** và hay bị bỏ quên khi mới học Django:

```python
class TicketService:
    @staticmethod
    @transaction.atomic
    def create_ticket(registration, expires_at) -> Ticket:
        # Tất cả logic phức tạp đặt ở đây
        ticket_code = secrets.token_urlsafe(16)
        ...
        ticket = Ticket.objects.create(...)
        return ticket
```

**Tại sao cần Service, không viết thẳng vào View?**

| Nếu bạn viết logic vào View | Với Service Layer |
|-----------------------------|-------------------|
| View dài 200 dòng, khó đọc | View chỉ 5-10 dòng, rõ ràng |
| Logic khó tái sử dụng (vd: cần gửi email + tạo ticket) | Service có thể gọi từ nhiều nơi |
| Khó test riêng lẻ | Test service độc lập với HTTP |

`@transaction.atomic` đảm bảo: nếu có lỗi bất kỳ trong block đó (vd: lỗi khi tạo ticket), **database sẽ rollback toàn bộ**, không bị data lỡ dở.

---

### 🎮 5. View – "Receptionist"

```python
def create(self, request):
    # 1. Nhận dữ liệu từ request → đưa vào Input Serializer validate
    input_serializer = CreateTicketInputSerializer(data=request.data)
    input_serializer.is_valid(raise_exception=True)

    # 2. Lấy data đã validate → gọi Service xử lý
    ticket = TicketService.create_ticket(
        input_serializer.validated_data["registration_id"],
        input_serializer.validated_data["expires_at"]
    )

    # 3. Lấy kết quả → đưa vào Output Serializer → trả về Response
    return Response(TicketOutputSerializer(ticket).data, status=201)
```

**View chỉ làm đúng 3 việc**: validate input → gọi service → format output. Không hơn.

---

## Luồng thực tế một request POST tạo ticket

```
POST /api/v1/registrations/tickets/
Body: { "registration_id": "uuid-xxx", "expires_at": "2026-12-31T00:00:00Z" }

1. core/urls.py nhận → route sang apps/registrations/urls.py
2. Router nhận POST → gọi TicketViewSet.create()
3. View tạo CreateTicketInputSerializer(data=request.data)
4. .is_valid() kiểm tra:
   - registration_id có phải UUID không? → OK
   - UUID đó có tồn tại trong DB không? → OK
   - expires_at đúng định dạng datetime không? → OK
5. View gọi TicketService.create_ticket(registration, expires_at)
6. Service (trong transaction.atomic):
   - Check đã có ticket chưa → chưa → OK
   - Tạo ticket_code random
   - Tạo qr_payload, qr_signature
   - INSERT vào DB
7. View nhận ticket object → TicketOutputSerializer format
8. Trả Response 201 với JSON ticket đầy đủ
```