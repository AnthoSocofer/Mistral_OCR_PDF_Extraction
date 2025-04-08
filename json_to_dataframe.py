#!/usr/bin/env python3
"""
Module pour convertir les données JSON extraites par OCR en DataFrame pandas.
Ce script sert à l'étape 6 du workflow, permettant de visualiser et manipuler
les données extraites sous forme tabulaire.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Union, Optional
from pathlib import Path
import os
import streamlit as st
from models import ExtractionResult, StructuredOCR


class JsonToDataFrame:
    """
    Classe pour convertir les données JSON extraites par OCR en DataFrame pandas.
    """
    
    @staticmethod
    def create_dataframe_from_extraction_result(extraction_result: ExtractionResult) -> Dict[str, pd.DataFrame]:
        """
        Crée un ou plusieurs DataFrames pandas à partir du résultat d'extraction.
        
        Args:
            extraction_result (ExtractionResult): Résultat d'extraction contenant les données structurées
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionnaire de DataFrames avec les noms des tableaux comme clés
        """
        # Récupérer les données extraites
        extracted_data = extraction_result.extracted_data
        
        # Vérifier si les données ont été correctement extraites
        if not extracted_data or isinstance(extracted_data, str):
            # Retourner un DataFrame vide ou avec un message d'erreur
            return {"Erreur": pd.DataFrame([{"Message": "Aucune donnée extraite ou format incorrect"}])}
        
        # Dictionnaire pour stocker les DataFrames résultants
        dataframes = {}
        
        # Parcourir toutes les clés de premier niveau dans les données extraites
        for key, value in extracted_data.items():
            # Cas 1: La valeur est une liste d'objets (tableau)
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                # Créer un DataFrame à partir de la liste d'objets
                dataframes[key] = pd.DataFrame(value)
            
            # Cas 2: La valeur est un dictionnaire
            elif isinstance(value, dict):
                # Créer un DataFrame à partir du dictionnaire
                dataframes[key] = pd.DataFrame([value])
            
            # Cas 3: Les valeurs simples sont regroupées dans un DataFrame "Informations générales"
            else:
                if "Informations générales" not in dataframes:
                    dataframes["Informations générales"] = pd.DataFrame()
                
                # Ajouter la valeur simple comme nouvelle colonne
                dataframes["Informations générales"][key] = [value]
        
        # Si aucun DataFrame n'a été créé dans les cas précédents
        if not dataframes:
            # Créer un DataFrame simple à partir de toutes les données de premier niveau
            simple_data = {k: [v] for k, v in extracted_data.items() if not isinstance(v, (list, dict))}
            if simple_data:
                dataframes["Informations générales"] = pd.DataFrame(simple_data)
        
        return dataframes
    
    @staticmethod
    def display_dataframes_in_streamlit(dataframes: Dict[str, pd.DataFrame]):
        """
        Affiche les DataFrames dans l'interface Streamlit avec des fonctionnalités
        d'exportation et de visualisation.
        
        Args:
            dataframes (Dict[str, pd.DataFrame]): Dictionnaire de DataFrames à afficher
        """
        if not dataframes:
            st.warning("Aucune donnée à afficher.")
            return
        
        # Utiliser des onglets pour chaque DataFrame
        if len(dataframes) > 1:
            tabs = st.tabs(list(dataframes.keys()))
            
            for i, (name, df) in enumerate(dataframes.items()):
                with tabs[i]:
                    st.subheader(name)
                    st.dataframe(df, use_container_width=True)
                    
                    # Options d'exportation
                    export_format = st.selectbox(f"Format d'exportation pour {name}", 
                                               ["CSV", "Excel", "JSON"], key=f"export_{i}")
                    
                    # Bouton d'exportation
                    if st.button(f"Exporter les données ({name})", key=f"export_button_{i}"):
                        JsonToDataFrame.export_dataframe(df, name, export_format)
        else:
            # S'il n'y a qu'un seul DataFrame, l'afficher directement
            name = list(dataframes.keys())[0]
            df = dataframes[name]
            
            st.subheader(name)
            st.dataframe(df, use_container_width=True)
            
            # Options d'exportation
            export_format = st.selectbox(f"Format d'exportation", 
                                       ["CSV", "Excel", "JSON"])
            
            # Bouton d'exportation
            if st.button(f"Exporter les données"):
                JsonToDataFrame.export_dataframe(df, name, export_format)
    
    @staticmethod
    def export_dataframe(df: pd.DataFrame, name: str, format: str = "CSV") -> Optional[str]:
        """
        Exporte un DataFrame dans le format spécifié.
        
        Args:
            df (pd.DataFrame): DataFrame à exporter
            name (str): Nom du DataFrame (utilisé pour le nom de fichier)
            format (str): Format d'exportation ("CSV", "Excel", "JSON")
            
        Returns:
            Optional[str]: Chemin du fichier exporté ou None en cas d'erreur
        """
        # Créer un dossier d'exportation s'il n'existe pas
        export_dir = Path("./exports")
        export_dir.mkdir(exist_ok=True)
        
        # Nettoyer le nom pour le fichier
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        safe_name = safe_name.replace(" ", "_").lower()
        
        try:
            if format == "CSV":
                file_path = export_dir / f"{safe_name}.csv"
                df.to_csv(file_path, index=False, encoding="utf-8")
                st.success(f"Données exportées avec succès vers {file_path}")
                
                # Proposer le téléchargement dans Streamlit
                with open(file_path, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="Télécharger CSV",
                        data=f,
                        file_name=f"{safe_name}.csv",
                        mime="text/csv"
                    )
                
            elif format == "Excel":
                file_path = export_dir / f"{safe_name}.xlsx"
                df.to_excel(file_path, index=False)
                st.success(f"Données exportées avec succès vers {file_path}")
                
                # Proposer le téléchargement dans Streamlit
                with open(file_path, "rb") as f:
                    st.download_button(
                        label="Télécharger Excel",
                        data=f,
                        file_name=f"{safe_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            elif format == "JSON":
                file_path = export_dir / f"{safe_name}.json"
                df.to_json(file_path, orient="records", force_ascii=False, indent=4)
                st.success(f"Données exportées avec succès vers {file_path}")
                
                # Proposer le téléchargement dans Streamlit
                with open(file_path, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="Télécharger JSON",
                        data=f,
                        file_name=f"{safe_name}.json",
                        mime="application/json"
                    )
            
            return str(file_path)
        
        except Exception as e:
            st.error(f"Erreur lors de l'exportation des données: {e}")
            return None


def extract_dataframes_from_ocr_json(ocr_result: Union[StructuredOCR, ExtractionResult, Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """
    Fonction principale pour extraire des DataFrames à partir du résultat OCR JSON.
    
    Args:
        ocr_result: Résultat OCR (peut être un objet StructuredOCR, ExtractionResult ou un dict)
            
    Returns:
        Dict[str, pd.DataFrame]: Dictionnaire de DataFrames
    """
    # Convertir en ExtractionResult si nécessaire
    if isinstance(ocr_result, StructuredOCR):
        extraction_result = ExtractionResult(
            pdf_file="document.pdf",
            prompt_name="default",
            extracted_data=ocr_result.ocr_contents
        )
    elif isinstance(ocr_result, dict):
        # Si c'est un dictionnaire brut, créer un ExtractionResult
        if "file_name" in ocr_result and "ocr_contents" in ocr_result:
            extraction_result = ExtractionResult(
                pdf_file=ocr_result.get("file_name", "document.pdf"),
                prompt_name="default",
                extracted_data=ocr_result["ocr_contents"]
            )
        else:
            # Considérer que le dictionnaire est directement les données extraites
            extraction_result = ExtractionResult(
                pdf_file="document.pdf",
                prompt_name="default",
                extracted_data=ocr_result
            )
    elif isinstance(ocr_result, ExtractionResult):
        extraction_result = ocr_result
    else:
        # Type non pris en charge
        raise TypeError(f"Type de résultat OCR non pris en charge: {type(ocr_result)}")
    
    # Créer les DataFrames
    return JsonToDataFrame.create_dataframe_from_extraction_result(extraction_result)


if __name__ == "__main__":
    # Code de test si exécuté directement
    sample_data = {
        "file_name": "AR DE COMMANDE",
        "ocr_contents": {
            "Votre Commande": "21854",
            "Pièces / Désignations": [
                {
                    "Pièce / Désignation": "SOCO-COW002-01PP21A S3G5JR/DKP 3.00 mm 110.00x681.54 Suivant notre devis N° : 27458-1",
                    "Qté": 2,
                    "PUHT": "11.36 €",
                    "Délai": "21/01/25"
                },
                {
                    "Pièce / Désignation": "SOCO-COW002-01PP25A 30AL \"LAF 3.00 mm 30.00x128.69 Suivant notre devis N° : 27458-1",
                    "Qté": 44,
                    "PUHT": "1.59 €",
                    "Délai": "21/01/25"
                }
            ]
        }
    }
    
    dataframes = extract_dataframes_from_ocr_json(sample_data)
    
    # Afficher les DataFrames (pour test en ligne de commande)
    for name, df in dataframes.items():
        print(f"\n=== {name} ===")
        print(df.to_string())
