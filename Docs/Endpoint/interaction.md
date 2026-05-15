# 14. API hỏi đáp trong sự kiện

| Method   | Endpoint                             | Quyền            | Mô tả                         |
| -------- | ------------------------------------ | ---------------- | ----------------------------- |
| `POST`   | `/events/{eventId}/questions`        | User             | Gửi câu hỏi cho BTC           |
| `GET`    | `/events/{eventId}/questions`        | Organizer        | Xem danh sách câu hỏi         |
| `GET`    | `/events/{eventId}/questions/public` | User             | Xem câu hỏi công khai         |
| `PATCH`  | `/questions/{questionId}`            | User             | Cập nhật câu hỏi của bản thân |
| `DELETE` | `/questions/{questionId}`            | User / Organizer | Xóa câu hỏi                   |
| `PATCH`  | `/questions/{questionId}/answer`     | Organizer        | Trả lời câu hỏi               |
| `PATCH`  | `/questions/{questionId}/pin`        | Organizer        | Ghim câu hỏi                  |
| `PATCH`  | `/questions/{questionId}/hide`       | Organizer        | Ẩn câu hỏi                    |

---

# 15. API feedback sau sự kiện

| Method   | Endpoint                              | Quyền            | Mô tả                          |
| -------- | ------------------------------------- | ---------------- | ------------------------------ |
| `POST`   | `/events/{eventId}/feedbacks`         | User             | Gửi feedback sau sự kiện       |
| `GET`    | `/events/{eventId}/feedbacks`         | Organizer        | Xem danh sách feedback         |
| `GET`    | `/events/{eventId}/feedbacks/summary` | Organizer        | Xem thống kê đánh giá          |
| `PATCH`  | `/feedbacks/{feedbackId}`             | User             | Cập nhật feedback của bản thân |
| `DELETE` | `/feedbacks/{feedbackId}`             | User / Organizer | Xóa feedback                   |

Body ví dụ:

```json
{
  "rating": 5,
  "comment": "Sự kiện rất hữu ích.",
  "isAnonymous": true
}
```

---
