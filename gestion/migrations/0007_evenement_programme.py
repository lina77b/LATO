from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0006_athlete_saison_evenement_saison_seance_saison'),
    ]

    operations = [
        migrations.AddField(
            model_name='evenement',
            name='programme',
            field=models.FileField(blank=True, null=True, upload_to='programmes/'),
        ),
    ]
