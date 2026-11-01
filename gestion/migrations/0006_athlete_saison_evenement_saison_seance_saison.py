from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0005_palmares'),
    ]

    operations = [
        migrations.AddField(
            model_name='athlete',
            name='saison',
            field=models.CharField(default='2025-2026', max_length=12),
        ),
        migrations.AddField(
            model_name='evenement',
            name='saison',
            field=models.CharField(default='2025-2026', max_length=12),
        ),
        migrations.AddField(
            model_name='seance',
            name='saison',
            field=models.CharField(default='2025-2026', max_length=12),
        ),
    ]
