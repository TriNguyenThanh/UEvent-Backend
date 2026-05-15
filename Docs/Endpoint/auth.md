# 2. API xác thực và tài khoản

| Method | Endpoint                | Quyền  | Mô tả                                  |
| ------ | ----------------------- | ------ | -------------------------------------- |
| `POST` | `/auth/register`        | Public | Đăng ký tài khoản bằng email sinh viên |
| `POST` | `/auth/send-otp`        | Public | Gửi mã OTP đến email sinh viên         |
| `POST` | `/auth/verify-otp`      | Public | Xác thực mã OTP                        |
| `POST` | `/auth/login`           | Public | Đăng nhập bằng email và mật khẩu       |
| `POST` | `/auth/google`          | Public | Đăng nhập bằng Google OAuth2           |
| `POST` | `/auth/logout`          | User   | Đăng xuất                              |
| `POST` | `/auth/refresh-token`   | Public | Làm mới access token                   |
| `POST` | `/auth/forgot-password` | Public | Yêu cầu đặt lại mật khẩu               |
| `POST` | `/auth/reset-password`  | Public | Đặt lại mật khẩu                       |
| `GET`  | `/auth/me`              | User   | Lấy thông tin người dùng hiện tại      |

---

# 3. API quản lý hồ sơ người dùng

| Method   | Endpoint                  | Quyền | Mô tả                                  |
| -------- | ------------------------- | ----- | -------------------------------------- |
| `GET`    | `/users/me`               | User  | Xem hồ sơ cá nhân                      |
| `PATCH`  | `/users/me`               | User  | Cập nhật hồ sơ cá nhân                 |
| `PATCH`  | `/users/me/avatar`        | User  | Cập nhật ảnh đại diện                  |
| `GET`    | `/users/me/organizations` | User  | Xem CLB/tổ chức đang tham gia          |
| `GET`    | `/users/me/events`        | User  | Xem sự kiện của người dùng             |
| `GET`    | `/users/me/registrations` | User  | Xem các sự kiện đã đăng ký             |
| `DELETE` | `/users/me`               | User  | Xóa hoặc vô hiệu hóa tài khoản cá nhân |

---

# 4. API bảo mật tài khoản / Passkey

| Method   | Endpoint                              | Quyền  | Mô tả                                |
| -------- | ------------------------------------- | ------ | ------------------------------------ |
| `GET`    | `/security/passkeys`                  | User   | Lấy danh sách Passkey của người dùng |
| `POST`   | `/security/passkeys/register-options` | User   | Tạo tùy chọn đăng ký Passkey         |
| `POST`   | `/security/passkeys/register`         | User   | Hoàn tất đăng ký Passkey             |
| `POST`   | `/security/passkeys/login-options`    | Public | Tạo tùy chọn đăng nhập bằng Passkey  |
| `POST`   | `/security/passkeys/login`            | Public | Đăng nhập bằng Passkey               |
| `DELETE` | `/security/passkeys/{passkeyId}`      | User   | Xóa Passkey                          |

---
