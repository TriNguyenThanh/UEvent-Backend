# 10. API form đăng ký sự kiện

| Method   | Endpoint                                               | Quyền     | Mô tả                          |
| -------- | ------------------------------------------------------ | --------- | ------------------------------ |
| `GET`    | `/events/{eventId}/registration-form`                  | User      | Lấy form đăng ký của sự kiện   |
| `POST`   | `/events/{eventId}/registration-form/fields`           | Organizer | Thêm trường tùy chỉnh vào form |
| `PATCH`  | `/events/{eventId}/registration-form/fields/{fieldId}` | Organizer | Cập nhật trường form           |
| `DELETE` | `/events/{eventId}/registration-form/fields/{fieldId}` | Organizer | Xóa trường form                |

Ví dụ field tùy chỉnh:

```json
{
  "label": "Size áo",
  "type": "select",
  "required": true,
  "options": ["S", "M", "L", "XL"]
}
```

---

# 11. API đăng ký tham gia sự kiện

| Method   | Endpoint                                                  | Quyền     | Mô tả                                       |
| -------- | --------------------------------------------------------- | --------- | ------------------------------------------- |
| `POST`   | `/api/v1/events/{eventId}/registrations/`                         | User      | Đăng ký tham gia sự kiện                    |
| `GET`    | `/api/v1/events/{eventId}/registrations/`                         | Organizer | Xem danh sách đăng ký                       |
| `GET`    | `/api/v1/events/{eventId}/registrations/{registrationId}/`        | Organizer | Xem chi tiết đăng ký                        |
| `DELETE` | `/api/v1/events/{eventId}/registrations/me/`                      | User      | Hủy đăng ký của bản thân                    |
| `PATCH`  | `/api/v1/events/{eventId}/registrations/{registrationId}/cancel/` | Organizer | BTC hủy đăng ký của người tham gia          |
| `GET`    | `/api/v1/registrations/me/`                                       | User      | Xem toàn bộ đăng ký của người dùng hiện tại |

Body đăng ký ví dụ:

```json
{
  "answers": [
    {
      "fieldId": "size_ao",
      "value": "L"
    },
    {
      "fieldId": "buoi_tham_gia",
      "value": "Buổi sáng"
    }
  ]
}
```

---

# 12. API vé QR

| Method  | Endpoint                             | Quyền            | Mô tả                            |
| ------- | ------------------------------------ | ---------------- | -------------------------------- |
| `GET`   | `/api/v1/tickets/me/`                | User             | Xem danh sách vé của tôi         |
| `GET`   | `/api/v1/tickets/{ticketId}/`        | User             | Xem chi tiết vé                  |
| `GET`   | `/api/v1/tickets/{ticketId}/qr/`     | User             | Lấy mã QR của vé                 |
| `POST`  | `/events/{eventId}/tickets/generate` | Organizer        | Tạo lại vé QR cho người tham gia |
| `PATCH` | `/api/v1/tickets/{ticketId}/cancel/` | User / Organizer | Hủy vé                           |

Nên lưu ý: mã QR không nên chứa toàn bộ thông tin cá nhân. QR chỉ nên chứa `ticketCode` hoặc token định danh vé.

---
