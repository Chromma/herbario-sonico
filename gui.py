# gui.py (Versión 9 - Corrección de proceso y fallo .exe)
import customtkinter as ctk
from tkinter import filedialog
import threading
import sys
import multiprocessing
from pathlib import Path
from types import SimpleNamespace
from pipeline import run_full_pipeline # Importación de función pipeline directo

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuración de la Ventana Principal ---
        self.title("Herbario Sónico")
        self.geometry("500x1000")
        ctk.set_appearance_mode("dark")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Frame para selección de archivos ---
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.file_frame.grid_columnconfigure(1, weight=1)
        
        self.input_folder_label = ctk.CTkLabel(self.file_frame, text="Carpeta de Imágenes:")
        self.input_folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.input_folder_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Selecciona una carpeta...")
        self.input_folder_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.input_folder_button = ctk.CTkButton(self.file_frame, text="Buscar...", width=100, command=self.select_input_folder)
        self.input_folder_button.grid(row=0, column=2, padx=10, pady=10)

        self.output_label = ctk.CTkLabel(self.file_frame, text="Archivo/Carpeta Salida:")
        self.output_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.output_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Selecciona una ruta de salida...")
        self.output_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.output_button = ctk.CTkButton(self.file_frame, text="Guardar en...", width=100, command=self.select_output)
        self.output_button.grid(row=1, column=2, padx=10, pady=10)

        # --- Pestañas para los Modos de Salida ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.tab_view.add("Audio (WAV)")
        self.tab_view.add("Partitura (MIDI)")

        # --- Controles de la Pestaña WAV ---
        self.wav_tab = self.tab_view.tab("Audio (WAV)")
        self.wav_tab.grid_columnconfigure(1, weight=1)
        
        self.duration_label = ctk.CTkLabel(self.wav_tab, text="Duración por Imagen (s):")
        self.duration_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.duration_entry = ctk.CTkEntry(self.wav_tab, placeholder_text="Ej: 10.0")
        self.duration_entry.insert(0, "10.0")
        self.duration_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.scale_label = ctk.CTkLabel(self.wav_tab, text="Escala Musical:")
        self.scale_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.scale_menu = ctk.CTkOptionMenu(self.wav_tab, values=["pentatonic", "major", "minor", "raw"])
        self.scale_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.mode_label = ctk.CTkLabel(self.wav_tab, text="Modo de Síntesis:")
        self.mode_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.mode_menu = ctk.CTkOptionMenu(self.wav_tab, values=["rgb_instrument", "brightness"])
        self.mode_menu.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.waveform_label = ctk.CTkLabel(self.wav_tab, text="Forma de Onda:")
        self.waveform_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.waveform_menu = ctk.CTkOptionMenu(self.wav_tab, values=["sine", "sawtooth", "square"])
        self.waveform_menu.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # --- Controles de la Pestaña MIDI ---
        self.midi_tab = self.tab_view.tab("Partitura (MIDI)")
        self.midi_tab.grid_columnconfigure(1, weight=1)
        midi_channels = [str(i) for i in range(1, 17)]

        self.r_channel_label = ctk.CTkLabel(self.midi_tab, text="Canal MIDI para Rojo:")
        self.r_channel_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.r_channel_menu = ctk.CTkOptionMenu(self.midi_tab, values=midi_channels); self.r_channel_menu.set("1")
        self.r_channel_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.g_channel_label = ctk.CTkLabel(self.midi_tab, text="Canal MIDI para Verde:")
        self.g_channel_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.g_channel_menu = ctk.CTkOptionMenu(self.midi_tab, values=midi_channels); self.g_channel_menu.set("2")        
        self.g_channel_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.b_channel_label = ctk.CTkLabel(self.midi_tab, text="Canal MIDI para Azul:")
        self.b_channel_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.b_channel_menu = ctk.CTkOptionMenu(self.midi_tab, values=midi_channels); self.b_channel_menu.set("3")        
        self.b_channel_menu.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        # Mapeo de Velocidad
        self.velocity_label = ctk.CTkLabel(self.midi_tab, text="Velocity (Fuerza):")
        self.velocity_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.velocity_menu = ctk.CTkOptionMenu(self.midi_tab, values=["brightness", "fixed"])
        self.velocity_menu.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        self.fixed_velocity_entry = ctk.CTkEntry(self.midi_tab, placeholder_text="Valor (0-127)"); self.fixed_velocity_entry.insert(0, "100")
        self.fixed_velocity_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # Mapeo de Control Change
        self.cc_label = ctk.CTkLabel(self.midi_tab, text="CC#1 (Mod Wheel):")
        self.cc_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.cc_menu = ctk.CTkOptionMenu(self.midi_tab, values=["saturation", "brightness", "none"])
        self.cc_menu.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # Mapeo de Pitch Bend
        self.pitch_bend_label = ctk.CTkLabel(self.midi_tab, text="Pitch Bend:")
        self.pitch_bend_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.pitch_bend_menu = ctk.CTkOptionMenu(self.midi_tab, values=["brightness_change", "none"])
        self.pitch_bend_menu.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # --- Botón Principal y Barra de Estado ---
        self.generate_button = ctk.CTkButton(self, text="Generar Composición", height=40, command=self.start_generation_thread)
        self.generate_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # --- Barra de proceso ---
        self.progress_label = ctk.CTkLabel(self, text="", text_color="gray", font=("Courier", 10))
        self.progress_label.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="w")
        
        self.status_textbox = ctk.CTkTextbox(self, height=100, wrap="word")
        self.status_textbox.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.update_status("Listo.", clear=True)

    # --- Funciones de la Interfaz ---
    def select_input_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_folder_entry.delete(0, "end")
            self.input_folder_entry.insert(0, folder_path)

    def select_output(self):
        # La función del botón cambia según la pestaña activa
        selected_tab = self.tab_view.get()
        if selected_tab == "Audio (WAV)":
            file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        else: # MIDI
            file_path = filedialog.askdirectory(title="Seleccionar carpeta para archivos MIDI")
        if file_path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, file_path)

    def update_status(self, text, clear=False):
        if clear: self.status_textbox.delete("1.0", "end")
        # Si el texto es de progreso, reemplaza la última línea
        current_text = self.status_textbox.get("1.0", "end-1c")
        if str(text).startswith("Sintetizando archivo"):
            lines = current_text.split('\n')
            if lines and lines[-1].startswith("Sintetizando archivo"):
                self.status_textbox.delete(f"{len(lines)}.0", "end")
                self.status_textbox.insert("end", str(text))
            else:
                self.status_textbox.insert("end", "\n" + str(text))
        else:
            self.status_textbox.insert("end", "\n" + str(text))
        self.status_textbox.see("end")

    def start_generation_thread(self):
        self.generate_button.configure(state="disabled")
        self.update_status("Iniciando proceso...", clear=True)
        threading.Thread(target=self.run_pipeline_direct).start()

    def run_pipeline_direct(self):
        try:
            args = SimpleNamespace() # Construir un objeto 'args' para pasar a la función del pipeline
            args.input_folder = self.input_folder_entry.get()
            output_path_str = self.output_entry.get()

            if not args.input_folder or not output_path_str:
                self.after(0, self.update_status, "Error: Por favor, selecciona la carpeta de entrada y la ruta de salida.")
                self.generate_button.configure(state="normal"); return
            
            selected_tab = self.tab_view.get()
            if selected_tab == "Audio (WAV)":
                args.output_mode = 'wav'
            else: # "Partitura (MIDI)"
                args.output_mode = 'midi'
            
            if args.output_mode == 'wav':
                args.output_file = output_path_str
                args.duration = float(self.duration_entry.get())
                args.scale = self.scale_menu.get()
                args.mode = self.mode_menu.get()
                args.waveform = self.waveform_menu.get()
            else: # midi
                args.output_file = str(Path(output_path_str) / "composition.mid")
                args.midi_r_channel = self.r_channel_menu.get()
                args.midi_g_channel = self.g_channel_menu.get()
                args.midi_b_channel = self.b_channel_menu.get()
                args.midi_velocity_map = self.velocity_menu.get()
                args.midi_fixed_velocity = int(self.fixed_velocity_entry.get())
                args.midi_cc_map = self.cc_menu.get()
                args.midi_pitch_bend_map = self.pitch_bend_menu.get()

            run_full_pipeline(args, status_callback=lambda text: self.after(0, self.update_status, text))
        except Exception as e:
            self.after(0, self.update_status, f"Error inesperado: {e}")
        
        self.generate_button.configure(state="normal")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
