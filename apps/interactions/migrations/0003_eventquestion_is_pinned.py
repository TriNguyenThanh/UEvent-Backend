from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("interactions", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventquestion",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="eventquestion",
            index=models.Index(
                fields=["event", "is_pinned", "moderation_status"],
                name="event_quest_event_i_298ad0_idx",
            ),
        ),
    ]
