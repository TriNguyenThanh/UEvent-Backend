from rest_framework.pagination import PageNumberPagination

from common.responses import success_response


class EnvelopePageNumberPagination(PageNumberPagination):
    """Pagination chuẩn trả dữ liệu list trong envelope chung."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request) or self.page.paginator.per_page
        pagination = {
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "page": self.page.number,
            "page_size": page_size,
            "total_pages": self.page.paginator.num_pages,
        }
        return success_response(
            data=data,
            message="Lấy danh sách dữ liệu thành công.",
            meta={"pagination": pagination},
        )
