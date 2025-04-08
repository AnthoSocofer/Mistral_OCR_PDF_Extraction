# PDF Data Extractor

Application Streamlit pour extraire des données de fichiers PDF en fonction de prompts d'extraction spécifiques.

## Fonctionnalités

- Chargement de fichiers PDF
- Conversion de PDF en images
- OCR sur les images avec Mistral OCR
- Extraction de données structurées selon des prompts spécifiques
- Affichage des résultats dans une interface conviviale

## Structure du projet

```
.
├── app.py                 # Application Streamlit principale
├── pdf_processor.py       # Module de conversion PDF en images
├── ocr_processor.py       # Module de traitement OCR
├── data_extractor.py      # Module d'extraction de données
├── models.py              # Modèles de données
├── prompt_extraction/     # Répertoire contenant les prompts d'extraction
│   ├── arcelorMital.md
│   ├── demoussis_industrie.md
│   ├── fluiconnecto.md
│   └── ...
└── requirements.txt       # Dépendances du projet
```

## Installation

1. Cloner le dépôt
2. Installer les dépendances :

```bash
pip install -r requirements.txt
```

3. Configurer la clé API Mistral :

```bash
export MISTRAL_API_KEY="votre_clé_api_mistral"
```

## Utilisation

Lancer l'application Streamlit :

```bash
streamlit run app.py
```

L'application sera accessible à l'adresse : http://localhost:8501

## Workflow

1. Charger un fichier PDF
2. Sélectionner un prompt d'extraction
3. Lancer l'extraction
4. Visualiser les résultats

## Ajout de nouveaux prompts d'extraction

Pour ajouter de nouveaux prompts d'extraction, créez un fichier markdown (.md) dans le répertoire `prompt_extraction/` avec le contenu du prompt.

## Dépendances

- streamlit: Interface utilisateur
- pdf2image: Conversion PDF en images
- pydantic: Validation de données
- pandas: Traitement de données tabulaires
- Mistral API: OCR et traitement de langage
