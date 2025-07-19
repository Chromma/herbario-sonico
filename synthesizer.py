# synthesizer.py (Versión 7 - Secuencial y optimización Numba)
# --- Quick Index ---
# Posible variable para revisión. Más control */*
import argparse
import json
import numpy as np
from pathlib import Path
from scipy.io.wavfile import write
from scipy import signal
from tqdm import tqdm
from numba import jit

# --- Paletas de Frecuencias (Escalas Musicales) ---
# Frecuencia base: La (A4) = 220 Hz
BASE_FREQ = 220
SCALES = { "pentatonic": [0, 2, 4, 7, 9], "major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10] }

@jit(nopython=True, cache=True)
def get_note_freq_numba(note_index, scale_array, num_notes, base_freq):
    octave = note_index // num_notes
    note_in_scale = scale_array[note_index % num_notes]
    semitones = 12 * octave + note_in_scale
    return base_freq * (2**(semitones / 12.0))

@jit(nopython=True, cache=True)
def _numba_synthesis_loop(pixel_data, h, w, total_samples, scale_array, mode_is_rgb, waveform_is_sq, waveform_is_saw, scale_is_raw, sample_rate, duration_per_pixel):
    """Bucle principal de síntesis, compilado por Numba."""
    audio_buffer = np.zeros((total_samples, 2), dtype=np.float32)
    max_time_step = float(w)
    num_notes = len(scale_array)
    note_range = num_notes * 4

    for time_step, pixels in pixel_data:
        time_percent = time_step / max_time_step
        start_sample = int(time_percent * total_samples)
        
        for p in pixels:
            y, brightness, r, g, b = p
            
            if scale_is_raw:
                main_freq = 80.0 + ((h - y) / float(h)) * 1420.0
            else:
                note_index = int(((h - y) / float(h)) * note_range)
                main_freq = get_note_freq_numba(note_index, scale_array, num_notes, BASE_FREQ)
            
            note_duration_s = 0.01 + (brightness / 255.0) * duration_per_pixel
            note_duration_samples = int(sample_rate * note_duration_s)
            
            wave = np.zeros(note_duration_samples, dtype=np.float32)
            for i in range(note_duration_samples):
                t_sample = i / float(sample_rate)
                angle = 2 * np.pi * main_freq * t_sample
                if waveform_is_sq: wave[i] = 1.0 if np.sin(angle) > 0 else -1.0
                elif waveform_is_saw: wave[i] = 2 * (angle / (2 * np.pi) - np.floor(0.5 + angle / (2 * np.pi)))
                else: wave[i] = np.sin(angle)
            
            if not mode_is_rgb:
                wave *= (brightness / 255.0) * 0.7
            else:
                amp_r, amp_g, amp_b = (r/255.0)*0.33, (g/255.0)*0.33, (b/255.0)*0.33
                wave1 = np.zeros(note_duration_samples, dtype=np.float32)
                wave2 = np.zeros(note_duration_samples, dtype=np.float32)
                wave3 = np.zeros(note_duration_samples, dtype=np.float32)
                for i in range(note_duration_samples):
                    t_sample = i / float(sample_rate)
                    wave1[i] = amp_r * wave[i]
                    wave2[i] = amp_g * np.sin(2 * np.pi * main_freq * 2 * t_sample)
                    wave3[i] = amp_b * np.sin(2 * np.pi * main_freq * 1.5 * t_sample)
                wave = wave1 + wave2 + wave3

            end_sample = min(start_sample + note_duration_samples, total_samples)
            actual_length = end_sample - start_sample
            wave_to_add = wave[:actual_length]
            
            pan = (h - y) / float(h)
            
            for i in range(actual_length):
                audio_buffer[start_sample + i, 0] += wave_to_add[i] * (1 - pan)
                audio_buffer[start_sample + i, 1] += wave_to_add[i] * pan
    return audio_buffer

def synthesize(data, output_path: Path, duration_s: float, scale: str, mode: str, waveform: str):
    h, w = data["image_height"], data["image_width"]
    pixel_data_for_numba = []
    for item in data["data"]:
        pixels = [(p["y"], p["brightness"], p["rgb"][0], p["rgb"][1], p["rgb"][2]) for p in item["pixels"]]
        pixel_data_for_numba.append((item["time_step"], pixels))
    scale_array = np.array(SCALES.get(scale, []), dtype=np.int32)
    audio_buffer = _numba_synthesis_loop(pixel_data_for_numba, h, w, int(duration_s * 44100), scale_array, mode == 'rgb_instrument', waveform == 'square', waveform == 'sawtooth', scale == 'raw', 44100, 0.5)
    # La impresión ahora solo ocurre si se llama directamente
    # print("Normalizando y guardando el archivo .wav...")
    max_val = np.max(np.abs(audio_buffer))
    if max_val > 0: audio_buffer /= max_val
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write(output_path, 44100, (audio_buffer * 32767).astype(np.int16))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sintetiza audio desde archivos .json.")
    parser.add_argument("--input", type=str, required=True, help="Ruta al archivo .json o carpeta de archivos .json.")
    parser.add_argument("--output", type=str, required=True, help="Ruta a la carpeta de salida para los archivos .wav.")
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--scale", type=str, default="pentatonic", choices=["raw", "pentatonic", "major", "minor"])
    parser.add_argument("--mode", type=str, default="rgb_instrument", choices=["brightness", "rgb_instrument"])
    parser.add_argument("--waveform", type=str, default="sine", choices=["sine", "square", "sawtooth"])
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    files_to_process = []
    if input_path.is_dir():
        files_to_process.extend(sorted(input_path.glob('*.json')))
    elif input_path.is_file():
        files_to_process.append(input_path)

    if not files_to_process:
        print(f"No se encontraron archivos .json en '{input_path}'.")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Se encontraron {len(files_to_process)} archivo(s). Iniciando síntesis secuencial...")
        for json_file in tqdm(files_to_process, desc="Sintetizando"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                output_path = output_dir / json_file.with_suffix(".wav").name
                synthesize(data, output_path, args.duration, args.scale, args.mode, args.waveform)
            except Exception as e:
                print(f"Error procesando {json_file.name}: {e}")
        print("Proceso de síntesis completado.")