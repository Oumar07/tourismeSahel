"""
Suite de tests fonctionnels et d'intégration de TourismeSahel (Phase 8).

Couvre notamment :
1. Le chargement de la page d'accueil (statut HTTP 200, templates, contexte dynamique) ;
2. La navigation dans le catalogue (destinations et sites touristiques) ;
3. La soumission complète d'une demande de réservation par un utilisateur de test
   (validation, création en base, calcul du montant total, page de confirmation) ;
4. Le contrôle d'accès et le traitement des réservations depuis le Dashboard Administrateur ;
5. La commande de management `load_demo_data`.
"""
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Reservation
from apps.circuits.models import Circuit, EtapeCircuit
from apps.guides.models import Guide, Langue
from apps.locations.models import Destination, Pays, Region
from apps.reviews.models import Avis
from apps.tourism.models import CategorieSite, SiteTouristique

User = get_user_model()


FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class TourismeSahelFunctionalTests(TestCase):
    """Tests fonctionnels de bout en bout pour la plateforme TourismeSahel."""

    @classmethod
    def setUpTestData(cls):
        cls.aujourd_hui = timezone.localdate()

        # 1. Géographie : Mali -> Mopti -> Djenné
        cls.pays = Pays.objects.create(
            nom="Mali",
            code_iso="ML",
            capitale="Bamako",
            devise="Franc CFA (XOF)",
        )
        cls.region = Region.objects.create(
            pays=cls.pays,
            nom="Mopti",
            chef_lieu="Mopti",
        )
        cls.destination = Destination.objects.create(
            region=cls.region,
            nom="Djenné",
            description_courte="Citadelle d'argile du delta intérieur du Niger.",
            description="L'une des plus anciennes villes d'Afrique subsaharienne.",
            image_principale="destinations/djenne.jpg",
            meilleure_periode="Novembre à février",
            en_vedette=True,
            est_actif=True,
        )

        # 2. Catalogue touristique : Grande Mosquée de Djenné
        cls.categorie = CategorieSite.objects.create(
            nom="Architecture en terre",
            famille=CategorieSite.Famille.HISTORIQUE,
            icone="bi-bank",
        )
        cls.site = SiteTouristique.objects.create(
            destination=cls.destination,
            categorie=cls.categorie,
            nom="Grande Mosquée de Djenné",
            description_courte="Plus grand édifice en terre crue du monde.",
            description="Chef-d'œuvre de l'architecture soudano-sahélienne.",
            histoire="Reconstruite en 1907 sur le site du XIIIe siècle.",
            prix_entree=Decimal("5000.00"),
            patrimoine_unesco=True,
            image_principale="sites/mosquee_djenne.jpg",
            en_vedette=True,
            est_actif=True,
        )

        # 3. Utilisateurs (Visiteur, Guide, Administrateur)
        cls.visiteur = User.objects.create_user(
            username="aminata_sow",
            email="aminata.sow@example.com",
            password="MotDePasseTest2026!",
            first_name="Aminata",
            last_name="Sow",
            telephone="+221770001122",
            role=User.Role.TOURISTE,
            pays_origine=cls.pays,
        )
        cls.compte_guide = User.objects.create_user(
            username="amadou_guide",
            email="amadou@tourismesahel.com",
            password="MotDePasseTest2026!",
            role=User.Role.GUIDE,
        )
        cls.admin_user = User.objects.create_user(
            username="admin_test",
            email="admin@tourismesahel.com",
            password="MotDePasseAdmin2026!",
            role=User.Role.ADMIN,
            is_staff=True,
        )

        # 4. Guide vérifié & Circuit publié
        cls.langue_fr = Langue.objects.create(code="fr", nom="Français")
        cls.guide = Guide.objects.create(
            utilisateur=cls.compte_guide,
            nom_complet="Amadou Dolo",
            titre_professionnel="Guide national certifié",
            bio="Spécialiste de Djenné et du Pays Dogon depuis 12 ans.",
            annees_experience=12,
            tarif_journalier=Decimal("35000.00"),
            statut_verification=Guide.StatutVerification.VERIFIE,
            en_vedette=True,
            est_actif=True,
        )
        cls.guide.langues.add(cls.langue_fr)
        cls.guide.regions.add(cls.region)

        cls.circuit = Circuit.objects.create(
            titre="Trésors du Delta et de Djenné",
            description_courte="4 jours au cœur du delta intérieur du Niger.",
            description="Découverte approfondie de Djenné et des villages environnants.",
            programme_detaille="Jour 1 à Jour 4.",
            destination_depart=cls.destination,
            guide_referent=cls.guide,
            duree_jours=4,
            tarif_par_personne=Decimal("180000.00"),
            participants_min=2,
            participants_max=8,
            difficulte=Circuit.Difficulte.FACILE,
            image_principale="circuits/delta_djenne.jpg",
            en_vedette=True,
            est_actif=True,
        )
        EtapeCircuit.objects.create(
            circuit=cls.circuit,
            site=cls.site,
            jour=1,
            ordre=1,
            titre="Arrivée et visite de la Grande Mosquée",
        )

        # 5. Avis validé affiché sur l'accueil
        cls.avis = Avis.objects.create(
            auteur=cls.visiteur,
            site=cls.site,
            note=5,
            titre="Inoubliable",
            commentaire="Un patrimoine exceptionnel au cœur du Sahel.",
            statut_validation=Avis.StatutValidation.VALIDE,
        )

    # -------------------------------------------------------------------------
    # 1. Test de la page d'accueil (code 200 & contenu dynamique)
    # -------------------------------------------------------------------------
    def test_chargement_page_accueil_code_200(self):
        """Vérifie que la page d'accueil répond en HTTP 200 et expose les sections dynamiques."""
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")

        # Vérification des données présentes dans le contexte
        self.assertIn(self.destination, response.context["destinations_populaires"])
        self.assertIn(self.site, response.context["sites_vedettes"])
        self.assertIn(self.circuit, response.context["circuits_vedettes"])
        self.assertIn(self.guide, response.context["guides_vedettes"])
        self.assertIn(self.avis, response.context["avis_recents"])

        # Vérification du rendu HTML
        self.assertContains(response, "Djenné")
        self.assertContains(response, "Grande Mosquée de Djenné")
        self.assertContains(response, "Trésors du Delta et de Djenné")
        self.assertContains(response, "Amadou Dolo")

    # -------------------------------------------------------------------------
    # 2. Test de soumission réussie d'une demande de réservation
    # -------------------------------------------------------------------------
    def test_soumission_demande_reservation_reussie(self):
        """
        Vérifie qu'un utilisateur connecté peut soumettre une demande de réservation,
        que celle-ci est enregistrée en base avec le bon montant et redirige vers
        la page de confirmation.
        """
        self.client.force_login(self.visiteur)
        url_creation = reverse("bookings:create")

        # Le formulaire pré-remplit les coordonnées de l'utilisateur connecté en GET
        response_get = self.client.get(url_creation, {"circuit": self.circuit.slug})
        self.assertEqual(response_get.status_code, 200)
        self.assertEqual(response_get.context["form"].initial["circuit"], self.circuit.pk)

        date_depart = self.aujourd_hui + timedelta(days=15)
        donnees_post = {
            "circuit": self.circuit.pk,
            "guide": self.guide.pk,
            "date_depart": date_depart.isoformat(),
            "nombre_personnes": 3,
            "nom_visiteur": "Aminata Sow",
            "email_visiteur": "aminata.sow@example.com",
            "telephone_visiteur": "+221770001122",
            "pays_visiteur": self.pays.pk,
            "demandes_speciales": "Transfert depuis Mopti souhaité.",
        }

        response_post = self.client.post(url_creation, data=donnees_post)

        # Une réservation doit avoir été créée en base
        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.first()

        # Vérification des champs calculés et enregistrés
        self.assertTrue(reservation.reference.startswith(f"TS-{self.aujourd_hui.year}-"))
        self.assertEqual(reservation.utilisateur, self.visiteur)
        self.assertEqual(reservation.circuit, self.circuit)
        self.assertEqual(reservation.guide, self.guide)
        self.assertEqual(reservation.statut, Reservation.Statut.EN_ATTENTE)
        self.assertEqual(reservation.nombre_personnes, 3)
        self.assertEqual(reservation.prix_unitaire, Decimal("180000.00"))
        self.assertEqual(reservation.montant_total, Decimal("540000.00"))
        self.assertEqual(reservation.date_fin, date_depart + timedelta(days=3))

        # Redirection vers la page de confirmation qui affiche la référence
        url_confirmation = reverse("bookings:confirmation", args=[reservation.reference])
        self.assertRedirects(response_post, url_confirmation)

        response_confirm = self.client.get(url_confirmation)
        self.assertEqual(response_confirm.status_code, 200)
        self.assertContains(response_confirm, reservation.reference)

    def test_soumission_reservation_date_passee_rejetee(self):
        """Vérifie qu'une date de départ dans le passé est refusée par le formulaire."""
        self.client.force_login(self.visiteur)
        donnees_invalides = {
            "circuit": self.circuit.pk,
            "date_depart": (self.aujourd_hui - timedelta(days=2)).isoformat(),
            "nombre_personnes": 2,
            "nom_visiteur": "Aminata Sow",
            "email_visiteur": "aminata.sow@example.com",
            "telephone_visiteur": "+221770001122",
        }
        response = self.client.post(reverse("bookings:create"), data=donnees_invalides)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 0)
        self.assertIn("date_depart", response.context["form"].errors)

    # -------------------------------------------------------------------------
    # 3. Tests du catalogue complet, pages statiques et Dashboard Administrateur
    # -------------------------------------------------------------------------
    def test_pages_catalogue_navigation_et_footer(self):
        """
        Vérifie que toutes les pages de la barre de navigation, les fiches de détail
        et les liens du pied de page répondent en HTTP 200 sans résidu de syntaxe Django.
        """
        urls_a_verifier = [
            reverse("core:home"),
            reverse("locations:destination_list"),
            reverse("locations:destination_detail", args=[self.destination.slug]),
            reverse("tourism:site_list"),
            reverse("tourism:site_detail", args=[self.site.slug]),
            reverse("circuits:circuit_list"),
            reverse("circuits:circuit_detail", args=[self.circuit.slug]),
            reverse("guides:guide_list"),
            reverse("guides:guide_detail", args=[self.guide.slug]),
            reverse("core:about"),
            reverse("core:contact"),
            reverse("core:faq"),
            reverse("core:become_guide"),
            reverse("core:mentions_legales"),
            reverse("core:confidentialite"),
            reverse("core:cgv"),
            reverse("bookings:create"),
            reverse("bookings:create_for_circuit", args=[self.circuit.slug]),
            reverse("accounts:login"),
            reverse("accounts:register"),
        ]
        for url in urls_a_verifier:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                html = resp.content.decode("utf-8")
                self.assertNotIn("{#", html)
                self.assertNotIn("#}", html)

        # Vérification des formulaires POST de contact et de newsletter
        resp_contact = self.client.post(
            reverse("core:contact"),
            data={
                "nom_complet": "Moussa Diarra",
                "email": "moussa@example.com",
                "sujet": "information",
                "message": "Bonjour, je souhaite organiser un circuit à Djenné en décembre.",
            },
        )
        self.assertRedirects(resp_contact, reverse("core:contact"))

        resp_news = self.client.post(reverse("core:newsletter"), data={"email": "voyageur@example.com"})
        self.assertEqual(resp_news.status_code, 302)

    def test_dashboard_admin_securite_et_changement_statut(self):
        """Vérifie la sécurité du dashboard admin et l'acceptation d'une réservation."""
        reservation = Reservation.objects.create(
            utilisateur=self.visiteur,
            circuit=self.circuit,
            guide=self.guide,
            nom_visiteur="Aminata Sow",
            email_visiteur="aminata.sow@example.com",
            telephone_visiteur="+221770001122",
            date_depart=self.aujourd_hui + timedelta(days=20),
            nombre_personnes=2,
        )
        url_dashboard = reverse("dashboard:index")
        url_statut = reverse("dashboard:reservation_statut", args=[reservation.reference])

        # Visiteur standard -> 403 Forbidden
        self.client.force_login(self.visiteur)
        self.assertEqual(self.client.get(url_dashboard).status_code, 403)
        self.assertEqual(self.client.post(url_statut, {"action": "accepter"}).status_code, 403)

        # Membre du staff -> 200 OK et acceptation de la réservation
        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(url_dashboard).status_code, 200)
        resp_post = self.client.post(url_statut, {"action": "accepter"})
        self.assertRedirects(resp_post, url_dashboard)

        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.ACCEPTEE)
        self.assertIsNotNone(reservation.date_reponse)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class LoadDemoDataCommandTests(TestCase):
    """Vérifie le bon fonctionnement et l'idempotence de `python manage.py load_demo_data`."""

    def test_load_demo_data_idempotent(self):
        out = StringIO()
        with tempfile.TemporaryDirectory() as tmp_media, override_settings(MEDIA_ROOT=tmp_media):
            call_command("load_demo_data", stdout=out)
            self.assertGreaterEqual(Destination.objects.count(), 6)
            self.assertGreaterEqual(SiteTouristique.objects.count(), 8)
            self.assertGreaterEqual(Circuit.objects.count(), 4)
            self.assertGreaterEqual(Guide.objects.count(), 4)
            self.assertGreaterEqual(Reservation.objects.count(), 4)

            # Un second appel ne doit pas lever d'erreur ni dupliquer les entités
            nb_destinations = Destination.objects.count()
            call_command("load_demo_data", stdout=out)
            self.assertEqual(Destination.objects.count(), nb_destinations)
