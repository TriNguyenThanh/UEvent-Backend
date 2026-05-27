from django.db import models

from .support_ticket import SupportTicket
from .support_message import SupportMessage
from .support_category import SupportCategory
from .support_article import SupportArticle
from .legal_document import LegalDocument

__all__ = [
    "SupportTicket",
    "SupportMessage",
    "SupportCategory",
    "SupportArticle",
    "LegalDocument",
]
