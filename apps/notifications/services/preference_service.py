from __future__ import annotations

from django.db import transaction

from apps.notifications.models import NotificationPreference


class NotificationPreferenceService:
    @staticmethod
    def get_for_user(*, user) -> NotificationPreference:
        preference, _ = NotificationPreference.objects.get_or_create(user=user)
        return preference

    @staticmethod
    @transaction.atomic
    def update_for_user(*, user, data: dict) -> NotificationPreference:
        preference, _ = (
            NotificationPreference.objects.select_for_update().get_or_create(user=user)
        )
        for field, value in data.items():
            setattr(preference, field, value)
        if data:
            preference.save(update_fields=[*data.keys(), "updated_at"])
        return preference

    @staticmethod
    def allows_push(*, user, category: str, now=None) -> bool:
        preference = NotificationPreferenceService.get_for_user(user=user)
        return preference.allows_push(category=category, now=now)
