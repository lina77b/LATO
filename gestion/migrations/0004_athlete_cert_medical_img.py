from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0003_alter_athlete_sexe_alter_club_statut_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='athlete',
            name='cert_medical_img',
            field=models.ImageField(blank=True, null=True, upload_to='certificats/'),
        ),
    ]
