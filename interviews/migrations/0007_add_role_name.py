from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("interviews", "0006_remove_flow_description_remove_flow_name_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            # Check if column exists before adding it
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name='interviews_flow' 
                    AND column_name='role_name'
                ) THEN
                    ALTER TABLE interviews_flow ADD COLUMN role_name varchar(255) NOT NULL DEFAULT '';
                END IF;
            END $$;
            """,
            reverse_sql="ALTER TABLE interviews_flow DROP COLUMN IF EXISTS role_name;",
        ),
    ]
