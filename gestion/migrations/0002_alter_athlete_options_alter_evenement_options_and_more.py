from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='athlete',
            options={},
        ),
        migrations.AlterModelOptions(
            name='evenement',
            options={},
        ),
        migrations.AlterModelOptions(
            name='notification',
            options={},
        ),
        migrations.AlterModelOptions(
            name='performance',
            options={},
        ),
        migrations.AlterModelOptions(
            name='recordwilaya',
            options={},
        ),
        migrations.AlterModelOptions(
            name='seance',
            options={},
        ),
        migrations.AddField(
            model_name='athlete',
            name='dossier_medical_url',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='athlete',
            name='poids',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='athlete',
            name='taille',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='club',
            name='informations_legales',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='club',
            name='statut',
            field=models.CharField(choices=[('EN_ATTENTE', 'En attente'), ('VALIDE', 'Validé'), ('SUSPENDU', 'Suspendu')], default='EN_ATTENTE', max_length=20),
        ),
        migrations.AddField(
            model_name='performance',
            name='commentaire',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='performance',
            name='unite',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='seance',
            name='contenu_pedagogique',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='seance',
            name='heure_fin',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='diplome',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='prenom',
            field=models.CharField(default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='evenement',
            name='type_event',
            field=models.CharField(choices=[('competition', 'Compétition'), ('meeting', 'Meeting'), ('cross', 'Cross Country'), ('national', 'National')], default='competition', max_length=20),
        ),
        migrations.AlterModelTable(
            name='evenement',
            table=None,
        ),
        migrations.AlterModelTable(
            name='notification',
            table=None,
        ),
        migrations.AlterModelTable(
            name='recordwilaya',
            table=None,
        ),
    ]
