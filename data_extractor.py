#!/usr/bin/env python3
"""
Module pour extraire des données structurées à partir des résultats OCR
en fonction de prompts d'extraction
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from models import PDFPage, StructuredOCR, ExtractionResult
from ocr_processor import OCRProcessor


class DataExtractor:
    """
    Classe pour extraire des données à partir des résultats OCR 
    en fonction de prompts d'extraction
    """
    
    def __init__(self, prompt_dir: str = "./prompt_extraction", ocr_processor: Optional[OCRProcessor] = None):
        """
        Initialise l'extracteur de données
        
        Args:
            prompt_dir (str): Répertoire contenant les prompts d'extraction
            ocr_processor (OCRProcessor, optional): Instance du processeur OCR à utiliser
        """
        self.prompt_dir = Path(prompt_dir)
        self.prompts = self._load_prompts()
        self.ocr_processor = ocr_processor
    
    def _load_prompts(self) -> Dict[str, str]:
        """
        Charge les prompts d'extraction depuis le répertoire spécifié
        
        Returns:
            Dict[str, str]: Dictionnaire de prompts (nom -> contenu)
        """
        prompts = {}
        if not self.prompt_dir.exists():
            raise FileNotFoundError(f"Le répertoire de prompts '{self.prompt_dir}' n'existe pas")
            
        for prompt_file in self.prompt_dir.glob("*.md"):
            prompt_name = prompt_file.stem
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_content = f.read()
            prompts[prompt_name] = prompt_content
            
        return prompts
    
    def get_available_prompts(self) -> List[str]:
        """
        Retourne la liste des prompts disponibles
        
        Returns:
            List[str]: Liste des noms de prompts disponibles
        """
        return list(self.prompts.keys())
    
    def extract_data(self, pdf_pages: List[PDFPage], prompt_name: str, 
                     pdf_file: str) -> ExtractionResult:
        """
        Extrait des données à partir des résultats OCR en utilisant un prompt spécifique
        
        Args:
            pdf_pages (List[PDFPage]): Liste des pages PDF avec données OCR
            prompt_name (str): Nom du prompt d'extraction à utiliser
            pdf_file (str): Nom du fichier PDF original
            
        Returns:
            ExtractionResult: Résultat de l'extraction
            
        Raises:
            ValueError: Si le prompt spécifié n'existe pas ou si aucun processeur OCR n'est disponible
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Le prompt '{prompt_name}' n'existe pas")
        
        # Si nous avons un processeur OCR, utiliser directement son processus d'extraction 
        # combiné pour toutes les pages
        if self.ocr_processor:
            # Traiter toutes les pages avec OCR et prompt d'extraction
            result = self.ocr_processor.process_pdf_pages(pdf_pages, prompt_name)
            
            # Si le résultat est un objet StructuredOCR (analyse combinée de toutes les pages)
            if isinstance(result, StructuredOCR):
                return ExtractionResult(
                    pdf_file=pdf_file,
                    prompt_name=prompt_name,
                    extracted_data=result.ocr_contents
                )
        
        # Fallback: utiliser les données OCR déjà présentes dans les pages
        extracted_data = {}
        
        for page in pdf_pages:
            if page.ocr_data:
                # Fusionner les données de chaque page dans les résultats extraits
                page_data = page.ocr_data.ocr_contents
                for key, value in page_data.items():
                    if key in extracted_data:
                        # Si la clé existe déjà, fusionner les valeurs
                        if isinstance(extracted_data[key], list):
                            if isinstance(value, list):
                                extracted_data[key].extend(value)
                            else:
                                extracted_data[key].append(value)
                        else:
                            # Convertir en liste si ce n'est pas déjà le cas
                            extracted_data[key] = [extracted_data[key], value]
                    else:
                        extracted_data[key] = value
        
        return ExtractionResult(
            pdf_file=pdf_file,
            prompt_name=prompt_name,
            extracted_data=extracted_data
        )
