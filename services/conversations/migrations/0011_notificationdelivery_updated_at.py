# Generated manually on 2026-03-29

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0010_auto_20260329_2101'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationdelivery',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
