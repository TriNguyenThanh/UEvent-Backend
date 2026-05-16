# 9. API mời người tham gia

| Method   | Endpoint                              | Quyền     | Mô tả                        |
| -------- | ------------------------------------- | --------- | ---------------------------- |
| `POST`   | `/events/{eventId}/invitations`       | Organizer | Gửi lời mời tham gia sự kiện |
| `GET`    | `/events/{eventId}/invitations`       | Organizer | Xem danh sách lời mời        |
| `POST`   | `/invitations/{invitationId}/accept`  | User      | Chấp nhận lời mời            |
| `POST`   | `/invitations/{invitationId}/decline` | User      | Từ chối lời mời              |
| `DELETE` | `/invitations/{invitationId}`         | Organizer | Hủy lời mời                  |

Body ví dụ:

```json
{
  "emails": ["student1@utc2.edu.vn", "student2@utc2.edu.vn"],
  "message": "Mời bạn tham gia sự kiện Workshop AI."
}
```

---
