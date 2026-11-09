"""
Commande de management Django : `python manage.py load_demo_data`

Peuple la base de données de TourismeSahel avec un jeu de données réaliste
inspiré du patrimoine sahélien (Djenné, Tombouctou, Pays Dogon, Saint-Louis,
Agadez, Sindou/Banfora), incluant :
- Pays, Régions et Destinations (avec coordonnées GPS et visuels générés) ;
- Catégories et Sites touristiques (UNESCO, horaires, tarifs, histoire) ;
- Langues, Spécialités et Guides locaux certifiés ;
- Circuits accompagnés et leurs étapes jour par jour (`EtapeCircuit`) ;
- Comptes de démonstration (Administrateur, Guides, Visiteurs) ;
- Réservations (acceptées, terminées, en attente), Avis et Favoris.

La commande est idempotente : elle peut être relancée plusieurs fois sans créer
de doublons. L'option `--reset` permet de purger préalablement les données.
"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.bookings.models import Reservation
from apps.circuits.models import Circuit, EtapeCircuit
from apps.guides.models import DisponibiliteGuide, Guide, Langue, SpecialiteGuide
from apps.locations.models import Destination, Pays, Region
from apps.reviews.models import Avis, Favori
from apps.tourism.models import CategorieSite, SiteTouristique


def creer_visuel_sahel(largeur=960, hauteur=640, couleur_principale=(20, 83, 45), couleur_accent=(214, 168, 75)):
    """
    Génère en mémoire une illustration JPEG légère aux couleurs de la charte
    TourismeSahel (dégradé + soleil doré + silhouette de dune/terre).
    """
    img = Image.new("RGB", (largeur, hauteur), couleur_principale)
    draw = ImageDraw.Draw(img)

    # Dégradé doux vertical
    for y in range(hauteur):
        ratio = y / max(hauteur - 1, 1)
        r = int(couleur_principale[0] * (1 - 0.35 * ratio) + couleur_accent[0] * (0.35 * ratio))
        g = int(couleur_principale[1] * (1 - 0.35 * ratio) + couleur_accent[1] * (0.35 * ratio))
        b = int(couleur_principale[2] * (1 - 0.35 * ratio) + couleur_accent[2] * (0.35 * ratio))
        draw.line([(0, y), (largeur, y)], fill=(r, g, b))

    # Soleil sahélien doré
    rayon = min(largeur, hauteur) // 6
    cx, cy = int(largeur * 0.72), int(hauteur * 0.32)
    draw.ellipse([cx - rayon, cy - rayon, cx + rayon, cy + rayon], fill=(214, 168, 75))

    # Bande d'horizon ocre / sable au bas de l'image
    horizon_y = int(hauteur * 0.72)
    draw.polygon(
        [(0, hauteur), (0, horizon_y), (int(largeur * 0.45), horizon_y - 35), (largeur, horizon_y + 10), (largeur, hauteur)],
        fill=(168, 92, 32),
    )
    draw.rectangle([0, int(hauteur * 0.86), largeur, hauteur], fill=(245, 235, 215))

    tampon = BytesIO()
    img.save(tampon, format="JPEG", quality=82)
    return tampon.getvalue()


def charger_image_lieu(nom_fichier, couleur_principale=(20, 83, 45), couleur_accent=(214, 168, 75)):
    """
    Charge la photographie authentique du lieu depuis `static/img/places/<nom_fichier>`.
    Utilise un visuel généré aux couleurs de la charte uniquement en secours si le fichier est absent.
    """
    chemin = Path(settings.BASE_DIR) / "static" / "img" / "places" / nom_fichier
    if chemin.is_file():
        return chemin.read_bytes()
    return creer_visuel_sahel(couleur_principale=couleur_principale, couleur_accent=couleur_accent)


class Command(BaseCommand):
    help = "Charge un jeu de données de démonstration réaliste pour la plateforme TourismeSahel."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les réservations, avis, favoris, circuits, sites, guides et destinations avant le chargement.",
        )
        parser.add_argument(
            "--refresh-images",
            action="store_true",
            help="Remplace les images principales existantes par les photographies correspondantes de chaque lieu.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        aujourd_hui = timezone.localdate()
        rafraichir_images = options["reset"] or options["refresh_images"]

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Nettoyage des données existantes (--reset)..."))
            Favori.objects.all().delete()
            Avis.objects.all().delete()
            Reservation.objects.all().delete()
            EtapeCircuit.objects.all().delete()
            Circuit.objects.all().delete()
            DisponibiliteGuide.objects.all().delete()
            Guide.objects.all().delete()
            SiteTouristique.objects.all().delete()
            CategorieSite.objects.all().delete()
            Destination.objects.all().delete()
            Region.objects.all().delete()
            Pays.objects.all().delete()

            racine_media = Path(settings.MEDIA_ROOT)
            for sous_dossier in ("locations", "tourism", "circuits", "guides"):
                cible = racine_media / sous_dossier
                if cible.is_dir():
                    shutil.rmtree(cible, ignore_errors=True)

        # Chargement des photographies dédiées à chaque lieu du Sahel
        photos_lieux = {
            "djenne_mosquee": charger_image_lieu("djenne_mosquee.jpg", (168, 92, 32), (214, 168, 75)),
            "tombouctou_djingareyber": charger_image_lieu("tombouctou_djingareyber.jpg", (38, 50, 56), (168, 92, 32)),
            "manuscrits_ahmed_baba": charger_image_lieu("manuscrits_ahmed_baba.jpg", (38, 50, 56), (214, 168, 75)),
            "pays_dogon_bandiagara": charger_image_lieu("pays_dogon_bandiagara.jpg", (168, 92, 32), (214, 168, 75)),
            "parc_djoudj_oiseaux": charger_image_lieu("parc_djoudj_oiseaux.jpg", (20, 83, 45), (214, 168, 75)),
            "saint_louis_pont_faidherbe": charger_image_lieu("saint_louis_pont_faidherbe.jpg", (20, 83, 45), (214, 168, 75)),
            "agadez_mosquee_air": charger_image_lieu("agadez_mosquee_air.jpg", (168, 92, 32), (214, 168, 75)),
            "banfora_pics_sindou": charger_image_lieu("banfora_pics_sindou.jpg", (20, 83, 45), (214, 168, 75)),
            "bivouac_caravane_sahel": charger_image_lieu("bivouac_caravane_sahel.jpg", (168, 92, 32), (214, 168, 75)),
        }

        # =====================================================================
        # 1. PAYS & RÉGIONS
        # =====================================================================
        self.stdout.write("1/7 — Création des pays et régions du Sahel...")
        pays_data = [
            {
                "code_iso": "ML",
                "nom": "Mali",
                "capitale": "Bamako",
                "devise": "Franc CFA (XOF)",
                "langues_officielles": "Bambara, Peul, Dogon, Songhaï, Tamasheq, Français",
                "description": "Berceau des grands empires ouest-africains, traversé par le fleuve Niger, célèbre pour Djenné, Tombouctou et les falaises du Pays Dogon.",
            },
            {
                "code_iso": "SN",
                "nom": "Sénégal",
                "capitale": "Dakar",
                "devise": "Franc CFA (XOF)",
                "langues_officielles": "Français, Wolof, Pulaar, Sérère",
                "description": "Terre de la Teranga, des cités historiques insulaires de Saint-Louis et Gorée jusqu'aux sanctuaires ornithologiques du delta du fleuve Sénégal.",
            },
            {
                "code_iso": "NE",
                "nom": "Niger",
                "capitale": "Niamey",
                "devise": "Franc CFA (XOF)",
                "langues_officielles": "Français, Haoussa, Tamasheq, Zarma",
                "description": "Carrefour historique des caravanes transsahariennes, abritant la cité d'Agadez, le massif volcanique de l'Aïr et les dunes du Ténéré.",
            },
            {
                "code_iso": "BF",
                "nom": "Burkina Faso",
                "capitale": "Ouagadougou",
                "devise": "Franc CFA (XOF)",
                "langues_officielles": "Mooré, Dioula, Fulfuldé, Français",
                "description": "Pays des Hommes intègres, réputé pour son artisanat, les aiguilles de grès de Sindou, les dômes de Fabédougou et l'architecture gourounsi.",
            },
        ]
        pays_map = {}
        for item in pays_data:
            obj, _ = Pays.objects.update_or_create(
                code_iso=item["code_iso"],
                defaults=item,
            )
            pays_map[item["code_iso"]] = obj

        regions_data = [
            ("ML", "Mopti", "Mopti", "Confluence du Niger et du Bani, cœur du delta intérieur et porte du Pays Dogon."),
            ("ML", "Tombouctou", "Tombouctou", "Région saharo-sahélienne mythique sur la boucle septentrionale du fleuve Niger."),
            ("SN", "Saint-Louis", "Saint-Louis", "Estuaire du fleuve Sénégal, entre patrimoine colonial classé et parcs naturels."),
            ("NE", "Agadez", "Agadez", "Grande région désertique et montagneuse englobant le massif de l'Aïr et le Ténéré."),
            ("BF", "Cascades", "Banfora", "Région verdoyante du sud-ouest burkinabè aux reliefs gréseux spectaculaires."),
        ]
        regions_map = {}
        for code_pays, nom_region, chef_lieu, desc in regions_data:
            reg, _ = Region.objects.update_or_create(
                pays=pays_map[code_pays],
                nom=nom_region,
                defaults={"chef_lieu": chef_lieu, "description": desc, "est_actif": True},
            )
            regions_map[nom_region] = reg

        # =====================================================================
        # 2. DESTINATIONS
        # =====================================================================
        self.stdout.write("2/7 — Création des destinations...")
        destinations_data = [
            {
                "region": regions_map["Mopti"],
                "nom": "Djenné",
                "description_courte": "Joyau de l'architecture soudano-sahélienne en banco au cœur du delta intérieur du Niger.",
                "description": (
                    "Fondée au IXe siècle, Djenné est l'une des plus anciennes villes subsahariennes. "
                    "Sa Grande Mosquée en terre crue et son marché hebdomadaire du lundi offrent un "
                    "voyage hors du temps au milieu des bras du fleuve Bani."
                ),
                "latitude": Decimal("13.906000"),
                "longitude": Decimal("-4.553300"),
                "meilleure_periode": "Novembre à février",
                "en_vedette": True,
                "visuel": ("djenne_mosquee.jpg", photos_lieux["djenne_mosquee"]),
            },
            {
                "region": regions_map["Tombouctou"],
                "nom": "Tombouctou",
                "description_courte": "La cité mystérieuse des 333 saints, carrefour spirituel et intellectuel du Sahara.",
                "description": (
                    "Capitale intellectuelle de l'Afrique de l'Ouest aux XVe et XVIe siècles, Tombouctou "
                    "fascine par ses trois grandes mosquées anciennes (Djingareyber, Sankoré, Sidi Yahia) "
                    "et ses bibliothèques familiales abritant des dizaines de milliers de manuscrits."
                ),
                "latitude": Decimal("16.766600"),
                "longitude": Decimal("-3.002600"),
                "meilleure_periode": "Novembre à février",
                "en_vedette": True,
                "visuel": ("tombouctou_djingareyber.jpg", photos_lieux["tombouctou_djingareyber"]),
            },
            {
                "region": regions_map["Mopti"],
                "nom": "Pays Dogon & Bandiagara",
                "description_courte": "Une falaise de grès de 150 km ponctuée de villages suspendus et de traditions vivantes.",
                "description": (
                    "Inscrit au patrimoine mondial de l'UNESCO à double titre (naturel et culturel), "
                    "le plateau et la falaise de Bandiagara offrent des randonnées inoubliables à travers "
                    "les greniers à mil coiffés de chaume et les anciens habitats Tellem."
                ),
                "latitude": Decimal("14.350000"),
                "longitude": Decimal("-3.610000"),
                "meilleure_periode": "Octobre à mars",
                "en_vedette": True,
                "visuel": ("pays_dogon_bandiagara.jpg", photos_lieux["pays_dogon_bandiagara"]),
            },
            {
                "region": regions_map["Saint-Louis"],
                "nom": "Saint-Louis & Delta du Fleuve",
                "description_courte": "Île historique classée à l'UNESCO aux portes du parc ornithologique du Djoudj.",
                "description": (
                    "Reliée au continent par le célèbre pont Faidherbe, l'île de Saint-Louis séduit "
                    "par ses quais colorés, ses calèches et sa proximité immédiate avec la Langue de Barbarie "
                    "et la troisième réserve ornithologique mondiale."
                ),
                "latitude": Decimal("16.017900"),
                "longitude": Decimal("-16.489600"),
                "meilleure_periode": "Novembre à avril",
                "en_vedette": True,
                "visuel": ("saint_louis_pont_faidherbe.jpg", photos_lieux["saint_louis_pont_faidherbe"]),
            },
            {
                "region": regions_map["Agadez"],
                "nom": "Agadez & Massif de l'Aïr",
                "description_courte": "Minaret hérissé de pieux en bois et oasis verdoyantes nichées dans la roche volcanique.",
                "description": (
                    "Porte historique du Sahara nigérien, le centre ancien d'Agadez dévoile des ruelles "
                    "en banco ocre rouge, le palais du Sultan et des expéditions vers les jardins "
                    "d'agrumes et de palmiers-dattiers de l'oasis de Timia."
                ),
                "latitude": Decimal("16.973300"),
                "longitude": Decimal("7.991100"),
                "meilleure_periode": "Novembre à février",
                "en_vedette": True,
                "visuel": ("agadez_mosquee_air.jpg", photos_lieux["agadez_mosquee_air"]),
            },
            {
                "region": regions_map["Cascades"],
                "nom": "Banfora & Pics de Sindou",
                "description_courte": "Citadelles de grès sculptées par le vent, cascades rafraîchissantes et lac aux hippopotames.",
                "description": (
                    "Dans le sud-ouest verdoyant du Burkina Faso, Banfora combine les chutes de Karfiguéla, "
                    "les dômes calcaires de Fabédougou et la chaîne féerique des aiguilles de Sindou."
                ),
                "latitude": Decimal("10.633300"),
                "longitude": Decimal("-4.766700"),
                "meilleure_periode": "Octobre à mars",
                "en_vedette": True,
                "visuel": ("banfora_pics_sindou.jpg", photos_lieux["banfora_pics_sindou"]),
            },
        ]
        destinations_map = {}
        for item in destinations_data:
            nom_fichier, contenu_img = item.pop("visuel")
            dest, _ = Destination.objects.update_or_create(
                nom=item["nom"],
                defaults={**item, "est_actif": True},
            )
            if not dest.image_principale or rafraichir_images:
                dest.image_principale.save(nom_fichier, ContentFile(contenu_img), save=True)
            destinations_map[dest.nom] = dest

        # =====================================================================
        # 3. CATÉGORIES & SITES TOURISTIQUES
        # =====================================================================
        self.stdout.write("3/7 — Création des catégories et sites touristiques...")
        categories_data = [
            ("Architecture en terre", CategorieSite.Famille.HISTORIQUE, "bi-bank", 1),
            ("Parcs & réserves naturelles", CategorieSite.Famille.NATUREL, "bi-tree", 2),
            ("Falaises & formations rocheuses", CategorieSite.Famille.NATUREL, "bi-compass", 3),
            ("Manuscrits & cités savantes", CategorieSite.Famille.CULTUREL, "bi-journal-richtext", 4),
        ]
        categories_map = {}
        for nom_cat, famille, icone, ordre in categories_data:
            cat, _ = CategorieSite.objects.update_or_create(
                nom=nom_cat,
                defaults={"famille": famille, "icone": icone, "ordre": ordre},
            )
            categories_map[nom_cat] = cat

        sites_data = [
            {
                "destination": destinations_map["Djenné"],
                "categorie": categories_map["Architecture en terre"],
                "nom": "Grande Mosquée de Djenné",
                "description_courte": "Le plus grand édifice en terre crue (banco) du monde, chef-d'œuvre de l'art soudano-sahélien.",
                "description": (
                    "Dominant la place du marché, la Grande Mosquée de Djenné repose sur une vaste terrasse "
                    "surélevée et se distingue par ses trois minarets couronnés d'œufs d'autruche."
                ),
                "histoire": (
                    "Érigée au XIIIe siècle par le sultan Koi Konboro puis reconstruite en 1907, elle fait "
                    "chaque année l'objet du « Crépissage », une fête communautaire où toute la ville "
                    "enduit les façades d'argile fraîche avant la saison des pluies."
                ),
                "adresse": "Place du Grand Marché, Djenné",
                "horaires_ouverture": "Tous les jours de 8h00 à 18h00 (panorama des terrasses et parvis).",
                "prix_entree": Decimal("5000"),
                "duree_visite_minutes": 90,
                "patrimoine_unesco": True,
                "en_vedette": True,
                "latitude": Decimal("13.905200"),
                "longitude": Decimal("-4.555400"),
                "visuel": ("djenne_mosquee.jpg", photos_lieux["djenne_mosquee"]),
            },
            {
                "destination": destinations_map["Tombouctou"],
                "categorie": categories_map["Architecture en terre"],
                "nom": "Mosquée Djingareyber",
                "description_courte": "Monument emblématique bâti en 1327 au retour du pèlerinage de l'empereur Kankou Moussa.",
                "description": (
                    "Construite en banco et pierre calcaire, la mosquée Djingareyber possède trois cours "
                    "intérieures et deux minarets qui veillent sur la vieille ville de Tombouctou depuis sept siècles."
                ),
                "histoire": (
                    "Conçue par le poète et architecte andalou Abou Ishaq es-Sahéli à la demande de Mansa Moussa, "
                    "elle constitue le plus ancien témoignage monumental de l'âge d'or de Tombouctou."
                ),
                "adresse": "Quartier Djingareyber, Tombouctou",
                "horaires_ouverture": "8h30 – 17h30 (hors heures de prière du vendredi).",
                "prix_entree": Decimal("5000"),
                "duree_visite_minutes": 75,
                "patrimoine_unesco": True,
                "en_vedette": True,
                "latitude": Decimal("16.771100"),
                "longitude": Decimal("-3.010800"),
                "visuel": ("tombouctou_djingareyber.jpg", photos_lieux["tombouctou_djingareyber"]),
            },
            {
                "destination": destinations_map["Tombouctou"],
                "categorie": categories_map["Manuscrits & cités savantes"],
                "nom": "Institut Ahmed Baba des Manuscrits Anciens",
                "description_courte": "Sanctuaire de traités d'astronomie, de droit, de médecine et de poésie du Moyen Âge sahélien.",
                "description": (
                    "Découvrez l'art de la calligraphie soudanaise et le travail minutieux de numérisation "
                    "et de conservation des manuscrits familiaux transmis de génération en génération."
                ),
                "histoire": (
                    "Baptisé en hommage au grand savant du XVIe siècle Ahmed Baba de Tombouctou, le centre "
                    "rassemble plus de 30 000 parchemins illustrant le rayonnement universitaire de Sankoré."
                ),
                "adresse": "Avenue de Sankoré, Tombouctou",
                "horaires_ouverture": "Lundi au samedi : 9h00 – 16h30.",
                "prix_entree": Decimal("3500"),
                "duree_visite_minutes": 90,
                "patrimoine_unesco": True,
                "en_vedette": False,
                "latitude": Decimal("16.775900"),
                "longitude": Decimal("-3.005400"),
                "visuel": ("manuscrits_ahmed_baba.jpg", photos_lieux["manuscrits_ahmed_baba"]),
            },
            {
                "destination": destinations_map["Pays Dogon & Bandiagara"],
                "categorie": categories_map["Falaises & formations rocheuses"],
                "nom": "Falaise de Bandiagara & Village de Sangha",
                "description_courte": "Escarpement grandiose abritant les maisons à toit conique dogon et les grottes Tellem.",
                "description": (
                    "Depuis le rebord du plateau jusqu'à la plaine du Séno, les sentiers de pierre "
                    "relient les villages de Sangha, Banani et Ireli dans un décor minéral saisissant."
                ),
                "histoire": (
                    "Habitée dès le XIe siècle par les Tellem puis par les Dogons à partir du XIVe siècle, "
                    "la falaise a préservé une cosmogonie, des danses de masques et une architecture uniques."
                ),
                "adresse": "Sangha, Cercle de Bandiagara",
                "horaires_ouverture": "Accès libre tous les jours (accompagnement par un guide local recommandé).",
                "prix_entree": Decimal("4000"),
                "duree_visite_minutes": 240,
                "patrimoine_unesco": True,
                "en_vedette": True,
                "latitude": Decimal("14.466700"),
                "longitude": Decimal("-3.316700"),
                "visuel": ("pays_dogon_bandiagara.jpg", photos_lieux["pays_dogon_bandiagara"]),
            },
            {
                "destination": destinations_map["Saint-Louis & Delta du Fleuve"],
                "categorie": categories_map["Parcs & réserves naturelles"],
                "nom": "Parc national des oiseaux du Djoudj",
                "description_courte": "Troisième réserve ornithologique mondiale, oasis d'eau douce pour trois millions d'oiseaux.",
                "description": (
                    "En pirogue au lever du soleil, observez d'immenses colonies de pélicans blancs, "
                    "flamants roses, hérons pourprés, dendrocygnes et aigles pêcheurs."
                ),
                "histoire": (
                    "Créé en 1971 et inscrit au patrimoine mondial de l'UNESCO dès 1981, le parc constitue "
                    "la première halte d'eau douce après la traversée du Sahara pour les migrateurs d'Europe."
                ),
                "adresse": "60 km au nord-est de Saint-Louis",
                "horaires_ouverture": "Novembre à mai : tous les jours de 7h00 à 18h00.",
                "prix_entree": Decimal("5000"),
                "duree_visite_minutes": 180,
                "patrimoine_unesco": True,
                "en_vedette": True,
                "latitude": Decimal("16.400000"),
                "longitude": Decimal("-16.233300"),
                "visuel": ("parc_djoudj_oiseaux.jpg", photos_lieux["parc_djoudj_oiseaux"]),
            },
            {
                "destination": destinations_map["Saint-Louis & Delta du Fleuve"],
                "categorie": categories_map["Manuscrits & cités savantes"],
                "nom": "Île de Saint-Louis & Pont Faidherbe",
                "description_courte": "Passerelle métallique de 507 mètres et demeures à balcons de bois face au fleuve Sénégal.",
                "description": (
                    "Promenez-vous le long des quais Roume et Hurley, visitez le musée de la Photographie "
                    "(MuPho) et le quartier des pêcheurs de Guet Ndar."
                ),
                "histoire": (
                    "Ancienne capitale du Sénégal et de la Mauritanie, l'île de Ndar est classée au patrimoine "
                    "mondial de l'UNESCO depuis l'an 2000 pour son urbanisme insulaire singulier."
                ),
                "adresse": "Île Nord & Sud, Saint-Louis",
                "horaires_ouverture": "Accès libre toute l'année.",
                "prix_entree": Decimal("0"),
                "duree_visite_minutes": 150,
                "patrimoine_unesco": True,
                "en_vedette": False,
                "latitude": Decimal("16.026500"),
                "longitude": Decimal("-16.504200"),
                "visuel": ("saint_louis_pont_faidherbe.jpg", photos_lieux["saint_louis_pont_faidherbe"]),
            },
            {
                "destination": destinations_map["Agadez & Massif de l'Aïr"],
                "categorie": categories_map["Architecture en terre"],
                "nom": "Grande Mosquée d'Agadez",
                "description_courte": "Minaret pyramidal de 27 mètres en banco, plus haute tour en terre crue du Sahara.",
                "description": (
                    "Repère historique des caravanes de sel du Ténéré, son minaret hérissé de treize "
                    "rangées de pieux en bois de rôner domine tout le vieux quartier d'Agadez."
                ),
                "histoire": (
                    "Édifiée en 1515 à l'époque du sultanat de l'Aïr et restaurée au XIXe siècle, "
                    "elle est inscrite au patrimoine mondial de l'UNESCO depuis 2013."
                ),
                "adresse": "Centre historique d'Agadez",
                "horaires_ouverture": "Tous les jours de 8h00 à 17h30.",
                "prix_entree": Decimal("3000"),
                "duree_visite_minutes": 60,
                "patrimoine_unesco": True,
                "en_vedette": True,
                "latitude": Decimal("16.974200"),
                "longitude": Decimal("7.986400"),
                "visuel": ("agadez_mosquee_air.jpg", photos_lieux["agadez_mosquee_air"]),
            },
            {
                "destination": destinations_map["Banfora & Pics de Sindou"],
                "categorie": categories_map["Falaises & formations rocheuses"],
                "nom": "Aiguilles de grès de Sindou",
                "description_courte": "Labyrinthe naturel de cheminées de grès ciselées par l'érosion au milieu des rizières.",
                "description": (
                    "Un sentier pédestre serpente entre des tours minérales de trente mètres de haut, "
                    "offrant au coucher du soleil des teintes cuivrées spectaculaires."
                ),
                "histoire": (
                    "Lieu sacré et ancien refuge naturel pour les communautés Sénoufo de la province de la Léraba."
                ),
                "adresse": "Sindou, à 50 km à l'ouest de Banfora",
                "horaires_ouverture": "Tous les jours de 7h00 à 17h30.",
                "prix_entree": Decimal("2500"),
                "duree_visite_minutes": 120,
                "patrimoine_unesco": False,
                "en_vedette": False,
                "latitude": Decimal("10.666700"),
                "longitude": Decimal("-5.166700"),
                "visuel": ("banfora_pics_sindou.jpg", photos_lieux["banfora_pics_sindou"]),
            },
        ]
        sites_map = {}
        for item in sites_data:
            nom_fichier, contenu_img = item.pop("visuel")
            site, _ = SiteTouristique.objects.update_or_create(
                nom=item["nom"],
                defaults={**item, "est_actif": True},
            )
            if not site.image_principale or rafraichir_images:
                site.image_principale.save(nom_fichier, ContentFile(contenu_img), save=True)
            sites_map[site.nom] = site

        # =====================================================================
        # 4. LANGUES, SPÉCIALITÉS, UTILISATEURS & GUIDES
        # =====================================================================
        self.stdout.write("4/7 — Création des langues, spécialités et guides certifiés...")
        langues_data = [
            ("fr", "Français"),
            ("en", "Anglais"),
            ("bm", "Bambara"),
            ("so", "Songhaï"),
            ("dg", "Dogon"),
            ("wo", "Wolof"),
            ("tm", "Tamasheq"),
        ]
        langues_map = {}
        for code, nom in langues_data:
            lg, _ = Langue.objects.update_or_create(code=code, defaults={"nom": nom})
            langues_map[code] = lg

        specialites_data = [
            ("Histoire & Manuscrits", "bi-journal-richtext"),
            ("Randonnée & Falaises", "bi-compass"),
            ("Ornithologie & Fleuve", "bi-binoculars"),
            ("Expéditions sahariennes", "bi-sun"),
        ]
        specialites_map = {}
        for nom_spec, icone in specialites_data:
            sp, _ = SpecialiteGuide.objects.update_or_create(nom=nom_spec, defaults={"icone": icone})
            specialites_map[nom_spec] = sp

        # Compte Administrateur
        admin_user, created = User.objects.update_or_create(
            username="admin_sahel",
            defaults={
                "email": "admin@tourismesahel.com",
                "first_name": "Mamadou",
                "last_name": "Konaté",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "pays_origine": pays_map["ML"],
            },
        )
        if created or not admin_user.has_usable_password():
            admin_user.set_password("AdminSahel2026!")
            admin_user.save(update_fields=["password"])

        # Comptes Guides + Profils Guide
        guides_data = [
            {
                "username": "amadou_dolo",
                "email": "amadou.dolo@tourismesahel.com",
                "first_name": "Amadou",
                "last_name": "Dolo",
                "pays": pays_map["ML"],
                "nom_complet": "Amadou Dolo",
                "titre_professionnel": "Guide national certifié — Spécialiste du Pays Dogon & Djenné",
                "bio": (
                    "Originaire de Sangha, j'accompagne depuis 12 ans les marcheurs et passionnés "
                    "d'architecture en terre entre le delta intérieur du Niger et la falaise de Bandiagara."
                ),
                "annees_experience": 12,
                "tarif_journalier": Decimal("35000"),
                "numero_licence": "ML-GUIDE-2014-089",
                "langues": ["fr", "en", "dg", "bm"],
                "specialites": ["Randonnée & Falaises", "Histoire & Manuscrits"],
                "regions": ["Mopti"],
                "en_vedette": True,
            },
            {
                "username": "fatoumata_haidara",
                "email": "fatoumata.haidara@tourismesahel.com",
                "first_name": "Fatoumata",
                "last_name": "Haïdara",
                "pays": pays_map["ML"],
                "nom_complet": "Fatoumata Haïdara",
                "titre_professionnel": "Historienne & guide conférencière — Tombouctou",
                "bio": (
                    "Issue d'une lignée de conservateurs de manuscrits à Tombouctou, je fais découvrir "
                    "les bibliothèques familiales, les mosquées classées et l'histoire des grandes caravanes."
                ),
                "annees_experience": 9,
                "tarif_journalier": Decimal("40000"),
                "numero_licence": "ML-GUIDE-2017-142",
                "langues": ["fr", "en", "so", "tm"],
                "specialites": ["Histoire & Manuscrits", "Expéditions sahariennes"],
                "regions": ["Tombouctou", "Mopti"],
                "en_vedette": True,
            },
            {
                "username": "ibrahima_fall",
                "email": "ibrahima.fall@tourismesahel.com",
                "first_name": "Ibrahima",
                "last_name": "Fall",
                "pays": pays_map["SN"],
                "nom_complet": "Ibrahima Fall",
                "titre_professionnel": "Guide ornithologue & patrimoine — Saint-Louis et Djoudj",
                "bio": (
                    "Passionné d'avifaune et d'histoire saint-louisienne, j'organise des expéditions "
                    "en pirogue dans le parc du Djoudj et des visites architecturales de l'île de Ndar."
                ),
                "annees_experience": 10,
                "tarif_journalier": Decimal("32000"),
                "numero_licence": "SN-SL-2016-054",
                "langues": ["fr", "en", "wo"],
                "specialites": ["Ornithologie & Fleuve", "Histoire & Manuscrits"],
                "regions": ["Saint-Louis"],
                "en_vedette": True,
            },
            {
                "username": "moussa_ag_mohamed",
                "email": "moussa.ag@tourismesahel.com",
                "first_name": "Moussa",
                "last_name": "Ag Mohamed",
                "pays": pays_map["NE"],
                "nom_complet": "Moussa Ag Mohamed",
                "titre_professionnel": "Chef d'expédition saharienne — Agadez & Massif de l'Aïr",
                "bio": (
                    "Né au pied des monts Bagzane, je guide les voyageurs à travers les vallées "
                    "volcaniques de l'Aïr, l'oasis de Timia et la vieille ville d'Agadez."
                ),
                "annees_experience": 15,
                "tarif_journalier": Decimal("45000"),
                "numero_licence": "NE-AGZ-2011-019",
                "langues": ["fr", "tm", "en"],
                "specialites": ["Expéditions sahariennes", "Randonnée & Falaises"],
                "regions": ["Agadez"],
                "en_vedette": True,
            },
        ]
        guides_map = {}
        for gdata in guides_data:
            u_guide, u_created = User.objects.update_or_create(
                username=gdata["username"],
                defaults={
                    "email": gdata["email"],
                    "first_name": gdata["first_name"],
                    "last_name": gdata["last_name"],
                    "role": User.Role.GUIDE,
                    "pays_origine": gdata["pays"],
                },
            )
            if u_created or not u_guide.has_usable_password():
                u_guide.set_password("GuideSahel2026!")
                u_guide.save(update_fields=["password"])

            guide_obj, _ = Guide.objects.update_or_create(
                utilisateur=u_guide,
                defaults={
                    "nom_complet": gdata["nom_complet"],
                    "titre_professionnel": gdata["titre_professionnel"],
                    "bio": gdata["bio"],
                    "annees_experience": gdata["annees_experience"],
                    "tarif_journalier": gdata["tarif_journalier"],
                    "numero_licence": gdata["numero_licence"],
                    "statut_verification": Guide.StatutVerification.VERIFIE,
                    "date_verification": timezone.now(),
                    "en_vedette": gdata["en_vedette"],
                    "est_actif": True,
                },
            )
            if rafraichir_images and guide_obj.photo:
                guide_obj.photo.delete(save=True)
            guide_obj.langues.set([langues_map[c] for c in gdata["langues"]])
            guide_obj.specialites.set([specialites_map[s] for s in gdata["specialites"]])
            guide_obj.regions.set([regions_map[r] for r in gdata["regions"]])
            guides_map[gdata["nom_complet"]] = guide_obj

        # =====================================================================
        # 5. CIRCUITS & ÉTAPES
        # =====================================================================
        self.stdout.write("5/7 — Création des circuits et de leurs étapes...")
        circuits_data = [
            {
                "titre": "Trésors du Delta : Djenné & Falaise de Bandiagara",
                "description_courte": "5 jours d'immersion entre la cité d'argile de Djenné et les villages perchés du Pays Dogon.",
                "description": (
                    "Un itinéraire emblématique reliant les rives du fleuve Bani aux sentiers escarpés "
                    "de Sangha. Rencontrez les maçons traditionnels (barey) de Djenné et randonnez au pied "
                    "des anciens greniers Tellem."
                ),
                "programme_detaille": (
                    "Jour 1 : Arrivée à Djenné et visite du quartier ancien.\n"
                    "Jour 2 : Grande Mosquée de Djenné, marché et route vers Bandiagara.\n"
                    "Jour 3 : Descente de la falaise de Sangha à Banani.\n"
                    "Jour 4 : Villages d'Ireli et Amani, nuit sous les étoiles.\n"
                    "Jour 5 : Retour par Songo et fin du circuit à Mopti."
                ),
                "destination_depart": destinations_map["Djenné"],
                "guide_referent": guides_map["Amadou Dolo"],
                "duree_jours": 5,
                "tarif_par_personne": Decimal("245000"),
                "participants_min": 2,
                "participants_max": 10,
                "difficulte": Circuit.Difficulte.MODERE,
                "inclus": "Transport 4x4 climatisé\nHébergement en campement de charme\nPension complète\nGuide national certifié\nDroits d'entrée sur les sites",
                "non_inclus": "Vols internationaux\nBoissons personnelles\nPourboires",
                "en_vedette": True,
                "visuel": ("pays_dogon_bandiagara.jpg", photos_lieux["pays_dogon_bandiagara"]),
                "etapes": [
                    (1, 1, "Découverte de la Grande Mosquée de Djenné", sites_map["Grande Mosquée de Djenné"], "Campement Le Maafiré"),
                    (3, 2, "Randonnée dans la Falaise de Bandiagara", sites_map["Falaise de Bandiagara & Village de Sangha"], "Campement Hôtel La Falaise"),
                ],
            },
            {
                "titre": "Sur la route des Caravanes : Tombouctou Mystérieuse",
                "description_courte": "4 jours au cœur des mosquées séculaires, des manuscrits anciens et des dunes du fleuve Niger.",
                "description": (
                    "Partez sur les traces des érudits de Sankoré et des caravaniers touaregs. Ce circuit "
                    "allie patrimoine écrit, architecture soudanaise et bivouac dans les dunes dorées."
                ),
                "programme_detaille": (
                    "Jour 1 : Traversée en pinasse à Kabara et installation à Tombouctou.\n"
                    "Jour 2 : Mosquée Djingareyber et quartier historique.\n"
                    "Jour 3 : Institut Ahmed Baba et rencontre avec les calligraphes.\n"
                    "Jour 4 : Lever du soleil sur les dunes et retour."
                ),
                "destination_depart": destinations_map["Tombouctou"],
                "guide_referent": guides_map["Fatoumata Haïdara"],
                "duree_jours": 4,
                "tarif_par_personne": Decimal("290000"),
                "participants_min": 2,
                "participants_max": 8,
                "difficulte": Circuit.Difficulte.FACILE,
                "inclus": "Transferts fluviaux et 4x4\nMaison d'hôtes traditionnelle et 1 nuit en bivouac\nRepas inclus\nAccès aux bibliothèques de manuscrits",
                "non_inclus": "Assurance personnelle\nDépenses d'artisanat",
                "en_vedette": True,
                "visuel": ("bivouac_caravane_sahel.jpg", photos_lieux["bivouac_caravane_sahel"]),
                "etapes": [
                    (2, 1, "Visite de la Mosquée Djingareyber", sites_map["Mosquée Djingareyber"], "Maison d'hôtes Alfarouk"),
                    (3, 2, "Exploration des Manuscrits Anciens", sites_map["Institut Ahmed Baba des Manuscrits Anciens"], "Bivouac des Dunes"),
                ],
            },
            {
                "titre": "Odyssée du Fleuve : Saint-Louis & Sanctuaire du Djoudj",
                "description_courte": "3 jours entre patrimoine insulaire classé UNESCO et navigation ornithologique en pirogue.",
                "description": (
                    "Idéal pour les amoureux de nature et d'histoire : flânez dans les ruelles de l'île "
                    "de Saint-Louis avant d'observer des milliers de pélicans au cœur du delta."
                ),
                "programme_detaille": (
                    "Jour 1 : Tour en calèche de l'île historique et Pont Faidherbe.\n"
                    "Jour 2 : Journée complète en pirogue au Parc national du Djoudj.\n"
                    "Jour 3 : Langue de Barbarie et marché artisanal."
                ),
                "destination_depart": destinations_map["Saint-Louis & Delta du Fleuve"],
                "guide_referent": guides_map["Ibrahima Fall"],
                "duree_jours": 3,
                "tarif_par_personne": Decimal("165000"),
                "participants_min": 1,
                "participants_max": 12,
                "difficulte": Circuit.Difficulte.FACILE,
                "inclus": "Hébergement sur l'île\nPirogue motorisée au parc du Djoudj\nEntrées des parcs\nAccompagnement ornithologique",
                "non_inclus": "Déjeuners libres du jour 3",
                "en_vedette": True,
                "visuel": ("parc_djoudj_oiseaux.jpg", photos_lieux["parc_djoudj_oiseaux"]),
                "etapes": [
                    (1, 1, "Patrimoine de l'Île de Saint-Louis", sites_map["Île de Saint-Louis & Pont Faidherbe"], "Hôtel de la Résidence"),
                    (2, 2, "Croisière ornithologique au Djoudj", sites_map["Parc national des oiseaux du Djoudj"], "Campement du Djoudj"),
                ],
            },
            {
                "titre": "Traversée Touarègue : Agadez & Oasis de l'Aïr",
                "description_courte": "6 jours d'aventure saharienne du minaret d'Agadez aux jardins verdoyants de Timia.",
                "description": (
                    "Une immersion grandiose dans le massif volcanique de l'Aïr : architecture de terre "
                    "d'Agadez, gravures rupestres, gueltas cristallines et hospitalité touarègue autour du thé."
                ),
                "programme_detaille": (
                    "Jour 1 : Vieille ville et Grande Mosquée d'Agadez.\n"
                    "Jours 2 à 5 : Expédition en 4x4 dans le massif de l'Aïr et l'oasis de Timia.\n"
                    "Jour 6 : Retour à Agadez et soirée artisanale."
                ),
                "destination_depart": destinations_map["Agadez & Massif de l'Aïr"],
                "guide_referent": guides_map["Moussa Ag Mohamed"],
                "duree_jours": 6,
                "tarif_par_personne": Decimal("340000"),
                "participants_min": 2,
                "participants_max": 8,
                "difficulte": Circuit.Difficulte.SPORTIF,
                "inclus": "Expédition 4x4 avec chauffeur\nBivouacs équipés et pension complète\nGuide touareg certifié",
                "non_inclus": "Sac de couchage personnel",
                "en_vedette": False,
                "visuel": ("agadez_mosquee_air.jpg", photos_lieux["agadez_mosquee_air"]),
                "etapes": [
                    (1, 1, "Cité historique & Grande Mosquée d'Agadez", sites_map["Grande Mosquée d'Agadez"], "Auberge d'Azel"),
                ],
            },
        ]
        circuits_map = {}
        for cdata in circuits_data:
            etapes = cdata.pop("etapes")
            nom_fichier, contenu_img = cdata.pop("visuel")
            circuit_obj, _ = Circuit.objects.update_or_create(
                titre=cdata["titre"],
                defaults={**cdata, "est_actif": True},
            )
            if not circuit_obj.image_principale or rafraichir_images:
                circuit_obj.image_principale.save(nom_fichier, ContentFile(contenu_img), save=True)
            for jour, ordre, titre_etape, site_etape, hebergement in etapes:
                EtapeCircuit.objects.update_or_create(
                    circuit=circuit_obj,
                    ordre=ordre,
                    defaults={
                        "jour": jour,
                        "titre": titre_etape,
                        "site": site_etape,
                        "hebergement": hebergement,
                        "repas_inclus": "Petit-déjeuner, déjeuner, dîner",
                    },
                )
            circuits_map[circuit_obj.titre] = circuit_obj

        # =====================================================================
        # 6. VISITEURS, RÉSERVATIONS, AVIS & FAVORIS
        # =====================================================================
        self.stdout.write("6/7 — Création des comptes visiteurs et réservations...")
        visiteurs_data = [
            ("awa_diop", "awa.diop@example.com", "Awa", "Diop", "+221771234567", pays_map["SN"]),
            ("ousmane_traore", "ousmane.traore@example.com", "Ousmane", "Traoré", "+22376112233", pays_map["ML"]),
            ("claire_dupont", "claire.dupont@example.com", "Claire", "Dupont", "+33612345678", pays_map["SN"]),
        ]
        visiteurs_map = {}
        for uname, email, fname, lname, tel, pays_orig in visiteurs_data:
            u_vis, created = User.objects.update_or_create(
                username=uname,
                defaults={
                    "email": email,
                    "first_name": fname,
                    "last_name": lname,
                    "telephone": tel,
                    "role": User.Role.TOURISTE,
                    "pays_origine": pays_orig,
                },
            )
            if created or not u_vis.has_usable_password():
                u_vis.set_password("VisiteurSahel2026!")
                u_vis.save(update_fields=["password"])
            visiteurs_map[uname] = u_vis

        c_djenne = circuits_map["Trésors du Delta : Djenné & Falaise de Bandiagara"]
        c_tombouctou = circuits_map["Sur la route des Caravanes : Tombouctou Mystérieuse"]
        c_djoudj = circuits_map["Odyssée du Fleuve : Saint-Louis & Sanctuaire du Djoudj"]
        c_agadez = circuits_map["Traversée Touarègue : Agadez & Oasis de l'Aïr"]

        reservations_demo = [
            {
                "utilisateur": visiteurs_map["awa_diop"],
                "circuit": c_djenne,
                "nom_visiteur": "Awa Diop",
                "email_visiteur": "awa.diop@example.com",
                "telephone_visiteur": "+221771234567",
                "pays_visiteur": pays_map["SN"],
                "date_depart": aujourd_hui + timedelta(days=14),
                "nombre_personnes": 2,
                "statut": Reservation.Statut.ACCEPTEE,
                "demandes_speciales": "Option végétarienne souhaitée pour une personne.",
            },
            {
                "utilisateur": visiteurs_map["ousmane_traore"],
                "circuit": c_tombouctou,
                "nom_visiteur": "Ousmane Traoré",
                "email_visiteur": "ousmane.traore@example.com",
                "telephone_visiteur": "+22376112233",
                "pays_visiteur": pays_map["ML"],
                "date_depart": aujourd_hui + timedelta(days=21),
                "nombre_personnes": 3,
                "statut": Reservation.Statut.EN_ATTENTE,
                "demandes_speciales": "Intérêt particulier pour la photographie des manuscrits.",
            },
            {
                "utilisateur": visiteurs_map["claire_dupont"],
                "circuit": c_djoudj,
                "nom_visiteur": "Claire Dupont",
                "email_visiteur": "claire.dupont@example.com",
                "telephone_visiteur": "+33612345678",
                "pays_visiteur": pays_map["SN"],
                "date_depart": aujourd_hui + timedelta(days=9),
                "nombre_personnes": 2,
                "statut": Reservation.Statut.EN_ATTENTE,
                "demandes_speciales": "Jumelles ornithologiques demandées si disponibles.",
            },
            {
                "utilisateur": visiteurs_map["awa_diop"],
                "circuit": c_agadez,
                "nom_visiteur": "Awa Diop",
                "email_visiteur": "awa.diop@example.com",
                "telephone_visiteur": "+221771234567",
                "pays_visiteur": pays_map["SN"],
                "date_depart": aujourd_hui - timedelta(days=30),
                "nombre_personnes": 4,
                "statut": Reservation.Statut.TERMINEE,
                "demandes_speciales": "",
            },
        ]
        res_creees = []
        for rdata in reservations_demo:
            res_obj, _ = Reservation.objects.update_or_create(
                utilisateur=rdata["utilisateur"],
                circuit=rdata["circuit"],
                date_depart=rdata["date_depart"],
                defaults=rdata,
            )
            res_creees.append(res_obj)

        self.stdout.write("7/7 — Création des avis vérifiés et favoris...")
        avis_demo = [
            {
                "auteur": visiteurs_map["awa_diop"],
                "site": sites_map["Grande Mosquée de Djenné"],
                "reservation": res_creees[0],
                "note": 5,
                "titre": "Une merveille architecturale inoubliable",
                "commentaire": (
                    "Voir la Grande Mosquée de Djenné s'illuminer au soleil couchant depuis les terrasses "
                    "voisines est un moment magique. Les explications d'Amadou étaient passionnantes !"
                ),
                "statut_validation": Avis.StatutValidation.VALIDE,
            },
            {
                "auteur": visiteurs_map["ousmane_traore"],
                "site": sites_map["Mosquée Djingareyber"],
                "note": 5,
                "titre": "Sept siècles d'histoire vivante",
                "commentaire": (
                    "L'atmosphère paisible de Tombouctou et la richesse des bibliothèques de manuscrits "
                    "dépassent tout ce qu'on peut imaginer."
                ),
                "statut_validation": Avis.StatutValidation.VALIDE,
            },
            {
                "auteur": visiteurs_map["claire_dupont"],
                "site": sites_map["Parc national des oiseaux du Djoudj"],
                "note": 5,
                "titre": "Un spectacle ornithologique grandiose",
                "commentaire": (
                    "Des milliers de pélicans qui s'envolent au ras de l'eau au lever du jour : "
                    "une excursion incontournable depuis Saint-Louis."
                ),
                "statut_validation": Avis.StatutValidation.VALIDE,
            },
            {
                "auteur": visiteurs_map["claire_dupont"],
                "circuit": c_djenne,
                "note": 4,
                "titre": "Superbe itinéraire entre fleuve et falaise",
                "commentaire": "Organisation impeccable et accueil chaleureux dans chaque village.",
                "statut_validation": Avis.StatutValidation.EN_ATTENTE,
            },
        ]
        for adata in avis_demo:
            filtre = {"auteur": adata["auteur"]}
            if "site" in adata:
                filtre["site"] = adata["site"]
            else:
                filtre["circuit"] = adata["circuit"]
            Avis.objects.update_or_create(
                **filtre,
                defaults={
                    **adata,
                    "date_validation": timezone.now()
                    if adata["statut_validation"] == Avis.StatutValidation.VALIDE
                    else None,
                },
            )

        Favori.objects.get_or_create(
            utilisateur=visiteurs_map["awa_diop"],
            destination=destinations_map["Djenné"],
        )
        Favori.objects.get_or_create(
            utilisateur=visiteurs_map["awa_diop"],
            site=sites_map["Falaise de Bandiagara & Village de Sangha"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nDonnées de démonstration TourismeSahel chargées avec succès !\n"
                f"  • Pays : {Pays.objects.count()} | Régions : {Region.objects.count()} | Destinations : {Destination.objects.count()}\n"
                f"  • Sites touristiques : {SiteTouristique.objects.count()} | Circuits : {Circuit.objects.count()} | Guides : {Guide.objects.count()}\n"
                f"  • Réservations : {Reservation.objects.count()} | Avis : {Avis.objects.count()} | Favoris : {Favori.objects.count()}\n"
                "  • Compte Admin  : admin_sahel / AdminSahel2026!\n"
                "  • Compte Client : awa_diop / VisiteurSahel2026!"
            )
        )

