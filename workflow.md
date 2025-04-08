[1] Charger le pdf depuis streamlit
[2] Demander à l'utilisateur de choisir un prompt d'extraction
[3] Convertir le pdf en images
[4] OCR sur les images en utilisant mistral OCR
[5] Extraire les champs en fonction du choix du prompt d'extraction, qui sont disponibles dans le directory ./prompt_extraction
[6] Afficher le pdf dans l'IHM streamlit et afficher le résultat de l'extraction dans un dataframe pandas dans l'IHM streamlit