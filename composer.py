# composer.py (Versión 2 - Barra de Progreso)
import argparse
import numpy as np
from pathlib import Path
from scipy.io.wavfile import read, write
from tqdm import tqdm 

def compose_audio(input_dir: Path, output_file: Path):
    """
    Lee todos los archivos .wav de una carpeta, los concatena en orden
    y guarda el resultado como un único archivo .wav.
    """
    # Sorted() para asegurar el orden alfabético
    wav_files = sorted(input_dir.glob('*.wav'))
    
    if not wav_files:
        print(f"No se encontraron archivos .wav en la carpeta '{input_dir}'.")
        return

    print(f"Componiendo {len(wav_files)} archivos de audio...")
    
    all_audio_data = []
    final_sample_rate = None

    try:
        # --- Bucle principal con barra de progreso ---
        for wav_file in tqdm(wav_files, desc="Uniendo pistas"):
            sample_rate, data = read(wav_file)
            
            if final_sample_rate is None:
                final_sample_rate = sample_rate
            
            if sample_rate != final_sample_rate:
                print(f"Advertencia: El archivo {wav_file.name} tiene una frecuencia de muestreo diferente. Se omitirá.")
                continue
            
            all_audio_data.append(data)
        
        print("Concatenando datos de audio...")
        final_composition = np.concatenate(all_audio_data, axis=0)
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"Guardando composición final...")
        write(output_file, final_sample_rate, final_composition)
        
        print(f"Composición finalizada Guardada en: {output_file}")

    except Exception as e:
        print(f"Ocurrió un error durante la composición: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Une múltiples archivos .wav en una sola composición.")
    parser.add_argument("--input", type=str, required=True, help="Carpeta que contiene los archivos .wav a unir.")
    parser.add_argument("--output", type=str, required=True, help="Ruta del archivo .wav final de salida (ej. 'composiciones/planta_final.wav').")
    
    args = parser.parse_args()
    
    compose_audio(Path(args.input), Path(args.output))