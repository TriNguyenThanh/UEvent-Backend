<div align="center">
  <img src="https://res.cloudinary.com/dkkvywz4g/image/upload/v1780654795/logo_kxy3gw.png" alt="UEvent Backend Logo" width="100" height="100" style="border-radius:20px"/>

  # UEvent API Gateway & Core Engine (Tiếng Việt)
  
  **Hạ Tầng Quản Lý Sự Kiện Chuẩn Doanh Nghiệp Dành Cho Khối Đại Học**

  [![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
  [![Django](https://img.shields.io/badge/Django-6.0+-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
  [![Build Status](https://img.shields.io/badge/build-passing-brightgreen?style=flat-square)](#)
  [![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen?style=flat-square)](#)

  *Được nghiên cứu và phát triển riêng cho **Phân hiệu Trường Đại học Giao thông Vận tải tại TP.HCM (UTC2)***
</div>

---

## 📖 Mục Lục

- [Giới Thiệu Dự Án](#-giới-thiệu-dự-án)
- [Kiến Trúc Hệ Thống](#-kiến-trúc-hệ-thống)
- [Tính Năng Cốt Lõi](#-tính-năng-cốt-lõi)
- [Cấu Trúc Mã Nguồn](#-cấu-trúc-mã-nguồn)
- [Cấu Hình Môi Trường](#-cấu-hình-môi-trường)
- [Hướng Dẫn Cài Đặt](#-hướng-dẫn-cài-đặt)
- [Sử Dụng & API Docs](#-sử-dụng--api-docs)
- [Kiểm Thử (Testing)](#-kiểm-thử-testing)
- [Hướng Dẫn Triển Khai (Deployment)](#-hướng-dẫn-triển-khai-deployment)
- [Lộ Trình Phát Triển](#-lộ-trình-phát-triển)
- [Hướng Dẫn Đóng Góp](#-hướng-dẫn-đóng-góp)
- [Bản Quyền & Lời Cảm Ơn](#-bản-quyền--lời-cảm-ơn)

---

## 🚀 Giới Thiệu Dự Án

**UEvent Backend** là bộ não trung tâm vận hành toàn bộ Hệ sinh thái UEvent. Được thiết kế để giải quyết bài toán phức tạp về hậu cần và quản trị sự kiện quy mô lớn trong môi trường đại học, hệ thống có khả năng xử lý hàng chục ngàn người dùng, quản lý phát hành vé động, kiểm soát phân cấp không gian và xác thực bảo mật đa tầng.

Hệ thống được thiết kế theo mô hình **Feature-First Monolithic Architecture**, đảm bảo code được chia module hóa cực cao (chuẩn bị sẵn sàng để bóc tách thành Microservices nếu cần trong tương lai).

### Tại Sao Lại Chọn UEvent?
- **Triệt Tiêu Lỗi Trùng Lặp Vé (Zero Double-Booking)**: Cam kết tính toàn vẹn dữ liệu bằng kỹ thuật khóa dòng cấp DB (`select_for_update`) khi có hàng ngàn sinh viên truy cập đăng ký vé cùng lúc.
- **Bảo Mật Vé Mã Hóa Chuẩn Quân Sự**: Loại bỏ hoàn toàn tình trạng chụp màn hình nhượng vé bằng cơ chế mã hóa QR xoay vòng 15 giây và xác thực bằng chữ ký điện tử ECDSA.
- **Tích Hợp Sâu Vào Giáo Dục**: Tương thích hoàn hảo với hệ thống mã số sinh viên 10 chữ số của UTC2 và tên miền định danh `@st.utc2.edu.vn`.

---

## 🏛 Kiến Trúc Hệ Thống

Cơ sở hạ tầng được xây dựng từ những công nghệ lõi mạnh mẽ nhất trong ngành.

```mermaid
graph TD
    Client(Clients: Web & Mobile) -->|HTTPS / REST| Nginx[NGINX Reverse Proxy]
    Nginx --> Gunicorn[Gunicorn / WSGI]
    Gunicorn --> Django[Django REST Framework]
    
    Django -->|Reads/Writes| Postgres[(PostgreSQL 16)]
    Django -->|Publishes| Celery[Celery Task Queue]
    Celery -->|Schedules| Redis[(Redis 7)]
    Celery -->|Delivers| FCM[Firebase Cloud Messaging]
    
    Django -->|Traces| Jaeger[Jaeger OTLP]
    Django -->|Logs| FluentBit[Fluent-bit]
    FluentBit -->|Aggregates| OpenObserve[(OpenObserve)]
```

### Bảng Công Nghệ Lõi
| Tầng Công Nghệ | Công Cụ | Mục Đích |
|-------|------------|---------|
| **Core Framework** | Django 6.0.3, DRF | ORM mạnh mẽ, trang Admin tích hợp, và khả năng sinh REST API siêu tốc. |
| **Cơ Sở Dữ Liệu** | PostgreSQL 16 | Đảm bảo tính toàn vẹn quan hệ (Relational) kết hợp cùng cột dữ liệu JSONB cho form đăng ký siêu linh hoạt. |
| **Message Broker** | Redis 7 & Celery | Xử lý các tác vụ nặng chạy ngầm (gửi Email hàng loạt, đẩy thông báo FCM, cron jobs). |
| **Trải Nghiệm Hệ Thống** | Jaeger & OpenObserve | Truy vết request phân tán (OpenTelemetry) và gom log tập trung thông qua Fluent-bit. |

---

## ✨ Tính Năng Cốt Lõi

### 1. Cấp Vé Tiên Tiến & Bảo Mật QR Code
- **Engine Chống Chụp Màn Hình**: Thuật toán sinh mã QR tạm thời chỉ có hiệu lực đúng 15 giây.
- **Chữ Ký Số**: Máy quét tại cổng sự kiện sẽ xác thực chữ ký của vé trước khi gọi API tới máy chủ, loại bỏ 99% các request giả mạo/DDOS.

### 2. Phân Quyền Sâu (RBAC)
- Phân quyền theo cấp bậc với từng sự kiện (Chủ sở hữu, Đồng tổ chức, Người soát vé, Nhân viên).
- Middleware tùy chỉnh kiểm soát chặt chẽ quyền hạn trên từng API endpoint.

### 3. Quy Trình Đăng Ký Động
- **JSONB Schemas**: Ban tổ chức tự do xây dựng các form khảo sát/đăng ký phức tạp (Trắc nghiệm, Điền chữ, Dropdown).
- Câu trả lời được lưu và lập chỉ mục (index) với tốc độ truy vấn cực cao nhờ sức mạnh của PostgreSQL JSONB.

### 4. Góc Tương Tác Sự Kiện
- Xử lý mượt mà các phiên Hỏi Đáp (Q&A) và đánh giá sau sự kiện.
- Bảng điều khiển kiểm duyệt chuyên sâu cho phép admin duyệt, ẩn, cảnh báo hoặc đánh dấu các nội dung vi phạm.

---

## 📂 Cấu Trúc Mã Nguồn

```bash
UEvent-Backend/
├── apps/                    # Các module tính năng cốt lõi (Feature-based)
│   ├── events/              # Vòng đời sự kiện, danh mục, ban tổ chức
│   ├── interactions/        # Q&A, Feedback
│   ├── locations/           # Quản lý Sức chứa Cơ sở, Tòa nhà, Phòng học
│   ├── moderation/          # Log kiểm duyệt nội dung đa hình (Polymorphic)
│   ├── notifications/       # Module đẩy thông báo Email & FCM
│   ├── registrations/       # Phát hành vé, Check-in, Biểu mẫu đăng ký
│   ├── support/             # Hệ thống quản lý Ticket hỗ trợ kỹ thuật
│   ├── system_admin/        # Tùy chỉnh Admin cấp cao
│   └── users/               # Quản lý User tùy chỉnh, RBAC, Sessions
├── common/                  # Tiện ích dùng chung
│   ├── models.py            # BaseModel tích hợp UUID & Xóa Mềm (Soft Delete)
│   ├── permissions.py       # Phân quyền DRF Permissions
│   └── exceptions.py        # Quản lý ngoại lệ (Exception) toàn hệ thống
├── core/                    # Cấu hình gốc (settings, wsgi, asgi)
├── docker-compose.yaml      # File khởi động hạ tầng Docker
└── manage.py                # Django CLI
```

---

## ⚙️ Cấu Hình Môi Trường (.env)

Tạo file `.env` dựa trên file `.env.example` và điều chỉnh các thông số bắt buộc:

| Biến Số | Chức Năng | Mặc Định | Bắt Buộc |
|----------|-------------|---------|----------|
| `DEBUG` | Chế độ gỡ lỗi | `True` | Có |
| `SECRET_KEY` | Mã bảo mật cốt lõi để mã hóa phiên bản Django | - | Có |
| `POSTGRES_DB` | Tên Database PostgreSQL | `uevent_db` | Có |
| `POSTGRES_USER` | Tên đăng nhập Database | `postgres` | Có |
| `POSTGRES_PASSWORD`| Mật khẩu Database | `postgres` | Có |
| `CELERY_BROKER_URL`| Chuỗi kết nối đến Redis | `redis://localhost:6379/0`| Có |
| `FCM_ENABLED` | Bật/tắt thông báo đẩy Firebase | `false` | Không |

---

## 💻 Hướng Dẫn Cài Đặt

### Cách 1: Sử Dụng Docker Compose (Khuyên dùng)

Cách dễ nhất để dựng toàn bộ hệ thống khổng lồ này chỉ bằng vài dòng lệnh.

```bash
# 1. Clone mã nguồn
git clone https://github.com/TriNguyenThanh/UEvent-backend-Django.git
cd UEvent-backend-Django

# 2. Chuẩn bị file môi trường
cp .env.example .env

# 3. Chạy toàn bộ cluster (Postgres, Redis, Celery, App, Jaeger)
docker-compose up -d --build

# 4. Migrate CSDL và nạp dữ liệu mẫu
docker-compose exec app python manage.py migrate
docker-compose exec app python manage.py loaddata seed_data.json
```

### Cách 2: Cài Đặt Trực Tiếp (Bare-metal)

```bash
# 1. Tạo môi trường ảo (Virtual Env)
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate

# 2. Cài đặt thư viện
pip install -r requirements.txt

# 3. Tự cài đặt Postgres & Redis trên máy, sau đó cập nhật .env

# 4. Migrate và khởi động
python manage.py migrate
python manage.py runserver
```

---

## 🔌 Sử Dụng & API Docs

Khi hệ thống khởi chạy, API sẽ hoạt động tại `http://localhost:8000/api/v1/`.

### Giao Diện Tài Liệu API
Hệ thống tuân thủ nghiêm ngặt tiêu chuẩn OpenAPI. Bạn có thể test trực tiếp trên trình duyệt:
- **Swagger UI**: `http://localhost:8000/api/v1/swagger/`
- **ReDoc**: `http://localhost:8000/api/v1/redoc/`

### Ví dụ Lệnh cURL (Đăng Nhập)
```bash
curl -X POST http://localhost:8000/api/v1/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "5651071902",
    "password": "MatKhauSieuKho123"
  }'
```

---

## 🗄 Quản Lý Cơ Sở Dữ Liệu

### Thuật Toán Xóa Mềm (Soft Delete)
Dữ liệu trong UEvent KHÔNG BAO GIỜ bị xóa vĩnh viễn:
- Lệnh `BaseModel.delete()` chỉ cập nhật cột `deleted_at = timezone.now()`.
- Lệnh query thông thường (`objects`) sẽ tự động ẩn các bản ghi đã xóa.
- Để xem lịch sử và các bản ghi bị xóa, lập trình viên sử dụng manager `all_objects`.

### Chống Quét ID
Toàn bộ khóa chính (PK) dùng `UUIDv4`, giúp ngăn chặn việc hacker dùng bot quét thứ tự tuần tự ID người dùng hoặc ID sự kiện.

---

## 🧪 Kiểm Thử (Testing)

Hệ thống có bộ Test Suite hoàn chỉnh. Chạy test trên môi trường Local:

```bash
# Chạy toàn bộ Test
python manage.py test

# Chỉ chạy test cho module Phát hành vé (Rất quan trọng)
python manage.py test apps.registrations
```

---

## 📦 Hướng Dẫn Triển Khai (Deployment)

1. Đặt `DEBUG=False` trong file `.env` thật.
2. Dùng `Gunicorn` làm server thay vì lệnh `runserver` mặc định của Django.
3. Cấu hình NGINX để làm Reverse Proxy và phục vụ các file Static/Media.
4. Bảo mật tuyệt đối file `firebase-service-account.json`, sử dụng Docker Secret.

---

## 🛤 Lộ Trình Phát Triển

- [x] **Giai đoạn 1**: Hoàn thiện lõi Sự kiện & Đăng ký vé.
- [x] **Giai đoạn 2**: Đẩy thông báo ngầm với Celery Workers.
- [x] **Giai đoạn 3**: Giám sát hệ thống với OpenTelemetry.
- [x] **Giai đoạn 4**: Tích hợp Passkeys (WebAuthn) và OAuth2.

---

## 🤝 Hướng Dẫn Đóng Góp

1. Fork dự án.
2. Tạo nhánh tính năng (`git checkout -b feature/TinhNangMoi`).
3. Chạy `npx gitnexus analyze` để xem xét mức độ ảnh hưởng của đoạn code bạn vừa thay đổi.
4. Commit code (`git commit -m 'Thêm TinhNangMoi'`).
5. Push nhánh (`git push origin feature/TinhNangMoi`).
6. Mở Pull Request.

---

## 📜 Bản Quyền & Lời Cảm Ơn

Được phân phối dưới giấy phép MIT License. Xem file `LICENSE` để biết thêm chi tiết.

*Xin gửi lời cảm ơn đặc biệt đến sinh viên và giảng viên Phân hiệu Đại học Giao thông Vận tải (UTC2) đã cung cấp góc nhìn thực tiễn về quy trình tổ chức sự kiện để dự án này được ra đời.*
