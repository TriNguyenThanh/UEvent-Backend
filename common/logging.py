from datetime import datetime

from opentelemetry import trace
from pythonjsonlogger import jsonlogger


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
