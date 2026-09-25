from django.db import migrations, models


def migrate_roles(apps, schema_editor):
    """Migrate old roles to new unified structure."""
    User = apps.get_model('accounts', 'User')
    
    # Migration mapping:
    # admin -> platform_admin
    # client_admin -> admin  
    # finance_staff -> financial_user
    # client_user -> financial_user
    
    role_mapping = {
        'admin': 'platform_admin',
        'client_admin': 'admin',
        'finance_staff': 'financial_user',
        'client_user': 'financial_user',
    }
    
    for user in User.objects.all():
        if user.role in role_mapping:
            user.role = role_mapping[user.role]
            user.save(update_fields=['role'])


def reverse_migrate_roles(apps, schema_editor):
    """Reverse migration."""
    User = apps.get_model('accounts', 'User')
    
    reverse_mapping = {
        'platform_admin': 'admin',
        'admin': 'client_admin',
        'financial_user': 'client_user',  # Financial users were originally client_users
    }
    
    for user in User.objects.all():
        if user.role in reverse_mapping:
            user.role = reverse_mapping[user.role]
            user.save(update_fields=['role'])


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_remove_mfa_and_normalize_otp_index'),
    ]

    operations = [
        # Update role choices
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('platform_admin', 'Platform Administrator'), ('admin', 'Administrator'), ('financial_user', 'Financial User')],
                default='financial_user',
                max_length=50
            ),
        ),
        # Add has_usable_password field
        migrations.AddField(
            model_name='user',
            name='has_usable_password',
            field=models.BooleanField(default=True),
        ),
        # Run role migration
        migrations.RunPython(migrate_roles, reverse_migrate_roles),
    ]
