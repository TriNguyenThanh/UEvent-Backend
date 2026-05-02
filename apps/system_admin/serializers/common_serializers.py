from rest_framework import serializers


class AdminErrorResponseSerializer(serializers.Serializer):
    """Schema lỗi chuẩn cho admin API."""

    code = serializers.CharField(help_text="Mã lỗi máy đọc được, ví dụ: validation_error.")
    message = serializers.CharField(help_text="Thông báo lỗi thân thiện với client.")
    details = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Chi tiết lỗi validation hoặc metadata liên quan.",
    )
    request_id = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="ID request hoặc trace ID để đối chiếu log/OpenSearch.",
    )


class AdminCsvExportResponseSerializer(serializers.Serializer):
    """Schema mô tả response export CSV."""

    file = serializers.CharField(help_text="CSV file trả về qua attachment response.")
