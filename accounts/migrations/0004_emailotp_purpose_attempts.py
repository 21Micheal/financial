from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_is_active_and_role_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailotp',
            name='purpose',
            field=models.CharField(
                choices=[('login', 'Standard Login'), ('break_glass', 'Break-Glass Emergency Access')],
                default='login',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='emailotp',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterIndexTogether(
            name='emailotp',
            index_together=set(),
        ),
        migrations.AddIndex(
            model_name='emailotp',
            index=models.Index(fields=['user', 'purpose', 'created_at'], name='accounts_em_user_id_purpose_idx'),
        ),
    ]
