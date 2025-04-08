#!/usr/bin/env python3
"""
Module pour traiter les images avec OCR en utilisant l'API Mistral
"""

import base64
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from models import PDFPage, StructuredOCR

# Importer le client Mistral et les classes de message appropriées
from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk, TextChunk


# Instance globale du client
client = None

class OCRProcessor:
    """
    Classe pour traiter les images avec OCR en utilisant Mistral OCR
    """
    
    def __init__(self, api_key: str = None, prompt_dir: str = "./prompt_extraction"):
        """
        Initialise le processeur OCR
        
        Args:
            api_key (str, optional): Clé API Mistral. Si None, cherche dans les variables d'environnement
            prompt_dir (str): Répertoire contenant les prompts d'extraction
        """
        # Initialisation du client avec la clé API
        global client
        if api_key is None:
            api_key = os.getenv("MISTRAL_API_KEY")
            if api_key is None:
                raise ValueError("La clé API Mistral est requise. Définissez la variable d'environnement MISTRAL_API_KEY ou passez-la en paramètre.")
        
        # Initialiser le client Mistral avec la clé API
        client = Mistral(api_key=api_key)
        
        # Répertoire des prompts d'extraction
        self.prompt_dir = Path(prompt_dir)
        if not self.prompt_dir.exists():
            print(f"Attention: Le répertoire de prompts {prompt_dir} n'existe pas")
    
    def get_extraction_prompt(self, prompt_name: str) -> str:
        """
        Récupère le contenu d'un prompt d'extraction
        
        Args:
            prompt_name (str): Nom du prompt (sans l'extension .md)
            
        Returns:
            str: Contenu du prompt
            
        Raises:
            FileNotFoundError: Si le fichier de prompt n'existe pas
        """
        prompt_path = self.prompt_dir / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Le prompt d'extraction '{prompt_name}' n'existe pas dans {self.prompt_dir}")
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def structured_ocr(self, image_path: str, prompt_name: Optional[str] = None) -> StructuredOCR:
        """
        Traite une image en utilisant OCR et extrait des données structurées
        
        Args:
            image_path (str): Chemin vers le fichier image à traiter
            prompt_name (str, optional): Nom du prompt d'extraction à utiliser
            
        Returns:
            StructuredOCR: Objet contenant les données extraites
            
        Raises:
            AssertionError: Si le fichier image n'existe pas
        """
        # Valider le fichier d'entrée
        image_file = Path(image_path)
        assert image_file.is_file(), "The provided image path does not exist."

        # Lire et encoder le fichier image
        encoded_image = base64.b64encode(image_file.read_bytes()).decode()
        base64_data_url = f"data:image/jpeg;base64,{encoded_image}"

        try:
            # Traiter l'image en utilisant OCR
            image_response = client.ocr.process(
                document=ImageURLChunk(image_url=base64_data_url),
                model="mistral-ocr-latest"
            )
            image_ocr_markdown = image_response.pages[0].markdown
            
            # Récupérer le prompt d'extraction si spécifié
            fields_extraction_text = ""
            if prompt_name:
                try:
                    fields_extraction_text = f"Extrait les champs suivants dans une réponse au format JSON et sélectionne dans les champs les informations qui correspondent à l'exemple:\n{self.get_extraction_prompt(prompt_name)}\n."
                except FileNotFoundError as e:
                    print(f"Attention: {e}")

            # Parse the OCR result into a structured JSON response
            chat_response = client.chat.parse(
                model="pixtral-12b-latest",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            ImageURLChunk(image_url=base64_data_url),
                            TextChunk(text=(
                                f"Ceci est l'OCR de l'image au format markdown:\n{image_ocr_markdown}\n.\n"
                                "Converti la en une réponse structurée au format JSON "
                                "avec le contenu de l'OCR dans un dictionnaire sensé. "
                                f"{fields_extraction_text}"
                                )
                            )
                        ]
                    }
                ],
                response_format=StructuredOCR,
                temperature=0
            )
            
            return chat_response.choices[0].message.parsed
            
        except Exception as e:
            # En cas d'erreur, renvoyer un résultat minimal
            return StructuredOCR(
                file_name=str(image_file.name),
                ocr_contents={
                    "error": str(e),
                    "file": str(image_file),
                    "message": "Erreur lors du traitement OCR"
                }
            )
    
    def process_pdf_pages(self, pdf_pages: List[PDFPage], prompt_name: Optional[str] = None) -> Union[List[PDFPage], StructuredOCR]:
        """
        Traite toutes les pages d'un PDF avec OCR et les combine pour extraction
        
        Args:
            pdf_pages (List[PDFPage]): Liste des pages PDF à traiter
            prompt_name (str, optional): Nom du prompt d'extraction à utiliser
            
        Returns:
            Union[List[PDFPage], StructuredOCR]: Soit la liste des pages traitées individuellement, 
                                               soit un résultat combiné structuré
        """
        if not pdf_pages:
            return []
        
        # Si prompt_name est spécifié, traiter toutes les pages ensemble
        if prompt_name:
            # Collecter l'OCR de toutes les pages
            all_ocr_markdowns = []
            for page in pdf_pages:
                try:
                    # Traiter l'OCR pour chaque page individuellement
                    image_file = Path(page.image_path)
                    encoded_image = base64.b64encode(image_file.read_bytes()).decode()
                    base64_data_url = f"data:image/jpeg;base64,{encoded_image}"
                    
                    # Traiter l'image avec OCR
                    image_response = client.ocr.process(
                        document=ImageURLChunk(image_url=base64_data_url),
                        model="mistral-ocr-latest"
                    )
                    image_ocr_markdown = image_response.pages[0].markdown
                    all_ocr_markdowns.append(f"=== Page {page.page_number} ===\n{image_ocr_markdown}")
                except Exception as e:
                    print(f"Erreur lors du traitement OCR de la page {page.page_number}: {e}")
            
            # Combiner l'OCR de toutes les pages en un seul texte
            combined_ocr_markdown = "\n\n".join(all_ocr_markdowns)
            
            # Obtenir le prompt d'extraction
            fields_extraction_text = ""
            try:
                fields_extraction_text = f"Extrait les champs suivants dans une réponse au format JSON et sélectionne dans les champs les informations qui correspondent à l'exemple:\n{self.get_extraction_prompt(prompt_name)}\n."
            except FileNotFoundError as e:
                print(f"Attention: {e}")
            
            try:
                # Utiliser la première page pour la référence visuelle
                reference_image = pdf_pages[0].image_path
                image_file = Path(reference_image)
                encoded_image = base64.b64encode(image_file.read_bytes()).decode()
                base64_data_url = f"data:image/jpeg;base64,{encoded_image}"
                
                # Parse the OCR results into a structured JSON response
                chat_response = client.chat.parse(
                    model="pixtral-12b-latest",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": base64_data_url}},
                                {"type": "text", "text": (
                                    f"Voici l'OCR complet d'un document de plusieurs pages:\n{combined_ocr_markdown}\n.\n"
                                    "Converti cela en une réponse structurée au format JSON "
                                    "avec le contenu de l'OCR dans un dictionnaire sensé. "
                                    f"{fields_extraction_text}"
                                    )
                                }
                            ]
                        }
                    ],
                    response_format=StructuredOCR,
                    temperature=0
                )
                
                # Créer un résultat structuré à partir de toutes les pages
                pdf_name = Path(pdf_pages[0].image_path).stem.split('_')[0]  # Extraire le nom du PDF à partir du nom de l'image
                combined_result = chat_response.choices[0].message.parsed
                
                # Stocker également le résultat dans la première page pour compatibilité
                pdf_pages[0].ocr_data = combined_result
                
                return combined_result
            
            except Exception as e:
                print(f"Erreur lors du traitement combiné des pages: {e}")
                # En cas d'échec, revenir au traitement individuel des pages
        
        # Traitement individuel des pages (fallback ou si prompt_name est None)
        for page in pdf_pages:
            ocr_data = self.structured_ocr(page.image_path, prompt_name)
            page.ocr_data = ocr_data
        
        return pdf_pages
