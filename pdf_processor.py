#!/usr/bin/env python3
"""
Module pour gérer la conversion des PDF en images
"""

import os
from pathlib import Path
from typing import List
from pdf2image import convert_from_path
from models import PDFPage


class PDFProcessor:
    """
    Classe pour gérer la conversion des PDF en images
    """
    
    @staticmethod
    def convert_pdf_to_images(pdf_path: str, output_dir: str = None, 
                             dpi: int = 300, fmt: str = 'jpeg') -> List[PDFPage]:
        """
        Convertit toutes les pages d'un fichier PDF en images
        
        Args:
            pdf_path (str): Chemin vers le fichier PDF à convertir
            output_dir (str, optional): Répertoire de sortie pour les images.
                                      Par défaut: même dossier que le PDF avec un sous-dossier du nom du PDF
            dpi (int, optional): Résolution des images en DPI. Par défaut: 300
            fmt (str, optional): Format des images ('jpeg', 'png', etc.). Par défaut: 'jpeg'
        
        Returns:
            List[PDFPage]: Liste des objets PDFPage générés
        """
        # Vérifier que le fichier existe
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Le fichier PDF '{pdf_path}' n'existe pas")
        
        # Déterminer le répertoire de sortie
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_images"
        else:
            output_dir = Path(output_dir)
        
        # Créer le répertoire de sortie s'il n'existe pas
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Convertir les pages du PDF en images
        images = convert_from_path(
            pdf_path, 
            dpi=dpi,
            fmt=fmt,
            thread_count=os.cpu_count()  # Utilisation de tous les coeurs CPU disponibles
        )
        
        # Enregistrer les images et créer les objets PDFPage
        pdf_pages = []
        for i, image in enumerate(images):
            # Créer le nom de fichier avec padding pour le tri (001, 002, etc.)
            image_path = output_dir / f"page_{i+1:03d}.{fmt}"
            image.save(image_path)
            
            # Créer un objet PDFPage pour chaque page
            pdf_page = PDFPage(
                page_number=i+1,
                image_path=str(image_path)
            )
            pdf_pages.append(pdf_page)
            
        return pdf_pages
