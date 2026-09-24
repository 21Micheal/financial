from django.db import migrations

# Names for the two values the old hard-coded SystemType enum allowed.
LEGACY_PRODUCTS = {
    "dms": ("FSE DMS (Document Management System)", 10),
    "inventory": ("Inventory Management", 200),
}


def backfill_products(apps, schema_editor):
    """Step 2 of 3: point every existing licence at a Product row (data only, no DDL)."""
    Product = apps.get_model("licensing", "Product")
    SystemLicense = apps.get_model("licensing", "SystemLicense")
    db = schema_editor.connection.alias

    slugs = SystemLicense.objects.using(db).order_by().values_list("system", flat=True).distinct()
    for slug in list(slugs):
        name, sort_order = LEGACY_PRODUCTS.get(slug, (slug.replace("-", " ").title(), 100))
        product, _ = Product.objects.using(db).get_or_create(
            slug=slug,
            defaults={"name": name, "sort_order": sort_order},
        )
        SystemLicense.objects.using(db).filter(system=slug).update(product=product)


class Migration(migrations.Migration):

    dependencies = [
        ("licensing", "0003_product_catalog"),
    ]

    operations = [
        migrations.RunPython(backfill_products, migrations.RunPython.noop),
    ]
