from django.db import transaction


class UserService:
    """Business logic for mobile user operations."""

    @staticmethod
    def update_profile(user, validated_data: dict):
        """Update user profile fields from validated PATCH data."""
        update_fields = []

        for field_name in ("full_name", "phone_number", "student_code", "faculty", "class_name"):
            if field_name in validated_data:
                setattr(user, field_name, validated_data[field_name])
                update_fields.append(field_name)

        if update_fields:
            with transaction.atomic():
                user.save(update_fields=update_fields)

        return user
