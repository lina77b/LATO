from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0007_evenement_programme'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='performance',
            index=models.Index(fields=['epreuve'], name='idx_perf_epreuve'),
        ),
        migrations.AddIndex(
            model_name='performance',
            index=models.Index(fields=['saison'], name='idx_perf_saison'),
        ),
        migrations.AddIndex(
            model_name='performance',
            index=models.Index(fields=['record_wilaya'], name='idx_perf_record'),
        ),
        migrations.AddIndex(
            model_name='performance',
            index=models.Index(fields=['athlete', 'epreuve'], name='idx_perf_athlete_epreuve'),
        ),
    ]
