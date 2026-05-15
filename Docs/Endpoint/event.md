# 6. API quản lý sự kiện

| Method   | Endpoint                               | Quyền             | Mô tả                                    |
| -------- | -------------------------------------- | ----------------- | ---------------------------------------- |
| `GET`    | `/events`                              | Public            | Lấy danh sách sự kiện công khai          |
| `GET`    | `/events/{eventId}`                    | Public            | Xem chi tiết sự kiện                     |
| `POST`   | `/events`                              | Organizer         | Tạo sự kiện mới                          |
| `PATCH`  | `/events/{eventId}`                    | Organizer         | Cập nhật thông tin sự kiện               |
| `DELETE` | `/events/{eventId}`                    | Organizer / Admin | Xóa sự kiện                              |
| `PATCH`  | `/events/{eventId}/publish`            | Organizer         | Gửi sự kiện lên chờ duyệt hoặc công khai |
| `PATCH`  | `/events/{eventId}/cancel`             | Organizer         | Hủy sự kiện                              |
| `PATCH`  | `/events/{eventId}/close-registration` | Organizer         | Đóng đăng ký sự kiện                     |
| `PATCH`  | `/events/{eventId}/open-registration`  | Organizer         | Mở đăng ký sự kiện                       |
| `GET`    | `/events/{eventId}/statistics`         | Organizer         | Xem thống kê sự kiện                     |

Ví dụ query cho danh sách sự kiện:

```http
GET /api/v1/events?keyword=workshop&category=academic&startDate=2026-05-01&endDate=2026-05-31&page=1&limit=10
```

---

# 7. API danh mục sự kiện

| Method   | Endpoint                         | Quyền  | Mô tả                          |
| -------- | -------------------------------- | ------ | ------------------------------ |
| `GET`    | `/event-categories`              | Public | Lấy danh sách danh mục sự kiện |
| `POST`   | `/event-categories`              | Admin  | Tạo danh mục sự kiện           |
| `PATCH`  | `/event-categories/{categoryId}` | Admin  | Cập nhật danh mục              |
| `DELETE` | `/event-categories/{categoryId}` | Admin  | Xóa danh mục                   |

Ví dụ danh mục:

```text
Âm nhạc
Học thuật
Thể thao
Tình nguyện
Câu lạc bộ
Kỹ năng
Hội thảo
```

---

# 8. API quản lý Ban tổ chức sự kiện

| Method   | Endpoint                                | Quyền     | Mô tả                           |
| -------- | --------------------------------------- | --------- | ------------------------------- |
| `GET`    | `/events/{eventId}/organizers`          | Organizer | Xem danh sách BTC của sự kiện   |
| `POST`   | `/events/{eventId}/organizers`          | Organizer | Thêm thành viên vào BTC         |
| `PATCH`  | `/events/{eventId}/organizers/{userId}` | Organizer | Cập nhật vai trò thành viên BTC |
| `DELETE` | `/events/{eventId}/organizers/{userId}` | Organizer | Xóa thành viên khỏi BTC         |

Vai trò trong BTC có thể gồm:

| Role            | Mô tả            |
| --------------- | ---------------- |
| `OWNER`         | Chủ sự kiện      |
| `MANAGER`       | Quản lý sự kiện  |
| `CHECKIN_STAFF` | Nhân sự check-in |
| `VIEWER`        | Chỉ xem dữ liệu  |

---
