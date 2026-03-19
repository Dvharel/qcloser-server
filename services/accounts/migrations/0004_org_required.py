from django.db import migrations, models
import django.db.models.deletion


def assign_default_org(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(org__isnull=True).update(org_id=1)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_user_managers"),
    ]

    operations = [
        migrations.RunPython(assign_default_org, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="org",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="users",
                to="accounts.organization",
            ),
        ),
    ]
