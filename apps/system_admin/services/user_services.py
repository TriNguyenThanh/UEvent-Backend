import logging
from django.db import transaction
from django.db.models import QuerySet
from apps.users.models import User, Role, UserRole
from common.exceptions import NotFoundError, ValidationError

audit_logger = logging.getLogger("uevent.audit")


class AdminUserService:

    @staticmethod
    def _log_audit(*, action, actor, target_user_id, reason="", metadata=None):
        audit_logger.info(
            f"Admin action: {action}",
            extra={
                "action_type": action,
                "actor_id": str(getattr(actor, 'pk', '')),
                "target_type": "users.User",
                "target_id": str(target_user_id),
                "reason": reason,
                "system_module": "system_admin",
                **(metadata or {}),
            },
        )

    @staticmethod
    def list_users() -> QuerySet[User]:
        # prefetch user_roles for optimal queries
        return User.objects.all().prefetch_related('user_roles__role')

    @staticmethod
    def get_user(user_id) -> User:
        try:
            return User.all_objects.prefetch_related('user_roles__role').get(pk=user_id)
        except User.DoesNotExist as exc:
            raise NotFoundError(f"User with ID {user_id} does not exist.") from exc

    @staticmethod
    @transaction.atomic
    def update_user(*, actor, user_id, data: dict) -> User:
        user = AdminUserService.get_user(user_id)
        
        # update fields here (only allowed fields should be passed by serializer)
        for field, value in data.items():
            setattr(user, field, value)
            
        user.save()
        
        AdminUserService._log_audit(
            action="update_user",
            actor=actor,
            target_user_id=user_id,
            metadata={"updated_fields": list(data.keys())}
        )
        return user

    @staticmethod
    @transaction.atomic
    def ban_user(*, actor, target_user_id, reason: str) -> User:
        user = AdminUserService.get_user(target_user_id)
        
        if user.account_status == User.AccountStatus.BANNED:
            raise ValidationError(f"User '{user.username}' is already banned.")
            
        user.account_status = User.AccountStatus.BANNED
        user.save(update_fields=['account_status', 'updated_at'])
        
        AdminUserService._log_audit(
            action="ban_user",
            actor=actor,
            target_user_id=target_user_id,
            reason=reason,
            metadata={"new_status": "banned"}
        )
        return user

    @staticmethod
    @transaction.atomic
    def unban_user(*, actor, target_user_id, reason: str) -> User:
        user = AdminUserService.get_user(target_user_id)
        
        if user.account_status != User.AccountStatus.BANNED:
            raise ValidationError(f"User '{user.username}' is not banned.")
            
        user.account_status = User.AccountStatus.ACTIVE
        user.save(update_fields=['account_status', 'updated_at'])
        
        AdminUserService._log_audit(
            action="unban_user",
            actor=actor,
            target_user_id=target_user_id,
            reason=reason,
            metadata={"new_status": "active"}
        )
        return user

    @staticmethod
    @transaction.atomic
    def soft_delete_user(*, actor, target_user_id, reason: str) -> User:
        user = AdminUserService.get_user(target_user_id)
        
        if user.deleted_at is not None:
            raise ValidationError(f"User '{user.username}' is already soft deleted.")
            
        user.delete()
        
        AdminUserService._log_audit(
            action="soft_delete_user",
            actor=actor,
            target_user_id=target_user_id,
            reason=reason
        )
        return user

    @staticmethod
    @transaction.atomic
    def restore_user(*, actor, target_user_id) -> User:
        user = AdminUserService.get_user(target_user_id)
            
        if user.deleted_at is None:
            raise ValidationError(f"User '{user.username}' is not deleted.")
            
        user.restore()
        
        AdminUserService._log_audit(
            action="restore_user",
            actor=actor,
            target_user_id=target_user_id
        )
        return user

    @staticmethod
    @transaction.atomic
    def assign_role(*, actor, target_user_id, role_code: str) -> User:
        user = AdminUserService.get_user(target_user_id)
        
        try:
            role = Role.objects.get(code=role_code)
        except Role.DoesNotExist as exc:
            raise NotFoundError(f"Role '{role_code}' does not exist.") from exc
            
        if UserRole.objects.filter(user=user, role=role).exists():
            raise ValidationError(f"User '{user.username}' already has role '{role_code}'.")
            
        # Nếu chưa có role nào, mark là primary
        is_primary = not UserRole.objects.filter(user=user).exists()
            
        UserRole.objects.create(
            user=user,
            role=role,
            assigned_by=actor,
            is_primary=is_primary
        )
        
        AdminUserService._log_audit(
            action="assign_role",
            actor=actor,
            target_user_id=target_user_id,
            metadata={"role_code": role_code}
        )
        return user

    @staticmethod
    @transaction.atomic
    def remove_role(*, actor, target_user_id, role_code: str) -> User:
        user = AdminUserService.get_user(target_user_id)
        
        try:
            role = Role.objects.get(code=role_code)
        except Role.DoesNotExist as exc:
            raise NotFoundError(f"Role '{role_code}' does not exist.") from exc
            
        try:
            user_role = UserRole.objects.get(user=user, role=role)
        except UserRole.DoesNotExist as exc:
            raise NotFoundError(f"User '{user.username}' does not have role '{role_code}'.") from exc
            
        if user_role.is_primary:
            raise ValidationError("Cannot remove primary role. Set another role as primary first.")
            
        user_role.delete()
        
        AdminUserService._log_audit(
            action="remove_role",
            actor=actor,
            target_user_id=target_user_id,
            metadata={"role_code": role_code}
        )
        return user
