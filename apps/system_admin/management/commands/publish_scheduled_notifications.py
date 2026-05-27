from django.core.management.base import BaseCommand, CommandError

from apps.system_admin.services.notification_services import AdminNotificationService


class Command(BaseCommand):
    help = "Gửi các thông báo đã lên lịch và đã đến thời điểm gửi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Số thông báo tối đa được xử lý trong một lần chạy.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size <= 0:
            raise CommandError("--batch-size phải lớn hơn 0.")

        result = AdminNotificationService.publish_due_scheduled_notifications(batch_size=batch_size)
        self.stdout.write(
            self.style.SUCCESS(
                "Đã gửi {published_count} thông báo đến hạn. Còn {remaining_due} thông báo đến hạn chưa xử lý.".format(
                    **result
                )
            )
        )
