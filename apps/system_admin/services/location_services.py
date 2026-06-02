from django.db import transaction
from django.db.models import Count, Q, QuerySet, Sum
from django.utils import timezone

from apps.events.models import Event
from apps.locations.models import Building, Campus, Room
from common.exceptions import NotFoundError

from .audit_service import AdminAuditService


class AdminLocationService:
    @staticmethod
    def _campus_counts() -> dict[str, Count]:
        return {
            "building_count": Count(
                "buildings",
                filter=Q(buildings__deleted_at__isnull=True),
                distinct=True,
            ),
            "room_count": Count(
                "buildings__rooms",
                filter=Q(
                    buildings__deleted_at__isnull=True,
                    buildings__rooms__deleted_at__isnull=True,
                ),
                distinct=True,
            ),
            "event_count": Count(
                "buildings__rooms__events",
                filter=Q(
                    buildings__deleted_at__isnull=True,
                    buildings__rooms__deleted_at__isnull=True,
                    buildings__rooms__events__deleted_at__isnull=True,
                ),
                distinct=True,
            ),
        }

    @staticmethod
    def _building_counts() -> dict[str, Count]:
        return {
            "room_count": Count(
                "rooms",
                filter=Q(rooms__deleted_at__isnull=True),
                distinct=True,
            ),
            "event_count": Count(
                "rooms__events",
                filter=Q(
                    rooms__deleted_at__isnull=True,
                    rooms__events__deleted_at__isnull=True,
                ),
                distinct=True,
            ),
        }

    @staticmethod
    def _room_counts() -> dict[str, Count]:
        return {
            "event_count": Count(
                "events",
                filter=Q(events__deleted_at__isnull=True),
                distinct=True,
            ),
        }

    @staticmethod
    def _log_audit(*, action, actor, target_type, target_id, reason="", metadata=None):
        AdminAuditService.log_action(
            action=action,
            actor=actor,
            target_type=target_type,
            target_id=str(target_id),
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_campuses() -> QuerySet[Campus]:
        return Campus.objects.annotate(**AdminLocationService._campus_counts())

    @staticmethod
    def get_campus(campus_id) -> Campus:
        try:
            return AdminLocationService.list_campuses().get(pk=campus_id)
        except Campus.DoesNotExist as exc:
            raise NotFoundError(f"Campus with ID {campus_id} does not exist.") from exc

    @staticmethod
    @transaction.atomic
    def create_campus(*, actor, data: dict) -> Campus:
        campus = Campus.objects.create(**data)
        AdminLocationService._log_audit(
            action="create_campus",
            actor=actor,
            target_type="locations.Campus",
            target_id=campus.pk,
            metadata={"created_fields": list(data.keys())},
        )
        return AdminLocationService.get_campus(campus.pk)

    @staticmethod
    @transaction.atomic
    def update_campus(*, actor, campus_id, data: dict) -> Campus:
        campus = AdminLocationService.get_campus(campus_id)
        for field, value in data.items():
            setattr(campus, field, value)

        if data:
            campus.save(update_fields=[*data.keys(), "updated_at"])
            AdminLocationService._log_audit(
                action="update_campus",
                actor=actor,
                target_type="locations.Campus",
                target_id=campus.pk,
                metadata={"updated_fields": list(data.keys())},
            )

        return AdminLocationService.get_campus(campus_id)

    @staticmethod
    @transaction.atomic
    def delete_campus(*, actor, campus_id, reason: str = "") -> None:
        campus = AdminLocationService.get_campus(campus_id)
        building_count = Building.objects.filter(campus=campus).count()
        room_count = Room.objects.filter(building__campus=campus).count()
        event_count = Event.objects.filter(room__building__campus=campus).count()

        if building_count or room_count or event_count:
            now = timezone.now()
            Campus.objects.filter(pk=campus.pk).update(is_active=False, updated_at=now)
            Building.objects.filter(campus=campus).update(is_active=False, updated_at=now)
            Room.objects.filter(building__campus=campus).update(is_active=False, updated_at=now)
            action = "deactivate_campus"
            metadata = {
                "building_count": building_count,
                "room_count": room_count,
                "event_count": event_count,
                "strategy": "set_is_active_false",
            }
        else:
            campus.delete()
            action = "delete_campus"
            metadata = {"strategy": "soft_delete"}

        AdminLocationService._log_audit(
            action=action,
            actor=actor,
            target_type="locations.Campus",
            target_id=campus.pk,
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_buildings() -> QuerySet[Building]:
        return (
            Building.objects.select_related("campus")
            .annotate(**AdminLocationService._building_counts())
        )

    @staticmethod
    def get_building(building_id) -> Building:
        try:
            return AdminLocationService.list_buildings().get(pk=building_id)
        except Building.DoesNotExist as exc:
            raise NotFoundError(f"Building with ID {building_id} does not exist.") from exc

    @staticmethod
    @transaction.atomic
    def create_building(*, actor, data: dict) -> Building:
        building = Building.objects.create(**data)
        AdminLocationService._log_audit(
            action="create_building",
            actor=actor,
            target_type="locations.Building",
            target_id=building.pk,
            metadata={"created_fields": list(data.keys()), "campus_id": str(building.campus_id)},
        )
        return AdminLocationService.get_building(building.pk)

    @staticmethod
    @transaction.atomic
    def update_building(*, actor, building_id, data: dict) -> Building:
        building = AdminLocationService.get_building(building_id)
        for field, value in data.items():
            setattr(building, field, value)

        if data:
            building.save(update_fields=[*data.keys(), "updated_at"])
            AdminLocationService._log_audit(
                action="update_building",
                actor=actor,
                target_type="locations.Building",
                target_id=building.pk,
                metadata={"updated_fields": list(data.keys())},
            )

        return AdminLocationService.get_building(building_id)

    @staticmethod
    @transaction.atomic
    def delete_building(*, actor, building_id, reason: str = "") -> None:
        building = AdminLocationService.get_building(building_id)
        room_count = Room.objects.filter(building=building).count()
        event_count = Event.objects.filter(room__building=building).count()

        if room_count or event_count:
            now = timezone.now()
            Building.objects.filter(pk=building.pk).update(is_active=False, updated_at=now)
            Room.objects.filter(building=building).update(is_active=False, updated_at=now)
            action = "deactivate_building"
            metadata = {
                "room_count": room_count,
                "event_count": event_count,
                "strategy": "set_is_active_false",
            }
        else:
            building.delete()
            action = "delete_building"
            metadata = {"strategy": "soft_delete"}

        AdminLocationService._log_audit(
            action=action,
            actor=actor,
            target_type="locations.Building",
            target_id=building.pk,
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_rooms() -> QuerySet[Room]:
        return (
            Room.objects.select_related("building", "building__campus")
            .annotate(**AdminLocationService._room_counts())
        )

    @staticmethod
    def get_room(room_id) -> Room:
        try:
            return AdminLocationService.list_rooms().get(pk=room_id)
        except Room.DoesNotExist as exc:
            raise NotFoundError(f"Room with ID {room_id} does not exist.") from exc

    @staticmethod
    @transaction.atomic
    def create_room(*, actor, data: dict) -> Room:
        room = Room.objects.create(**data)
        AdminLocationService._log_audit(
            action="create_room",
            actor=actor,
            target_type="locations.Room",
            target_id=room.pk,
            metadata={"created_fields": list(data.keys()), "building_id": str(room.building_id)},
        )
        return AdminLocationService.get_room(room.pk)

    @staticmethod
    @transaction.atomic
    def update_room(*, actor, room_id, data: dict) -> Room:
        room = AdminLocationService.get_room(room_id)
        for field, value in data.items():
            setattr(room, field, value)

        if data:
            room.save(update_fields=[*data.keys(), "updated_at"])
            AdminLocationService._log_audit(
                action="update_room",
                actor=actor,
                target_type="locations.Room",
                target_id=room.pk,
                metadata={"updated_fields": list(data.keys())},
            )

        return AdminLocationService.get_room(room_id)

    @staticmethod
    @transaction.atomic
    def delete_room(*, actor, room_id, reason: str = "") -> None:
        room = AdminLocationService.get_room(room_id)
        event_count = Event.objects.filter(room=room).count()

        if event_count:
            Room.objects.filter(pk=room.pk).update(is_active=False, updated_at=timezone.now())
            action = "deactivate_room"
            metadata = {"event_count": event_count, "strategy": "set_is_active_false"}
        else:
            room.delete()
            action = "delete_room"
            metadata = {"strategy": "soft_delete"}

        AdminLocationService._log_audit(
            action=action,
            actor=actor,
            target_type="locations.Room",
            target_id=room.pk,
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def get_statistics() -> dict:
        total_capacity = Room.objects.aggregate(total=Sum("capacity"))["total"] or 0
        return {
            "total_campuses": Campus.objects.count(),
            "active_campuses": Campus.objects.filter(is_active=True).count(),
            "total_buildings": Building.objects.count(),
            "active_buildings": Building.objects.filter(is_active=True).count(),
            "total_rooms": Room.objects.count(),
            "active_rooms": Room.objects.filter(is_active=True).count(),
            "rooms_with_events": Room.objects.filter(events__isnull=False).distinct().count(),
            "total_capacity": total_capacity,
        }
