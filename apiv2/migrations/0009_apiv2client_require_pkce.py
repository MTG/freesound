from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("apiv2", "0008_rename_allow_oauth_passoword_grant_apiv2client_allow_oauth_password_grant"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # PKCE is optional for existing registrations and required for new ones.
            database_operations=[
                migrations.AddField(
                    model_name="apiv2client",
                    name="require_pkce",
                    field=models.BooleanField(default=False),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="apiv2client",
                    name="require_pkce",
                    field=models.BooleanField(default=True),
                ),
            ],
        ),
    ]
