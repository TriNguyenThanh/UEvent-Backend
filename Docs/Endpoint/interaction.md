# 14. API hỏi đáp trong sự kiện

| Method   | Endpoint                             | Quyền            | Mô tả                         |
| -------- | ------------------------------------ | ---------------- | ----------------------------- |
| `POST`   | `/api/v1/events/{eventId}/questions/`        | User             | Gửi câu hỏi cho BTC           |
| `GET`    | `/api/v1/events/{eventId}/questions/`        | Organizer        | Xem danh sách câu hỏi         |
| `GET`    | `/api/v1/events/{eventId}/questions/public/` | User             | Xem câu hỏi công khai         |
| `PATCH`  | `/api/v1/questions/{questionId}/`            | User             | Cập nhật câu hỏi của bản thân |
| `DELETE` | `/api/v1/questions/{questionId}/`            | User / Organizer | Xóa câu hỏi                   |
| `PATCH`  | `/api/v1/questions/{questionId}/answer/`     | Organizer        | Trả lời câu hỏi               |
| `PATCH`  | `/api/v1/questions/{questionId}/pin/`        | Organizer        | Ghim câu hỏi                  |
| `PATCH`  | `/api/v1/questions/{questionId}/hide/`       | Organizer        | Ẩn câu hỏi                    |

---

# 15. API feedback sau sự kiện

| Method   | Endpoint                              | Quyền            | Mô tả                          |
| -------- | ------------------------------------- | ---------------- | ------------------------------ |
| `POST`   | `/api/v1/events/{eventId}/feedbacks/`         | User             | Gửi feedback sau sự kiện       |
| `GET`    | `/api/v1/events/{eventId}/feedbacks/`         | Organizer        | Xem danh sách feedback         |
| `GET`    | `/api/v1/events/{eventId}/feedbacks/summary/` | Organizer        | Xem thống kê đánh giá          |
| `PATCH`  | `/api/v1/feedbacks/{feedbackId}/`             | User             | Cập nhật feedback của bản thân |
| `DELETE` | `/api/v1/feedbacks/{feedbackId}/`             | User / Organizer | Xóa feedback                   |

Body ví dụ:

```json
{
  "rating": 5,
  "comment": "Sự kiện rất hữu ích.",
  "isAnonymous": true
}
```

---
