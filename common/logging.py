from datetime import datetime

from opentelemetry import trace
from pythonjsonlogger import jsonlogger


SENSITIVE_LOG_KEYS = {
    "authorization",
    "access",
    "access_token",
    "refresh",
    "refresh_token",
    "token",
    "password",
    "secret",
    "api_key",
}
MASK_VALUE = "***REDACTED***"


def mask_sensitive_log_fields(value):
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in SENSITIVE_LOG_KEYS:
                masked[key_text] = MASK_VALUE
            else:
                masked[key_text] = mask_sensitive_log_fields(item)
        return masked

    if isinstance(value, list):
        return [mask_sensitive_log_fields(item) for item in value]

    return value


class TraceIdJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        if "timestamp" not in log_record:
            log_record["timestamp"] = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"

        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)

        span = trace.get_current_span()
        span_context = span.get_span_context() if span is not None else None

        if span_context and span_context.is_valid:
            log_record["trace_id"] = format(span_context.trace_id, "032x")
            log_record["span_id"] = format(span_context.span_id, "016x")
        else:
            log_record["trace_id"] = None
            log_record["span_id"] = None

        for key, value in list(log_record.items()):
            if str(key).lower() in SENSITIVE_LOG_KEYS:
                log_record[key] = MASK_VALUE
            else:
                log_record[key] = mask_sensitive_log_fields(value)
