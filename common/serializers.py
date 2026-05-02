from rest_framework import serializers


class ApiResponseSerializer(serializers.Serializer):
    """Envelope response chuẩn dùng chung cho toàn backend."""

    success = serializers.BooleanField(help_text="Response thành công hay thất bại.")
    code = serializers.CharField(help_text="Mã response ổn định cho client.")
    message = serializers.CharField(help_text="Thông báo ngắn, an toàn để hiển thị nếu cần.")
    data = serializers.JSONField(required=False, allow_null=True, help_text="Payload chính khi success=true.")
    errors = serializers.JSONField(required=False, allow_null=True, help_text="Chi tiết lỗi khi success=false.")
    meta = serializers.JSONField(required=False, help_text="Metadata như request_id, pagination, export.")


class ApiSuccessResponseSerializer(ApiResponseSerializer):
    """Schema success response theo envelope chuẩn."""


class ApiErrorResponseSerializer(ApiResponseSerializer):
    """Schema error response theo envelope chuẩn."""


class PaginationMetaSerializer(serializers.Serializer):
    count = serializers.IntegerField(help_text="Tổng số bản ghi.")
    next = serializers.CharField(allow_null=True, help_text="URL trang tiếp theo.")
    previous = serializers.CharField(allow_null=True, help_text="URL trang trước.")
    page = serializers.IntegerField(help_text="Trang hiện tại.")
    page_size = serializers.IntegerField(help_text="Số bản ghi mỗi trang.")
    total_pages = serializers.IntegerField(help_text="Tổng số trang.")


class PaginatedApiResponseSerializer(ApiSuccessResponseSerializer):
    """Schema list response có pagination trong meta.pagination."""


class CsvExportResponseSerializer(serializers.Serializer):
    """Schema mô tả response export CSV."""

    file = serializers.CharField(help_text="CSV file trả về qua attachment response.")
