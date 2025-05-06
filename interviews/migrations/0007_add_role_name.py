from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("interviews", "0006_remove_flow_description_remove_flow_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="flow",
            name="role_name",
            field=models.CharField(max_length=255, default=""),
            preserve_default=False,
        ),
    ]
