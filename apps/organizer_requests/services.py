from __future__ import annotations

import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.system_admin.services.audit_service import AdminAuditService
from apps.notifications.services.system_notification_service import SystemNotificationService
from apps.organizer_requests.models import OrganizerRequest
from apps.users.models import Role, User, UserRole
from apps.utils.s3 import S3Client
from common.exceptions import NotFoundError, ValidationError


class OrganizerRequestService:
    @staticmethod
    def _requests_with_related() -> QuerySet[OrganizerRequest]:
        return OrganizerRequest.objects.select_related("user", "reviewed_by")

    @staticmethod
    def _user_has_organizer_role(user: User) -> bool:
        return UserRole.objects.filter(user=user, role__code="organizer").exists()

    @staticmethod
    def create_proof_upload_url(*, actor: User, file_name: str, content_type: str) -> dict:
        object_key = f"organizer-requests/{actor.id}/{uuid.uuid4().hex}-{file_name}"
        expires_in = settings.AWS_S3_PRESIGNED_URL_EXPIRES
        presigned_url = S3Client().generate_presigned_url(
            object_key,
            method="put_object",
            expires_in=expires_in,
            params={"ContentType": content_type},
        )
        return {
            "object_key": object_key,
            "presigned_upload_url": presigned_url,
            "presigned_url": presigned_url,
            "method": "PUT",
            "expires_in": expires_in,
        }

    @classmethod
    @transaction.atomic
    def create_request(cls, *, actor: User, data: dict) -> OrganizerRequest:
        if actor.account_status == User.AccountStatus.BANNED:
            raise ValidationError("Tài khoản bị khóa không thể gửi yêu cầu.")

        if cls._user_has_organizer_role(actor):
            raise ValidationError("Bạn đã có quyền tổ chức sự kiện.")

        if OrganizerRequest.objects.filter(
            user=actor,
            status=OrganizerRequest.Status.PENDING,
        ).exists():
            raise ValidationError("Bạn đang có yêu cầu chờ duyệt.")

        request = OrganizerRequest.objects.create(user=actor, **data)
        return cls.get_request_for_user(actor=actor, request_id=request.pk)

    @classmethod
    def list_my_requests(cls, *, actor: User) -> QuerySet[OrganizerRequest]:
        return cls._requests_with_related().filter(user=actor).order_by("-created_at")

    @classmethod
    def get_current_request(cls, *, actor: User) -> OrganizerRequest | None:
        return cls.list_my_requests(actor=actor).first()

    @classmethod
    def get_request_for_user(cls, *, actor: User, request_id) -> OrganizerRequest:
        try:
            return cls._requests_with_related().get(pk=request_id, user=actor)
        except OrganizerRequest.DoesNotExist as exc:
            raise NotFoundError("Không tìm thấy yêu cầu tổ chức sự kiện.") from exc

    @classmethod
    @transaction.atomic
    def cancel_request(cls, *, actor: User, request_id) -> OrganizerRequest:
        request = (
            OrganizerRequest.objects.select_for_update()
            .select_related("user")
            .filter(pk=request_id, user=actor)
            .first()
        )
        if request is None:
            raise NotFoundError("Không tìm thấy yêu cầu tổ chức sự kiện.")
        if request.status != OrganizerRequest.Status.PENDING:
            raise ValidationError("Chỉ có thể hủy yêu cầu đang chờ duyệt.")

        request.status = OrganizerRequest.Status.CANCELLED
        request.save(update_fields=["status", "updated_at"])
        return cls.get_request_for_user(actor=actor, request_id=request_id)

    @classmethod
    def list_requests(
        cls,
        *,
        status: str | None = None,
        search: str | None = None,
        ordering: str | None = None,
    ) -> QuerySet[OrganizerRequest]:
        queryset = cls._requests_with_related()
        if status:
            queryset = queryset.filter(status=status)
        if search:
            keyword = search.strip()
            queryset = queryset.filter(
                Q(user__username__icontains=keyword)
                | Q(user__email__icontains=keyword)
                | Q(user__full_name__icontains=keyword)
                | Q(proof_file_name__icontains=keyword)
            )

        valid_ordering = {"created_at", "-created_at", "reviewed_at", "-reviewed_at", "status", "-status"}
        return queryset.order_by(ordering if ordering in valid_ordering else "-created_at")

    @classmethod
    def get_request(cls, request_id) -> OrganizerRequest:
        try:
            return cls._requests_with_related().get(pk=request_id)
        except OrganizerRequest.DoesNotExist as exc:
            raise NotFoundError("Không tìm thấy yêu cầu tổ chức sự kiện.") from exc

    @staticmethod
    def get_statistics() -> dict:
        counts = dict(
            OrganizerRequest.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        return {
            "pending": counts.get(OrganizerRequest.Status.PENDING, 0),
            "approved": counts.get(OrganizerRequest.Status.APPROVED, 0),
            "rejected": counts.get(OrganizerRequest.Status.REJECTED, 0),
            "cancelled": counts.get(OrganizerRequest.Status.CANCELLED, 0),
            "total": sum(counts.values()),
        }

    @classmethod
    @transaction.atomic
    def approve_request(cls, *, actor: User, request_id, note: str = "") -> OrganizerRequest:
        try:
            request = (
                OrganizerRequest.objects.select_for_update()
                .select_related("user")
                .get(pk=request_id)
            )
        except OrganizerRequest.DoesNotExist as exc:
            raise NotFoundError("Không tìm thấy yêu cầu tổ chức sự kiện.") from exc
        if request.status != OrganizerRequest.Status.PENDING:
            raise ValidationError("Chỉ có thể duyệt yêu cầu đang chờ xử lý.")

        role = Role.objects.filter(code="organizer", is_active=True).first()
        if role is None:
            raise NotFoundError("Role organizer chưa được cấu hình.")

        list(UserRole.all_objects.select_for_update().filter(user=request.user))
        UserRole.all_objects.filter(user=request.user, is_primary=True).exclude(role=role).update(
            is_primary=False,
            updated_at=timezone.now(),
        )
        user_role = (
            UserRole.all_objects.select_for_update()
            .filter(user=request.user, role=role)
            .first()
        )
        if user_role is None:
            UserRole.objects.create(
                user=request.user,
                role=role,
                assigned_by=actor,
                is_primary=True,
            )
        else:
            update_fields = ["assigned_by", "assigned_at", "updated_at"]
            user_role.assigned_by = actor
            user_role.assigned_at = timezone.now()
            if user_role.deleted_at is not None:
                user_role.deleted_at = None
                update_fields.append("deleted_at")
            if not user_role.is_primary:
                user_role.is_primary = True
                update_fields.append("is_primary")
            user_role.save(update_fields=update_fields)

        request.status = OrganizerRequest.Status.APPROVED
        request.reviewed_by = actor
        request.reviewed_at = timezone.now()
        request.review_note = note
        request.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])

        AdminAuditService.log_action(
            action="approve_organizer_request",
            actor=actor,
            target_type="organizer_requests.OrganizerRequest",
            target_id=str(request.pk),
            reason=note,
            metadata={"target_user_id": str(request.user_id), "new_status": request.status},
        )

        transaction.on_commit(lambda: SystemNotificationService.notify_organizer_request_approved(request))

        return cls.get_request(request.pk)

    @classmethod
    @transaction.atomic
    def reject_request(cls, *, actor: User, request_id, note: str = "") -> OrganizerRequest:
        try:
            request = (
                OrganizerRequest.objects.select_for_update()
                .select_related("user")
                .get(pk=request_id)
            )
        except OrganizerRequest.DoesNotExist as exc:
            raise NotFoundError("Không tìm thấy yêu cầu tổ chức sự kiện.") from exc
        if request.status != OrganizerRequest.Status.PENDING:
            raise ValidationError("Chỉ có thể từ chối yêu cầu đang chờ xử lý.")

        request.status = OrganizerRequest.Status.REJECTED
        request.reviewed_by = actor
        request.reviewed_at = timezone.now()
        request.review_note = note
        request.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])

        AdminAuditService.log_action(
            action="reject_organizer_request",
            actor=actor,
            target_type="organizer_requests.OrganizerRequest",
            target_id=str(request.pk),
            reason=note,
            metadata={"target_user_id": str(request.user_id), "new_status": request.status},
        )

        transaction.on_commit(lambda: SystemNotificationService.notify_organizer_request_rejected(request))

        return cls.get_request(request.pk)
