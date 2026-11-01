from django import forms
from datetime import date
from .models import Club, Utilisateur, Athlete, Seance, Evenement

EPREUVES_CHOICES = [
    ('60m','60m'),('100m','100m'),('200m','200m'),('400m','400m'),
    ('800m','800m'),('1500m','1500m'),('3000m','3000m'),('5000m','5000m'),
    ('10000m','10000m'),('Marathon','Marathon'),
    ('110m haies','110m haies'),('400m haies','400m haies'),
    ('Longueur','Longueur'),('Triple saut','Triple saut'),
    ('Hauteur','Hauteur'),('Perche','Perche'),
    ('Poids','Poids'),('Disque','Disque'),('Javelot','Javelot'),
]

W = {'class': 'form-control'}
WS = {'class': 'form-select'}

class ClubForm(forms.ModelForm):
    responsable_nom = forms.CharField(max_length=120, widget=forms.TextInput(attrs=W), label="Nom du responsable")
    responsable_prenom = forms.CharField(max_length=100, widget=forms.TextInput(attrs=W), label="Prénom du responsable")
    responsable_email = forms.EmailField(widget=forms.TextInput(attrs=W), label="Email du responsable")

    class Meta:
        model = Club
        fields = ['nom', 'ville', 'wilaya', 'email', 'telephone']
        widgets = {f: forms.TextInput(attrs=W) for f in ['nom', 'ville', 'wilaya', 'telephone']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update(W)
class AthleteForm(forms.ModelForm):
    epreuves_select = forms.MultipleChoiceField(
        choices=EPREUVES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False, label="Epreuves")
    class Meta:
        model = Athlete
        fields = ['nom','prenom','date_naissance','sexe','club','coach','groupe','categorie','cert_medical_img']
        widgets = {
            'nom': forms.TextInput(attrs=W), 'prenom': forms.TextInput(attrs=W),
            'date_naissance': forms.DateInput(attrs={**W, 'type':'date'}),
            'sexe': forms.Select(attrs=WS), 'club': forms.Select(attrs=WS),
            'coach': forms.Select(attrs=WS), 'groupe': forms.TextInput(attrs=W),
            'categorie': forms.Select(attrs=WS),
        }
    def __init__(self, *args, **kwargs):
        club_id = kwargs.pop('club_id', None)
        self._club_id = club_id
        super().__init__(*args, **kwargs)
        if club_id:
            self.fields['coach'].queryset = Utilisateur.objects.filter(role='coach', club_id=club_id)
            self.fields['club'].queryset = Club.objects.filter(pk=club_id)
        else:
            self.fields['coach'].queryset = Utilisateur.objects.filter(role='coach')
        self.fields['coach'].empty_label = "-- Aucun coach --"
        self.fields['club'].empty_label = "-- Choisir un club --"
        if self.instance.pk and self.instance.epreuves:
            self.fields['epreuves_select'].initial = self.instance.epreuves

    def clean_club(self):
        if self._club_id:
            return Club.objects.get(pk=self._club_id)
        return self.cleaned_data.get('club')

    def save(self, commit=True):
        inst = super().save(commit=False)
        inst.epreuves = self.cleaned_data.get('epreuves_select', [])
        if inst.cert_medical_img:
            inst.cert_medical = True
        if commit: inst.save()
        return inst

class SeanceForm(forms.ModelForm):
    class Meta:
        model = Seance
        fields = ['titre','date','heure','lieu','epreuve','groupe','notes']
        widgets = {
            'titre': forms.TextInput(attrs=W), 'lieu': forms.TextInput(attrs=W),
            'date': forms.DateInput(attrs={**W,'type':'date'}),
            'heure': forms.TimeInput(attrs={**W,'type':'time'}),
            'epreuve': forms.TextInput(attrs=W), 'groupe': forms.TextInput(attrs=W),
            'notes': forms.Textarea(attrs={**W,'rows':3}),
        }

class EvenementForm(forms.ModelForm):
    class Meta:
        model = Evenement
        fields = ['titre','date','lieu','type_event','epreuves','description']
        widgets = {
            'titre': forms.TextInput(attrs=W),
            'date': forms.DateInput(attrs={**W,'type':'date'}),
            'lieu': forms.TextInput(attrs=W),
            'type_event': forms.Select(attrs=WS),
            'epreuves': forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs={**W,'rows':3}),
        }

class UtilisateurForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['nom','email','specialite']
        widgets = {
            'nom': forms.TextInput(attrs=W),
            'email': forms.EmailInput(attrs=W),
            'specialite': forms.TextInput(attrs=W),
        }

class FiltreForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(
        attrs={**W,'placeholder':'Rechercher...'}))
    club = forms.ModelChoiceField(queryset=Club.objects.filter(actif=True),
        required=False, empty_label="Tous les clubs", widget=forms.Select(attrs=WS))
    categorie = forms.ChoiceField(required=False, widget=forms.Select(attrs=WS),
        choices=[('','Toutes'),('Benjamin','Benjamin'),('Minime','Minime'),
                 ('Cadet','Cadet'),('Junior','Junior'),('Senior','Senior')])
    sexe = forms.ChoiceField(required=False, widget=forms.Select(attrs=WS),
        choices=[('','Tous'),('M','Hommes'),('F','Femmes')])
    statut = forms.ChoiceField(required=False, widget=forms.Select(attrs=WS),
        choices=[('','Tous'),('licencie','Licencies'),('en_attente','En attente'),
                 ('incomplet','Incomplets'),('non_licencie','Non licencies')])

class SaisieForm(forms.Form):
    epreuve = forms.ChoiceField(choices=EPREUVES_CHOICES, widget=forms.Select(attrs=WS))
    date = forms.DateField(widget=forms.DateInput(attrs={**W,'type':'date'}), initial=date.today)
    lieu = forms.CharField(required=False, widget=forms.TextInput(attrs=W))
    saison = forms.ChoiceField(choices=[('2025-2026','2025-2026'),('2024-2025','2024-2025')],
                               widget=forms.Select(attrs=WS))
