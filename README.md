
# 🎵 MusiPal – AI Music Generator

![MusiPal Logo](static/images/Musipal.png)

**MusiPal** is a web application that lets users create unique, royalty-free music by simply describing what they want to hear. Powered by Meta's **MusicGen** model, it translates text prompts into audio – perfect for musicians, content creators, and anyone exploring music creation.

This project was developed as a **3rd‑year school project** by a team of four, with the main developer taking charge of model integration, backend logic, and system architecture.

---

## ✨ Features

- 🔑 User authentication (signup/login with session management)
- 🎼 Generate music from text prompts (5–60 seconds)
- 🎚️ Adjustable music length via slider
- 💾 Automatic storage of generated tracks with metadata
- 📝 Edit track title, artist, and cover image (ID3 tags embedded in MP3)
- 🖼️ Personal profile page showing your music history
- 🤖 Built‑in chatbot with keyword‑based responses (typo‑tolerant)
- 📱 Fully responsive design

---

## 🛠️ Tech Stack

| Layer        | Technologies                                                                 |
|--------------|------------------------------------------------------------------------------|
| **Backend**  | Python, Flask, SQLite, Transformers (Hugging Face), PyTorch, Torchaudio     |
| **Frontend** | HTML, CSS, JavaScript (vanilla)                                              |
| **Audio**    | Pydub, Mutagen (MP3/ID3), FFmpeg                                            |
| **Model**    | Meta's MusicGen (conditional generation)                                    |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and added to your system PATH (or set manually in `app.py`)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/musipal.git
   cd musipal
   ```

2. **Set up a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Place the MusicGen model**
   - Download the model files and place them in a folder named `music_gen/` in the project root.
   - The app expects the following structure (or adjust the path in `app.py`):
     ```
     music_gen/
       ├── config.json
       ├── model.safetensors
       ├── ...
     ```

5. **Set up the database**
   - The app will automatically create `UserDatabase.db` on first run.
   - Ensure the `users` and `MusicHistory` tables exist (the SQL schema is handled by the app).

6. **Configure FFmpeg**
   - If FFmpeg is not in your PATH, edit `app.py` and set the converter path manually (around line 75):
     ```python
     AudioSegment.converter = "C:\\path\\to\\ffmpeg.exe"
     ```

7. **Run the app**
   ```bash
   python app.py
   ```
   Then open `http://127.0.0.1:5000` in your browser.

---

## 📁 Project Structure
musipal/
├── app.py                 # Main Flask application
├── config.py              # Environment configuration (OAuth, secrets)
├── requirements.txt       # Python dependencies
├── UserDatabase.db        # SQLite database (auto‑created)
├── music_gen/             # MusicGen model folder (not included in repo)
├── static/
│   ├── style.css          # Global styles
│   ├── images/            # Logos, favicon
│   ├── user_data/         # User‑specific audio files (created on the fly)
│   └── cover_images/      # Uploaded cover images
├── templates/
│   ├── index.html
│   ├── musicgen.html
│   ├── login.html
│   ├── profile.html
│   ├── about.html
│   └── base.html
└── README.md


---

## 👥 Team & Contributions

- **Johnrick** – Main Developer / Tech Lead  
  *Integrated the MusicGen model, built the Flask backend, connected frontend with APIs, handled file processing and metadata embedding.*

- **Ken** – UI/UX Designer  
  *Designed the overall look, created wireframes, and ensured a responsive, intuitive interface.*

- **Miiko** – Project Manager / QA Tester  
  *Managed tasks, scheduled meetings, performed testing, and reported bugs.*

- **Ralph** – Documentation Lead  
  *Wrote technical and user documentation, maintained setup guides and version tracking.*

> *Note: The main developer contributed least to the visual design; the UI was primarily crafted by Ken.*

---

## ⚠️ Important Notes

- The MusicGen model is **large** (~several GB) and must be downloaded separately. We cannot include it in the repository due to size limits.
- This is a **student project** – it is not intended for production use without further security hardening (e.g., secure secret keys, HTTPS, rate limiting).
- The chatbot uses a simple keyword‑matching system with Levenshtein distance for typo tolerance, not an LLM.
- The `node_modules` folder (or any equivalent large dependency directory) is not included in this repository because it contains thousands of files and is not suitable for version control. If your setup requires frontend build tools, install the necessary packages via your package manager (e.g., `npm install`) – otherwise, this note does not apply to this Python‑based project.

---

## 📜 License

This project is for educational purposes only. All generated music is royalty‑free, but the source code is not licensed for commercial use.

---

## 🙏 Acknowledgments

- [Meta's MusicGen](https://huggingface.co/facebook/musicgen-small) and Hugging Face for the model.
- The Flask, PyTorch, and Transformers communities for their excellent libraries.

---

**Happy music making! 🎶**
