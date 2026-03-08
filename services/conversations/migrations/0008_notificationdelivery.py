from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0007_auto_20260223_1850'),
    ]

    operations = [
        migrations.AddField(
            model_name='callrecording',
            name='salesperson_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='callrecording',
            name='client_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.CreateModel(
            name='NotificationDelivery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('analysis', 'Analysis'), ('feedback', 'Feedback'), ('followup', 'Followup')], max_length=16)),
                ('channel', models.CharField(choices=[('email', 'Email')], default='email', max_length=16)),
                ('salesperson_email', models.EmailField(max_length=254)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sending', 'Sending'), ('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=16)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('subject', models.CharField(blank=True, default='', max_length=255)),
                ('body', models.TextField(blank=True, default='')),
                ('last_error', models.TextField(blank=True, null=True)),
                ('last_attempt_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recording', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='conversations.callrecording')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
