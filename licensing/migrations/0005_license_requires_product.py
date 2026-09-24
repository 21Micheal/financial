import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3 of 3: make the product link mandatory and drop the old `system` string."""

    dependencies = [
        ("licensing", "0004_backfill_license_products"),
    ]

    operations = [
        migrations.AlterUniqueTogether(name="systemlicense", unique_together=set()),
        migrations.RemoveIndex(model_name="systemlicense", name="licensing_s_organiz_b570be_idx"),
        migrations.AlterModelOptions(
            name="systemlicense",
            options={"ordering": ["organization", "product"]},
        ),
        migrations.RemoveField(model_name="systemlicense", name="system"),
        migrations.AlterField(
            model_name="systemlicense",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="licenses",
                to="licensing.product",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="systemlicense",
            unique_together={("organization", "product")},
        ),
    ]
