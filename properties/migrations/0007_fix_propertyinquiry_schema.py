from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0006_merge_20260107_1152"),
    ]

    operations = [
        migrations.AlterField(
            model_name="propertyinquiry",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AlterField(
            model_name="propertyinquiry",
            name="inquirer",
            field=models.ForeignKey(
                blank=True,
                help_text="User who submitted the inquiry (should be a tenant).",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="inquiries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="propertyinquiry",
            name="inquirer_role",
            field=models.CharField(
                blank=True,
                choices=[("tenant", "Tenant"), ("landlord", "Landlord")],
                help_text="Role of inquirer at time of submission.",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="propertyinquiry",
            name="name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="propertyinquiry",
            name="tenant",
            field=models.ForeignKey(
                default=1,  # temporary default to satisfy existing rows; adjust if needed
                help_text="Tenant who submitted the inquiry.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="property_inquiries",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="propertyinquiry",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
    ]

