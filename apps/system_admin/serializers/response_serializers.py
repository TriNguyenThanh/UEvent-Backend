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
