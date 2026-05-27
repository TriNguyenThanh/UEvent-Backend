import csv
from collections.abc import Iterable, Mapping, Sequence
from io import StringIO

from django.http import HttpResponse


class AdminCsvExportService:
    """Helper tạo response CSV dùng chung cho admin export endpoints."""

    DEFAULT_CONTENT_TYPE = "text/csv; charset=utf-8"

    @classmethod
    def build_response(
        cls,
        *,
        filename: str,
        headers: Sequence[str],
        rows: Iterable[Mapping[str, object]],
    ) -> HttpResponse:
        safe_filename = cls._sanitize_filename(filename)
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(headers), extrasaction="ignore")
        writer.writeheader()

        for row in rows:
            writer.writerow({key: cls._stringify(row.get(key, "")) for key in headers})

        response = HttpResponse(buffer.getvalue(), content_type=cls.DEFAULT_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
        return response

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        cleaned = "".join(char for char in filename if char.isalnum() or char in {"-", "_", "."})
        if not cleaned.endswith(".csv"):
            cleaned = f"{cleaned or 'export'}.csv"
        return cleaned

    @staticmethod
    def _stringify(value: object) -> str:
        if value is None:
            return ""
        return str(value)
