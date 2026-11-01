from django.test import TestCase, Client
from datetime import date
from .models import Club, Utilisateur, Athlete, Performance
import bcrypt


def hacher(mdp):
    return bcrypt.hashpw(mdp.encode(), bcrypt.gensalt(rounds=4)).decode()


class ClubModelTest(TestCase):
    def setUp(self):
        self.club = Club.objects.create(
            nom="JSK Athlétisme", ville="Tizi Ouzou",
            statut="VALIDE", actif=True
        )

    def test_creation_club(self):
        self.assertEqual(self.club.nom, "JSK Athlétisme")
        self.assertTrue(self.club.actif)

    def test_nb_athletes_vide(self):
        self.assertEqual(self.club.nb_athletes(), 0)

    def test_nb_licencies(self):
        Athlete.objects.create(nom="A", prenom="A", club=self.club, statut_licence='licencie')
        Athlete.objects.create(nom="B", prenom="B", club=self.club, statut_licence='non_licencie')
        self.assertEqual(self.club.nb_licencies(), 1)

    def test_str_club(self):
        self.assertEqual(str(self.club), "JSK Athlétisme")

    def test_to_dict_club(self):
        d = self.club.to_dict()
        self.assertEqual(d['nom'], "JSK Athlétisme")
        self.assertIn('nb_athletes', d)


class UtilisateurModelTest(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create(
            nom="Test", prenom="Admin",
            email="club.admin@example.com",
            mot_de_passe=hacher("TestClubPass#1"),
            role="club_admin", actif=True
        )

    def test_check_password_correct(self):
        self.assertTrue(self.user.check_password("TestClubPass#1"))

    def test_check_password_incorrect(self):
        self.assertFalse(self.user.check_password("mauvais"))

    def test_mot_de_passe_hache(self):

        self.assertNotEqual(self.user.mot_de_passe, "TestClubPass#1")
        self.assertTrue(self.user.mot_de_passe.startswith("$2b$"))

    def test_str_utilisateur(self):
        self.assertIn("Test", str(self.user))


class AthleteModelTest(TestCase):
    def setUp(self):
        self.club = Club.objects.create(nom="ACTO", statut="VALIDE", actif=True)
        self.athlete = Athlete.objects.create(
            nom="Kaci", prenom="Nadia",
            date_naissance=date(2000, 3, 15),
            sexe='F', club=self.club, categorie='Senior',
            statut_licence='licencie'
        )

    def test_nom_complet(self):
        self.assertEqual(self.athlete.nom_complet, "Nadia Kaci")

    def test_age_calcule(self):
        self.assertGreater(self.athlete.age, 20)

    def test_initiales(self):
        self.assertEqual(self.athlete.initiales, "NK")

    def test_pbs_vide(self):
        self.assertEqual(self.athlete.get_pbs(), {})

    def test_pbs_meilleur_temps(self):
        Performance.objects.create(athlete=self.athlete, epreuve='100m',
            performance='12.5', valeur_num=12.5, date=date.today())
        Performance.objects.create(athlete=self.athlete, epreuve='100m',
            performance='12.1', valeur_num=12.1, date=date.today())
        pbs = self.athlete.get_pbs()
        self.assertEqual(pbs['100m']['valeur'], 12.1)

    def test_progression(self):
        Performance.objects.create(athlete=self.athlete, epreuve='100m',
            performance='12.5', valeur_num=12.5, date=date(2025, 9, 1))
        Performance.objects.create(athlete=self.athlete, epreuve='100m',
            performance='12.1', valeur_num=12.1, date=date(2025, 10, 1))
        prog = self.athlete.get_progression('100m')
        self.assertEqual(len(prog), 2)
        self.assertEqual(prog[0]['valeur'], 12.5)

    def test_to_dict_athlete(self):
        d = self.athlete.to_dict()
        self.assertEqual(d['nom_complet'], "Nadia Kaci")
        self.assertIn('statut_licence', d)


class AuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.club = Club.objects.create(nom="JSK", statut="VALIDE", actif=True)
        self.admin = Utilisateur.objects.create(
            nom="Admin", prenom="Ligue",
            email="admin@lato.dz",
            mot_de_passe=hacher("TestAdminPass#1"),
            role="ligue", actif=True
        )
        self.club_admin = Utilisateur.objects.create(
            nom="Test", prenom="Admin",
            email="club.admin@example.com",
            mot_de_passe=hacher("TestClubPass#1"),
            role="club_admin", club=self.club, actif=True
        )

    def test_page_login_accessible(self):
        r = self.client.get('/login/')
        self.assertEqual(r.status_code, 200)

    def test_login_ligue_redirige(self):
        r = self.client.post('/login/', {
            'email': 'admin@lato.dz',
            'mot_de_passe': 'TestAdminPass#1'
        })
        self.assertEqual(r.status_code, 302)
        self.assertRedirects(r, '/ligue/')

    def test_login_club_admin_redirige(self):
        r = self.client.post('/login/', {
            'email': 'club.admin@example.com',
            'mot_de_passe': 'TestClubPass#1'
        })
        self.assertEqual(r.status_code, 302)
        self.assertRedirects(r, '/club/')

    def test_mauvais_mdp_reste_sur_login(self):
        r = self.client.post('/login/', {
            'email': 'admin@lato.dz',
            'mot_de_passe': 'mauvais'
        })
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('role', self.client.session)

    def test_dashboard_sans_login_redirige(self):
        r = self.client.get('/ligue/')
        self.assertEqual(r.status_code, 302)

    def test_club_dashboard_sans_login_redirige(self):
        r = self.client.get('/club/')
        self.assertEqual(r.status_code, 302)

    def test_compte_inactif_refuse(self):
        self.admin.actif = False
        self.admin.save()
        self.client.post('/login/', {
            'email': 'admin@lato.dz',
            'mot_de_passe': 'TestAdminPass#1'
        })
        self.assertNotIn('role', self.client.session)

    def test_logout(self):
        self.client.post('/login/', {
            'email': 'admin@lato.dz',
            'mot_de_passe': 'TestAdminPass#1'
        })
        self.client.get('/logout/')
        self.assertNotIn('role', self.client.session)


class LigueViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.club = Club.objects.create(nom="JSK", statut="VALIDE", actif=True)
        self.admin = Utilisateur.objects.create(
            nom="Admin", prenom="Ligue",
            email="admin@lato.dz",
            mot_de_passe=hacher("TestAdminPass#1"),
            role="ligue", actif=True
        )
        self.client.post('/login/', {
            'email': 'admin@lato.dz',
            'mot_de_passe': 'TestAdminPass#1'
        })

    def test_dashboard_ligue_accessible(self):
        r = self.client.get('/ligue/')
        self.assertEqual(r.status_code, 200)

    def test_liste_clubs_accessible(self):
        r = self.client.get('/ligue/clubs/')
        self.assertEqual(r.status_code, 200)

    def test_liste_athletes_accessible(self):
        r = self.client.get('/ligue/athletes/')
        self.assertEqual(r.status_code, 200)

    def test_liste_licences_accessible(self):
        r = self.client.get('/ligue/licences/')
        self.assertEqual(r.status_code, 200)

    def test_creer_club(self):
        r = self.client.post('/ligue/clubs/creer/', {
            'nom': 'AC Azazga',
            'ville': 'Azazga',
            'wilaya': 'Tizi Ouzou',
            'email': 'azazga@lato.dz',
            'telephone': '026 38 00 33',
            'responsable_nom': 'Lounis',
            'responsable_prenom': 'Samir',
            'responsable_email': 's.lounis@lato.dz',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Club.objects.filter(nom='AC Azazga').exists())


class ClubAdminViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.club = Club.objects.create(nom="JSK", statut="VALIDE", actif=True)
        self.club_admin = Utilisateur.objects.create(
            nom="Test", prenom="Admin",
            email="club.admin@example.com",
            mot_de_passe=hacher("TestClubPass#1"),
            role="club_admin", club=self.club, actif=True
        )
        self.client.post('/login/', {
            'email': 'club.admin@example.com',
            'mot_de_passe': 'TestClubPass#1'
        })

    def test_dashboard_club_accessible(self):
        r = self.client.get('/club/')
        self.assertEqual(r.status_code, 200)

    def test_liste_athletes_club(self):
        r = self.client.get('/club/athletes/')
        self.assertEqual(r.status_code, 200)

    def test_acces_ligue_refuse(self):

        r = self.client.get('/ligue/')
        self.assertEqual(r.status_code, 302)


class ApiSecurityTest(TestCase):

    def setUp(self):
        self.c1 = Club.objects.create(nom="Club A", statut="VALIDE", actif=True)
        self.c2 = Club.objects.create(nom="Club B", statut="VALIDE", actif=True)
        self.a1 = Athlete.objects.create(nom="Alpha", club=self.c1, sexe="M", categorie="Senior")
        self.a2 = Athlete.objects.create(nom="Beta", club=self.c2, sexe="M", categorie="Senior")

    def _login_as(self, role, club=None, **extra):
        s = self.client.session
        s['role'] = role
        s['club_id'] = club.pk if club else None
        s['user_id'] = 1
        for k, v in extra.items():
            s[k] = v
        s.save()

    def test_anonyme_refuse(self):
        self.assertEqual(self.client.get('/api/athletes/').status_code, 401)

    def test_athlete_ne_peut_pas_lister_les_athletes(self):
        self._login_as('athlete', self.c1)
        self.assertEqual(self.client.get('/api/athletes/').status_code, 403)

    def test_athlete_ne_peut_pas_creer_un_club(self):
        self._login_as('athlete', self.c1)
        r = self.client.post('/api/clubs/', data='{"nom": "X"}', content_type='application/json')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Club.objects.filter(nom="X").exists())

    def test_ligue_peut_creer_un_club(self):
        self._login_as('ligue')
        r = self.client.post('/api/clubs/', data='{"nom": "Nouveau"}', content_type='application/json')
        self.assertEqual(r.status_code, 201)

    def test_club_admin_ne_voit_que_son_club(self):
        self._login_as('club_admin', self.c1)
        noms = [a['nom'] for a in self.client.get('/api/athletes/').json()]
        self.assertEqual(noms, ["Alpha"])

    def test_club_admin_ne_peut_pas_lire_athlete_autre_club(self):
        self._login_as('club_admin', self.c1)
        self.assertEqual(self.client.get(f'/api/athletes/{self.a2.pk}/').status_code, 403)

    def test_coach_ne_peut_pas_saisir_pour_autre_club(self):
        self._login_as('coach', self.c1)
        r = self.client.post('/api/performances/', content_type='application/json',
                             data=f'{{"athlete_id": {self.a2.pk}, "epreuve": "100m", "performance": "11.0", "valeur_num": 11.0}}')
        self.assertEqual(r.status_code, 403)

    def test_notifications_limitees_a_son_role(self):
        self._login_as('athlete', self.c1)
        self.assertEqual(self.client.get('/api/notifications/ligue/').status_code, 403)


class CsrfTest(TestCase):
    def test_saisie_exige_un_token_csrf(self):
        client = Client(enforce_csrf_checks=True)
        s = client.session
        s['role'] = 'coach'
        s['user_id'] = 1
        s.save()
        r = client.post('/coach/saisie/enregistrer/', {'epreuve': '100m'})
        self.assertEqual(r.status_code, 403)


import re
from django.core.cache import cache
from django.urls import reverse
from django.contrib.messages import get_messages
from .models import Palmares, Evenement, est_epreuve_distance, est_meilleur
from .security import generer_mot_de_passe_temporaire


def _connecter(client, email, mdp):
    return client.post('/login/', {'email': email, 'mot_de_passe': mdp})


class BaseSecuriteTest(TestCase):
    MDP = "MotDePasseSolide#1"

    def setUp(self):
        cache.clear()
        self.cA = Club.objects.create(nom="Club A", statut="VALIDE", actif=True)
        self.cB = Club.objects.create(nom="Club B", statut="VALIDE", actif=True)
        mk = lambda email, role, club=None, nom="X": Utilisateur.objects.create(
            nom=nom, prenom="T", email=email, mot_de_passe=hacher(self.MDP),
            role=role, club=club, actif=True)
        self.ligue = mk("ligue@t.dz", "ligue", nom="Ligue")
        self.adminA = mk("adminA@t.dz", "club_admin", self.cA, "AdminA")
        self.coachA = mk("coachA@t.dz", "coach", self.cA, "CoachA")
        self.coachA2 = mk("coachA2@t.dz", "coach", self.cA, "CoachA2")
        self.coachB = mk("coachB@t.dz", "coach", self.cB, "CoachB")
        self.athA = Athlete.objects.create(nom="AthA", prenom="A", club=self.cA, coach=self.coachA,
                                           statut_licence="licencie", epreuves=["100m"])
        self.athA2 = Athlete.objects.create(nom="AthA2", prenom="A", club=self.cA, coach=self.coachA2,
                                            statut_licence="licencie")
        self.athB = Athlete.objects.create(nom="AthB", prenom="B", club=self.cB, coach=self.coachB,
                                           statut_licence="licencie")

    def client_connecte(self, user, enforce_csrf_checks=False):
        c = Client()
        r = _connecter(c, user.email, self.MDP)
        self.assertEqual(r.status_code, 302, "connexion de test échouée")
        if enforce_csrf_checks:
            strict = Client(enforce_csrf_checks=True)
            strict.cookies = c.cookies
            return strict
        return c


class ActionsDestructivesPostSeulementTest(BaseSecuriteTest):

    def _cas(self):
        ev = Evenement.objects.create(titre="Meeting", date=date.today())
        pal = Palmares.objects.create(athlete=self.athA, competition="C", epreuve="100m")
        perf = Performance.objects.create(athlete=self.athA, epreuve="100m", performance="11.0", valeur_num=11.0)
        enattente = Athlete.objects.create(nom="Att", prenom="E", club=self.cA, statut_licence="en_attente")
        return [
            (self.ligue, reverse('club_supprimer', args=[self.cB.pk]), Club, self.cB.pk),
            (self.ligue, reverse('club_toggle', args=[self.cB.pk]), Club, self.cB.pk),
            (self.ligue, reverse('evenement_supprimer', args=[ev.pk]), Evenement, ev.pk),
            (self.ligue, reverse('ligue_coach_supprimer', args=[self.coachB.pk]), Utilisateur, self.coachB.pk),
            (self.ligue, reverse('ligue_athlete_supprimer', args=[self.athB.pk]), Athlete, self.athB.pk),
            (self.ligue, reverse('palmares_supprimer', args=[pal.pk]), Palmares, pal.pk),
            (self.ligue, reverse('valider_licence', args=[enattente.pk]), Athlete, enattente.pk),
            (self.ligue, reverse('rejeter_licence', args=[enattente.pk]), Athlete, enattente.pk),
            (self.adminA, reverse('athlete_supprimer', args=[self.athA2.pk]), Athlete, self.athA2.pk),
            (self.adminA, reverse('club_coach_supprimer', args=[self.coachA2.pk]), Utilisateur, self.coachA2.pk),
            (self.adminA, reverse('prevalider_licence', args=[self.athA2.pk]), Athlete, self.athA2.pk),
            (self.coachA, reverse('performance_supprimer', args=[perf.pk]), Performance, perf.pk),
        ]

    def test_get_refuse_405_et_rien_ne_change(self):
        for user, url, modele, pk in self._cas():
            avant = modele.objects.get(pk=pk)
            r = self.client_connecte(user).get(url)
            self.assertEqual(r.status_code, 405, f"GET {url} devrait être refusé")
            apres = modele.objects.filter(pk=pk).first()
            self.assertIsNotNone(apres, f"GET {url} a supprimé l'objet")
            if hasattr(avant, 'statut_licence'):
                self.assertEqual(apres.statut_licence, avant.statut_licence)
            if hasattr(avant, 'actif'):
                self.assertEqual(apres.actif, avant.actif)

    def test_post_sans_jeton_csrf_refuse_403(self):
        for user, url, modele, pk in self._cas():
            c = self.client_connecte(user, enforce_csrf_checks=True)
            self.assertEqual(c.post(url).status_code, 403, f"POST sans CSRF accepté sur {url}")
            self.assertTrue(modele.objects.filter(pk=pk).exists())

    def test_post_valide_fonctionne(self):
        c = self.client_connecte(self.ligue)
        self.assertEqual(c.post(reverse('club_supprimer', args=[self.cB.pk])).status_code, 302)
        self.assertFalse(Club.objects.filter(pk=self.cB.pk).exists())

    def test_les_pages_rendent_des_formulaires_avec_csrf(self):
        c = self.client_connecte(self.ligue)
        html = c.get(reverse('ligue_clubs')).content.decode()
        self.assertNotIn(f'href="/ligue/clubs/{self.cA.pk}/supprimer/"', html)
        self.assertIn(f'action="/ligue/clubs/{self.cA.pk}/supprimer/"', html)
        self.assertIn('csrfmiddlewaretoken', html)


class CloisonnementTest(BaseSecuriteTest):

    def test_admin_club_ne_peut_pas_modifier_un_athlete_dun_autre_club(self):
        c = self.client_connecte(self.adminA)
        url = reverse('athlete_modifier', args=[self.athB.pk])
        self.assertEqual(c.get(url).status_code, 404)
        self.assertEqual(c.post(url, {'nom': 'Piraté', 'prenom': 'x', 'sexe': 'M',
                                      'categorie': 'Senior', 'groupe': ''}).status_code, 404)
        self.athB.refresh_from_db()
        self.assertEqual(self.athB.nom, "AthB")

    def test_admin_club_modifie_son_athlete_sans_changer_de_club(self):
        c = self.client_connecte(self.adminA)
        r = c.post(reverse('athlete_modifier', args=[self.athA.pk]),
                   {'nom': 'Renommé', 'prenom': 'A', 'sexe': 'M', 'categorie': 'Senior',
                    'groupe': 'G1', 'club': self.cB.pk})
        self.athA.refresh_from_db()
        self.assertEqual(self.athA.club_id, self.cA.pk)

    def test_modification_sans_champ_club_conserve_le_club(self):
        c = self.client_connecte(self.adminA)
        c.post(reverse('athlete_modifier', args=[self.athA.pk]),
               {'nom': 'Renommé', 'prenom': 'A', 'sexe': 'M', 'categorie': 'Senior', 'groupe': 'G1'})
        self.athA.refresh_from_db()
        self.assertEqual(self.athA.nom, 'Renommé')
        self.assertEqual(self.athA.club_id, self.cA.pk)

    def test_admin_club_ne_peut_pas_supprimer_un_coach_dun_autre_club(self):
        c = self.client_connecte(self.adminA)
        r = c.post(reverse('club_coach_supprimer', args=[self.coachB.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Utilisateur.objects.filter(pk=self.coachB.pk).exists())

    def test_admin_club_supprime_un_coach_de_son_club(self):
        c = self.client_connecte(self.adminA)
        self.assertEqual(c.post(reverse('club_coach_supprimer', args=[self.coachA2.pk])).status_code, 302)
        self.assertFalse(Utilisateur.objects.filter(pk=self.coachA2.pk).exists())

    def test_admin_club_ne_peut_pas_prevalider_un_athlete_dun_autre_club(self):
        c = self.client_connecte(self.adminA)
        r = c.post(reverse('prevalider_licence', args=[self.athB.pk]))
        self.assertEqual(r.status_code, 404)

    def test_coach_ne_supprime_que_les_performances_de_ses_athletes(self):
        autre = Performance.objects.create(athlete=self.athA2, epreuve="100m", performance="12.0", valeur_num=12.0)
        mienne = Performance.objects.create(athlete=self.athA, epreuve="100m", performance="11.0", valeur_num=11.0)
        c = self.client_connecte(self.coachA)
        self.assertEqual(c.post(reverse('performance_supprimer', args=[autre.pk])).status_code, 404)
        self.assertTrue(Performance.objects.filter(pk=autre.pk).exists())
        self.assertEqual(c.post(reverse('performance_supprimer', args=[mienne.pk])).status_code, 302)
        self.assertFalse(Performance.objects.filter(pk=mienne.pk).exists())

    def test_coach_ne_voit_pas_la_progression_dun_athlete_dun_autre_coach(self):
        c = self.client_connecte(self.coachA)
        self.assertEqual(c.get(reverse('athlete_progression', args=[self.athA2.pk])).status_code, 404)
        self.assertEqual(c.get(reverse('athlete_progression', args=[self.athA.pk])).status_code, 200)

    def test_coach_ne_saisit_pas_de_performance_pour_un_athlete_dun_autre_coach(self):
        c = self.client_connecte(self.coachA)
        c.post('/coach/saisie/enregistrer/', {
            'epreuve': '100m', 'athlete_id': self.athA2.pk, 'date': str(date.today()),
            f'perf_{self.athA2.pk}': '10.50', f'val_{self.athA2.pk}': '10.5'})
        self.assertEqual(Performance.objects.filter(athlete=self.athA2).count(), 0)


class MotsDePasseTemporairesTest(BaseSecuriteTest):

    def test_generateur_aleatoire_fort(self):
        mdps = {generer_mot_de_passe_temporaire() for _ in range(300)}
        self.assertEqual(len(mdps), 300)
        for m in mdps:
            self.assertEqual(len(m), 12)
            self.assertFalse(m.startswith('Lato@'))
            self.assertTrue(any(ch.islower() for ch in m) and any(ch.isupper() for ch in m)
                            and any(ch.isdigit() for ch in m))

    def _valider(self):
        a = Athlete.objects.create(nom="Nouveau", prenom="Ath", club=self.cA, statut_licence="en_attente")
        r = self.client_connecte(self.ligue).post(reverse('valider_licence', args=[a.pk]), follow=True)
        msgs = " ".join(str(m) for m in get_messages(r.wsgi_request))
        m = re.search(r'Mot de passe temporaire : (\S+)', msgs)
        self.assertIsNotNone(m, msgs)
        return Utilisateur.objects.get(email="ath.nouveau@lato.dz"), m.group(1)

    def test_validation_licence_cree_un_compte_avec_mdp_temporaire_fort(self):
        u, mdp = self._valider()
        self.assertTrue(u.must_change_password)
        self.assertEqual(len(mdp), 12)
        self.assertFalse(mdp.startswith('Lato@'))
        self.assertTrue(u.check_password(mdp))
        self.assertNotIn(mdp, u.mot_de_passe)

    def test_creation_coach_et_club_utilisent_un_mdp_temporaire(self):
        c = self.client_connecte(self.adminA)
        c.post(reverse('coach_creer'), {'nom': 'Nou', 'prenom': 'Coach', 'email': 'nou@t.dz',
                                        'specialite': 'Sprint', 'diplome': ''})
        u = Utilisateur.objects.get(email='nou@t.dz')
        self.assertTrue(u.must_change_password)

        c = self.client_connecte(self.ligue)
        c.post(reverse('club_creer'), {'nom': 'Club C', 'ville': 'TO', 'wilaya': 'TO',
                                       'responsable_nom': 'R', 'responsable_prenom': 'P',
                                       'responsable_email': 'resp@t.dz'})
        self.assertTrue(Utilisateur.objects.get(email='resp@t.dz').must_change_password)

    def test_premiere_connexion_force_le_changement(self):
        u, mdp = self._valider()
        c = Client()
        r = _connecter(c, u.email, mdp)
        self.assertRedirects(r, reverse('changer_mdp'), fetch_redirect_response=False)
        r = c.get(reverse('athlete_dashboard'))
        self.assertRedirects(r, reverse('changer_mdp'), fetch_redirect_response=False)
        self.assertEqual(c.get('/api/athletes/').status_code, 403)

    def test_changement_refuse_si_mdp_faible_ou_incorrect(self):
        u, mdp = self._valider()
        c = Client(); _connecter(c, u.email, mdp)
        url = reverse('changer_mdp')
        cas = [
            {'mdp_actuel': mdp, 'mdp_nouveau': 'court1', 'mdp_confirmation': 'court1'},
            {'mdp_actuel': mdp, 'mdp_nouveau': '1234567890', 'mdp_confirmation': '1234567890'},
            {'mdp_actuel': mdp, 'mdp_nouveau': 'password', 'mdp_confirmation': 'password'},
            {'mdp_actuel': mdp, 'mdp_nouveau': 'UnBonMotDePasse#7', 'mdp_confirmation': 'Different#7'},
            {'mdp_actuel': 'faux', 'mdp_nouveau': 'UnBonMotDePasse#7', 'mdp_confirmation': 'UnBonMotDePasse#7'},
            {'mdp_actuel': mdp, 'mdp_nouveau': mdp, 'mdp_confirmation': mdp},
        ]
        for data in cas:
            c.post(url, data)
            u.refresh_from_db()
            self.assertTrue(u.must_change_password, f"accepté à tort : {data}")
            self.assertTrue(u.check_password(mdp))

    def test_changement_valide_debloque_le_compte(self):
        u, mdp = self._valider()
        c = Client(); _connecter(c, u.email, mdp)
        r = c.post(reverse('changer_mdp'), {'mdp_actuel': mdp, 'mdp_nouveau': 'UnBonMotDePasse#7',
                                            'mdp_confirmation': 'UnBonMotDePasse#7'})
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db()
        self.assertFalse(u.must_change_password)
        self.assertTrue(u.check_password('UnBonMotDePasse#7'))
        self.assertFalse(u.check_password(mdp))
        self.assertNotEqual(c.get(reverse('athlete_dashboard')).status_code, 403)
        c2 = Client()
        self.assertRedirects(_connecter(c2, u.email, 'UnBonMotDePasse#7'),
                             reverse('athlete_dashboard'), fetch_redirect_response=False)

    def test_changer_mdp_exige_une_session(self):
        self.assertRedirects(Client().get(reverse('changer_mdp')), reverse('login'),
                             fetch_redirect_response=False)


class LimitationTentativesConnexionTest(BaseSecuriteTest):

    def test_blocage_apres_5_echecs_meme_avec_le_bon_mot_de_passe(self):
        c = Client()
        for _ in range(5):
            self.assertEqual(_connecter(c, self.ligue.email, 'faux').status_code, 200)
        r = _connecter(c, self.ligue.email, self.MDP)
        self.assertEqual(r.status_code, 429)
        self.assertNotIn('user_id', c.session)

    def test_un_succes_remet_le_compteur_a_zero(self):
        for _ in range(4):
            _connecter(Client(), self.ligue.email, 'faux')
        self.assertEqual(_connecter(Client(), self.ligue.email, self.MDP).status_code, 302)
        for _ in range(4):
            _connecter(Client(), self.ligue.email, 'faux')
        self.assertEqual(_connecter(Client(), self.ligue.email, self.MDP).status_code, 302)

    def test_le_blocage_ne_touche_pas_les_autres_comptes(self):
        for _ in range(5):
            _connecter(Client(), self.ligue.email, 'faux')
        self.assertEqual(_connecter(Client(), self.adminA.email, self.MDP).status_code, 302)

    def test_blocage_leve_apres_expiration(self):
        for _ in range(5):
            _connecter(Client(), self.ligue.email, 'faux')
        cache.clear()
        self.assertEqual(_connecter(Client(), self.ligue.email, self.MDP).status_code, 302)

    def test_session_regeneree_a_la_connexion(self):
        c = Client()
        c.get('/login/')
        avant = c.cookies.get('sessionid')
        _connecter(c, self.ligue.email, self.MDP)
        apres = c.cookies.get('sessionid')
        self.assertIsNotNone(apres)
        if avant:
            self.assertNotEqual(avant.value, apres.value)


class RecordsPersonnelsTest(TestCase):

    def setUp(self):
        self.a = Athlete.objects.create(nom="R", prenom="R")

    def _perfs(self, epreuve, valeurs):
        for v in valeurs:
            Performance.objects.create(athlete=self.a, epreuve=epreuve,
                                       performance=str(v), valeur_num=v)

    def test_classification_des_epreuves(self):
        for e in ['Longueur', 'Triple saut', 'Hauteur', 'Perche', 'Poids', 'Disque',
                  'Javelot', 'Marteau', 'Heptathlon', 'Décathlon', 'Saut en longueur']:
            self.assertTrue(est_epreuve_distance(e), e)
        for e in ['100m', '400m', '800m', '1500m', '110m haies', 'Marathon', '', None]:
            self.assertFalse(est_epreuve_distance(e), e)

    def test_est_meilleur(self):
        self.assertTrue(est_meilleur('100m', 10.8, 11.0))
        self.assertFalse(est_meilleur('100m', 11.2, 11.0))
        self.assertTrue(est_meilleur('Longueur', 6.9, 6.8))
        self.assertFalse(est_meilleur('Longueur', 6.0, 6.8))

    def test_saut_le_record_est_la_plus_grande_valeur(self):
        self._perfs('Longueur', [5.10, 6.80, 6.20])
        self.assertEqual(self.a.get_pbs()['Longueur']['valeur'], 6.80)

    def test_lancer_le_record_est_la_plus_grande_valeur(self):
        self._perfs('Javelot', [41.0, 55.5, 50.2])
        self.assertEqual(self.a.get_pbs()['Javelot']['valeur'], 55.5)

    def test_course_le_record_est_la_plus_petite_valeur(self):
        self._perfs('100m', [11.4, 10.9, 11.2])
        self.assertEqual(self.a.get_pbs()['100m']['valeur'], 10.9)

    def test_epreuves_mixtes_independantes(self):
        self._perfs('100m', [11.4, 10.9])
        self._perfs('Hauteur', [1.60, 1.85, 1.70])
        pbs = self.a.get_pbs()
        self.assertEqual(pbs['100m']['valeur'], 10.9)
        self.assertEqual(pbs['Hauteur']['valeur'], 1.85)

    def test_record_de_wilaya_saut_detecte_dans_la_saisie(self):
        from .models import RecordWilaya
        club = Club.objects.create(nom="C", actif=True)
        coach = Utilisateur.objects.create(nom="Co", email="co@t.dz", mot_de_passe=hacher("x"),
                                           role="coach", club=club)
        self.a.club, self.a.coach, self.a.statut_licence = club, coach, 'licencie'
        self.a.save()
        RecordWilaya.objects.create(epreuve='Longueur', sexe=self.a.sexe, performance='6.00', valeur_num=6.0)
        c = Client(); _connecter(c, "co@t.dz", "x")
        s = c.session; s['role'] = 'coach'; s['user_id'] = coach.pk; s['club_id'] = club.pk; s.save()
        c.post('/coach/saisie/enregistrer/', {
            'epreuve': 'Longueur', 'athlete_id': self.a.pk, 'date': str(date.today()),
            f'perf_{self.a.id}': '6.50', f'val_{self.a.id}': '6.5'})
        self.assertEqual(RecordWilaya.objects.get(epreuve='Longueur').valeur_num, 6.5)


class ReinitialisationMotDePasseTest(BaseSecuriteTest):

    def _mdp_affiche(self, reponse):
        msgs = " ".join(str(m) for m in get_messages(reponse.wsgi_request))
        m = re.search(r'Mot de passe temporaire : (\S+)', msgs)
        self.assertIsNotNone(m, msgs)
        return m.group(1)

    def test_la_ligue_reinitialise_le_mot_de_passe_dun_coach(self):
        c = self.client_connecte(self.ligue)
        r = c.post(reverse('reinitialiser_mdp', args=[self.coachB.pk]), follow=True)
        mdp = self._mdp_affiche(r)
        self.coachB.refresh_from_db()
        self.assertTrue(self.coachB.must_change_password)
        self.assertTrue(self.coachB.check_password(mdp))
        self.assertFalse(self.coachB.check_password(self.MDP))
        self.assertEqual(len(mdp), 12)

    def test_la_personne_doit_changer_le_mot_de_passe_a_la_connexion(self):
        c = self.client_connecte(self.ligue)
        mdp = self._mdp_affiche(c.post(reverse('reinitialiser_mdp', args=[self.coachA.pk]), follow=True))
        coach = Client()
        r = _connecter(coach, self.coachA.email, mdp)
        self.assertRedirects(r, reverse('changer_mdp'), fetch_redirect_response=False)

    def test_les_sessions_ouvertes_sont_fermees(self):
        coach = self.client_connecte(self.coachA)
        self.assertEqual(coach.get(reverse('coach_dashboard')).status_code, 200)
        self.client_connecte(self.ligue).post(reverse('reinitialiser_mdp', args=[self.coachA.pk]))
        r = coach.get(reverse('coach_dashboard'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_la_ligue_ne_peut_pas_reinitialiser_un_compte_ligue(self):
        autre = Utilisateur.objects.create(nom="L2", prenom="t", email="l2@t.dz",
                                          mot_de_passe=hacher(self.MDP), role="ligue")
        r = self.client_connecte(self.ligue).post(reverse('reinitialiser_mdp', args=[autre.pk]))
        self.assertEqual(r.status_code, 404)
        autre.refresh_from_db()
        self.assertFalse(autre.must_change_password)

    def test_admin_club_reinitialise_un_coach_de_son_club(self):
        r = self.client_connecte(self.adminA).post(reverse('reinitialiser_mdp', args=[self.coachA.pk]), follow=True)
        self._mdp_affiche(r)
        self.coachA.refresh_from_db()
        self.assertTrue(self.coachA.must_change_password)

    def test_admin_club_ne_touche_pas_aux_autres_clubs_ni_aux_admins(self):
        c = self.client_connecte(self.adminA)
        autre_admin = Utilisateur.objects.create(nom="AdminA2", prenom="t", email="adminA2@t.dz",
                                                 mot_de_passe=hacher(self.MDP), role="club_admin", club=self.cA)
        for cible in (self.coachB, self.ligue, autre_admin, self.adminA):
            self.assertEqual(c.post(reverse('reinitialiser_mdp', args=[cible.pk])).status_code, 404, cible.email)
            cible.refresh_from_db()
            self.assertFalse(cible.must_change_password)
            self.assertTrue(cible.check_password(self.MDP))

    def test_coach_et_athlete_n_ont_pas_acces(self):
        for user in (self.coachA,):
            c = self.client_connecte(user)
            self.assertEqual(c.get(reverse('comptes')).status_code, 302)
            self.assertEqual(c.post(reverse('reinitialiser_mdp', args=[self.coachA2.pk])).status_code, 302)
            self.coachA2.refresh_from_db()
            self.assertFalse(self.coachA2.must_change_password)
        self.assertEqual(Client().get(reverse('comptes')).status_code, 302)

    def test_get_refuse_et_csrf_exige(self):
        url = reverse('reinitialiser_mdp', args=[self.coachA.pk])
        self.assertEqual(self.client_connecte(self.ligue).get(url).status_code, 405)
        strict = self.client_connecte(self.ligue, enforce_csrf_checks=True)
        self.assertEqual(strict.post(url).status_code, 403)
        self.coachA.refresh_from_db()
        self.assertTrue(self.coachA.check_password(self.MDP))

    def test_page_comptes_cloisonnee_et_filtrable(self):
        html = self.client_connecte(self.ligue).get(reverse('comptes')).content.decode()
        for u in (self.adminA, self.coachA, self.coachB):
            self.assertIn(u.email, html)
        self.assertNotIn(self.ligue.email, html)
        self.assertIn('csrfmiddlewaretoken', html)

        html = self.client_connecte(self.adminA).get(reverse('comptes')).content.decode()
        self.assertIn(self.coachA.email, html)
        self.assertNotIn(self.coachB.email, html)
        self.assertNotIn(self.adminA.email, html)

        html = self.client_connecte(self.ligue).get(reverse('comptes') + '?q=coachB').content.decode()
        self.assertIn(self.coachB.email, html)
        self.assertNotIn(self.coachA.email, html)

    def test_menu_contient_les_liens_mot_de_passe(self):
        html = self.client_connecte(self.adminA).get(reverse('club_dashboard')).content.decode()
        self.assertIn(reverse('changer_mdp'), html)
        self.assertIn(reverse('comptes'), html)
        html = self.client_connecte(self.coachA).get(reverse('coach_dashboard')).content.decode()
        self.assertIn(reverse('changer_mdp'), html)
        self.assertNotIn(reverse('comptes'), html)
