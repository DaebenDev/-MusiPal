import tkinter as tk
from tkinter import messagebox
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torch
import torchaudio
import threading

def generate_music():
    try:
        # Load the processor and model
        processor = AutoProcessor.from_pretrained(r"C:\Users\Ralph\OneDrive\Documents\1Drive\OneDrive\Desktop\music_gen\music_gen")
        model = MusicgenForConditionalGeneration.from_pretrained(r"C:\Users\Ralph\OneDrive\Documents\1Drive\OneDrive\Desktop\music_gen\music_gen")

        # Prepare the input prompt
        inputs = processor(text=["A calming piano melody"], return_tensors="pt")

        # Generate audio with a maximum length (limit the time)
        # Example: max_length=100 for shorter music (you can adjust this)
        audio_values = model.generate(**inputs, max_length=100)

        # Save the generated audio with a lower sample rate (e.g., 8000Hz instead of 16000Hz)
        torchaudio.save("generated_music.wav", audio_values[0], sample_rate=8000)

        # Close the splash screen and show success message
        splash_root.destroy()
        messagebox.showinfo("Success", "Music generated successfully!")

    except Exception as e:
        # Close the splash screen and show error message
        splash_root.destroy()
        messagebox.showerror("Error", f"An error occurred: {e}")

def show_loading_screen():
    global splash_root
    splash_root = tk.Tk()
    splash_root.title("Generating Music")
    splash_root.geometry("300x100")

    label = tk.Label(splash_root, text="Generating music, please wait...", font=("Helvetica", 12))
    label.pack(pady=20)

    splash_root.after(100, generate_music)
    splash_root.mainloop()

if __name__ == "__main__":
    threading.Thread(target=show_loading_screen).start()
