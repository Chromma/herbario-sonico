# pipeline.py (Versión 3 - Soporte MIDI)
import argparse
from pathlib import Path
import multiprocessing
from functools import partial
from tqdm import tqdm
import json

# Importa las funciones principales de nuestros otros scripts
from scanner import analyze_image
from synthesizer import synthesize as synthesize_wav # Mayor claridad
from midi_synthesizer import synthesize_midi
from composer import compose_audio


# --- Workers para parelelización ---
def wav_synthesis_worker(json_file: Path, wav_dir: Path, args):
    with open(json_file, 'r') as f: data = json.load(f)
    output_filename = json_file.with_suffix(".wav").name
    output_path = wav_dir / output_filename
    synthesize_wav(data, output_path, args.duration, args.scale, args.mode, args.waveform)

def midi_synthesis_worker(json_file: Path, midi_dir: Path, args):
    with open(json_file, 'r') as f: data = json.load(f)
    output_filename = json_file.with_suffix(".mid").name
    output_path = midi_dir / output_filename
    # Recopilar parámetros MIDI de los argumentos
    midi_params = {
        'r_channel': args.midi_r_channel,
        'g_channel': args.midi_g_channel,
        'b_channel': args.midi_b_channel
    }
    synthesize_midi(data, output_path, midi_params)

def run_full_pipeline(args):
    # Ejecuta el flujo completo y guarda los archivos intermedios en carpetas permanentes.
    input_folder = Path(args.input_folder)
    output_file = Path(args.output_file)
    output_mode = args.output_mode

    # Lógica de directorios intermedios
    intermediate_dir = output_file.parent / (output_file.stem + "_intermediate_files")
    json_dir = intermediate_dir / "1_json_data"
    json_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Archivos intermedios se guardarán en: {intermediate_dir}")
    
    # --- PASO 1: ANÁLISIS (SCANNER) ---
    image_files = sorted(input_folder.glob('*.*'))
    print(f"--- PASO 1 de 3: Analizando {len(image_files)} imagenes ---")
    for image_file in tqdm(image_files, desc="Analizando"):
        output_path = json_dir / image_file.with_suffix(".json").name
        analyze_image(image_file, output_path)

    # --- PASO 2: SÍNTESIS (WAV o MIDI) ---
    json_files = sorted(json_dir.glob('*.json'))
    print(f"--- PASO 2 de 3: Sintetizando {len(json_files)} archivos en modo {output_mode} ---")

    if output_mode == 'wav':
        wav_dir = intermediate_dir / "2_wav_individual_sounds"
        wav_dir.mkdir(parents=True, exist_ok=True)
        with multiprocessing.Pool() as pool:
            task = partial(wav_synthesis_worker, wav_dir=wav_dir, args=args)
            for _ in tqdm(pool.imap_unordered(task, json_files), total=len(json_files), desc="Sintetizando WAV"):
                pass
        
        # --- PASO 3: COMPOSICIÓN (COMPOSER) ---
        print(f"--- PASO 3 de 3: Componiendo la pieza final de audio ---")
        compose_audio(wav_dir, output_file)

    elif output_mode == 'midi':
        midi_dir = intermediate_dir / "2_midi_files"
        midi_dir.mkdir(parents=True, exist_ok=True)
        # La síntesis MIDI es muy rápida, no siempre necesita paralelización
        for json_file in tqdm(json_files, desc="Sintetizando MIDI"):
            midi_synthesis_worker(json_file, midi_dir, args)
        print("Los archivos MIDI individuales han sido creados. La composición final no aplica para MIDI.")


    print(f"\nPipeline completado! Revisa la carpeta: {intermediate_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline completo para sonificación de imágenes.")
    # Argumentos principales
    parser.add_argument("--input-folder", required=True)
    parser.add_argument("--output-file", required=True, help="Ruta del archivo de salida (.wav para modo WAV, no se usa para MIDI).")
    parser.add_argument("--output-mode", default="wav", choices=["wav", "midi"])
    
    # Argumentos WAV
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--scale", default="pentatonic")
    parser.add_argument("--mode", default="rgb_instrument")
    parser.add_argument("--waveform", default="sine")

    # Argumentos MIDI
    parser.add_argument("--midi-r-channel", default=1)
    parser.add_argument("--midi-g-channel", default=2)
    parser.add_argument("--midi-b-channel", default=3)
    
    args = parser.parse_args()
    run_full_pipeline(args)