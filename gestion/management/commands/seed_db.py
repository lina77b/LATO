import secrets

import bcrypt
from decouple import config
from django.core.management.base import BaseCommand

from gestion.models import Club, Utilisateur


def hash_password(mdp):
    return bcrypt.hashpw(mdp.encode(), bcrypt.gensalt()).decode()


class Command(BaseCommand):
    help = "Initialise la base avec un club de démonstration et un compte Super Admin Ligue"

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Supprimer toutes les données avant')

    def handle(self, *args, **options):
        if options['reset']:
            Utilisateur.objects.all().delete()
            Club.objects.all().delete()
            self.stdout.write(self.style.WARNING('Base vidée'))

        if Club.objects.exists():
            self.stdout.write(self.style.WARNING(
                'Base déjà initialisée. Utilisez --reset pour réinitialiser.'))
            return

        admin_email = config('ADMIN_EMAIL', default='admin@example.com')
        admin_pwd = config('ADMIN_PASSWORD', default='') or secrets.token_urlsafe(12)
        generated = not config('ADMIN_PASSWORD', default='')

        Club.objects.create(
            nom='Club de démonstration',
            ville='Tizi Ouzou',
            wilaya='Tizi Ouzou',
            email='demo-club@example.com',
            telephone='000 00 00 00',
            actif=True,
        )

        Utilisateur.objects.create(
            nom='Admin', prenom='Ligue', email=admin_email,
            mot_de_passe=hash_password(admin_pwd),
            role='ligue', club=None, actif=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Base initialisée : {Club.objects.count()} club, '
            f'{Utilisateur.objects.count()} compte.'))
        self.stdout.write(f'Super Admin Ligue : {admin_email}')
        if generated:
            self.stdout.write(self.style.WARNING(
                f'Mot de passe généré (à noter, affiché une seule fois) : {admin_pwd}'))
        else:
            self.stdout.write('Mot de passe : celui défini dans ADMIN_PASSWORD (.env)')
