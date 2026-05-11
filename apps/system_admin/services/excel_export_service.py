from collections.abc import Iterable, Mapping, Sequence
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook


class AdminExcelExportService:
    """Helper tạo response Excel XLSX dùng chung cho admin export endpoints."""

    DEFAULT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @classmethod
    def build_response(
        cls,
        *,
        filename: str,
        headers: Sequence[str],
        rows: Iterable[Mapping[str, object]],
        sheet_name: str = "Export",
    ) -> HttpResponse:
        safe_filename = cls._sanitize_filename(filename)
        response = HttpResponse(
            cls.build_bytes(headers=headers, rows=rows, sheet_name=sheet_name),
            content_type=cls.DEFAULT_CONTENT_TYPE,
        )
        response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
        return response

    @classmethod
    def build_bytes(
        cls,
        *,
        headers: Sequence[str],
        rows: Iterable[Mapping[str, object]],
        sheet_name: str = "Export",
    ) -> bytes:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name[:31] or "Export"

        worksheet.append(list(headers))
        for row in rows:
            worksheet.append([cls._stringify(row.get(key, "")) for key in headers])

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        cleaned = "".join(char for char in filename if char.isalnum() or char in {"-", "_", "."})
        if not cleaned.endswith(".xlsx"):
            cleaned = f"{cleaned.removesuffix('.csv') or 'export'}.xlsx"
        return cleaned

    @staticmethod
    def _stringify(value: object) -> str:
        if value is None:
            return ""
        return str(value)
