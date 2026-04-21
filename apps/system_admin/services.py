from django.db import transaction
from apps.users.models import User
from common.exceptions import NotFoundError
from .models import AdminActionLog

class AdminUserService:

    @staticmethod
    @transaction.atomic
    def ban_user(*, actor, target_user_id, reason: str):

        try:
            user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist as exc:
            raise NotFoundError(f"User with ID {target_user_id} does not exist.") from exc
        
        if user.account_status == User.AccountStatus.BANNED:
            raise ValueError(f"User '{user.username}' is already banned.")

        user.account_status = User.AccountStatus.BANNED

        user.save(update_fields=['account_status', 'updated_at'])

        # AdminActionLog.objects.create(
        #     actor=actor,
        #     action='ban_user',
        #     target_type='users.User',
        #     target_id=str(target_user_id),
        #     reason=reason,
        #     metadata={'new_status': 'banned'}
        # )

        return user

