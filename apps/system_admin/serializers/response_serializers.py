from common.serializers import ApiErrorResponseSerializer, ApiSuccessResponseSerializer, PaginatedApiResponseSerializer


class AdminLoginEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin login."""


class AdminLogoutEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin logout."""


class AdminUserInfoEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin me."""


class AdminUserEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin user detail/action."""


class AdminUserListEnvelopeResponseSerializer(PaginatedApiResponseSerializer):
    """Envelope response cho admin user list."""


class AdminUserStatisticsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin user statistics."""


class AdminExportJobEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin export job."""


class AdminCategoryEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin category detail/action."""


class AdminCategoryListEnvelopeResponseSerializer(PaginatedApiResponseSerializer):
    """Envelope response cho admin category list."""


class AdminCategoryStatisticsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin category statistics."""


class AdminEventEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin event detail/action."""


class AdminEventListEnvelopeResponseSerializer(PaginatedApiResponseSerializer):
    """Envelope response cho admin event list."""


class AdminEventStatisticsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin event statistics."""


class AdminEventModerationPulseEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin event moderation pulse."""


class AdminEventModerationActivitiesEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin event moderation activities."""


class AdminEventPolicyHandbookEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin event policy handbook."""


class AdminSupportTicketEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin support ticket detail/action."""


class AdminSupportTicketListEnvelopeResponseSerializer(PaginatedApiResponseSerializer):
    """Envelope response cho admin support ticket list."""


class AdminSupportTicketStatisticsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin support ticket statistics."""


class AdminNotificationEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin notification detail/action."""


class AdminNotificationListEnvelopeResponseSerializer(PaginatedApiResponseSerializer):
    """Envelope response cho admin notification list."""


class AdminNotificationStatisticsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin notification statistics."""


class AdminSettingsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin settings."""


class AdminAuditListEnvelopeResponseSerializer(PaginatedApiResponseSerializer):
    """Envelope response cho admin audit log list."""


class AdminAuditSummaryEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin audit summary."""


class AdminDashboardOverviewEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin dashboard overview."""


class AdminDashboardStatsEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin dashboard stats."""


class AdminDashboardGrowthEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin dashboard growth."""


class AdminDashboardQueueEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin dashboard queue."""


class AdminDashboardAuditSummaryEnvelopeResponseSerializer(ApiSuccessResponseSerializer):
    """Envelope response cho admin dashboard audit summary."""
