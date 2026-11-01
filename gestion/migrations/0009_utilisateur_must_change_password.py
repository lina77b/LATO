from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0008_performance_idx_perf_epreuve_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='must_change_password',
            field=models.BooleanField(default=False),
        ),
    ]
