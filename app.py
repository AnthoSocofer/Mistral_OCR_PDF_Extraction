#!/usr/bin/env python3
"""
Application Streamlit pour extraire des données de fichiers PDF
en fonction de prompts d'extraction
"""

import os
import tempfile
import streamlit as st
import pandas as pd
from pathlib import Path
import base64
from typing import List, Dict, Any

from pdf_processor import PDFProcessor
from ocr_processor import OCRProcessor
from data_extractor import DataExtractor
from json_to_dataframe import JsonToDataFrame, extract_dataframes_from_ocr_json
from models import PDFPage, ExtractionResult


class PDFExtractionApp:
    """
    Application principale pour l'extraction de données de PDF
    """
    
    def __init__(self):
        """
        Initialise l'application d'extraction PDF
        """
        self.title = "PDF Data Extractor"
        
        # Configurer Streamlit
        st.set_page_config(
            page_title=self.title,
            page_icon="📄",
            layout="wide"
        )
        
        # Initialiser les composants
        # Initialiser l'OCR Processor seulement si une clé API est disponible
        api_key = os.getenv("MISTRAL_API_KEY")
        self.ocr_processor = None
        if api_key:
            try:
                self.ocr_processor = OCRProcessor(api_key=api_key, prompt_dir="./prompt_extraction")
            except Exception as e:
                st.error(f"Erreur lors de l'initialisation du processeur OCR: {e}")
                
        # Initialiser l'extracteur de données avec le processeur OCR
        self.data_extractor = DataExtractor(ocr_processor=self.ocr_processor)
    
    def run(self):
        """
        Exécute l'application Streamlit
        """
        st.title(self.title)
        

        # Vérifier la clé API Mistral
        if not os.getenv("MISTRAL_API_KEY"):
            st.warning("⚠️ La clé API Mistral n'est pas définie. Définissez la variable d'environnement MISTRAL_API_KEY.")
            
            # Permettre à l'utilisateur de saisir une clé API
            api_key = st.text_input("Entrez votre clé API Mistral:", type="password")
            if api_key:
                try:
                    self.ocr_processor = OCRProcessor(api_key=api_key)
                    st.success("✅ Clé API Mistral validée!")
                except Exception as e:
                    st.error(f"❌ Erreur lors de la validation de la clé API: {e}")
        
        # Étape 1: Charger le PDF depuis Streamlit
        self._step_load_pdf()
        
        # Si un PDF est chargé, continuer avec les autres étapes
        if "pdf_file" in st.session_state and st.session_state.pdf_file:
            # Étape 2: Choisir un prompt d'extraction
            self._step_select_extraction_prompt()
            
            # Bouton pour lancer le traitement
            if st.button("Lancer l'extraction"):
                # Vérifier que l'OCR Processor est disponible
                if not self.ocr_processor:
                    st.error("❌ L'OCR Processor n'est pas initialisé. Vérifiez votre clé API Mistral.")
                    return
                
                # Afficher une barre de progression
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Étape 3: Convertir le PDF en images
                    status_text.text("Conversion du PDF en images...")
                    pdf_pages = self._step_convert_pdf_to_images()
                    progress_bar.progress(0.25)
                    
                    # Étape 4: OCR sur les images
                    status_text.text("Traitement OCR des images...")
                    pdf_pages_with_ocr = self._step_process_ocr(pdf_pages)
                    progress_bar.progress(0.50)
                    
                    # Étape 5: Extraire les données selon le prompt
                    status_text.text("Extraction des données selon le prompt choisi...")
                    extraction_result = self._step_extract_data(pdf_pages_with_ocr)
                    progress_bar.progress(0.75)
                    
                    # Étape 6: Afficher les résultats
                    status_text.text("Affichage des résultats...")
                    self._step_display_results(pdf_pages, extraction_result)
                    progress_bar.progress(1.0)
                    
                    # Supprimer les messages de statut et la barre de progression
                    status_text.empty()
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors du traitement: {e}")
    
    def _step_load_pdf(self):
        """
        Étape 1: Chargement du fichier PDF
        """
        st.header("1. Charger un fichier PDF")
        
        uploaded_file = st.file_uploader("Choisissez un fichier PDF", type=["pdf"])
        if uploaded_file is not None:
            # Créer un fichier temporaire pour stocker le PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                pdf_path = tmp_file.name
            
            # Sauvegarder le chemin du fichier dans la session
            st.session_state.pdf_file = pdf_path
            st.session_state.pdf_name = uploaded_file.name
            
            st.success(f"✅ Fichier PDF chargé: {uploaded_file.name}")
    
    def _step_select_extraction_prompt(self):
        """
        Étape 2: Sélection du prompt d'extraction
        """
        st.header("2. Choisir un prompt d'extraction")
        
        # Récupérer la liste des prompts disponibles
        available_prompts = self.data_extractor.get_available_prompts()
        
        if not available_prompts:
            st.warning("⚠️ Aucun prompt d'extraction trouvé dans le répertoire ./prompt_extraction")
            return
        
        # Permettre à l'utilisateur de sélectionner un prompt
        selected_prompt = st.selectbox(
            "Sélectionnez un prompt d'extraction:",
            available_prompts
        )
        
        # Sauvegarder le prompt sélectionné dans la session
        st.session_state.selected_prompt = selected_prompt
    
    def _step_convert_pdf_to_images(self) -> List[PDFPage]:
        """
        Étape 3: Conversion du PDF en images
        
        Returns:
            List[PDFPage]: Liste des objets PDFPage générés
        """
        # Créer un répertoire temporaire pour les images
        temp_dir = Path(tempfile.mkdtemp())
        
        # Convertir le PDF en images
        pdf_processor = PDFProcessor()
        pdf_pages = pdf_processor.convert_pdf_to_images(
            st.session_state.pdf_file,
            output_dir=str(temp_dir),
            dpi=300,
            fmt="jpeg"
        )
        
        return pdf_pages
    
    def _step_process_ocr(self, pdf_pages: List[PDFPage]) -> List[PDFPage]:
        """
        Étape 4: Traitement OCR des images
        
        Args:
            pdf_pages (List[PDFPage]): Liste des pages PDF à traiter
            
        Returns:
            List[PDFPage]: Liste des pages PDF avec données OCR ajoutées
        """
        # Traiter chaque image avec OCR
        # Noter que nous n'utilisons pas encore le prompt d'extraction ici
        # car nous voulons d'abord extraire le texte OCR des images
        processed_pages = self.ocr_processor.process_pdf_pages(pdf_pages)
        
        return processed_pages
    
    def _step_extract_data(self, pdf_pages: List[PDFPage]) -> ExtractionResult:
        """
        Étape 5: Extraction des données selon le prompt choisi
        
        Args:
            pdf_pages (List[PDFPage]): Liste des pages PDF avec données OCR
            
        Returns:
            ExtractionResult: Résultat de l'extraction
        """
        try:
            # Extraire les données selon le prompt choisi
            # Le data_extractor utilisera automatiquement le OCRProcessor si disponible
            # pour traiter toutes les pages PDF ensemble avec le prompt d'extraction
            extraction_result = self.data_extractor.extract_data(
                pdf_pages,
                st.session_state.selected_prompt,
                st.session_state.pdf_name
            )
            
            return extraction_result
        except Exception as e:
            st.error(f"Erreur lors de l'extraction des données: {e}")
            # Créer un résultat d'extraction minimal en cas d'erreur
            return ExtractionResult(
                pdf_file=st.session_state.pdf_name,
                prompt_name=st.session_state.selected_prompt,
                extracted_data={"error": str(e)}
            )
    
    def _step_create_dataframes(self, extraction_result: ExtractionResult) -> Dict[str, pd.DataFrame]:
        """
        Étape 6: Création des DataFrames à partir des données extraites
        
        Args:
            extraction_result (ExtractionResult): Résultat de l'extraction
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionnaire de DataFrames générés
        """
        try:
            # Utiliser notre nouveau module pour convertir les données JSON en DataFrames
            dataframes = extract_dataframes_from_ocr_json(extraction_result)
            return dataframes
        except Exception as e:
            st.error(f"Erreur lors de la création des DataFrames: {e}")
            # En cas d'erreur, retourner un DataFrame minimal avec le message d'erreur
            return {"Erreur": pd.DataFrame([{"Message": str(e)}])}
    
    def _step_display_results(self, pdf_pages: List[PDFPage], extraction_result: ExtractionResult):
        """
        Étape 7: Affichage des résultats
        
        Args:
            pdf_pages (List[PDFPage]): Liste des pages PDF traitées
            extraction_result (ExtractionResult): Résultat de l'extraction
        """
        st.header("Résultats de l'extraction")
        
        # Diviser l'affichage en deux colonnes
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Aperçu du PDF")
            
            # Créer des onglets pour chaque page du PDF
            if pdf_pages:
                tabs = st.tabs([f"Page {page.page_number}" for page in pdf_pages])
                
                for i, tab in enumerate(tabs):
                    with tab:
                        # Afficher l'image
                        image_path = pdf_pages[i].image_path
                        st.image(image_path, use_container_width=True)
        
        with col2:
            st.subheader("Données extraites")
            
            # Afficher le prompt utilisé
            st.markdown(f"**Prompt d'extraction:** {extraction_result.prompt_name}")
            
            # Générer les DataFrames à partir du résultat d'extraction
            dataframes = self._step_create_dataframes(extraction_result)
            
            # Utiliser la fonction d'affichage de JsonToDataFrame pour afficher les DataFrames
            if dataframes:
                JsonToDataFrame.display_dataframes_in_streamlit(dataframes)
            else:
                st.info("Aucune donnée extraite.")


# Point d'entrée de l'application
if __name__ == "__main__":
    app = PDFExtractionApp()
    app.run()
