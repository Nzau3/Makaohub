from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedProperty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saved_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=models.CASCADE, related_name='saved_properties', to=settings.AUTH_USER_MODEL)),
                ('property', models.ForeignKey(on_delete=models.CASCADE, related_name='saved_by', to='properties.property')),
            ],
            options={
                'unique_together': {('tenant', 'property')},
                'ordering': ['-saved_at'],
            },
        ),
    ]

