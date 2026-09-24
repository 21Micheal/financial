from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        # 0001 created `role` without the choices the model declares.
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Platform Administrator"),
                    ("finance_staff", "Finance Staff"),
                    ("client_admin", "Client Administrator"),
                    ("client_user", "Client User"),
                ],
                default="client_user",
                max_length=50,
            ),
        ),
    ]