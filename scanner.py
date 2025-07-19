# scanner.py (Versión 3 - Optimizado con Numba)
# --- Quick Index ---
# Posible variable para revisión. Más control */*
# Posible variable para revisión. Más eficiente */*
import argparse
import json
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import numpy as np
from numba import jit

@jit(nopython=True, cache=True)
def _numba_scan(image_array_gray, image_array_rgb, width, height, brightness_threshold): # Esta función es compilada por Numba para máxima velocidad
    pixel_data = []
    for x in range(width):
        # Usamos una tupla para la columna porque Numba no soporta listas de diccionarios
        column_pixels = []
        for y in range(height):
            if image_array_gray[y, x] > brightness_threshold:
                r, g, b = image_array_rgb[y, x]
                # Guardamos como tuplas: (y, brillo, r, g, b)
                column_pixels.append((y, image_array_gray[y, x], r, g, b))
        
        if len(column_pixels) > 0:
            pixel_data.append((x, column_pixels))
    return pixel_data

def analyze_image(image_path: Path, output_path: Path):
    # Analiza imágenes y tranforma data a pixeles en un json.
    try:
        with Image.open(image_path) as img:
            # Asegurar la carga de imágenes RGB*
            rgb_img = img.convert("RGB")
            grayscale_img = img.convert("L") # Escala de grises para umbral de brillo
            
            # Convertir imágenes a arrays de NumPy para Numba
            image_array_rgb = np.array(rgb_img)
            image_array_gray = np.array(grayscale_img)
            width, height = img.size
            
            # Llamar a la función optimizada
            numba_result = _numba_scan(image_array_gray, image_array_rgb, width, height, 20)
            
            # Para registrar cada columna como representación del tiempo. Tal vez deba modificar para mejorar rendimiento a cambio de data.
            # Posible variable para revisión. Más eficiente */*
            # Convertir el resultado de Numba a un formato JSON estándar
            final_data = []
            for x, pixels in numba_result:
                column_list = []
                for p in pixels:
                    column_list.append({"y": int(p[0]), "brightness": int(p[1]), "rgb": [int(p[2]), int(p[3]), int(p[4])]})
                final_data.append({"time_step": x, "pixels": column_list})

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump({ "image_width": width, "image_height": height, "data": final_data }, f)
    except Exception as e:
        print(f"Error procesando {image_path.name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analiza imágenes y extrae datos de píxeles para sonificación.")
    parser.add_argument("--input", type=str, required=True, help="Ruta a la imagen o carpeta de imágenes a analizar.")
    args = parser.parse_args()
    input_path = Path(args.input)
    
    files_to_process = []
    if input_path.is_dir():
        # Sorted para asegurar el orden alfabético
        files_to_process.extend(sorted(input_path.glob('*.*')))
    elif input_path.is_file():
        files_to_process.append(input_path)

    if not files_to_process:
        print(f"No se encontraron imágenes en '{input_path}'.")
    else:
        
        # --- Bucle con barra de progreso ---
        for image_file in tqdm(files_to_process, desc="Analizando imágenes"):
            output_filename = image_file.with_suffix(".json").name
            # Output
            if input_path.is_dir():
                output_dir = Path("data_output") / input_path.name
            else:
                output_dir = Path("data_output") / (input_path.parent.name if input_path.parent.name != "input_images" else "")
            output_path = output_dir / output_filename
            analyze_image(image_file, output_path)
        print("Análisis por lotes completado")