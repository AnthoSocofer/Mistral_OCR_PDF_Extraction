#!/usr/bin/env python3
"""
Modèles de données pour l'application d'extraction de PDF
"""

from enum import Enum
from pathlib import Path
from pydantic import BaseModel


class StructuredOCR(BaseModel):
    """
    Modèle pour les données OCR structurées
    """
    file_name: str
    ocr_contents: dict


class PDFPage(BaseModel):
    """
    Modèle pour une page de PDF convertie en image
    """
    page_number: int
    image_path: str
    ocr_data: StructuredOCR = None


class ExtractionResult(BaseModel):
    """
    Modèle pour les résultats d'extraction
    """
    pdf_file: str
    prompt_name: str
    extracted_data: dict
