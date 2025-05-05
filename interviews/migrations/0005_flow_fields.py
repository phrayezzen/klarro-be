from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0004_alter_candidate_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="flow",
            name="role_name",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="flow",
            name="role_description",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="flow",
            name="role_function",
            field=models.CharField(
                choices=[
                    ("business_ops", "Business & Operations"),
                    ("sales_cs", "Sales & Customer Success"),
                    ("marketing_growth", "Marketing & Growth"),
                    ("product_design", "Product & Design"),
                    ("engineering_data", "Engineering & Data"),
                    ("people_hr", "People & HR"),
                    ("finance_legal", "Finance & Legal"),
                    ("support_services", "Support & Services"),
                    ("science_research", "Science & Research"),
                    ("executive_leadership", "Executive & Leadership"),
                ],
                default="business_ops",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="flow",
            name="location",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="flow",
            name="is_remote_allowed",
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveField(
            model_name="flow",
            name="role",
        ),
    ]
