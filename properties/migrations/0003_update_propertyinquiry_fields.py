from django.db import migrations


class Migration(migrations.Migration):
    """
    This legacy migration is intentionally left empty to resolve conflicts
    with newer migrations that already define the correct schema.
    """

    dependencies = [
        ("properties", "0002_add_savedproperty_table"),
    ]

    operations = []

