import json
import os
from django.conf import settings
from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import (Club, Utilisateur, Athlete, Performance, RecordWilaya, Seance, Evenement,
                     Notification, Palmares, est_meilleur)
from .security import (generer_mot_de_passe_temporaire, hacher_mot_de_passe, connexion_bloquee,
                       enregistrer_echec, reinitialiser_echecs, invalider_sessions)
from .forms import ClubForm, AthleteForm, EvenementForm, UtilisateurForm, FiltreForm, SaisieForm
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
def public_home(request):
    evenements = Evenement.objects.all().order_by('-date')[:6]
    records = RecordWilaya.objects.all().order_by('epreuve')[:10]
    clubs = Club.objects.filter(actif=True).order_by('nom')
    perfs_recentes = Performance.objects.select_related('athlete', 'athlete__club').order_by('-date')[:5]
    return render(request, 'public/home.html', {
        'evenements': evenements,
        'records': records,
        'clubs': clubs,
        'perfs_recentes': perfs_recentes,
    })
def public_clubs(request):
    clubs = Club.objects.filter(actif=True).order_by('nom')
    return render(request, 'public/clubs.html', {'clubs': clubs})

def public_disciplines(request):
    return render(request, 'public/disciplines.html')

def public_inscription(request):
    clubs = Club.objects.filter(actif=True).order_by('nom')
    return render(request, 'public/inscription.html', {'clubs': clubs})
def get_user(request):
    uid = request.session.get('user_id')
    return Utilisateur.objects.filter(id=uid).first() if uid else None


def require_role(*roles):
    def decorator(fn):
        def wrapper(request, *args, **kwargs):
            role = request.session.get('role')
            if not role:
                return redirect('login')
            if role not in roles:
                messages.error(request, "Acces non autorise.")
                return redirect('login')
            if request.session.get('must_change_password'):
                messages.warning(request, "Vous devez d'abord choisir un nouveau mot de passe.")
                return redirect('changer_mdp')
            return fn(request, *args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


def notifs(role, club_id=None, athlete_id=None):
    q = Notification.objects.filter(destinataire_role=role)
    if club_id:
        q = q.filter(Q(club_id=club_id) | Q(club__isnull=True))
    if athlete_id:
        q = q.filter(Q(athlete_id=athlete_id) | Q(athlete__isnull=True))
    return {'notifications': q[:10], 'notif_count': q.filter(lu=False).count()}


def ctx(request, extra=None):
    user = get_user(request)
    role = request.session.get('role', '')
    cid = request.session.get('club_id')
    aid = request.session.get('athlete_id')
    saison = request.session.get('saison', '2025-2026')
    base = {'user': user, 'role': role, 'club_id': cid, 'saison_active': saison,
            'saisons': ['2023-2024', '2024-2025', '2025-2026']}
    base.update(notifs(role, club_id=cid, athlete_id=aid))
    if extra:
        base.update(extra)
    return base


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        mdp = request.POST.get('mot_de_passe', '')

        if connexion_bloquee(request, email):
            messages.error(request, "Trop de tentatives échouées. Réessayez dans 15 minutes.")
            return render(request, 'auth/login.html', status=429)

        user = Utilisateur.objects.filter(email=email, actif=True).first()
        if user and user.check_password(mdp):
            reinitialiser_echecs(request, email)
            request.session.cycle_key()
            request.session['user_id'] = user.id
            request.session['role'] = user.role
            request.session['club_id'] = user.club_id
            request.session['user_nom'] = user.nom
            request.session['must_change_password'] = user.must_change_password
            if user.role == 'athlete':
                a = Athlete.objects.filter(
                    prenom__iexact=user.prenom,
                    nom__iexact=user.nom,
                    club=user.club
                ).first()
                request.session['athlete_id'] = a.id if a else None
            if user.must_change_password:
                messages.warning(request, "Première connexion : choisissez votre mot de passe.")
                return redirect('changer_mdp')
            messages.success(request, f"Bienvenue, {user.nom} !")
            return redirect(_role_home(user.role))
        enregistrer_echec(request, email)
        messages.error(request, "Email ou mot de passe invalide.")
    return render(request, 'auth/login.html')


def changer_mot_de_passe(request):
    user = get_user(request)
    if not user:
        return redirect('login')
    forced = request.session.get('must_change_password', False)
    if request.method == 'POST':
        actuel = request.POST.get('mdp_actuel', '')
        nouveau = request.POST.get('mdp_nouveau', '')
        confirmation = request.POST.get('mdp_confirmation', '')
        erreurs = []
        if not user.check_password(actuel):
            erreurs.append("Le mot de passe actuel est incorrect.")
        if nouveau != confirmation:
            erreurs.append("Les deux nouveaux mots de passe ne correspondent pas.")
        if nouveau == actuel:
            erreurs.append("Le nouveau mot de passe doit être différent de l'actuel.")
        if not erreurs:
            try:
                validate_password(nouveau)
            except ValidationError as e:
                erreurs.extend(e.messages)
        if erreurs:
            for e in erreurs:
                messages.error(request, e)
        else:
            user.mot_de_passe = hacher_mot_de_passe(nouveau)
            user.must_change_password = False
            user.save(update_fields=['mot_de_passe', 'must_change_password'])
            request.session['must_change_password'] = False
            request.session.cycle_key()
            messages.success(request, "Mot de passe mis à jour.")
            return redirect(_role_home(user.role))
    return render(request, 'auth/changer_mdp.html', {'forced': forced})


def _comptes_gerables(request):
    if request.session.get('role') == 'ligue':
        return Utilisateur.objects.exclude(role='ligue')
    return Utilisateur.objects.filter(club_id=request.session.get('club_id'),
                                      role__in=['coach', 'athlete'])


@require_role('ligue', 'club_admin')
def comptes(request):
    est_ligue = request.session.get('role') == 'ligue'
    qs = _comptes_gerables(request).select_related('club')
    q = request.GET.get('q', '').strip()
    role_filtre = request.GET.get('role', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(email__icontains=q))
    if role_filtre in ('club_admin', 'coach', 'athlete'):
        qs = qs.filter(role=role_filtre)
    page = Paginator(qs.order_by('club__nom', 'role', 'nom'), 25).get_page(request.GET.get('page'))
    return render(request, 'ligue/comptes.html' if est_ligue else 'club/comptes.html', ctx(request, {
        'page': page, 'q': q, 'role_filtre': role_filtre, 'est_ligue': est_ligue,
    }))


@require_role('ligue', 'club_admin')
@require_POST
def reinitialiser_mdp(request, pk):
    u = get_object_or_404(_comptes_gerables(request), pk=pk)
    mdp = generer_mot_de_passe_temporaire()
    u.mot_de_passe = hacher_mot_de_passe(mdp)
    u.must_change_password = True
    u.save(update_fields=['mot_de_passe', 'must_change_password'])
    invalider_sessions(u.pk)
    messages.success(request, f"Mot de passe de {u.email} réinitialisé. Mot de passe temporaire : {mdp} "
                              f"(à transmettre à la personne ; elle devra le changer à sa prochaine connexion).")
    return redirect('comptes')


def _role_home(role):
    return {
        'ligue': 'ligue_dashboard',
        'club_admin': 'club_dashboard',
        'coach': 'coach_dashboard',
        'athlete': 'athlete_dashboard'
    }.get(role, 'login')


def logout_view(request):
    request.session.flush()
    return redirect('login')

@require_role('ligue')
def ligue_dashboard(request):
    saison = request.session.get('saison', '2025-2026')
    stats = {
        'nb_licencies': Athlete.objects.filter(statut_licence='licencie', saison=saison).count(),
        'nb_total': Athlete.objects.filter(saison=saison).count(),
        'nb_clubs_actifs': Club.objects.filter(actif=True).count(),
        'nb_attente': Athlete.objects.filter(statut_licence__in=['en_attente', 'incomplet'], saison=saison).count(),
        'nb_records': RecordWilaya.objects.count(),
        'nb_perfs': Performance.objects.filter(saison=saison).count(),
    }
    categories = {c: Athlete.objects.filter(categorie=c, saison=saison).count()
                  for c in ['Benjamin', 'Minime', 'Cadet', 'Junior', 'Senior']}
    clubs_top = sorted([{'club': c, 'nb': Athlete.objects.filter(club=c, saison=saison).count()}
                        for c in Club.objects.filter(actif=True)],
                       key=lambda x: -x['nb'])
    return render(request, 'ligue/dashboard.html', ctx(request, {
        'stats': stats,
        'categories': categories,
        'clubs_top': clubs_top,
        'saison': saison,
        'perfs_recentes': Performance.objects.filter(saison=saison).select_related('athlete', 'athlete__club').order_by('-date')[:8],
        'events_prochains': Evenement.objects.filter(saison=saison, date__gte=date.today()).order_by('date')[:4],
        'licences_attente': Athlete.objects.filter(statut_licence='en_attente', saison=saison).select_related('club')[:5],
    }))
def changer_saison(request):
    saison = request.GET.get('saison', '2025-2026')
    request.session['saison'] = saison
    next_url = request.GET.get('next', '/')
    return redirect(next_url)
@require_role('ligue')
def ligue_clubs(request):
    clubs = Club.objects.annotate(total=Count('athlete')).order_by('-total')
    nouveau_compte = request.session.pop('nouveau_compte', None)
    return render(request, 'ligue/clubs.html', ctx(request, {
        'clubs': clubs,
        'nouveau_compte': nouveau_compte,
    }))

@require_role('ligue')
@require_POST
def club_supprimer(request, pk):
    club = get_object_or_404(Club, pk=pk)
    club.delete()
    messages.success(request, f"Club {club.nom} supprimé.")
    return redirect('ligue_clubs')
@require_role('ligue')
def club_creer(request):
    form = ClubForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        c = form.save()

        nom = form.cleaned_data['responsable_nom']
        prenom = form.cleaned_data['responsable_prenom']
        email_resp = form.cleaned_data['responsable_email']
        mdp_clair = generer_mot_de_passe_temporaire()
        mdp_hash = hacher_mot_de_passe(mdp_clair)

        utilisateur, created = Utilisateur.objects.get_or_create(
            email=email_resp,
            defaults={
                'nom': nom,
                'prenom': prenom,
                'mot_de_passe': mdp_hash,
                'role': 'club_admin',
                'club': c,
                'actif': True,
                'must_change_password': True,
            }
        )

        request.session['nouveau_compte'] = {
            'titre': f"Club: {c.nom}",
            'email': email_resp,
            'mdp': mdp_clair if created else None,
        }

        return redirect('ligue_clubs')
    return render(request, 'ligue/club_form.html', ctx(request, {'form': form, 'titre': 'Creer un club'}))


@require_role('ligue')
def club_detail(request, pk):
    club = get_object_or_404(Club, pk=pk)
    return render(request, 'ligue/club_detail.html', ctx(request, {
        'club': club,
        'athletes': Athlete.objects.filter(club=club).select_related('coach'),
        'perfs': Performance.objects.filter(athlete__club=club).order_by('-date')[:10],
    }))
@require_role('ligue')
def club_modifier(request, pk):
    club = get_object_or_404(Club, pk=pk)
    if request.method == 'POST':
        club.nom = request.POST.get('nom', club.nom)
        club.ville = request.POST.get('ville', club.ville)
        club.email = request.POST.get('email', club.email)
        club.telephone = request.POST.get('telephone', club.telephone)
        club.informations_legales = request.POST.get('informations_legales', club.informations_legales)
        club.save()
        messages.success(request, f"Club {club.nom} modifié avec succès.")
        return redirect('ligue_clubs')
    return render(request, 'ligue/club_modifier.html', ctx(request, {'club': club}))

@require_role('ligue')
@require_POST
def club_toggle(request, pk):
    c = get_object_or_404(Club, pk=pk)
    c.actif = not c.actif
    c.save()
    messages.success(request, f"{c.nom} {'active' if c.actif else 'suspendu'}.")
    return redirect('ligue_clubs')
@require_role('ligue')
def evenement_modifier(request, pk):
    e = get_object_or_404(Evenement, pk=pk)
    form = EvenementForm(request.POST or None, instance=e)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('ligue_calendrier')
    return render(request, 'ligue/evenement_form.html', ctx(request, {'form': form, 'titre': 'Modifier une compétition', 'evenement': e}))


@require_role('ligue')
def ligue_athletes(request):
    form = FiltreForm(request.GET or None)
    qs = Athlete.objects.select_related('club', 'coach').all()
    saison = request.session.get('saison', '2025-2026')
    qs = qs.filter(saison=saison)
    if request.GET and form.is_valid():
        if form.cleaned_data.get('search'):
            s = form.cleaned_data['search']
            qs = qs.filter(Q(nom__icontains=s) | Q(prenom__icontains=s))
        if form.cleaned_data.get('club'):
            qs = qs.filter(club=form.cleaned_data['club'])
        if form.cleaned_data.get('categorie'):
            qs = qs.filter(categorie=form.cleaned_data['categorie'])
        if form.cleaned_data.get('sexe'):
            qs = qs.filter(sexe=form.cleaned_data['sexe'])
        if form.cleaned_data.get('statut'):
            qs = qs.filter(statut_licence=form.cleaned_data['statut'])
    return render(request, 'ligue/athletes.html', ctx(request, {
        'athletes': qs, 'form': form, 'total': qs.count()
    }))


@require_role('ligue')
def ligue_athlete_detail(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)
    return render(request, 'ligue/athlete_detail.html', ctx(request, {
        'athlete': athlete,
        'pbs': athlete.get_pbs(),
        'perfs_recentes': athlete.performance_set.order_by('-date')[:10],
    }))


@require_role('ligue')
@require_POST
def ligue_athlete_supprimer(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)
    nom = athlete.nom_complet
    athlete.delete()
    messages.success(request, f"L'athlete {nom} a bien ete supprime.")
    return redirect('ligue_athletes')


@require_role('ligue')
def ligue_licences(request):
    return render(request, 'ligue/licences.html', ctx(request, {
        'en_attente': Athlete.objects.filter(statut_licence='en_attente').select_related('club').order_by('-created_at'),
        'incomplets': Athlete.objects.filter(statut_licence='incomplet').select_related('club'),
        'licencies': Athlete.objects.filter(statut_licence='licencie').select_related('club').order_by('-created_at')[:10],
    }))


@require_role('ligue')
@require_POST
def valider_licence(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    if a.statut_licence == 'en_attente':
        a.statut_licence = 'licencie'
        a.licence_no = f"26-2026-{1000 + a.id:04d}"
        a.save()

        email = f"{a.prenom.lower().replace(' ', '')}.{a.nom.lower().replace(' ', '')}@lato.dz"
        mdp_clair = generer_mot_de_passe_temporaire()
        mdp_hash = hacher_mot_de_passe(mdp_clair)

        utilisateur, created = Utilisateur.objects.get_or_create(
            email=email,
            defaults={
                'nom': a.nom,
                'prenom': a.prenom,
                'mot_de_passe': mdp_hash,
                'role': 'athlete',
                'club': a.club,
                'actif': True,
                'must_change_password': True,
            }
        )

        Notification.objects.create(
            destinataire_role='athlete', athlete=a,
            texte=f"Votre licence N° {a.licence_no} est validee.")

        if created:
            messages.success(request, f"Licence de {a.nom_complet} validee - N° {a.licence_no} | Compte: {email} | Mot de passe temporaire : {mdp_clair} (changement obligatoire à la 1re connexion)")
        else:
            messages.success(request, f"Licence de {a.nom_complet} validee - N° {a.licence_no} | Compte existant: {email}")

    return redirect('ligue_licences')
@require_role('ligue')
@require_POST
def ligue_coach_supprimer(request, pk):
    coach = get_object_or_404(Utilisateur, pk=pk, role='coach')
    coach.delete()
    return redirect('ligue_coaches')
@require_role('ligue')
def ligue_coaches(request):
    coaches = Utilisateur.objects.filter(role='coach').select_related('club').order_by('club__nom')
    return render(request, 'ligue/coaches.html', ctx(request, {'coaches': coaches}))
@require_role('ligue')
@require_POST
def rejeter_licence(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    a.statut_licence = 'non_licencie'
    a.save()
    messages.warning(request, f"Demande de {a.nom_complet} rejetee.")
    return redirect('ligue_licences')


@require_role('ligue')
def ligue_records(request):
    if request.method == 'POST':
        RecordWilaya.objects.update_or_create(
            epreuve=request.POST.get('epreuve'),
            sexe=request.POST.get('sexe'),
            defaults={
                'performance': request.POST.get('performance'),
                'valeur_num': float(request.POST.get('valeur_num', 0)),
                'athlete_nom': request.POST.get('athlete_nom'),
                'club_nom': request.POST.get('club_nom', ''),
                'date': request.POST.get('date') or None,
                'lieu': request.POST.get('lieu', ''),
            }
        )
        messages.success(request, "Record enregistré.")
        return redirect('ligue_records')
    return render(request, 'ligue/records.html', ctx(request, {
        'records_h': RecordWilaya.objects.filter(sexe='M').order_by('epreuve'),
        'records_f': RecordWilaya.objects.filter(sexe='F').order_by('epreuve'),
    }))


@require_role('ligue')
def ligue_calendrier(request):
    form = EvenementForm(request.POST or None)
    saison = request.session.get('saison', '2025-2026')
    if request.method == 'POST' and form.is_valid():
        e = form.save()
        messages.success(request, f"Evenement '{e.titre}' ajoute.")
        return redirect('ligue_calendrier')
    return render(request, 'ligue/calendrier.html', ctx(request, {
        'evenements': Evenement.objects.filter(saison=saison).order_by('date'),
        'form': form,
    }))


@require_role('ligue')
@require_POST
def evenement_supprimer(request, pk):
    e = get_object_or_404(Evenement, pk=pk)
    nom = e.titre
    e.delete()
    messages.success(request, f"Evenement '{nom}' supprime.")
    return redirect('ligue_calendrier')


@require_role('club_admin')
def club_dashboard(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid) if cid else None
    ath = Athlete.objects.filter(club=club) if club else Athlete.objects.none()
    saison = request.session.get('saison', '2025-2026')
    ath = ath.filter(saison=saison)
    return render(request, 'club/dashboard.html', ctx(request, {
        'club': club,
        'nb_athletes': ath.count(),
        'nb_licencies': ath.filter(statut_licence='licencie').count(),
        'nb_attente': ath.filter(statut_licence__in=['non_licencie', 'incomplet']).count(),
        'nb_coaches': Utilisateur.objects.filter(role='coach', club=club).count() if club else 0,
        'perfs_recentes': Performance.objects.filter(athlete__club=club).order_by('-date')[:6] if club else [],
        'groupes': ath.values('groupe').annotate(nb=Count('id')).order_by('-nb')[:6],
    }))

@require_role('club_admin')
def club_seances(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    seances = Seance.objects.filter(club=club).select_related('coach').order_by('-date')
    return render(request, 'club/seances.html', ctx(request, {'club': club, 'seances': seances}))


@require_role('coach')
def seance_creer(request):
    uid = request.session.get('user_id')
    coach = get_object_or_404(Utilisateur, pk=uid)

    if request.method == 'POST':
        Seance.objects.create(
            titre=request.POST.get('titre', ''),
            date=request.POST.get('date'),
            heure=request.POST.get('heure', '09:00'),
            heure_fin=request.POST.get('heure_fin', ''),
            lieu=request.POST.get('lieu', ''),
            epreuve=request.POST.get('epreuve', ''),
            groupe=request.POST.get('groupe', ''),
            contenu_pedagogique=request.POST.get('contenu_pedagogique', ''),
            notes=request.POST.get('notes', ''),
            club=coach.club,
            coach=coach,
            saison=request.session.get('saison', '2025-2026'),
        )
        return redirect('coach_seances')
    return render(request, 'coach/seance_creer.html', ctx(request, {'coach': coach}))
@require_role('club_admin')
@require_POST
def club_coach_supprimer(request, pk):
    cid = request.session.get('club_id')
    coach = get_object_or_404(Utilisateur, pk=pk, role='coach', club_id=cid)
    coach.delete()
    return redirect('club_coaches')
@require_role('club_admin')
def club_athletes(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    form = FiltreForm(request.GET or None)
    qs = Athlete.objects.filter(club=club).select_related('coach')
    saison = request.session.get('saison', '2025-2026')
    qs = qs.filter(saison=saison)

    groupe = request.GET.get('groupe')
    if groupe:
        qs = qs.filter(groupe=groupe)

    if form.is_valid():
        if form.cleaned_data.get('search'):
            s = form.cleaned_data['search']
            qs = qs.filter(Q(nom__icontains=s) | Q(prenom__icontains=s))
        if form.cleaned_data.get('categorie'):
            qs = qs.filter(categorie=form.cleaned_data['categorie'])
        if form.cleaned_data.get('sexe'):
            qs = qs.filter(sexe=form.cleaned_data['sexe'])
        if form.cleaned_data.get('statut'):
            qs = qs.filter(statut_licence=form.cleaned_data['statut'])

    return render(request, 'club/athletes.html', ctx(request, {
        'athletes': qs, 'form': form, 'club': club, 'groupe_filtre': groupe
    }))


    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    form = AthleteForm(request.POST or None, club_id=cid)
    if request.method == 'POST' and form.is_valid():
        a = form.save(commit=False)
        a.club = club
        a.statut_licence = 'incomplet'
        a.save()
        messages.success(request, f"{a.nom_complet} ajoute avec succes.")
        return redirect('club_athlete_succes', athlete_id=a.pk)
    return render(request, 'club/athlete_form.html', ctx(request, {
        'form': form, 'club': club, 'titre': 'Ajouter un athlete'
    }))
@require_role('club_admin')
def athlete_creer(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    form = AthleteForm(request.POST or None, request.FILES or None, club_id=cid)
    if request.method == 'POST' and form.is_valid():
        a = form.save(commit=False)
        a.club = club
        a.statut_licence = 'incomplet'
        a.save()
        messages.success(request, f"{a.nom_complet} ajoute avec succes.")
        return redirect('club_athlete_succes', athlete_id=a.pk)
    return render(request, 'club/athlete_form.html', ctx(request, {
        'form': form, 'club': club, 'titre': 'Ajouter un athlete'
    }))

@require_role('club_admin')
def athlete_succes(request, athlete_id):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    athlete = get_object_or_404(Athlete, pk=athlete_id, club=club)
    return render(request, 'club/athlete_succes.html', ctx(request, {
        'club': club, 'athlete': athlete
    }))


@require_role('club_admin')
def generer_fiche_medicale(request, athlete_id):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    athlete = get_object_or_404(Athlete, pk=athlete_id, club=club)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Demande_Licence_{athlete.nom}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle(f"Demande de Licence - {athlete.nom_complet}")
    form = p.acroForm

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-ligue.png')
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 45, 725, width=55, height=55, mask='auto')
    else:
        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(colors.red)
        p.drawString(45, 755, "[Logo Introuvable]")
        p.setFillColor(colors.black)

    p.setFont("Helvetica-Bold", 12)
    p.drawString(115, 755, "LIGUE D'ATHLETISME DE TIZI OUZOU")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(115, 735, "DEMANDE DE LICENCE - RENSEIGNEMENTS GENERAUX")

    p.rect(470, 715, 75, 90, fill=0)
    p.setFont("Helvetica", 10)
    p.drawCentredString(507, 755, "Photo")
    p.setLineWidth(1.5)
    p.line(45, 705, 545, 705)

    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, 680, "N° d'identification Nationale Biometrique : ")
    form.textfield(name='num_biometrique', x=245, y=676, width=220, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(45, 655, f"Club : {club.nom.upper()}")
    p.drawString(280, 655, "Wilaya : Tizi Ouzou")
    p.drawString(430, 655, f"Categorie : {athlete.categorie}")

    p.setFont("Helvetica-Bold", 11)
    p.drawString(45, 625, "RENSEIGNEMENTS GENERAUX & FILIATION")
    p.rect(45, 465, 500, 145, fill=0)

    p.setFont("Helvetica", 10)
    p.drawString(60, 585, f"Nom : {athlete.nom}")
    p.drawString(280, 585, f"Prenoms : {athlete.prenom}")
    sexe_affiche = "Masculin (M)" if athlete.sexe == 'M' else "Feminin (F)"
    p.drawString(450, 585, f"Sexe : {sexe_affiche}")
    date_naiss = athlete.date_naissance.strftime('%d/%m/%Y') if athlete.date_naissance else ""
    p.drawString(60, 560, f"Ne(e) le : {date_naiss}")
    p.drawString(220, 560, "a : ")
    form.textfield(name='lieu_naissance', x=240, y=556, width=150, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(405, 560, "Gp. Sanguin : ")
    form.textfield(name='groupe_sanguin', x=475, y=556, width=50, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(60, 535, "Adresse : ")
    form.textfield(name='adresse_athlete', x=115, y=531, width=410, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(60, 510, "Nationalite : ")
    form.textfield(name='nationalite', x=125, y=506, width=150, height=15,
                   value="Algerienne", borderStyle='underlined', borderColor=colors.blue)
    p.drawString(60, 485, "Nom & Prenom du pere : ")
    form.textfield(name='pere', x=180, y=481, width=345, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(60, 470, "Nom & Prenom de la mere : ")
    form.textfield(name='mere', x=190, y=466, width=335, height=15,
                   borderStyle='underlined', borderColor=colors.blue)

    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, 435, "Club Quitte : ")
    form.textfield(name='club_quitte', x=115, y=431, width=180, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(305, 435, "Wilaya : ")
    form.textfield(name='wilaya_quittee', x=350, y=431, width=100, height=15,
                   borderStyle='underlined', borderColor=colors.blue)

    p.setFont("Helvetica-Bold", 11)
    p.drawString(45, 405, "CERTIFICAT MEDICAL")
    p.rect(45, 315, 500, 75, fill=0)
    p.setFont("Helvetica", 10)
    p.drawString(55, 365, "Je soussigne(e) Docteur : ")
    form.textfield(name='nom_medecin', x=175, y=361, width=350, height=15,
                   borderStyle='underlined', borderColor=colors.blue)
    p.drawString(55, 345, f"certifie que l'examen de l'athlete : {athlete.nom_complet.upper()}")
    p.drawString(55, 325, "ne revele pas de contre-indication a la pratique de l'athletisme.")
    p.drawString(55, 295, "Certificat etabli a : ")
    form.textfield(name='lieu_certif', x=145, y=291, width=120, height=15,
                   value="Tizi Ouzou", borderStyle='underlined', borderColor=colors.blue)
    p.drawString(275, 295, "Le : ")
    form.textfield(name='date_certif', x=295, y=291, width=100, height=15,
                   value=date.today().strftime('%d/%m/%Y'), borderStyle='underlined', borderColor=colors.blue)
    p.setFont("Helvetica-Bold", 9)
    p.drawRightString(530, 295, "Cachet & Signature du medecin")

    p.line(45, 275, 545, 275)
    p.drawString(45, 255, "Signature de l'Athlete")
    p.drawCentredString(295, 255, "Visa et Signature du Club")
    p.drawRightString(545, 255, "Visa et signature de la Ligue Wilaya")

    p.rect(45, 175, 500, 45, fill=0)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 200, "IMPORTANT :")
    p.setFont("Helvetica", 8)
    p.drawString(115, 200, "Toutes les informations relevent de la responsabilite exclusive du president du club.")
    p.drawString(50, 185, "notamment le certificat medical d'aptitude et l'assurance de l'athlete.")

    p.setFont("Helvetica-Bold", 9.5)
    p.drawString(45, 145, "Dossier a Joindre avec le formulaire :")
    p.setFont("Helvetica", 8.5)
    p.drawString(60, 125, "- 02 photos d'identite recente.")
    p.drawString(60, 110, "- Copie de la carte d'identite Biometrique ou Passeport ou Extrait de naissance.")
    p.drawString(60, 95, "- Autorisation paternelle legalisee par l'APC pour les mineurs.")

    p.setStrokeColor(colors.gray)
    p.line(45, 60, 545, 60)
    p.setFont("Helvetica", 7.5)
    p.drawString(45, 45, "Plateforme Numerique - Ligue d'Athletisme de Tizi Ouzou")

    p.showPage()
    p.save()
    return response


@require_role('club_admin')
def gerer_certificat(request, pk):
    cid = request.session.get('club_id')
    a = get_object_or_404(Athlete, pk=pk, club_id=cid)
    if request.method == 'POST':
        if request.FILES.get('cert_medical_img'):
            a.cert_medical_img = request.FILES['cert_medical_img']
            a.cert_medical = True
            if a.statut_licence == 'incomplet':
                a.statut_licence = 'non_licencie'
        a.save()
        messages.success(request, f"Certificat uploadé pour {a.nom_complet}.")
    return redirect('club_inscriptions')

def telecharger_licence(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    return render(request, 'shared/licence_print.html', {'athlete': a})
@require_role('club_admin', 'coach', 'ligue')
def athlete_detail(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    role = request.session.get('role')
    cid = request.session.get('club_id')
    if role == 'club_admin' and a.club_id and a.club_id != cid:
        messages.error(request, "Acces non autorise.")
        return redirect('club_athletes')
    if role == 'coach':
        u = get_user(request)
        if u and a.coach_id != u.id:
            messages.error(request, "Acces non autorise.")
            return redirect('coach_athletes')
    epreuves = a.epreuves if isinstance(a.epreuves, list) else []
    try:
        progressions = {epr: a.get_progression(epr) for epr in epreuves if a.get_progression(epr)}
    except Exception:
        progressions = {}
    return render(request, 'shared/athlete_detail.html', ctx(request, {
        'athlete': a,
        'perfs': a.performance_set.order_by('-date')[:20],
        'pbs': a.get_pbs(),
        'progressions_json': json.dumps(progressions),
    }))


@require_role('club_admin')
def athlete_modifier(request, pk):
    cid = request.session.get('club_id')
    a = get_object_or_404(Athlete, pk=pk, club_id=cid)
    form = AthleteForm(request.POST or None, instance=a, club_id=cid)
    if request.method == 'POST' and form.is_valid():
        a = form.save()
        if a.cert_medical and a.statut_licence == 'incomplet':
            a.statut_licence = 'non_licencie'
            a.save()
        messages.success(request, f"{a.nom_complet} mis a jour.")
        if a.statut_licence in ['incomplet', 'non_licencie', 'en_attente']:
            return redirect('club_inscriptions')
        return redirect('club_athletes')
    return render(request, 'club/athlete_form.html', ctx(request, {
        'form': form, 'athlete': a, 'titre': 'Modifier'
    }))


@require_role('club_admin')
@require_POST
def athlete_supprimer(request, pk):
    cid = request.session.get('club_id')
    athlete = get_object_or_404(Athlete, pk=pk, club_id=cid)
    nom = athlete.nom_complet
    athlete.delete()
    messages.success(request, f"L'athlete {nom} a ete supprime.")
    return redirect('club_athletes')


@require_role('club_admin')
@require_POST
def prevalider_licence(request, pk):
    cid = request.session.get('club_id')
    a = get_object_or_404(Athlete, pk=pk, club_id=cid)
    if not a.cert_medical_img:
        messages.error(request, "Certificat medical manquant.")
        return redirect('club_inscriptions')
    a.statut_licence = 'en_attente'
    a.save()
    Notification.objects.create(
        destinataire_role='ligue',
        texte=f"Demande licence: {a.nom_complet} ({a.club.nom if a.club else ''}) - {a.categorie}")
    messages.success(request, f"Dossier de {a.nom_complet} transmis a la Ligue.")
    return redirect('club_inscriptions')

@require_role('club_admin')
def club_inscriptions(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    return render(request, 'club/inscriptions.html', ctx(request, {
        'club': club,
        'non_lic': Athlete.objects.filter(club=club, statut_licence='non_licencie'),
        'incomplets': Athlete.objects.filter(club=club, statut_licence='incomplet'),
        'en_attente': Athlete.objects.filter(club=club, statut_licence='en_attente'),
    }))


@require_role('club_admin')
def club_coaches(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    nouveau_compte = request.session.pop('nouveau_compte', None)
    return render(request, 'club/coaches.html', ctx(request, {
        'club': club,
        'coaches': Utilisateur.objects.filter(role='coach', club=club),
        'nouveau_compte': nouveau_compte,
    }))

@require_role('club_admin')
def coach_creer(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    form = UtilisateurForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        u = form.save(commit=False)
        u.club = club
        u.role = 'coach'
        mdp_clair = generer_mot_de_passe_temporaire()
        mdp_hash = hacher_mot_de_passe(mdp_clair)
        u.mot_de_passe = mdp_hash
        u.must_change_password = True
        u.save()

        request.session['nouveau_compte'] = {
            'titre': f"Coach: {u.prenom} {u.nom}",
            'email': u.email,
            'mdp': mdp_clair,
        }

        return redirect('club_coaches')
    return render(request, 'club/coach_form.html', ctx(request, {'form': form, 'titre': 'Ajouter un coach'}))


@require_role('club_admin')
def club_groupes(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)

    groupes_raw = Athlete.objects.filter(club=club).values('groupe').annotate(nb=Count('id')).order_by('groupe')

    groupes = []
    for g in groupes_raw:
        athletes = Athlete.objects.filter(club=club, groupe=g['groupe'])
        coach = athletes.filter(coach__isnull=False).values_list(
            'coach__prenom', 'coach__nom'
        ).first()
        groupes.append({
            'groupe': g['groupe'],
            'nb': g['nb'],
            'coach': f"{coach[0]} {coach[1]}" if coach else None,
            'athletes': [f"{a.prenom} {a.nom}" for a in athletes],
        })

    return render(request, 'club/groupes.html', ctx(request, {'club': club, 'groupes': groupes}))


@require_role('club_admin')
def club_performances(request):
    cid = request.session.get('club_id')
    club = get_object_or_404(Club, pk=cid)
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'club/performances.html', ctx(request, {
        'club': club,
        'perfs': Performance.objects.filter(athlete__club=club, saison=saison).select_related('athlete').order_by('-date')[:50],
    }))

@require_role('club_admin')
def club_calendrier(request):
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'shared/calendrier.html', ctx(request, {
        'evenements': Evenement.objects.filter(saison=saison).order_by('date'),
    }))


@require_role('coach')
def coach_dashboard(request):
    user = get_user(request)
    cid = request.session.get('club_id')
    saison = request.session.get('saison', '2025-2026')
    club = Club.objects.filter(pk=cid).first() if cid else None
    groupe = Athlete.objects.filter(coach=user, saison=saison).select_related('club') if user else Athlete.objects.none()
    return render(request, 'coach/dashboard.html', ctx(request, {
        'club': club,
        'mon_groupe': groupe,
        'nb_athletes': groupe.count(),
        'seances': Seance.objects.filter(coach=user, saison=saison).order_by('-date')[:3],
        'perfs_recentes': Performance.objects.filter(coach=user, saison=saison).select_related('athlete').order_by('-date')[:6],
        'prochaine_seance': Seance.objects.filter(coach=user, saison=saison, date__gte=date.today()).order_by('date').first(),
        'nb_seances_mois': Seance.objects.filter(coach=user, saison=saison, date__month=date.today().month).count(),
        'nb_perfs': Performance.objects.filter(coach=user, saison=saison).count(),
        'nb_records': Performance.objects.filter(coach=user, saison=saison, record_wilaya=True).count(),
    }))


@require_role('coach')
def coach_athletes(request):
    user = get_user(request)
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'coach/athletes.html', ctx(request, {
        'athletes': Athlete.objects.filter(coach=user, saison=saison).select_related('club'),
    }))


@require_role('coach')
def coach_seances(request):
    user = get_user(request)
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'coach/seances.html', ctx(request, {
        'seances': Seance.objects.filter(coach=user, saison=saison).order_by('-date'),
    }))


@require_role('coach')
def coach_saisie(request):
    user = get_user(request)
    form = SaisieForm(request.POST or None)
    return render(request, 'coach/saisie.html', ctx(request, {
        'form': form,
        'athletes': Athlete.objects.filter(coach=user, statut_licence='licencie'),
    }))

@require_role('coach')
@require_POST
def performance_supprimer(request, pk):
    user = get_user(request)
    p = get_object_or_404(Performance, pk=pk, athlete__coach=user)
    athlete_id = p.athlete_id
    p.delete()
    return redirect('athlete_progression', pk=athlete_id)
@require_role('coach')
def saisie_enregistrer(request):
    if request.method != 'POST':
        return redirect('coach_saisie')
    user = get_user(request)
    epreuve = request.POST.get('epreuve')
    perf_date_str = request.POST.get('date', str(date.today()))
    lieu = request.POST.get('lieu', '')
    saison = request.POST.get('saison', '2025-2026')
    contexte = request.POST.get('contexte', 'entrainement')
    evenement_id = request.POST.get('evenement_id', '')
    athlete_id = request.POST.get('athlete_id')

    if athlete_id:
        athletes = Athlete.objects.filter(pk=athlete_id, coach=user, statut_licence='licencie')
    else:
        athletes = Athlete.objects.filter(coach=user, statut_licence='licencie')


    saved = 0
    for a in athletes:
        perf_str = request.POST.get(f'perf_{a.id}', '').strip()
        val_str = request.POST.get(f'val_{a.id}', '').strip()
        commentaire = request.POST.get(f'comment_{a.id}', '').strip()
        if contexte == 'competition' and evenement_id:
            ev = Evenement.objects.filter(pk=evenement_id).first()
            commentaire = f"[Compétition: {ev.titre}] {commentaire}" if ev else commentaire
        else:
            commentaire = f"[Entraînement] {commentaire}"
        if perf_str and val_str:
            try:
                val = float(val_str)
                from django.db import transaction
                with transaction.atomic():
                    p = Performance.objects.create(
                        athlete=a, epreuve=epreuve, performance=perf_str,
                        valeur_num=val,
                        date=datetime.strptime(perf_date_str, '%Y-%m-%d').date(),
                        lieu=lieu, saison=saison, coach=user,
                        commentaire=commentaire,
                    )
                    try:
                        rw = RecordWilaya.objects.get(epreuve=epreuve, sexe=a.sexe)
                        est_nouveau_record = est_meilleur(epreuve, val, rw.valeur_num)
                        if est_nouveau_record:
                            rw.valeur_num = val
                            rw.performance = perf_str
                            rw.athlete = a
                            rw.athlete_nom = a.nom_complet
                            rw.club_nom = a.club.nom if a.club else ''
                            rw.date = p.date
                            rw.save()
                            p.record_wilaya = True
                            p.save()
                            Notification.objects.create(
                                destinataire_role='ligue',
                                texte=f"RECORD Wilaya {epreuve} - {a.nom_complet}: {perf_str}")
                    except RecordWilaya.DoesNotExist:
                        pass
                saved += 1
            except (ValueError, Exception):
                pass

    messages.success(request, f"{saved} performance(s) enregistree(s).")
    if athlete_id:
        return redirect('athlete_progression', pk=athlete_id)
    return redirect('coach_saisie')


@require_role('coach')
def coach_progressions(request):
    user = get_user(request)
    return render(request, 'coach/progressions.html', ctx(request, {
        'athletes': Athlete.objects.filter(coach=user).select_related('club'),
    }))


@require_role('coach')
def athlete_progression(request, pk):
    a = get_object_or_404(Athlete, pk=pk, coach=get_user(request))
    saison = request.session.get('saison', '2025-2026')
    evenements = Evenement.objects.filter(saison=saison).order_by('-date')
    perfs_par_epreuve = []
    progressions = {}
    for epr in (a.epreuves or []):
        perfs = list(a.performance_set.filter(epreuve=epr, saison=saison).order_by('-date').values('id', 'date', 'performance', 'lieu', 'commentaire', 'record_wilaya'))
        perfs_par_epreuve.append({'epreuve': epr, 'perfs': perfs})
        progressions[epr] = a.get_progression(epr)
    return render(request, 'coach/progression_detail.html', ctx(request, {
        'athlete': a,
        'pbs': a.get_pbs(),
        'evenements': evenements,
        'today': date.today().strftime('%Y-%m-%d'),
        'perfs_par_epreuve': perfs_par_epreuve,
        'progressions_json': json.dumps(progressions),
    }))


@require_role('athlete')
def athlete_dashboard(request):
    aid = request.session.get('athlete_id')
    a = get_object_or_404(Athlete, pk=aid) if aid else None
    if not a:
        return redirect('login')
    saison = request.session.get('saison', '2025-2026')
    progressions = {epr: a.get_progression(epr) for epr in (a.epreuves or []) if a.get_progression(epr)}
    return render(request, 'athlete/dashboard.html', ctx(request, {
        'athlete': a,
        'pbs': a.get_pbs(),
        'perfs_recentes': a.performance_set.filter(saison=saison).order_by('-date')[:5],
        'prochaine_seance': Seance.objects.filter(club=a.club, saison=saison, date__gte=date.today()).order_by('date').first(),
        'events_prochains': Evenement.objects.filter(saison=saison, date__gte=date.today()).order_by('date')[:3],
        'progressions_json': json.dumps(progressions),
    }))


@require_role('athlete')
def athlete_profil(request):
    aid = request.session.get('athlete_id')
    a = get_object_or_404(Athlete, pk=aid)
    return render(request, 'athlete/profil.html', ctx(request, {'athlete': a, 'pbs': a.get_pbs()}))


@require_role('athlete')
def athlete_performances(request):
    aid = request.session.get('athlete_id')
    a = get_object_or_404(Athlete, pk=aid)
    epreuve = request.GET.get('epreuve', '')
    saison = request.session.get('saison', '2025-2026')
    qs = a.performance_set.filter(saison=saison)
    if epreuve:
        qs = qs.filter(epreuve=epreuve)
    progressions = {epr: a.get_progression(epr) for epr in (a.epreuves or []) if a.get_progression(epr)}
    return render(request, 'athlete/performances.html', ctx(request, {
        'athlete': a, 'perfs': qs.order_by('-date'), 'pbs': a.get_pbs(),
        'epreuve_sel': epreuve, 'saison': saison,
        'progressions_json': json.dumps(progressions),
    }))


@require_role('athlete')
def athlete_licence(request):
    aid = request.session.get('athlete_id')
    a = get_object_or_404(Athlete, pk=aid)
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'athlete/licence.html', ctx(request, {
        'athlete': a,
        'saison': saison,
    }))


@require_role('athlete')
def athlete_seances(request):
    aid = request.session.get('athlete_id')
    a = get_object_or_404(Athlete, pk=aid)
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'athlete/seances.html', ctx(request, {
        'athlete': a,
        'seances': Seance.objects.filter(club=a.club, saison=saison).order_by('-date'),
    }))


@require_role('athlete')
def athlete_calendrier(request):
    aid = request.session.get('athlete_id')
    a = get_object_or_404(Athlete, pk=aid)
    saison = request.session.get('saison', '2025-2026')
    return render(request, 'shared/calendrier.html', ctx(request, {
        'athlete': a,
        'evenements': Evenement.objects.filter(saison=saison).order_by('date'),
    }))
@require_role('ligue')
def ligue_bilan(request):
    saison = request.session.get('saison', '2025-2026')
    categories = ['Benjamin', 'Minime', 'Cadet', 'Junior', 'Senior', 'Master']
    clubs = Club.objects.filter(actif=True).order_by('nom')

    tableau_clubs = []
    for club in clubs:
        aths = Athlete.objects.filter(club=club, saison=saison)
        row = {'club': club, 'categories': {}}
        total_h = total_f = 0
        for cat in categories:
            h = aths.filter(categorie=cat, sexe='M').count()
            f = aths.filter(categorie=cat, sexe='F').count()
            row['categories'][cat] = {'H': h, 'F': f, 'total': h + f}
            total_h += h
            total_f += f
        row['total_H'] = total_h
        row['total_F'] = total_f
        row['total'] = total_h + total_f
        if row['total'] > 0:
            tableau_clubs.append(row)

    totaux = {}
    for cat in categories:
        h = Athlete.objects.filter(categorie=cat, sexe='M', club__actif=True).count()
        f = Athlete.objects.filter(categorie=cat, sexe='F', club__actif=True).count()
        totaux[cat] = {'H': h, 'F': f, 'total': h + f}
    totaux['TOTAL'] = {
        'H': Athlete.objects.filter(sexe='M', club__actif=True).count(),
        'F': Athlete.objects.filter(sexe='F', club__actif=True).count(),
        'total': Athlete.objects.filter(club__actif=True).count(),
    }

    competitions = Evenement.objects.filter(saison=saison).order_by('date')

    laureats = Palmares.objects.filter(
        saison=saison, classement__in=['or', 'argent', 'bronze']
    ).select_related('athlete', 'athlete__club').order_by('classement', 'epreuve')

    finalistes = Palmares.objects.filter(
        saison=saison, classement='finaliste'
    ).select_related('athlete', 'athlete__club').order_by('epreuve')

    return render(request, 'ligue/bilan.html', ctx(request, {
        'saison': saison,
        'categories': categories,
        'tableau_clubs': tableau_clubs,
        'totaux': totaux,
        'competitions': competitions,
        'laureats': laureats,
        'finalistes': finalistes,
        'saisons': ['2023-2024', '2024-2025', '2025-2026'],
        'all_athletes': Athlete.objects.filter(club__actif=True).select_related('club').order_by('nom'),
    }))


@require_role('ligue')
def palmares_creer(request):
    if request.method == 'POST':
        Palmares.objects.create(
            athlete_id=request.POST.get('athlete'),
            saison=request.POST.get('saison', '2025-2026'),
            competition=request.POST.get('competition', ''),
            nature=request.POST.get('nature', 'national'),
            epreuve=request.POST.get('epreuve', ''),
            date=request.POST.get('date') or None,
            lieu=request.POST.get('lieu', ''),
            classement=request.POST.get('classement', 'or'),
            performance=request.POST.get('performance', ''),
        )
        messages.success(request, "Résultat ajouté au palmarès.")
    return redirect('ligue_bilan')


@require_role('ligue')
@require_POST
def palmares_supprimer(request, pk):
    p = get_object_or_404(Palmares, pk=pk)
    p.delete()
    messages.success(request, "Résultat supprimé.")
    return redirect('ligue_bilan')
@require_role('ligue')
def evenement_upload_programme(request, pk):
    e = get_object_or_404(Evenement, pk=pk)
    if request.method == 'POST' and request.FILES.get('programme'):
        e.programme = request.FILES['programme']
        e.save()
        messages.success(request, f"Programme uploadé pour {e.titre}.")
    return redirect('ligue_calendrier')
