#!/usr/bin/env python3
"""
Script d'extraction de champs à partir de documents Markdown
en utilisant OpenAI GPT et les instructions spécifiées dans le dossier prompt.
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
import openai
import pandas as pd

# Charger les variables d'environnement
load_dotenv()

# Récupérer la clé API OpenAI des variables d'environnement
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Erreur: La clé API OpenAI n'est pas définie dans les variables d'environnement.")
    print("Veuillez créer un fichier .env à la racine du projet avec OPENAI_API_KEY=votre_clé_api")
    sys.exit(1)

# Configurer le client OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_extraction_instructions(prompt_file):
    """
    Lit le fichier de prompt et retourne les instructions d'extraction.
    """
    try:
        with open(prompt_file, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier de prompt {prompt_file}: {e}")
        sys.exit(1)

def read_markdown_file(md_file):
    """
    Lit le contenu d'un fichier Markdown.
    """
    try:
        with open(md_file, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Markdown {md_file}: {e}")
        sys.exit(1)

def analyze_prompt_fields(extraction_instructions):
    """
    Analyse les instructions d'extraction pour identifier les champs demandés.
    Retourne une liste des noms de champs à extraire.
    """
    # Rechercher les patterns courants dans les instructions indiquant les champs à extraire
    field_patterns = [
        r'\*\s*([^\n\*]+)',            # Format: * Champ
        r'-\s*([^\n-]+)',              # Format: - Champ
        r'\"([^\"]+)\"',             # Format: "Champ"
        r'[\*\-]?\s*([A-Z][^\n:]+):'  # Format: Champ:
    ]
    
    import re
    fields = []
    
    for pattern in field_patterns:
        matches = re.findall(pattern, extraction_instructions)
        for match in matches:
            # Nettoyer le nom du champ
            field = re.sub(r'\([^)]*\)', '', match).strip()  # Supprimer les exemples entre parenthèses
            field = re.sub(r'\s*(exemple|:).*$', '', field, flags=re.IGNORECASE).strip()  # Supprimer "exemple:" et tout ce qui suit
            
            if field and field not in fields and len(field) > 1:
                fields.append(field)
    
    # Si aucun champ n'a été trouvé, utiliser des valeurs par défaut
    if not fields:
        fields = ["Contenu"]  # Valeur par défaut si aucun champ n'est détecté
    
    return fields

def extract_fields_with_openai(markdown_content, extraction_instructions, model="gpt-4o"):
    """
    Utilise l'API OpenAI pour extraire les champs spécifiés dans les instructions
    à partir du contenu Markdown.
    """
    # Analyser les champs requis à partir des instructions
    fields = analyze_prompt_fields(extraction_instructions)
    fields_str = ", ".join(fields)
    
    prompt = f"""
Voici un document Markdown:

{markdown_content}

{extraction_instructions}

Réponds au format JSON structuré avec les champs suivants exactement : {fields_str}.
Si un champ contient plusieurs éléments, renvoie une liste d'objets avec tous ces champs.
Ne retourne que le JSON, sans aucun texte supplémentaire.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Tu es un assistant spécialisé dans l'extraction de données structurées à partir de documents. Tu dois extraire avec précision selon le format demandé."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Récupérer la réponse JSON
        json_response = response.choices[0].message.content
        extracted_data = json.loads(json_response)
        return extracted_data
    
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OpenAI: {e}")
        return None

def create_dataframe_from_extracted_data(extracted_data):
    """
    Crée un DataFrame pandas structuré à partir des données extraites.
    Si le format contient des champs au niveau supérieur et une liste d'items,
    les champs de niveau supérieur sont répliqués dans chaque ligne du DataFrame.
    
    Args:
        extracted_data: Dictionnaire ou liste contenant les données extraites
        
    Returns:
        pandas.DataFrame: DataFrame structuré contenant les données extraites
    """
    # Cas où les données ne sont pas un dictionnaire
    if not isinstance(extracted_data, dict):
        return pd.DataFrame(extracted_data)
    
    # Identifier les champs de niveau supérieur et les listes d'objets
    top_level_fields = {}
    list_fields = {}
    
    for key, value in extracted_data.items():
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            list_fields[key] = value
        else:
            top_level_fields[key] = value
    
    # Si aucune liste d'objets n'est trouvée, retourner un simple DataFrame
    if not list_fields:
        return pd.DataFrame([extracted_data])
    
    # Prendre la première liste d'objets trouvée (habituellement 'lignes' ou similaire)
    primary_list_key = list(list_fields.keys())[0]
    primary_list = list_fields[primary_list_key]
    
    # Si la liste est vide, retourner un DataFrame avec seulement les champs de niveau supérieur
    if not primary_list:
        return pd.DataFrame([top_level_fields])
    
    # Créer un DataFrame à partir de la liste principale
    df = pd.DataFrame(primary_list)
    
    # Ajouter les champs de niveau supérieur à chaque ligne du DataFrame
    for key, value in top_level_fields.items():
        df[key] = value
    
    # Réorganiser les colonnes pour mettre les champs de niveau supérieur en premier
    # Récupérer toutes les colonnes du DataFrame
    all_columns = list(df.columns)
    # Isoler les champs de niveau supérieur
    top_level_keys = list(top_level_fields.keys())
    # Identifier les colonnes qui ne sont pas des champs de niveau supérieur
    other_columns = [col for col in all_columns if col not in top_level_keys]
    # Réorganiser les colonnes avec les champs de niveau supérieur en premier
    df = df[top_level_keys + other_columns]
    
    return df

def save_to_csv(extracted_data, output_file):
    """
    Sauvegarde les données extraites dans un fichier CSV.
    """
    try:
        # Si aucune donnée n'a été extraite, sortir
        if not extracted_data:
            print("Aucune donnée n'a été extraite.")
            return False
        
        # Récupérer les en-têtes à partir des clés du dictionnaire
        headers = list(extracted_data.keys())
        
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Écrire les données dans le fichier CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerow(extracted_data)
        
        print(f"Les données ont été sauvegardées dans {output_file}")
        return True
    
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des données dans le fichier CSV: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Extrait des champs d'un fichier Markdown en utilisant OpenAI GPT.")
    parser.add_argument("--markdown", "-m", required=True, help="Chemin vers le fichier Markdown source")
    parser.add_argument("--prompt", "-p", required=True, help="Chemin vers le fichier d'instructions d'extraction")
    parser.add_argument("--output", "-o", help="Chemin vers le fichier CSV de sortie (par défaut: output.csv)")
    parser.add_argument("--model", default="gpt-4o", help="Modèle OpenAI à utiliser (par défaut: gpt-4o)")
    
    args = parser.parse_args()
    
    # Vérifier que les fichiers existent
    if not os.path.exists(args.markdown):
        print(f"Erreur: Le fichier Markdown {args.markdown} n'existe pas.")
        sys.exit(1)
    
    if not os.path.exists(args.prompt):
        print(f"Erreur: Le fichier de prompt {args.prompt} n'existe pas.")
        sys.exit(1)
    
    # Définir le fichier de sortie si non spécifié
    if not args.output:
        md_filename = Path(args.markdown).stem
        args.output = f"output/{md_filename}.csv"
    
    print(f"Extraction des champs à partir de {args.markdown}...")
    
    # Lire les fichiers
    markdown_content = read_markdown_file(args.markdown)
    extraction_instructions = get_extraction_instructions(args.prompt)
    
    # Extraire les champs
    extracted_data = extract_fields_with_openai(markdown_content, extraction_instructions, args.model)
    
    # Sauvegarder les données extraites dans un fichier CSV
    if extracted_data:
        success = save_to_csv(extracted_data, args.output)
        if success:
            print("Extraction terminée avec succès.")
        else:
            print("Échec de l'extraction.")
    else:
        print("Aucune donnée n'a été extraite.")

if __name__ == "__main__":
    main()
