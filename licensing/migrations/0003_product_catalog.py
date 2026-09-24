import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1 of 3: add the Product table and a nullable licence -> product link."""

    dependencies = [
        ("licensing", "0002_remove_usersystemrole"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slug", models.SlugField(help_text="Stable identifier used in URLs and integrations, e.g. 'dms'.", unique=True)),
                ("name", models.CharField(max_length=200, unique=True)),
                ("description", models.TextField(blank=True)),
                ("info_url", models.URLField(blank=True, help_text="Public product page.")),
                ("launch_url", models.URLField(blank=True, help_text="Where users land after SSO. Leave blank to use this deployment's default for the product.")),
                ("provisioning_mode", models.CharField(
                    choices=[("role_api", "Product role API (per-user provisioning)"), ("license_only", "Licence only (no per-user check)")],
                    default="role_api",
                    help_text="How per-user access is decided. 'Product role API' fails closed if the integration is not configured.",
                    max_length=20,
                )),
                ("is_enabled", models.BooleanField(default=True, help_text="Disabled products are hidden from every launcher, licensed or not.")),
                ("sort_order", models.PositiveSmallIntegerField(default=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="systemlicense",
            name="product",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="licenses",
                to="licensing.product",
            ),
        ),
    ]
