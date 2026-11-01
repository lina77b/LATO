from django.contrib import admin
from .models import Club, Utilisateur, Athlete, Performance, RecordWilaya, Seance, Evenement

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['nom','ville','actif','nb_athletes']
    list_filter = ['actif']
    search_fields = ['nom']

@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ['nom_complet','club','categorie','sexe','statut_licence']
    list_filter = ['categorie','sexe','statut_licence','club']
    search_fields = ['nom','prenom']

@admin.register(Performance)
class PerfAdmin(admin.ModelAdmin):
    list_display = ['athlete','epreuve','performance','date','record_wilaya']
    list_filter = ['epreuve','record_wilaya','saison']
    search_fields = ['athlete__nom']

@admin.register(RecordWilaya)
class RecordAdmin(admin.ModelAdmin):
    list_display = ['epreuve','sexe','performance','athlete_nom','club_nom','date']

admin.site.register(Utilisateur)
admin.site.register(Seance)
admin.site.register(Evenement)
admin.site.site_header = "Ligue d'Athlétisme de Tizi Ouzou - Administration"
admin.site.site_title = "Ligue Athlétisme TO"
