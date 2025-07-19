# pipeline.py (Versión 8 - Manejo de errores en paralelo)
import argparse
import json
import multiprocessing
from pathlib import Path

# Importa las funciones principales de nuestros otros scripts
from scanner import analyze_image
from synthesizer import synthesize as synthesize_wav # Mayor claridad
from midi_synthesizer import synthesize_midi
from composer import compose_audio

# --- Workers para paralelización ---
def wav_synthesis_worker(json_file, wav_dir, args):
    try:
        with open(json_file, 'r') as f: data = json.load(f)
        output_path = wav_dir / json_file.with_suffix(".wav").name
        synthesize_wav(data, output_path, args.duration, args.scale, args.mode, args.waveform)
        return (True, f"Procesado: {json_file.name}")
    except Exception as e:
        return (False, f"Error en {json_file.name}: {e}")

def midi_synthesis_worker(json_file, midi_dir, args):
    try:
        with open(json_file, 'r') as f: data = json.load(f)
        output_path = midi_dir / json_file.with_suffix(".mid").name
        midi_params = {
            'r_channel': args.midi_r_channel, 'g_channel': args.midi_g_channel, 'b_channel': args.midi_b_channel,
            'velocity_map': args.midi_velocity_map, 'fixed_velocity': args.midi_fixed_velocity,
            'cc_map': args.midi_cc_map, 'pitch_bend_map': args.midi_pitch_bend_map
        }
        synthesize_midi(data, output_path, midi_params)
        return (True, f"Procesado: {json_file.name}")
    except Exception as e:
        return (False, f"Error en {json_file.name}: {e}")

def run_full_pipeline(args, status_callback=print):
    input_folder, output_file, output_mode = Path(args.input_folder), Path(args.output_file), args.output_mode
    intermediate_dir = output_file.parent / (output_file.stem + "_intermediate_files")
    json_dir = intermediate_dir / "1_json_data"
    json_dir.mkdir(parents=True, exist_ok=True)
    status_callback(f"Archivos intermedios se guardarán en: {intermediate_dir}")
    
    image_files = sorted(input_folder.glob('*.*'))
    if not image_files:
        status_callback(f"Error: No se encontraron imágenes en '{input_folder}'.")
        return

    status_callback(f"--- PASO 1 de 3: Analizando {len(image_files)} imagenes ---")
    for image_file in image_files:
        analyze_image(image_file, json_dir / image_file.with_suffix(".json").name)

    json_files = sorted(json_dir.glob('*.json'))
    status_callback(f"--- PASO 2 de 3: Sintetizando {len(json_files)} archivos en modo {output_mode} ---")

    results = []
    error_found = False
    with multiprocessing.Pool() as pool:
        worker_func = wav_synthesis_worker if output_mode == 'wav' else midi_synthesis_worker
        output_dir = intermediate_dir / ("2_wav_individual_sounds" if output_mode == 'wav' else "2_midi_files")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for json_file in json_files:
            results.append(pool.apply_async(worker_func, args=(json_file, output_dir, args)))

        total_tasks = len(results)
        for i, res in enumerate(results):
            status_callback(f"Sintetizando archivo {i+1} de {total_tasks}...")
            success, message = res.get()
            if not success:
                error_found = True
                status_callback(message) # Muestra el error específico
    
    # Si se encontró un error, detener el proceso aquí
    if error_found:
        status_callback("\nProceso detenido debido a errores en la síntesis.")
        return

    if output_mode == 'wav':
        status_callback(f"--- PASO 3 de 3: Componiendo la pieza final de audio ---")
        compose_audio(output_dir, output_file)
    else:
        status_callback("Los archivos MIDI individuales han sido creados correctamente.")
    
    status_callback(f"\nPipeline completado! Revisa la carpeta de salida.")

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
    parser.add_argument("--midi-velocity-map", default="brightness", choices=["brightness", "fixed"])
    parser.add_argument("--midi-fixed-velocity", type=int, default=100)
    parser.add_argument("--midi-cc-map", default="saturation", choices=["saturation", "brightness", "none"])
    parser.add_argument("--midi-pitch-bend-map", default="brightness_change", choices=["brightness_change", "none"])
    
    args = parser.parse_args()
    run_full_pipeline(args)