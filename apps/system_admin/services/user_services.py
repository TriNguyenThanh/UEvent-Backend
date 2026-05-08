from django.db import transaction
from django.db.models import Count, QuerySet
from django.db.models.functions import TruncDate
from django.utils import timezone
from apps.users.models import User, Role, UserRole
from common.exceptions import NotFoundError, ValidationError
from .audit_service import AdminAuditService


class AdminUserService:

    @staticmethod
    def _users_with_related() -> QuerySet[User]:
        return User.all_objects.prefetch_related('user_roles__role', 'sessions')

    @staticmethod
    def _sync_user_roles(*, user: User, actor, role_codes: list[str]) -> None:
        """
        Đồng bộ hoá danh sách roles của user theo role_codes đầu vào.

        Strategy (tối ưu cho SoftDelete + UniqueConstraint):
        - UserRole là bảng nối (junction), KHÔNG cần soft-delete → dùng hard_delete.
        - Dùng all_objects để thao tác trên toàn bộ rows (kể cả đã soft-delete)
          tránh vi phạm UniqueConstraint khi tạo mới.
        - Primary role: giữ nguyên nếu vẫn nằm trong danh sách mới,
          nếu không thì chọn role đầu tiên trong danh sách.
        """
        # Deduplicate giữ thứ tự
        deduped_codes = list(dict.fromkeys(role_codes))

        # Validate tất cả role codes tồn tại
        roles = Role.objects.filter(code__in=deduped_codes)
        role_map = {r.code: r for r in roles}
        missing = [c for c in deduped_codes if c not in role_map]
        if missing:
            raise NotFoundError(f"Role(s) do not exist: {', '.join(missing)}")

        # Lock + lấy TẤT CẢ rows (kể cả soft-deleted) để tránh race condition
        existing_rows = {
            ur.role.code: ur
            for ur in UserRole.all_objects
                .select_for_update()
                .select_related("role")
                .filter(user=user)
        }

        # Xác định primary: giữ primary cũ nếu còn trong list, nếu không → phần tử đầu
        old_primary_code = next(
            (code for code, ur in existing_rows.items() if ur.is_primary and ur.deleted_at is None),
            None,
        )
        target_primary = (
            old_primary_code if old_primary_code in deduped_codes
            else (deduped_codes[0] if deduped_codes else None)
        )

        # 1) Hard-delete rows không còn trong danh sách mới
        codes_to_remove = set(existing_rows.keys()) - set(deduped_codes)
        if codes_to_remove:
            UserRole.all_objects.filter(user=user, role__code__in=codes_to_remove).delete()

        # 2) Restore hoặc tạo mới rows cần có
        for code in deduped_codes:
            ur = existing_rows.get(code)
            if ur is not None:
                # Row đã tồn tại (có thể đang soft-deleted) → restore + cập nhật
                needs_save = False
                if ur.deleted_at is not None:
                    ur.deleted_at = None
                    needs_save = True
                new_primary = (code == target_primary)
                if ur.is_primary != new_primary:
                    ur.is_primary = new_primary
                    needs_save = True
                if needs_save:
                    ur.save(update_fields=["deleted_at", "is_primary", "updated_at"])
            else:
                # Row chưa tồn tại → tạo mới
                UserRole(
                    user=user,
                    role=role_map[code],
                    assigned_by=actor,
                    is_primary=(code == target_primary),
                ).save()

        # 3) Nếu deduped_codes rỗng (xoá hết roles) → đã hard_delete ở bước 1

    @staticmethod
    def _log_audit(*, action, actor, target_user_id, reason="", metadata=None):
        AdminAuditService.log_action(
            action=action,
            actor=actor,
            target_type="users.User",
            target_id=str(target_user_id),
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def get_user_statistics() -> dict:
        """Thống kê tổng quan về user cho Admin Dashboard."""
        alive_qs = User.objects.all()  # SoftDeleteManager → chỉ user chưa bị xoá
        all_qs = User.all_objects.all()

        total_users = alive_qs.count()
        total_deleted = all_qs.filter(deleted_at__isnull=False).count()

        # Phân bổ theo account_status
        by_status = dict(
            alive_qs.values_list('account_status')
            .annotate(count=Count('id'))
            .values_list('account_status', 'count')
        )

        # Phân bổ theo faculty (top 10, bỏ null/blank)
        by_faculty = list(
            alive_qs
            .exclude(faculty__isnull=True)
            .exclude(faculty='')
            .values('faculty')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Phân bổ theo role
        by_role = list(
            UserRole.objects.filter(user__deleted_at__isnull=True)
            .values('role__code', 'role__name')
            .annotate(count=Count('user_id', distinct=True))
            .order_by('-count')
        )

        # User mới đăng ký theo ngày (30 ngày gần nhất)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        new_users_per_day = list(
            alive_qs
            .filter(created_at__gte=thirty_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return {
            'total_users': total_users,
            'total_deleted': total_deleted,
            'by_status': {
                'active': by_status.get('active', 0),
                'pending': by_status.get('pending', 0),
                'banned': by_status.get('banned', 0),
            },
            'by_faculty': by_faculty,
            'by_role': by_role,
            'new_users_per_day': new_users_per_day,
        }

    @staticmethod
    def list_users() -> QuerySet[User]:
        return AdminUserService._users_with_related().filter(deleted_at__isnull=True)

    @staticmethod
    def get_user(user_id) -> User:
        try:
            return AdminUserService._users_with_related().get(pk=user_id)
        except User.DoesNotExist as exc:
            raise NotFoundError(f"User with ID {user_id} does not exist.") from exc

    @staticmethod
    @transaction.atomic
    def update_user(*, actor, user_id, data: dict) -> User:
        user = AdminUserService.get_user(user_id)
        role_codes = data.pop("role_codes", None)
        
        # update fields here (only allowed fields should be passed by serializer)
        for field, value in data.items():
            setattr(user, field, value)
            
        if data:
            user.save()

        if role_codes is not None:
            AdminUserService._sync_user_roles(user=user, actor=actor, role_codes=role_codes)
        
        AdminUserService._log_audit(
            action="update_user",
            actor=actor,
            target_user_id=user_id,
            metadata={
                "updated_fields": list(data.keys()),
                "role_codes": role_codes if role_codes is not None else None,
            }
        )
        return AdminUserService.get_user(user_id)

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
        return AdminUserService.get_user(target_user_id)

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
        return AdminUserService.get_user(target_user_id)
