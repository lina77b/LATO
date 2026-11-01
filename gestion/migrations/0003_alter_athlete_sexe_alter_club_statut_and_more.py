from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0002_alter_athlete_options_alter_evenement_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='athlete',
            name='sexe',
            field=models.CharField(choices=[('M', 'Masculin'), ('F', 'Féminin')], default='M', max_length=1),
        ),
        migrations.AlterField(
            model_name='club',
            name='statut',
            field=models.CharField(choices=[('EN_ATTENTE', 'En attente'), ('VALIDE', 'Valide'), ('SUSPENDU', 'Suspendu')], default='EN_ATTENTE', max_length=20),
        ),
        migrations.AlterField(
            model_name='evenement',
            name='type_event',
            field=models.CharField(choices=[('competition', 'Competition'), ('meeting', 'Meeting'), ('cross', 'Cross Country'), ('national', 'National')], default='competition', max_length=20),
        ),
    ]
