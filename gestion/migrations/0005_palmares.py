import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0004_athlete_cert_medical_img'),
    ]

    operations = [
        migrations.CreateModel(
            name='Palmares',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saison', models.CharField(default='2025-2026', max_length=12)),
                ('competition', models.CharField(max_length=200)),
                ('nature', models.CharField(choices=[('national', 'National'), ('regional', 'Régional'), ('wilaya', 'Wilaya'), ('international', 'International')], default='national', max_length=20)),
                ('epreuve', models.CharField(max_length=80)),
                ('date', models.DateField(blank=True, null=True)),
                ('lieu', models.CharField(blank=True, default='', max_length=150)),
                ('classement', models.CharField(choices=[('or', 'Or — 1ère place'), ('argent', 'Argent — 2ème place'), ('bronze', 'Bronze — 3ème place'), ('finaliste', 'Finaliste')], default='or', max_length=20)),
                ('performance', models.CharField(blank=True, default='', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='palmares', to='gestion.athlete')),
            ],
            options={
                'db_table': 'palmares',
                'ordering': ['-date'],
            },
        ),
    ]
