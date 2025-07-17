# gui.py (Versión 5 - Corregido el error de codificación Unicode)
import customtkinter as ctk
from tkinter import filedialog
import subprocess
import threading
import sys
import locale 

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuración de la Ventana Principal ---
        self.title("Herbario Sónico")
        self.geometry("500x600")
        ctk.set_appearance_mode("dark")
        self.grid_columnconfigure(1, weight=1)

        # --- Widgets de la Interfaz ---
        self.input_folder_label = ctk.CTkLabel(self, text="Carpeta de Imágenes:")
        self.input_folder_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.input_folder_entry = ctk.CTkEntry(self, placeholder_text="Selecciona una carpeta...")
        self.input_folder_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="ew")
        self.input_folder_button = ctk.CTkButton(self, text="Buscar...", width=100, command=self.select_input_folder)
        self.input_folder_button.grid(row=0, column=2, padx=20, pady=(20, 5))

        self.output_file_label = ctk.CTkLabel(self, text="Archivo de Salida:")
        self.output_file_label.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.output_file_entry = ctk.CTkEntry(self, placeholder_text="Selecciona dónde guardar...")
        self.output_file_entry.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        self.output_file_button = ctk.CTkButton(self, text="Guardar como...", width=100, command=self.select_output_file)
        self.output_file_button.grid(row=1, column=2, padx=20, pady=5)
        
        self.params_frame = ctk.CTkFrame(self)
        self.params_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=20, sticky="ew")
        self.params_frame.grid_columnconfigure(1, weight=1)

        self.duration_label = ctk.CTkLabel(self.params_frame, text="Duración por Imagen (s):")
        self.duration_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.duration_entry = ctk.CTkEntry(self.params_frame)
        self.duration_entry.insert(0, "10.0")
        self.duration_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.scale_label = ctk.CTkLabel(self.params_frame, text="Escala Musical:")
        self.scale_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.scale_menu = ctk.CTkOptionMenu(self.params_frame, values=["pentatonic", "major", "minor", "raw"])
        self.scale_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.mode_label = ctk.CTkLabel(self.params_frame, text="Modo de Síntesis:")
        self.mode_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.mode_menu = ctk.CTkOptionMenu(self.params_frame, values=["rgb_instrument", "brightness"])
        self.mode_menu.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.waveform_label = ctk.CTkLabel(self.params_frame, text="Forma de Onda:")
        self.waveform_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.waveform_menu = ctk.CTkOptionMenu(self.params_frame, values=["sine", "sawtooth", "square"])
        self.waveform_menu.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        self.generate_button = ctk.CTkButton(self, text="Generar Composición", height=40, command=self.start_generation_thread)
        self.generate_button.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")

        self.status_textbox = ctk.CTkTextbox(self, height=100, wrap="word")
        self.status_textbox.grid(row=4, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="nsew")
        self.update_status("Listo.", clear=True)

    def select_input_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_folder_entry.delete(0, "end")
            self.input_folder_entry.insert(0, folder_path)

    def select_output_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if file_path:
            self.output_file_entry.delete(0, "end")
            self.output_file_entry.insert(0, file_path)

    def update_status(self, text, clear=False):
        if clear: self.status_textbox.delete("1.0", "end")
        self.status_textbox.insert("end", text + "\n")
        self.status_textbox.see("end")

    def start_generation_thread(self):
        self.generate_button.configure(state="disabled")
        self.update_status("Iniciando proceso...", clear=True)
        thread = threading.Thread(target=self.run_pipeline)
        thread.start()

    def run_pipeline(self):
        input_folder = self.input_folder_entry.get()
        output_file = self.output_file_entry.get()
        if not input_folder or not output_file:
            self.after(0, self.update_status, "Error: Por favor, selecciona la carpeta de entrada y el archivo de salida.")
            self.generate_button.configure(state="normal")
            return
        command = [ sys.executable, "pipeline.py", "--input-folder", input_folder, "--output-file", output_file, "--duration", self.duration_entry.get(), "--scale", self.scale_menu.get(), "--mode", self.mode_menu.get(), "--waveform", self.waveform_menu.get() ]
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            # Usa la codificación preferida del sistema
            encoding=locale.getpreferredencoding(),
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        for line in iter(process.stdout.readline, ''):
            self.after(0, self.update_status, line.strip())
        process.wait()
        if process.returncode == 0:
            self.after(0, self.update_status, f"\n¡Completado! Archivo guardado en {output_file}")
        else:
            self.after(0, self.update_status, f"\nError: El proceso falló con código {process.returncode}.")
        self.generate_button.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()