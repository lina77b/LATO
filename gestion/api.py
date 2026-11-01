import json
from functools import wraps
from datetime import date, datetime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Club, Utilisateur, Athlete, Performance, RecordWilaya, Seance, Evenement, Notification


def jr(data, status=200):
    return JsonResponse(data, status=status, safe=isinstance(data, dict), json_dumps_params={'ensure_ascii': False})


def api_login_required(roles=None, write_roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            role = request.session.get('role')
            if not role:
                return jr({'error': 'Non authentifié'}, 401)
            if request.session.get('must_change_password'):
                return jr({'error': 'Changement de mot de passe requis'}, 403)
            allowed = roles
            if write_roles is not None and request.method not in ('GET', 'HEAD', 'OPTIONS'):
                allowed = write_roles
            if allowed and role not in allowed:
                return jr({'error': 'Accès non autorisé'}, 403)
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator


def _scope_club(request):
    if request.session.get('role') == 'ligue':
        return None
    return request.session.get('club_id') or -1


def _forbidden():
    return jr({'error': 'Accès non autorisé'}, 403)


@api_login_required(roles=['ligue', 'club_admin'])
def stats(request):
    cats = {c: Athlete.objects.filter(categorie=c).count()
            for c in ['Benjamin','Minime','Cadet','Junior','Senior','Master']}
    clubs_data = sorted([{'nom': c.nom, 'nb': c.nb_athletes()}
                         for c in Club.objects.filter(actif=True)], key=lambda x: -x['nb'])
    return jr({
        'nb_athletes_licencies': Athlete.objects.filter(statut_licence='licencie').count(),
        'nb_athletes_total': Athlete.objects.count(),
        'nb_clubs_actifs': Club.objects.filter(actif=True).count(),
        'nb_clubs_total': Club.objects.count(),
        'nb_licences_attente': Athlete.objects.filter(statut_licence__in=['en_attente','incomplet']).count(),
        'nb_records': RecordWilaya.objects.count(),
        'nb_performances': Performance.objects.count(),
        'categories': cats,
        'clubs_repartition': clubs_data,
    })


@api_login_required(roles=['ligue', 'club_admin'], write_roles=['ligue'])
def clubs(request):
    if request.method == 'GET':
        scope = _scope_club(request)
        qs = Club.objects.all() if scope is None else Club.objects.filter(pk=scope)
        return jr([c.to_dict() for c in qs])
    d = json.loads(request.body)
    c = Club.objects.create(nom=d['nom'], ville=d.get('ville',''), email=d.get('email',''))
    return jr(c.to_dict(), 201)


@api_login_required(roles=['ligue', 'club_admin'], write_roles=['ligue'])
def club_detail(request, pk):
    c = get_object_or_404(Club, pk=pk)
    scope = _scope_club(request)
    if scope is not None and c.pk != scope:
        return _forbidden()
    if request.method == 'GET':
        return jr(c.to_dict())
    if request.method == 'PUT':
        d = json.loads(request.body)
        for f in ['nom','ville','actif']:
            if f in d: setattr(c, f, d[f])
        c.save()
        return jr(c.to_dict())
    if request.method == 'DELETE':
        c.actif = False; c.save()
        return jr({'success': True})


@api_login_required(roles=['ligue', 'club_admin', 'coach'], write_roles=['ligue', 'club_admin'])
def athletes(request):
    if request.method == 'GET':
        q = Athlete.objects.select_related('club','coach').all()
        scope = _scope_club(request)
        if scope is not None:
            q = q.filter(club_id=scope)
        if request.GET.get('club_id'): q = q.filter(club_id=request.GET['club_id'])
        if request.GET.get('categorie'): q = q.filter(categorie=request.GET['categorie'])
        if request.GET.get('sexe'): q = q.filter(sexe=request.GET['sexe'])
        if request.GET.get('statut'): q = q.filter(statut_licence=request.GET['statut'])
        if request.GET.get('search'):
            s = request.GET['search']
            q = q.filter(Q(nom__icontains=s) | Q(prenom__icontains=s))
        if request.GET.get('coach_id'): q = q.filter(coach_id=request.GET['coach_id'])
        return jr([a.to_dict() for a in q])
    d = json.loads(request.body)
    a = Athlete.objects.create(
        nom=d['nom'], prenom=d.get('prenom',''),
        date_naissance=datetime.strptime(d['date_naissance'],'%Y-%m-%d').date() if d.get('date_naissance') else None,
        sexe=d.get('sexe','M'),
        club_id=d.get('club_id') if _scope_club(request) is None else _scope_club(request),
        groupe=d.get('groupe',''), categorie=d.get('categorie','Senior'),
        epreuves=d.get('epreuves',[]), cert_medical=d.get('cert_medical',False)
    )
    return jr(a.to_dict(), 201)


@api_login_required(roles=['ligue', 'club_admin', 'coach'], write_roles=['ligue', 'club_admin'])
def athlete_detail(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    scope = _scope_club(request)
    if scope is not None and a.club_id != scope:
        return _forbidden()
    if request.method == 'GET':
        data = a.to_dict()
        data['performances'] = [p.to_dict() for p in a.performance_set.order_by('-date')[:20]]
        data['progressions'] = {epr: a.get_progression(epr) for epr in (a.epreuves or []) if a.get_progression(epr)}
        return jr(data)
    if request.method == 'PUT':
        d = json.loads(request.body)
        for f in ['statut_licence','licence_no','cert_medical','groupe','coach_id','categorie']:
            if f in d: setattr(a, f, d[f])
        if 'epreuves' in d: a.epreuves = d['epreuves']
        a.save()
        return jr(a.to_dict())
    if request.method == 'DELETE':
        a.delete()
        return jr({'success': True})


@api_login_required(roles=['ligue'])
def valider(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    if a.statut_licence != 'en_attente':
        return jr({'error': 'Statut invalide'}, 400)
    a.statut_licence = 'licencie'
    a.licence_no = f"26-2026-{1000 + a.id:04d}"
    a.save()
    Notification.objects.create(destinataire_role='athlete', athlete=a,
        texte=f"Votre licence N° {a.licence_no} a ete validee par la Ligue.")
    return jr({'success': True, 'licence_no': a.licence_no})


@api_login_required(roles=['ligue', 'club_admin'])
def prevalider(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    scope = _scope_club(request)
    if scope is not None and a.club_id != scope:
        return _forbidden()
    if not a.cert_medical:
        return jr({'error': 'Certificat medical manquant'}, 400)
    a.statut_licence = 'en_attente'
    a.save()
    Notification.objects.create(destinataire_role='ligue',
        texte=f"Demande de licence: {a.nom_complet} ({a.club.nom if a.club else ''}) - {a.categorie}")
    return jr({'success': True})


@api_login_required(roles=['ligue'])
def rejeter(request, pk):
    a = get_object_or_404(Athlete, pk=pk)
    a.statut_licence = 'non_licencie'
    a.save()
    Notification.objects.create(destinataire_role='club_admin', club=a.club,
        texte=f"Licence refusee: {a.nom_complet} - verifiez le dossier")
    return jr({'success': True})


@api_login_required(roles=['ligue', 'club_admin', 'coach'], write_roles=['coach'])
def performances(request):
    if request.method == 'GET':
        q = Performance.objects.select_related('athlete','athlete__club').all()
        scope = _scope_club(request)
        if scope is not None:
            q = q.filter(athlete__club_id=scope)
        if request.GET.get('athlete_id'): q = q.filter(athlete_id=request.GET['athlete_id'])
        if request.GET.get('club_id'):
            aids = list(Athlete.objects.filter(club_id=request.GET['club_id']).values_list('id', flat=True))
            q = q.filter(athlete_id__in=aids)
        if request.GET.get('epreuve'): q = q.filter(epreuve=request.GET['epreuve'])
        if request.GET.get('saison'): q = q.filter(saison=request.GET['saison'])
        if request.GET.get('record_wilaya') == 'true': q = q.filter(record_wilaya=True)
        return jr([p.to_dict() for p in q.order_by('-date')[:100]])
    d = json.loads(request.body)
    athlete = get_object_or_404(Athlete, pk=d['athlete_id'])
    if athlete.club_id != _scope_club(request):
        return _forbidden()
    p = Performance.objects.create(
        athlete=athlete, epreuve=d['epreuve'], performance=d['performance'],
        valeur_num=float(d.get('valeur_num', 0)),
        date=datetime.strptime(d['date'],'%Y-%m-%d').date() if d.get('date') else date.today(),
        lieu=d.get('lieu',''), saison=d.get('saison','2025-2026')
    )
    try:
        rw = RecordWilaya.objects.get(epreuve=d['epreuve'], sexe=athlete.sexe)
        if p.valeur_num < rw.valeur_num:
            rw.valeur_num = p.valeur_num; rw.performance = p.performance
            rw.athlete = athlete; rw.athlete_nom = athlete.nom_complet
            rw.club_nom = athlete.club.nom if athlete.club else ''; rw.date = p.date; rw.save()
            p.record_wilaya = True; p.save()
            Notification.objects.create(destinataire_role='ligue',
                texte=f"RECORD Wilaya {d['epreuve']} - {athlete.nom_complet}: {d['performance']}")
    except RecordWilaya.DoesNotExist:
        pass
    return jr(p.to_dict(), 201)


@api_login_required(roles=['ligue', 'club_admin', 'coach'], write_roles=['coach'])
def seances(request):
    if request.method == 'GET':
        q = Seance.objects.select_related('club','coach').all()
        scope = _scope_club(request)
        if scope is not None:
            q = q.filter(club_id=scope)
        if request.GET.get('club_id'): q = q.filter(club_id=request.GET['club_id'])
        if request.GET.get('coach_id'): q = q.filter(coach_id=request.GET['coach_id'])
        return jr([s.to_dict() for s in q])
    d = json.loads(request.body)
    s = Seance.objects.create(
        titre=d['titre'], date=datetime.strptime(d['date'],'%Y-%m-%d').date(),
        heure=d.get('heure','09:00'), lieu=d.get('lieu',''), epreuve=d.get('epreuve',''),
        groupe=d.get('groupe',''), club_id=_scope_club(request), coach_id=request.session.get('user_id'),
        notes=d.get('notes',''))
    return jr(s.to_dict(), 201)


@api_login_required(write_roles=['ligue'])
def evenements(request):
    if request.method == 'GET':
        return jr([e.to_dict() for e in Evenement.objects.all()])
    d = json.loads(request.body)
    e = Evenement.objects.create(
        titre=d['titre'], date=datetime.strptime(d['date'],'%Y-%m-%d').date(),
        lieu=d.get('lieu',''), type_event=d.get('type_event','competition'), epreuves=d.get('epreuves',''))
    return jr(e.to_dict(), 201)


@api_login_required()
def records(request):
    q = RecordWilaya.objects.all()
    if request.GET.get('sexe'): q = q.filter(sexe=request.GET['sexe'])
    return jr([r.to_dict() for r in q])


@api_login_required()
def notifications(request, role):
    me = request.session.get('role')
    if me != 'ligue' and role != me:
        return _forbidden()
    q = Notification.objects.filter(destinataire_role=role)
    club_id = request.GET.get('club_id') if me == 'ligue' else request.session.get('club_id')
    athlete_id = request.GET.get('athlete_id') if me == 'ligue' else request.session.get('athlete_id')
    if club_id and role != 'ligue': q = q.filter(Q(club_id=club_id) | Q(club__isnull=True))
    if athlete_id and role == 'athlete': q = q.filter(Q(athlete_id=athlete_id) | Q(athlete__isnull=True))
    notifs = list(q.order_by('-created_at')[:20])
    return jr({'notifications': [n.to_dict() for n in notifs], 'unread': q.filter(lu=False).count()})


@api_login_required(roles=['ligue'])
def utilisateurs(request):
    if request.method == 'GET':
        q = Utilisateur.objects.select_related('club').all()
        if request.GET.get('role'): q = q.filter(role=request.GET['role'])
        if request.GET.get('club_id'): q = q.filter(club_id=request.GET['club_id'])
        return jr([u.to_dict() for u in q])
    d = json.loads(request.body)
    u = Utilisateur.objects.create(nom=d['nom'], email=d['email'],
        role=d.get('role','coach'), club_id=d.get('club_id'), specialite=d.get('specialite',''))
    return jr(u.to_dict(), 201)
