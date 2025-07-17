# pipeline.py (Versión 2 - Guarda archivos intermedios)
import argparse
from pathlib import Path
import multiprocessing
from functools import partial
from tqdm import tqdm

# Importar las funciones principales de nuestros otros scripts
from scanner import analyze_image
from synthesizer import synthesize
from composer import compose_audio

def synthesis_worker(json_file: Path, temp_wav_dir: Path, args):
    """Función que envuelve la lógica para sintetizar un único archivo en paralelo."""
    try:
        output_filename = json_file.with_suffix(".wav").name
        output_path = temp_wav_dir / output_filename
        synthesize(json_file, output_path, args.duration, args.scale, args.mode, args.waveform)
    except Exception as e:
        print(f"Error sintetizando {json_file.name}: {e}")

def run_full_pipeline(args):
    """
    Ejecuta el flujo completo y guarda los archivos intermedios en una
    carpeta permanente.
    """
    input_folder = Path(args.input_folder)
    output_file = Path(args.output_file)

    if not input_folder.is_dir():
        print(f"Error: La carpeta de entrada '{input_folder}' no existe.")
        return

    # --- Creación de carpetas permanentes para archivos intermedios ---
    # Se crea una carpeta con el nombre del archivo de salida para organizar.
    intermediate_dir = output_file.parent / (output_file.stem + "_intermediate_files")
    json_dir = intermediate_dir / "1_json_data"
    wav_dir = intermediate_dir / "2_wav_individual_sounds"
    json_dir.mkdir(parents=True, exist_ok=True)
    wav_dir.mkdir(parents=True, exist_ok=True)

    print(f"Archivos intermedios se guardarán en: {intermediate_dir}")

    # --- PASO 1: ANÁLISIS (SCANNER) ---
    image_files = sorted(input_folder.glob('*.*'))
    if not image_files:
        print(f"No se encontraron imágenes en '{input_folder}'.")
        return
    
    print(f"\n--- PASO 1 de 3: Analizando {len(image_files)} imágenes ---")
    for image_file in tqdm(image_files, desc="Analizando"):
        output_filename = image_file.with_suffix(".json").name
        output_path = json_dir / output_filename
        analyze_image(image_file, output_path)

    # --- PASO 2: SÍNTESIS (SYNTHESIZER) ---
    json_files = sorted(json_dir.glob('*.json'))
    print(f"\n--- PASO 2 de 3: Sintetizando {len(json_files)} archivos de audio ---")
    
    with multiprocessing.Pool() as pool:
        task = partial(synthesis_worker, temp_wav_dir=wav_dir, args=args)
        for _ in tqdm(pool.imap_unordered(task, json_files), total=len(json_files), desc="Sintetizando en paralelo"):
            pass
    
    # --- PASO 3: COMPOSICIÓN (COMPOSER) ---
    print(f"\n--- PASO 3 de 3: Componiendo la pieza final ---")
    compose_audio(wav_dir, output_file)

    print(f"\n¡Pipeline completado! La composición final está en: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline completo para convertir una secuencia de imágenes en una composición de audio.")
    parser.add_argument("--input-folder", type=str, required=True, help="Carpeta que contiene la secuencia de imágenes originales.")
    parser.add_argument("--output-file", type=str, required=True, help="Ruta del archivo .wav final de salida.")
    
    parser.add_argument("--duration", type=float, default=10.0, help="Duración en segundos del audio generado POR CADA imagen.")
    parser.add_argument("--scale", type=str, default="pentatonic", choices=["raw", "pentatonic", "major", "minor"])
    parser.add_argument("--mode", type=str, default="rgb_instrument", choices=["brightness", "rgb_instrument"])
    parser.add_argument("--waveform", type=str, default="sine", choices=["sine", "square", "sawtooth"])
    
    args = parser.parse_args()
    run_full_pipeline(args)