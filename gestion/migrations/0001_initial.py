import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=120)),
                ('ville', models.CharField(default='', max_length=80)),
                ('wilaya', models.CharField(default='Tizi Ouzou', max_length=80)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('telephone', models.CharField(blank=True, default='', max_length=20)),
                ('actif', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'clubs',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='Evenement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=150)),
                ('date', models.DateField()),
                ('lieu', models.CharField(default='', max_length=120)),
                ('type_event', models.CharField(choices=[('competition', 'Competition'), ('meeting', 'Meeting'), ('cross', 'Cross Country'), ('national', 'National')], default='competition', max_length=20)),
                ('epreuves', models.CharField(default='', max_length=250)),
                ('description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'evenements',
                'ordering': ['date'],
            },
        ),
        migrations.CreateModel(
            name='Athlete',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('prenom', models.CharField(default='', max_length=100)),
                ('date_naissance', models.DateField(blank=True, null=True)),
                ('sexe', models.CharField(default='M', max_length=1)),
                ('groupe', models.CharField(default='', max_length=80)),
                ('categorie', models.CharField(choices=[('Benjamin', 'Benjamin'), ('Minime', 'Minime'), ('Cadet', 'Cadet'), ('Junior', 'Junior'), ('Senior', 'Senior'), ('Master', 'Master')], default='Senior', max_length=20)),
                ('epreuves', models.JSONField(default=list)),
                ('statut_licence', models.CharField(choices=[('non_licencie', 'Non licencie'), ('incomplet', 'Incomplet'), ('en_attente', 'En attente'), ('licencie', 'Licencie')], default='non_licencie', max_length=20)),
                ('licence_no', models.CharField(blank=True, max_length=30, null=True)),
                ('cert_medical', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('club', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.club')),
            ],
            options={
                'db_table': 'athletes',
                'ordering': ['nom', 'prenom'],
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destinataire_role', models.CharField(max_length=20)),
                ('texte', models.TextField()),
                ('lu', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('athlete', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gestion.athlete')),
                ('club', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gestion.club')),
            ],
            options={
                'db_table': 'notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Utilisateur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('mot_de_passe', models.CharField(default='', max_length=128)),
                ('role', models.CharField(choices=[('ligue', 'Super Admin Ligue'), ('club_admin', 'Admin Club'), ('coach', 'Coach'), ('athlete', 'Athlete')], max_length=20)),
                ('specialite', models.CharField(blank=True, default='', max_length=60)),
                ('actif', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('club', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.club')),
            ],
            options={
                'db_table': 'utilisateurs',
            },
        ),
        migrations.CreateModel(
            name='Seance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=150)),
                ('date', models.DateField()),
                ('heure', models.CharField(default='09:00', max_length=10)),
                ('lieu', models.CharField(default='', max_length=120)),
                ('epreuve', models.CharField(default='', max_length=60)),
                ('groupe', models.CharField(default='', max_length=80)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('club', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.club')),
                ('coach', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.utilisateur')),
            ],
            options={
                'db_table': 'seances',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='Performance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('epreuve', models.CharField(max_length=60)),
                ('performance', models.CharField(max_length=30)),
                ('valeur_num', models.FloatField(default=0)),
                ('date', models.DateField(default=datetime.date.today)),
                ('lieu', models.CharField(default='', max_length=120)),
                ('record_wilaya', models.BooleanField(default=False)),
                ('saison', models.CharField(default='2025-2026', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion.athlete')),
                ('coach', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.utilisateur')),
            ],
            options={
                'db_table': 'performances',
                'ordering': ['-date'],
            },
        ),
        migrations.AddField(
            model_name='athlete',
            name='coach',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='athletes_coaches', to='gestion.utilisateur'),
        ),
        migrations.CreateModel(
            name='RecordWilaya',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('epreuve', models.CharField(max_length=60)),
                ('sexe', models.CharField(max_length=1)),
                ('performance', models.CharField(max_length=30)),
                ('valeur_num', models.FloatField(default=0)),
                ('athlete_nom', models.CharField(default='', max_length=120)),
                ('club_nom', models.CharField(default='', max_length=120)),
                ('date', models.DateField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('athlete', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.athlete')),
            ],
            options={
                'db_table': 'records_wilaya',
                'ordering': ['epreuve'],
                'unique_together': {('epreuve', 'sexe')},
            },
        ),
    ]
