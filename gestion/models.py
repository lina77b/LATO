from django.db import models
from datetime import date

MOTS_EPREUVES_DISTANCE = (
    'saut', 'longueur', 'hauteur', 'triple', 'perche',
    'poids', 'disque', 'javelot', 'marteau', 'lancer', 'athlon',
)


def est_epreuve_distance(epreuve):
    nom = (epreuve or '').lower()
    return any(mot in nom for mot in MOTS_EPREUVES_DISTANCE)


def est_meilleur(epreuve, valeur, reference):
    if est_epreuve_distance(epreuve):
        return valeur > reference
    return valeur < reference


class Club(models.Model):
    STATUTS = [
        ('EN_ATTENTE', 'En attente'),
        ('VALIDE', 'Valide'),
        ('SUSPENDU', 'Suspendu'),
    ]
    nom = models.CharField(max_length=120)
    ville = models.CharField(max_length=80, default='')
    wilaya = models.CharField(max_length=80, default='Tizi Ouzou')
    email = models.EmailField(blank=True, default='')
    telephone = models.CharField(max_length=20, blank=True, default='')
    informations_legales = models.TextField(blank=True, default='')
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'clubs'
        ordering = ['nom']


    def __str__(self): return self.nom
    def nb_athletes(self): return self.athlete_set.count()
    def nb_licencies(self): return self.athlete_set.filter(statut_licence='licencie').count()

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom, 'ville': self.ville,
            'wilaya': self.wilaya, 'email': self.email,
            'telephone': self.telephone, 'actif': self.actif,
            'statut': self.statut,
            'nb_athletes': self.nb_athletes(),
            'nb_licencies': self.nb_licencies(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Utilisateur(models.Model):
    ROLES = [
        ('ligue', 'Super Admin Ligue'),
        ('club_admin', 'Admin Club'),
        ('coach', 'Coach'),
        ('athlete', 'Athlete'),
    ]
    nom = models.CharField(max_length=120)
    prenom = models.CharField(max_length=100, default='')
    email = models.EmailField(unique=True)
    mot_de_passe = models.CharField(max_length=128, default='')
    role = models.CharField(max_length=20, choices=ROLES)
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.SET_NULL)
    specialite = models.CharField(max_length=60, blank=True, default='')
    diplome = models.CharField(max_length=100, blank=True, default='')
    actif = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def check_password(self, raw_password):
        try:
            import bcrypt
            return bcrypt.checkpw(raw_password.encode(), self.mot_de_passe.encode())
        except Exception:
            return False


    class Meta:
        db_table = 'utilisateurs'


    def __str__(self):
        return f"{self.nom} ({self.get_role_display()})"

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom, 'prenom': self.prenom,
            'email': self.email, 'role': self.role,
            'club_id': self.club_id,
            'club_nom': self.club.nom if self.club else None,
            'specialite': self.specialite, 'actif': self.actif,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Athlete(models.Model):
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    STATUTS = [
        ('non_licencie', 'Non licencie'),
        ('incomplet', 'Incomplet'),
        ('en_attente', 'En attente'),
        ('licencie', 'Licencie'),
    ]
    CATEGORIES = [
        ('Benjamin', 'Benjamin'),
        ('Minime', 'Minime'),
        ('Cadet', 'Cadet'),
        ('Junior', 'Junior'),
        ('Senior', 'Senior'),
        ('Master', 'Master'),
    ]
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, default='')
    date_naissance = models.DateField(null=True, blank=True)
    sexe = models.CharField(max_length=1,choices=SEXE_CHOICES, default='M')
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.SET_NULL)
    coach = models.ForeignKey(Utilisateur, null=True, blank=True, on_delete=models.SET_NULL, related_name='athletes_coaches')
    groupe = models.CharField(max_length=80, default='')
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='Senior')
    epreuves = models.JSONField(default=list)
    statut_licence = models.CharField(max_length=20, choices=STATUTS, default='non_licencie')
    licence_no = models.CharField(max_length=30, blank=True, null=True)
    cert_medical = models.BooleanField(default=False)
    cert_medical_img = models.ImageField(upload_to='certificats/', null=True, blank=True)
    dossier_medical_url = models.CharField(max_length=255, blank=True, default='')
    poids = models.FloatField(null=True, blank=True)
    taille = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    saison = models.CharField(max_length=12, default='2025-2026')


    class Meta:
        db_table = 'athletes'


    def __str__(self):
        return f"{self.prenom} {self.nom}"


    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()


    @property
    def initiales(self):
        parts = self.nom_complet.split()
        return ''.join(p[0] for p in parts[:2]).upper() if parts else '?'


    @property
    def age(self):
        if not self.date_naissance:
            return None
        today = date.today()
        return (today.year - self.date_naissance.year
                - ((today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)))


    def get_pbs(self):
        pbs = {}
        for p in self.performance_set.all():
            if p.epreuve not in pbs or est_meilleur(p.epreuve, p.valeur_num, pbs[p.epreuve]['valeur']):
                pbs[p.epreuve] = {
                    'valeur': p.valeur_num,
                    'perf': p.performance,
                    'date': p.date.isoformat() if p.date else None,
                    'record_wilaya': p.record_wilaya,
                }
        return pbs


    def get_progression(self, epreuve):
        return [
            { 'id': p.id,'date': p.date.isoformat(), 'perf': p.performance, 'valeur': p.valeur_num}
            for p in self.performance_set.filter(epreuve=epreuve).order_by('date')
        ]

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom, 'prenom': self.prenom,
            'nom_complet': self.nom_complet,
            'date_naissance': self.date_naissance.isoformat() if self.date_naissance else None,
            'age': self.age, 'sexe': self.sexe,
            'club_id': self.club_id,
            'club_nom': self.club.nom if self.club else None,
            'coach_id': self.coach_id,
            'coach_nom': f"{self.coach.prenom} {self.coach.nom}" if self.coach else None,
            'groupe': self.groupe, 'categorie': self.categorie,
            'epreuves': self.epreuves,
            'statut_licence': self.statut_licence,
            'licence_no': self.licence_no,
            'cert_medical': self.cert_medical,
            'saison': self.saison,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Performance(models.Model):
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE)
    epreuve = models.CharField(max_length=60)
    performance = models.CharField(max_length=30)
    valeur_num = models.FloatField(default=0)
    unite = models.CharField(max_length=20, blank=True, default='')
    commentaire = models.CharField(max_length=255, blank=True, default='')
    date = models.DateField(default=date.today)
    lieu = models.CharField(max_length=120, default='')
    record_wilaya = models.BooleanField(default=False)
    saison = models.CharField(max_length=12, default='2025-2026')
    coach = models.ForeignKey(Utilisateur, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'performances'
        indexes = [
            models.Index(fields=['epreuve'], name='idx_perf_epreuve'),
            models.Index(fields=['saison'], name='idx_perf_saison'),
            models.Index(fields=['record_wilaya'], name='idx_perf_record'),
            models.Index(fields=['athlete', 'epreuve'], name='idx_perf_athlete_epreuve'),
        ]


    def __str__(self):
        return f"{self.athlete} - {self.epreuve}: {self.performance}"

    def to_dict(self):
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'athlete_nom': self.athlete.nom_complet if self.athlete else None,
            'club_nom': self.athlete.club.nom if self.athlete and self.athlete.club else None,
            'epreuve': self.epreuve, 'performance': self.performance,
            'valeur_num': self.valeur_num, 'unite': self.unite,
            'commentaire': self.commentaire,
            'date': self.date.isoformat() if self.date else None,
            'lieu': self.lieu, 'record_wilaya': self.record_wilaya,
            'saison': self.saison,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RecordWilaya(models.Model):
    epreuve = models.CharField(max_length=60)
    sexe = models.CharField(max_length=1)
    performance = models.CharField(max_length=30)
    valeur_num = models.FloatField(default=0)
    athlete = models.ForeignKey(Athlete, null=True, blank=True, on_delete=models.SET_NULL)
    athlete_nom = models.CharField(max_length=120, default='')
    club_nom = models.CharField(max_length=120, default='')
    date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = [['epreuve', 'sexe']]


    def __str__(self):
        return f"RW {self.epreuve} {self.sexe}: {self.performance}"

    def to_dict(self):
        return {
            'id': self.id, 'epreuve': self.epreuve, 'sexe': self.sexe,
            'performance': self.performance, 'valeur_num': self.valeur_num,
            'athlete_id': self.athlete_id, 'athlete_nom': self.athlete_nom,
            'club_nom': self.club_nom,
            'date': self.date.isoformat() if self.date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Seance(models.Model):
    titre = models.CharField(max_length=150)
    date = models.DateField()
    heure = models.CharField(max_length=10, default='09:00')
    heure_fin = models.CharField(max_length=10, blank=True, default='')
    lieu = models.CharField(max_length=120, default='')
    epreuve = models.CharField(max_length=60, default='')
    groupe = models.CharField(max_length=80, default='')
    contenu_pedagogique = models.TextField(blank=True, default='')
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.SET_NULL)
    coach = models.ForeignKey(Utilisateur, null=True, blank=True, on_delete=models.SET_NULL)
    saison = models.CharField(max_length=12, default='2025-2026')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'seances'


    def __str__(self):
        return self.titre

    def to_dict(self):
        return {
            'id': self.id, 'titre': self.titre,
            'date': self.date.isoformat() if self.date else None,
            'heure': self.heure, 'heure_fin': self.heure_fin,
            'lieu': self.lieu, 'epreuve': self.epreuve, 'groupe': self.groupe,
            'club_id': self.club_id,
            'club_nom': self.club.nom if self.club else None,
            'coach_id': self.coach_id,
            'coach_nom': f"{self.coach.prenom} {self.coach.nom}" if self.coach else None,
            'notes': self.notes, 'saison': self.saison,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Evenement(models.Model):
    TYPES = [
        ('competition', 'Competition'),
        ('meeting', 'Meeting'),
        ('cross', 'Cross Country'),
        ('national', 'National'),
    ]
    titre = models.CharField(max_length=150)
    date = models.DateField()
    lieu = models.CharField(max_length=120, default='')
    type_event = models.CharField(max_length=20, choices=TYPES, default='competition')
    saison = models.CharField(max_length=12, default='2025-2026')
    epreuves = models.CharField(max_length=250, default='')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    programme = models.FileField(upload_to='programmes/', null=True, blank=True)

    def __str__(self):
        return self.titre

    def to_dict(self):
        return {
            'id': self.id, 'titre': self.titre,
            'date': self.date.isoformat() if self.date else None,
            'lieu': self.lieu, 'type_event': self.type_event,
            'epreuves': self.epreuves, 'description': self.description,
            'saison': self.saison,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Notification(models.Model):
    destinataire_role = models.CharField(max_length=20)
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.CASCADE)
    athlete = models.ForeignKey(Athlete, null=True, blank=True, on_delete=models.CASCADE)
    texte = models.TextField()
    lu = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.texte[:60]

    def to_dict(self):
        return {
            'id': self.id,
            'destinataire_role': self.destinataire_role,
            'club_id': self.club_id,
            'athlete_id': self.athlete_id,
            'texte': self.texte, 'lu': self.lu,
            'time_ago': self.time_ago(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


    def time_ago(self):
        from datetime import datetime
        delta = datetime.now() - self.created_at.replace(tzinfo=None)
        if delta.days > 0:
            return f"il y a {delta.days}j"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"il y a {hours}h"
        return f"il y a {max(1, delta.seconds // 60)} min"

class Palmares(models.Model):
    CLASSEMENTS = [
        ('or', 'Or — 1ère place'),
        ('argent', 'Argent — 2ème place'),
        ('bronze', 'Bronze — 3ème place'),
        ('finaliste', 'Finaliste'),
    ]
    NATURES = [
        ('national', 'National'),
        ('regional', 'Régional'),
        ('wilaya', 'Wilaya'),
        ('international', 'International'),
    ]
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE, related_name='palmares')
    saison = models.CharField(max_length=12, default='2025-2026')
    competition = models.CharField(max_length=200)
    nature = models.CharField(max_length=20, choices=NATURES, default='national')
    epreuve = models.CharField(max_length=80)
    date = models.DateField(null=True, blank=True)
    lieu = models.CharField(max_length=150, blank=True, default='')
    classement = models.CharField(max_length=20, choices=CLASSEMENTS, default='or')
    performance = models.CharField(max_length=30, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'palmares'
        ordering = ['-date']

    def __str__(self):
        return f"{self.athlete.nom_complet} — {self.epreuve} — {self.get_classement_display()}"
