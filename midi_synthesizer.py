# midi_synthesizer.py
import mido
import numpy as np

def create_midi_track(pixel_data, h, w, params):
    track = mido.MidiTrack()
    
    # Mapeo de canales de color a canales MIDI
    channel_map = {
        'r': int(params['r_channel']) - 1,
        'g': int(params['g_channel']) - 1,
        'b': int(params['b_channel']) - 1,
    }

    ticks_per_time_step = 480 // 4 # Duración de una semicorchea por cada columna de píxeles
    last_brightness = {} # Para calcular el pitch bend

    for item in pixel_data:
        time_step = item["time_step"]
        pixels = item["pixels"]
        
        # --- Evento de Control Change (CC) ---
        # Calcula la saturación promedio de la columna de píxeles
        if params['cc_map'] != 'none':
            values_for_cc = []
            for p in pixels:
                if params['cc_map'] == 'saturation':
                    r, g, b = [x / 255.0 for x in p['rgb']]
                    cmax, cmin = max(r, g, b), min(r, g, b)
                    if cmax != cmin: values_for_cc.append((cmax - cmin) / (1 - abs(cmax + cmin - 1)))
                elif params['cc_map'] == 'brightness':
                    values_for_cc.append(p['brightness'] / 255.0)
            
            if values_for_cc:
                cc_value = int(np.mean(values_for_cc) * 127)
                track.append(mido.Message('control_change', channel=channel_map['r'], control=1, value=cc_value, time=0))

        # --- Eventos de Nota (Note On/Off) ---
        for i, p in enumerate(pixels):
            y, brightness, rgb = p["y"], p["brightness"], p["rgb"]
            
            # Determinar el canal por el color dominante
            dominant_color_index = np.argmax(rgb)
            if dominant_color_index == 0: channel = channel_map['r']
            elif dominant_color_index == 1: channel = channel_map['g']
            else: channel = channel_map['b']

            # Nota (Pitch): 127 notas posibles, mapeadas a la altura
            note_pitch = 127 - int((y / h) * 127)
            
            # --- Mapeo de Velocidad ---
            # Velocidad (Velocity): Mapeada al brillo
            if params['velocity_map'] == 'brightness':
                velocity = min(127, int((brightness / 255.0) * 127))
            else: # fixed
                velocity = int(params['fixed_velocity'])

            duration_ticks = ticks_per_time_step // 2

            # --- Evento de Pitch Bend ---
            # Si hay un cambio brusco de brillo respecto al píxel anterior en el mismo canal
            if params['pitch_bend_map'] == 'brightness_change':
                if last_brightness.get(channel) and abs(brightness - last_brightness[channel]) > 50:
                    bend_amount = int(((brightness - last_brightness[channel]) / 255.0) * 4096) + 8192
                    track.append(mido.Message('pitchwheel', channel=channel, pitch=bend_amount, time=0))
            
            track.append(mido.Message('note_on', channel=channel, note=note_pitch, velocity=velocity, time=ticks_per_time_step if i == 0 else 0))
            track.append(mido.Message('note_off', channel=channel, note=note_pitch, velocity=velocity, time=duration_ticks))
            
            last_brightness[channel] = brightness
            
    return track

# --- Función principal para crear y guardar el archivo MIDI. ---
def synthesize_midi(data, output_path, params):
    pixel_data = data["data"]
    h, w = data["image_height"], data["image_width"]
    
    mid = mido.MidiFile()
    track = create_midi_track(pixel_data, h, w, params)
    mid.tracks.append(track)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))