#!/usr/bin/env python3
"""
Script pour convertir toutes les pages d'un PDF en images JPEG
"""

import os
import argparse
from pathlib import Path
from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_path, output_dir=None, dpi=300, fmt='jpeg'):
    """
    Convertit toutes les pages d'un fichier PDF en images JPEG
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF à convertir
        output_dir (str, optional): Répertoire de sortie pour les images.
                                    Par défaut: même dossier que le PDF avec un sous-dossier du nom du PDF
        dpi (int, optional): Résolution des images en DPI. Par défaut: 300
        fmt (str, optional): Format des images ('jpeg', 'png', etc.). Par défaut: 'jpeg'
    
    Returns:
        list: Liste des chemins des images générées
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
    
    print(f"Conversion du PDF: {pdf_path}")
    print(f"Sortie dans: {output_dir}")
    print(f"Résolution: {dpi} DPI")
    print("Conversion en cours...")
    
    # Convertir les pages du PDF en images
    images = convert_from_path(
        pdf_path, 
        dpi=dpi,
        fmt=fmt,
        thread_count=os.cpu_count()  # Utilisation de tous les coeurs CPU disponibles
    )
    
    # Enregistrer les images
    image_paths = []
    for i, image in enumerate(images):
        # Créer le nom de fichier avec padding pour le tri (001, 002, etc.)
        image_path = output_dir / f"page_{i+1:03d}.{fmt}"
        image.save(image_path)
        image_paths.append(image_path)
        print(f"Page {i+1}/{len(images)} convertie -> {image_path}")
    
    print(f"\nConversion terminée: {len(images)} pages converties en images {fmt.upper()}")
    return image_paths

def main():
    # Configurer l'analyseur d'arguments
    parser = argparse.ArgumentParser(description="Convertir un PDF en images JPEG")
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF à convertir")
    parser.add_argument(
        "-o", "--output-dir", 
        help="Répertoire de sortie pour les images (facultatif)"
    )
    parser.add_argument(
        "-d", "--dpi", 
        type=int, 
        default=300, 
        help="Résolution des images en DPI (défaut: 300)"
    )
    parser.add_argument(
        "-f", "--format", 
        default="jpeg", 
        choices=["jpeg", "png", "tiff"], 
        help="Format des images de sortie (défaut: jpeg)"
    )
    
    args = parser.parse_args()
    
    # Convertir le PDF en images
    try:
        convert_pdf_to_images(
            args.pdf_path, 
            args.output_dir, 
            args.dpi, 
            args.format
        )
    except Exception as e:
        print(f"Erreur lors de la conversion: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
