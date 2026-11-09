# TourismeSahel — Plateforme de Tourisme Culturel & Responsable au Sahel

**TourismeSahel** est une application web Full Stack développée avec **Django 6** et **Bootstrap 5**, dédiée à la mise en valeur du patrimoine historique, culturel et naturel des pays du Sahel (Mali, Sénégal, Niger, Burkina Faso…) ainsi qu'à la réservation de circuits accompagnés par des guides locaux certifiés.

---

## 1. Architecture modulaire du projet

Le projet suit une architecture modulaire découpée par domaines métier dans le dossier `apps/` :

```text
tourismeSahel/
├── apps/
│   ├── core/          # Modèles abstraits (TimeStampedModel, SluggedModel…), Accueil, commande load_demo_data, tests
│   ├── accounts/      # Modèle User personnalisé (TOURISTE, GUIDE, ADMIN), authentification, espace visiteur
│   ├── locations/     # Référentiel géographique : Pays, Region, Destination, PhotoDestination
│   ├── tourism/       # Catalogue touristique : CategorieSite, SiteTouristique, PhotoSite
│   ├── guides/        # Guides certifiés : Langue, SpecialiteGuide, Guide, DisponibiliteGuide
│   ├── circuits/      # Offres de circuits & étapes jour par jour : Circuit, EtapeCircuit
│   ├── bookings/      # Tunnel de réservation, calcul de tarifs figés et suivi des statuts : Reservation
│   ├── reviews/       # Avis modérés (notes 1–5) et Favoris avec contraintes d'intégrité SQL : Avis, Favori
│   └── dashboard/     # Dashboard Administrateur sur mesure (KPIs, graphiques Chart.js, traitement POST + CSRF)
├── static/
│   └── css/style.css  # Charte graphique sahélienne (#14532D, #65A30D, #D6A84B, #A85C20, #F5EBD7, #263238)
├── templates/         # Templates HTML responsives étendant base.html
├── tourismeSahel/     # Configuration centrale Django (settings.py, urls.py, wsgi.py)
├── manage.py
└── requirements.txt
```

---

## 2. Prérequis

- **Python** 3.12 ou supérieur
- **pip** et `venv`

---

## 3. Installation & mise en route rapide

### Étape 1 — Activer l'environnement virtuel

Sous **Windows (PowerShell)** :

```powershell
cd C:\Users\HP\tourismeSahel
.\env\Scripts\Activate.ps1
```

Sous **Linux / macOS** :

```bash
source env/bin/activate
```

### Étape 2 — Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 3 — Appliquer les migrations de base de données

```bash
python manage.py makemigrations
python manage.py migrate
```

### Étape 4 — Charger les données de démonstration

La commande `load_demo_data` peuple automatiquement la base avec des pays, régions, destinations emblématiques (*Djenné*, *Tombouctou*, *Pays Dogon*, *Saint-Louis*, *Agadez*, *Banfora*), des sites classés UNESCO, des guides certifiés, des circuits, des réservations et des avis (ainsi que des visuels générés automatiquement via Pillow) :

```bash
python manage.py load_demo_data
```

> Pour réinitialiser et recharger proprement les données de démonstration à tout moment :
> ```bash
> python manage.py load_demo_data --reset
> ```

### Étape 5 — Lancer le serveur de développement

```bash
python manage.py runserver
```

L'application est alors accessible sur **http://127.0.0.1:8000/**.

---

## 4. Comptes de démonstration créés par `load_demo_data`

| Rôle | Identifiant (`username`) | E-mail | Mot de passe | Accès principal |
|---|---|---|---|---|
| **Administrateur** | `admin_sahel` | `admin@tourismesahel.com` | `AdminSahel2026!` | `/administration/` et `/admin/` |
| **Visiteur (Touriste)** | `awa_diop` | `awa.diop@example.com` | `VisiteurSahel2026!` | `/comptes/mon-espace/` |
| **Visiteur (Touriste)** | `ousmane_traore` | `ousmane.traore@example.com` | `VisiteurSahel2026!` | `/comptes/mon-espace/` |
| **Guide certifié** | `amadou_dolo` | `amadou.dolo@tourismesahel.com` | `GuideSahel2026!` | Profil guide & espace personnel |

---

## 5. Principales URLs de la plateforme

- **Accueil** : `http://127.0.0.1:8000/`
- **Catalogue des Destinations** : `http://127.0.0.1:8000/destinations/`
- **Catalogue des Sites Touristiques** : `http://127.0.0.1:8000/sites/`
- **Catalogue des Circuits** : `http://127.0.0.1:8000/circuits/`
- **Annuaire des Guides Certifiés** : `http://127.0.0.1:8000/guides/`
- **À propos / Contact / FAQ / Devenir guide** : `/a-propos/`, `/contact/`, `/faq/`, `/devenir-guide/`
- **Demande de Réservation** : `http://127.0.0.1:8000/reservations/nouvelle/`
- **Espace Visiteur (Dashboard client)** : `http://127.0.0.1:8000/comptes/mon-espace/`
- **Dashboard Administrateur sur mesure (Chart.js)** : `http://127.0.0.1:8000/administration/`
- **Interface d'administration native Django** : `http://127.0.0.1:8000/admin/`

---

## 6. Exécution des tests automatisés

Pour exécuter la suite de tests fonctionnels (page d'accueil HTTP 200, tunnel de réservation, sécurité du dashboard administrateur et commande `load_demo_data`) :

```bash
python manage.py test
```

