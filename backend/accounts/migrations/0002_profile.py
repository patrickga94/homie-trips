from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="display_name",
            new_name="preferred_name",
        ),
        migrations.AddField(
            model_name="user",
            name="dietary_restrictions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
