# 5. API quản lý tổ chức / câu lạc bộ

| Method   | Endpoint                                                | Quyền             | Mô tả                       |
| -------- | ------------------------------------------------------- | ----------------- | --------------------------- |
| `GET`    | `/organizations`                                        | User              | Xem danh sách tổ chức/CLB   |
| `GET`    | `/organizations/{organizationId}`                       | User              | Xem chi tiết tổ chức/CLB    |
| `POST`   | `/organizations`                                        | Admin             | Tạo tổ chức/CLB             |
| `PATCH`  | `/organizations/{organizationId}`                       | Admin / Organizer | Cập nhật thông tin tổ chức  |
| `DELETE` | `/organizations/{organizationId}`                       | Admin             | Xóa tổ chức/CLB             |
| `GET`    | `/organizations/{organizationId}/members`               | Organizer         | Xem danh sách thành viên    |
| `POST`   | `/organizations/{organizationId}/members`               | Organizer         | Thêm thành viên             |
| `DELETE` | `/organizations/{organizationId}/members/{userId}`      | Organizer         | Xóa thành viên khỏi tổ chức |
| `PATCH`  | `/organizations/{organizationId}/members/{userId}/role` | Organizer         | Cập nhật vai trò thành viên |

---
