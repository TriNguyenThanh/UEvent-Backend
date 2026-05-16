# 13. API check-in / điểm danh

| Method   | Endpoint                                  | Quyền     | Mô tả                                     |
| -------- | ----------------------------------------- | --------- | ----------------------------------------- |
| `POST`   | `/events/{eventId}/check-in/scan`         | Organizer | Quét và xác thực mã QR                    |
| `POST`   | `/events/{eventId}/check-in/manual`       | Organizer | Check-in thủ công bằng MSSV/email         |
| `GET`    | `/events/{eventId}/check-ins`             | Organizer | Xem danh sách đã check-in                 |
| `GET`    | `/events/{eventId}/absentees`             | Organizer | Xem danh sách chưa check-in               |
| `DELETE` | `/events/{eventId}/check-ins/{checkInId}` | Organizer | Hủy trạng thái check-in nếu thao tác nhầm |

Body quét QR ví dụ:

```json
{
  "ticketCode": "UEVENT-TICKET-20260515-ABC123"
}
```

Response ví dụ:

```json
{
  "success": true,
  "message": "Check-in thành công",
  "data": {
    "studentName": "Nguyễn Văn A",
    "mssv": "2251123456",
    "eventName": "Workshop AI UTC2",
    "checkedInAt": "2026-05-15T08:30:00Z"
  }
}
```

---
