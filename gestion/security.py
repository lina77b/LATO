import secrets
import string

import bcrypt
from django.core.cache import cache


_ALPHABET = ''.join(c for c in string.ascii_letters + string.digits
                    if c not in '0OoIl1')
LONGUEUR_MDP_TEMP = 12


def generer_mot_de_passe_temporaire(longueur=LONGUEUR_MDP_TEMP):
    while True:
        mdp = ''.join(secrets.choice(_ALPHABET) for _ in range(longueur))
        if (any(c.islower() for c in mdp) and any(c.isupper() for c in mdp)
                and any(c.isdigit() for c in mdp)):
            return mdp


def hacher_mot_de_passe(mdp):
    return bcrypt.hashpw(mdp.encode(), bcrypt.gensalt()).decode()


MAX_ECHECS_COMPTE = 5
MAX_ECHECS_IP = 30
VERROUILLAGE_SECONDES = 15 * 60


def _ip(request):
    return request.META.get('REMOTE_ADDR', 'inconnue')


def _cles(request, email):
    ip = _ip(request)
    return f'login:echecs:{ip}:{email.strip().lower()}', f'login:echecs-ip:{ip}'


def connexion_bloquee(request, email):
    k_compte, k_ip = _cles(request, email)
    return (cache.get(k_compte, 0) >= MAX_ECHECS_COMPTE
            or cache.get(k_ip, 0) >= MAX_ECHECS_IP)


def enregistrer_echec(request, email):
    for cle in _cles(request, email):
        cache.add(cle, 0, VERROUILLAGE_SECONDES)
        try:
            cache.incr(cle)
        except ValueError:
            cache.set(cle, 1, VERROUILLAGE_SECONDES)


def reinitialiser_echecs(request, email):
    cache.delete(_cles(request, email)[0])


def invalider_sessions(user_id):
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if session.get_decoded().get('user_id') == user_id:
            session.delete()
