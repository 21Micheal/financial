from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_emailotp_purpose_attempts"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="emailotp",
            name="accounts_em_user_id_034f04_idx",
        ),
        migrations.RenameIndex(
            model_name="emailotp",
            old_name="accounts_em_user_id_purpose_idx",
            new_name="accounts_em_user_id_1533d7_idx",
        ),
        migrations.RemoveField(
            model_name="user",
            name="mfa_enabled",
        ),
    ]