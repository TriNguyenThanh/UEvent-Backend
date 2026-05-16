Dưới đây là **danh sách API endpoint đề xuất** cho hệ thống **UEvent – Quản lý sự kiện sinh viên UTC2**. Có thể dùng cho báo cáo phân tích thiết kế hoặc làm tài liệu backend REST API.

---

# 1. Quy ước chung

Base URL đề xuất:

```http
/api/v1
```

Một số nhóm quyền chính:

| Role        | Mô tả                       |
| ----------- | --------------------------- |
| `STUDENT`   | Sinh viên / Người tham gia  |
| `ORGANIZER` | Người tổ chức / Ban tổ chức |
| `ADMIN`     | Quản trị viên hệ thống      |

Một số trạng thái HTTP thường dùng:

| Mã                          | Ý nghĩa                |
| --------------------------- | ---------------------- |
| `200 OK`                    | Thành công             |
| `201 Created`               | Tạo mới thành công     |
| `400 Bad Request`           | Dữ liệu không hợp lệ   |
| `401 Unauthorized`          | Chưa đăng nhập         |
| `403 Forbidden`             | Không có quyền         |
| `404 Not Found`             | Không tìm thấy dữ liệu |
| `409 Conflict`              | Xung đột dữ liệu       |
| `500 Internal Server Error` | Lỗi hệ thống           |

---

# 16. API thông báo

| Method   | Endpoint                               | Quyền | Mô tả                                      |
| -------- | -------------------------------------- | ----- | ------------------------------------------ |
| `GET`    | `/notifications/me`                    | User  | Xem danh sách thông báo                    |
| `PATCH`  | `/notifications/{notificationId}/read` | User  | Đánh dấu đã đọc                            |
| `PATCH`  | `/notifications/read-all`              | User  | Đánh dấu tất cả là đã đọc                  |
| `DELETE` | `/notifications/{notificationId}`      | User  | Xóa thông báo                              |
| `POST`   | `/notifications/device-token`          | User  | Lưu device token để nhận Push Notification |
| `DELETE` | `/notifications/device-token`          | User  | Xóa device token                           |

---

# 17. API Calendar

| Method | Endpoint                         | Quyền | Mô tả                                                           |
| ------ | -------------------------------- | ----- | --------------------------------------------------------------- |
| `GET`  | `/events/{eventId}/calendar`     | User  | Lấy thông tin lịch của sự kiện                                  |
| `GET`  | `/events/{eventId}/calendar/ics` | User  | Tải file `.ics` để thêm vào Calendar                            |
| `POST` | `/events/{eventId}/calendar/add` | User  | Thêm sự kiện vào Calendar thiết bị hoặc tài khoản được liên kết |

---

# 18. API chia sẻ sự kiện / Deep link

| Method | Endpoint                                  | Quyền     | Mô tả                           |
| ------ | ----------------------------------------- | --------- | ------------------------------- |
| `GET`  | `/events/{eventId}/share-link`            | User      | Lấy link chia sẻ sự kiện        |
| `POST` | `/events/{eventId}/share-link/regenerate` | Organizer | Tạo lại link chia sẻ            |
| `GET`  | `/deeplink/events/{slug}`                 | Public    | Truy cập sự kiện bằng Deep link |

---

# 19. API xuất báo cáo Google Sheets

| Method | Endpoint                                  | Quyền     | Mô tả                                   |
| ------ | ----------------------------------------- | --------- | --------------------------------------- |
| `POST` | `/events/{eventId}/exports/google-sheets` | Organizer | Xuất danh sách tham dự ra Google Sheets |
| `GET`  | `/events/{eventId}/exports`               | Organizer | Xem lịch sử xuất báo cáo                |
| `GET`  | `/events/{eventId}/exports/{exportId}`    | Organizer | Xem chi tiết bản xuất                   |
| `GET`  | `/events/{eventId}/exports/csv`           | Organizer | Xuất danh sách ra file CSV              |
| `GET`  | `/events/{eventId}/exports/excel`         | Organizer | Xuất danh sách ra file Excel            |

Body ví dụ:

```json
{
  "type": "ATTENDANCE",
  "includeRegistered": true,
  "includeCheckedIn": true,
  "includeAbsent": true
}
```

---

# 20. API Admin quản lý người dùng

| Method   | Endpoint                       | Quyền | Mô tả                         |
| -------- | ------------------------------ | ----- | ----------------------------- |
| `GET`    | `/admin/users`                 | Admin | Xem danh sách người dùng      |
| `GET`    | `/admin/users/{userId}`        | Admin | Xem chi tiết người dùng       |
| `PATCH`  | `/admin/users/{userId}`        | Admin | Cập nhật thông tin người dùng |
| `PATCH`  | `/admin/users/{userId}/role`   | Admin | Cập nhật vai trò người dùng   |
| `PATCH`  | `/admin/users/{userId}/lock`   | Admin | Khóa tài khoản                |
| `PATCH`  | `/admin/users/{userId}/unlock` | Admin | Mở khóa tài khoản             |
| `DELETE` | `/admin/users/{userId}`        | Admin | Xóa tài khoản người dùng      |

---

# 21. API Admin kiểm duyệt sự kiện

| Method   | Endpoint                          | Quyền | Mô tả                      |
| -------- | --------------------------------- | ----- | -------------------------- |
| `GET`    | `/admin/events`                   | Admin | Xem toàn bộ sự kiện        |
| `GET`    | `/admin/events/pending`           | Admin | Xem sự kiện đang chờ duyệt |
| `PATCH`  | `/admin/events/{eventId}/approve` | Admin | Duyệt sự kiện              |
| `PATCH`  | `/admin/events/{eventId}/reject`  | Admin | Từ chối sự kiện            |
| `PATCH`  | `/admin/events/{eventId}/lock`    | Admin | Khóa sự kiện vi phạm       |
| `PATCH`  | `/admin/events/{eventId}/unlock`  | Admin | Mở khóa sự kiện            |
| `DELETE` | `/admin/events/{eventId}`         | Admin | Xóa sự kiện vi phạm        |

Body từ chối sự kiện ví dụ:

```json
{
  "reason": "Nội dung sự kiện chưa phù hợp với quy định của nhà trường."
}
```

---

# 22. API Admin thiết lập hệ thống

| Method  | Endpoint            | Quyền | Mô tả                         |
| ------- | ------------------- | ----- | ----------------------------- |
| `GET`   | `/admin/settings`   | Admin | Xem thiết lập hệ thống        |
| `PATCH` | `/admin/settings`   | Admin | Cập nhật thiết lập hệ thống   |
| `GET`   | `/admin/audit-logs` | Admin | Xem lịch sử thao tác hệ thống |
| `GET`   | `/admin/statistics` | Admin | Xem thống kê toàn hệ thống    |

Ví dụ thiết lập hệ thống:

```json
{
  "allowPublicEventCreation": false,
  "requireAdminApproval": true,
  "allowedEmailDomains": ["utc2.edu.vn", "student.utc2.edu.vn"],
  "maxEventCapacity": 1000,
  "cancelRegistrationBeforeHours": 24
}
```

---

# 23. API upload file / hình ảnh

| Method   | Endpoint                           | Quyền            | Mô tả                 |
| -------- | ---------------------------------- | ---------------- | --------------------- |
| `POST`   | `/uploads/images`                  | User             | Upload hình ảnh chung |
| `POST`   | `/uploads/events/{eventId}/banner` | Organizer        | Upload banner sự kiện |
| `DELETE` | `/uploads/{fileId}`                | User / Organizer | Xóa file đã upload    |

---

# 24. Tổng hợp endpoint theo module

| Module       | Endpoint chính                      |
| ------------ | ----------------------------------- |
| Auth         | `/auth/*`                           |
| User         | `/users/*`                          |
| Security     | `/security/*`                       |
| Organization | `/organizations/*`                  |
| Event        | `/events/*`                         |
| Category     | `/event-categories/*`               |
| Registration | `/events/{eventId}/registrations/*` |
| Ticket       | `/tickets/*`                        |
| Check-in     | `/events/{eventId}/check-in/*`      |
| Question     | `/events/{eventId}/questions/*`     |
| Feedback     | `/events/{eventId}/feedbacks/*`     |
| Notification | `/notifications/*`                  |
| Calendar     | `/events/{eventId}/calendar/*`      |
| Export       | `/events/{eventId}/exports/*`       |
| Admin        | `/admin/*`                          |
| Upload       | `/uploads/*`                        |

---

# 25. Các endpoint quan trọng nhất nên ưu tiên làm trước

Nếu làm project demo, có thể ưu tiên các API sau:

| Mức ưu tiên | Endpoint                                  |
| ----------- | ----------------------------------------- |
| Cao         | `/auth/register`                          |
| Cao         | `/auth/login`                             |
| Cao         | `/auth/google`                            |
| Cao         | `/users/me`                               |
| Cao         | `/events`                                 |
| Cao         | `/events/{eventId}`                       |
| Cao         | `/events/{eventId}/registrations`         |
| Cao         | `/tickets/me`                             |
| Cao         | `/events/{eventId}/check-in/scan`         |
| Cao         | `/events/{eventId}/registrations`         |
| Trung bình  | `/events/{eventId}/questions`             |
| Trung bình  | `/events/{eventId}/feedbacks`             |
| Trung bình  | `/notifications/me`                       |
| Trung bình  | `/events/{eventId}/exports/google-sheets` |
| Sau cùng    | `/admin/*`                                |
| Sau cùng    | `/security/passkeys/*`                    |
| Sau cùng    | `/events/{eventId}/calendar/*`            |

---

Nếu cần rút gọn cho báo cáo, hệ thống có thể chia thành **8 nhóm API chính**:

1. API xác thực tài khoản
2. API quản lý người dùng
3. API quản lý tổ chức/câu lạc bộ
4. API quản lý sự kiện
5. API đăng ký và vé QR
6. API check-in điểm danh
7. API tương tác, thông báo và feedback
8. API quản trị hệ thống
