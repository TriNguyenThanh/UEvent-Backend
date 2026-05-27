# 2. API Xác thực và Tài khoản (Keycloak OIDC)

> **Lưu ý Quan trọng:** Hệ thống xác thực và quản lý tài khoản (Đăng nhập, Đăng ký, Quên mật khẩu, OTP, Social Login bằng Google, Passkey) đã được di chuyển hoàn toàn sang **Keycloak Server**. Backend Django sẽ không trực tiếp cung cấp các API như `/auth/login` hay `/auth/register` nữa.
> Các client (Mobile/Web/Web Admin) cần gọi các API chuẩn OIDC/OAuth2 của Keycloak để nhận JWT Access Token trước khi giao tiếp với Backend.

Các endpoint quan trọng trên Keycloak:
| Method | Endpoint (Trên Keycloak)                                       | Mô tả                                  |
| ------ | -------------------------------------------------------------- | -------------------------------------- |
| `POST` | `/realms/uevent/protocol/openid-connect/token`                 | Đăng nhập để lấy Access/Refresh Token  |
| `POST` | `/realms/uevent/protocol/openid-connect/token` (refresh_token) | Làm mới Access Token                   |
| `GET`  | `/realms/uevent/protocol/openid-connect/auth`                  | Khởi tạo luồng Login qua Trình duyệt   |

---

# 3. API quản lý hồ sơ người dùng (Django Backend)

Tất cả các request tới Backend phải đính kèm Header `Authorization: Bearer <Access Token lấy từ Keycloak>`.

| Method   | Endpoint                  | Quyền | Mô tả                                  |
| -------- | ------------------------- | ----- | -------------------------------------- |
| `GET`    | `/auth/profile`           | User  | Xem hồ sơ cá nhân hiện tại             |
| `PATCH`  | `/auth/profile`           | User  | Cập nhật hồ sơ cá nhân                 |
| `GET`    | `/users/me/organizations` | User  | Xem CLB/tổ chức đang tham gia (Dự kiến)|
| `GET`    | `/users/me/events`        | User  | Xem sự kiện của người dùng (Dự kiến)   |
| `GET`    | `/users/me/registrations` | User  | Xem các sự kiện đã đăng ký (Dự kiến)   |
