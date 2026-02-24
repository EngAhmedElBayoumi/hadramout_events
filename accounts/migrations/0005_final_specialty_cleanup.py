import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_migrate_specialty_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='doctor',
            name='specialty',
        ),
        migrations.RenameField(
            model_name='doctor',
            old_name='specialty_fk',
            new_name='specialty',
        ),
        migrations.AlterField(
            model_name='doctor',
            name='specialty',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.specialty', verbose_name='Specialty'),
        ),
    ]
