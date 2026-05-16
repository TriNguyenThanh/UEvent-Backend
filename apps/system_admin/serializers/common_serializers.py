from common.serializers import ApiErrorResponseSerializer, CsvExportResponseSerializer


class AdminErrorResponseSerializer(ApiErrorResponseSerializer):
    """Schema lỗi chuẩn cho admin API theo envelope chung."""


class AdminCsvExportResponseSerializer(CsvExportResponseSerializer):
    """Schema mô tả response export CSV."""
