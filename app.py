from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from werkzeug.utils import secure_filename
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torch
import torchaudio
import base64
import io
import sqlite3
import os
import shutil
import logging
from datetime import datetime

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import torchaudio
import base64
import io # Needed for mutagen APIC (if embedding image)

# --- NEW IMPORTS FOR MP3 & METADATA ---
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC
# TCOM for Composer, TPE2 for Album Artist, TALB for Album (optional additions)

UPLOAD_FOLDER = os.path.join('static', 'cover_images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
DATABASE = 'UserDatabase.db'

app = Flask(__name__)
app.secret_key = 'Hello'   # Replace with a strong key
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load model once at startup
# Get the directory of the current script (e.g., app.py)
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the music_gen folder relative to the script
model_dir = os.path.join(current_script_dir, "music_gen")

processor = AutoProcessor.from_pretrained(model_dir)
model = MusicgenForConditionalGeneration.from_pretrained(model_dir)

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

FFMPEG_PATH = shutil.which('ffmpeg') # Try to find it automatically first

if FFMPEG_PATH:
    AudioSegment.converter = FFMPEG_PATH
    logging.info(f"ffmpeg found and set for pydub: {FFMPEG_PATH}")
else:
    # Fallback for when shutil.which fails or ffmpeg is not in PATH
    # You MUST replace this with your actual ffmpeg.exe or ffmpeg binary path
    # Example for Windows:
    # AudioSegment.converter = "C:\\ffmpeg\\bin\\ffmpeg.exe"
    # Example for macOS/Linux:
    # AudioSegment.converter = "/usr/local/bin/ffmpeg"

    # As a last resort, if you know where it is, hardcode it.
    # But if it's not found by shutil.which, it might mean the environment is messed up.
    logging.error("ffmpeg not found in system PATH. Please ensure it's installed and accessible.")
    # If you hardcode, make sure to uncomment this and set the correct path:
    # AudioSegment.converter = "YOUR_EXACT_FFMPEG_EXECUTABLE_PATH_HERE"
    AudioSegment.converter = "C:\Program Files\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

# ------------------ ROUTES ------------------

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html', logged_in=False)
    return render_template('index.html', logged_in=True)

@app.route('/musicgen')
def musicgen():
    # Ensure user folder exists when accessing musicgen page
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_folder = os.path.join('static', 'user_data', f"user_{session['user_id']}")
    os.makedirs(user_folder, exist_ok=True)  # Create user folder if it doesn't exist

    return render_template('musicgen.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        if user and user[3] == password:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('index'))  # Redirect to home page with profile button
        else:
            flash("Invalid credentials")
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    signup_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, email, password, signup_date) VALUES (?, ?, ?, ?)",
                   (username, email, password, signup_date))
    conn.commit()

    # Get the user ID of the new user
    user_id = cursor.lastrowid

    # Create user folder for storing generated music
    user_folder = os.path.join('static', 'user_data', f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    flash("Signup successful! You can now log in.")
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    # Updated SELECT statement to include new columns
    cursor.execute("SELECT prompt, audio_path, gen_date, music_name, artist, cover_image, music_id FROM MusicHistory WHERE user_id=? ORDER BY gen_date DESC", (user_id,))
    music_history = cursor.fetchall()

    return render_template('profile.html', username=session['username'], music_history=music_history)

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
def generate_music():
    if 'user_id' not in session:
        logging.warning("User not logged in during music generation attempt.")
        return jsonify({"error": "User not logged in"}), 401

    conn = None
    path_to_store_in_db = None
    wav_path = None # Ensure wav_path is defined for finally block cleanup

    try:
        data = request.json
        prompt = data.get('prompt', '')
        time_length = min(int(data.get('timeLength', 30)), 60)

        logging.info(f"Received prompt: '{prompt}', time: {time_length} seconds for user {session.get('user_id')}")

        inputs = processor(text=[prompt], return_tensors="pt")
        sample_rate = 16000
        estimated_tokens_per_second = 28
        max_new_tokens = time_length * estimated_tokens_per_second

        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

        user_audio_folder = os.path.join('static', 'user_data', f"user_{session['user_id']}")
        os.makedirs(user_audio_folder, exist_ok=True)
        logging.info(f"User audio folder ensured: {user_audio_folder}")

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        wav_filename = f"{timestamp}.wav"
        wav_path = os.path.join(user_audio_folder, wav_filename)
        
        mp3_filename = f"{timestamp}.mp3"
        mp3_path = os.path.join(user_audio_folder, mp3_filename)
        mp3_path_rel = os.path.relpath(mp3_path, 'static').replace("\\", "/")

        logging.info(f"Saving temporary WAV to: {wav_path}")
        torchaudio.save(wav_path, audio_values[0], sample_rate=sample_rate)
        logging.info("WAV file saved successfully.")

        # --- Attempt to convert WAV to MP3 and embed initial metadata ---
        try:
            logging.info(f"Attempting to convert WAV to MP3: {wav_path} -> {mp3_path}")
            audio_segment = AudioSegment.from_wav(wav_path)
            audio_segment.export(mp3_path, format="mp3")
            logging.info("MP3 conversion successful.")

            logging.info("Embedding initial metadata into MP3.")
            audio_mp3 = MP3(mp3_path, ID3=ID3)
            # If tags don't exist, this line ensures they are added.
            # While `MP3(..., ID3=ID3)` generally creates tags if missing,
            # explicit addition before setting can prevent issues in edge cases.
            if audio_mp3.tags is None:
                audio_mp3.add_tags() 

            # Set initial title (from prompt) and artist (default)
            audio_mp3.tags.add(TIT2(encoding=3, text=prompt))
            audio_mp3.tags.add(TPE1(encoding=3, text=u"AI Generated MusiPal"))
            audio_mp3.save()
            logging.info("Initial metadata embedded successfully.")

            path_to_store_in_db = mp3_path_rel
            
            # Remove temporary WAV file after successful MP3 creation
            if os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                    logging.info(f"Removed temporary WAV file: {wav_path}")
                except OSError as e:
                    logging.warning(f"Could not remove temporary WAV file {wav_path}: {e}")

        except Exception as e:
            logging.error(f"Error during MP3 conversion or metadata embedding. Falling back to WAV. Error: {e}", exc_info=True)
            path_to_store_in_db = os.path.relpath(wav_path, 'static').replace("\\", "/")
            logging.info(f"Storing WAV path in DB: {path_to_store_in_db}")

        if not path_to_store_in_db:
            path_to_store_in_db = os.path.relpath(wav_path, 'static').replace("\\", "/")
            logging.error("CRITICAL: path_to_store_in_db was not set, defaulting to WAV path.")

        conn = get_db()
        cursor = conn.cursor()
        logging.info(f"Inserting into MusicHistory: prompt='{prompt}', audio_path='{path_to_store_in_db}'")
        cursor.execute(
            "INSERT INTO MusicHistory (user_id, prompt, audio_path, gen_date, music_name, artist) VALUES (?, ?, ?, ?, ?, ?)",
            (session['user_id'], prompt, path_to_store_in_db, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), prompt, 'AI Generated MusiPal')
        )
        conn.commit()
        logging.info("Music history entry committed to DB.")

        file_to_return_path = mp3_path if os.path.exists(mp3_path) else wav_path
        logging.info(f"Returning audio from: {file_to_return_path}")

        with open(file_to_return_path, 'rb') as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({
            "audio": audio_base64,
            "audioPath": path_to_store_in_db
        })

    except Exception as e:
        logging.critical(f"A fatal error occurred in generate_music: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
        if wav_path and os.path.exists(wav_path) and (path_to_store_in_db is None or path_to_store_in_db != os.path.relpath(wav_path, 'static').replace("\\", "/")):
            try:
                os.remove(wav_path)
                logging.info(f"Cleaned up lingering temporary WAV file: {wav_path}")
            except OSError as e:
                logging.warning(f"Could not clean up temporary WAV file {wav_path}: {e}")

@app.route('/fix_paths')
def fix_paths():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT music_id, audio_path FROM MusicHistory")
    records = cursor.fetchall()

    for music_id, path in records:
        # Normalize slashes and strip leading 'static/' if present
        fixed_path = path.replace('\\', '/').replace('static/', '')

        cursor.execute("""
            UPDATE MusicHistory
            SET audio_path=?
            WHERE music_id=?""",
            (fixed_path, music_id)
        )

    conn.commit()
    return "Paths fixed!"

UPLOAD_FOLDER = os.path.join('static', 'cover_images') # Define an upload folder for cover images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/edit_music_metadata', methods=['POST'])
def edit_music_metadata():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    conn = None # Initialize conn to None for finally block
    try:
        music_id = request.form.get('music_id')
        music_name = request.form.get('music_name')
        artist = request.form.get('artist')
        
        conn = get_db()
        cursor = conn.cursor()

        # Get the current audio path (MP3) and existing cover image path from DB
        cursor.execute("SELECT audio_path, cover_image FROM MusicHistory WHERE music_id=? AND user_id=?", (music_id, session['user_id']))
        result = cursor.fetchone()
        if not result:
            return jsonify({"success": False, "error": "Music record not found or unauthorized"}), 404
        
        current_audio_rel_path, existing_cover_image_rel_path = result
        
        # Construct the full path to the audio file on the server
        audio_full_path = os.path.join('static', current_audio_rel_path)

        # Initialize new_cover_image_rel_path to the existing one
        new_cover_image_rel_path = existing_cover_image_rel_path 

        # Handle cover image upload
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                user_cover_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{session['user_id']}")
                os.makedirs(user_cover_folder, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S_')
                unique_filename = timestamp + filename
                file_path = os.path.join(user_cover_folder, unique_filename)
                file.save(file_path)
                new_cover_image_rel_path = os.path.relpath(file_path, 'static').replace("\\", "/")
                
                # Optional: Delete old cover image file if a new one is uploaded
                if existing_cover_image_rel_path and os.path.exists(os.path.join('static', existing_cover_image_rel_path)):
                    try:
                        os.remove(os.path.join('static', existing_cover_image_rel_path))
                    except OSError as e:
                        print(f"Error deleting old cover image: {e}")
            elif file.filename == '' and 'current_cover_image_kept' in request.form:
                    # This branch handles the case where the user submits the form
                    # but doesn't select a new file and implicitly wants to keep the old one.
                    # The JavaScript should signal this. For now, it's covered by initializing
                    # new_cover_image_rel_path with existing_cover_image_rel_path.
                    pass # No change needed to new_cover_image_rel_path
            # If the user explicitly wants to remove the image (e.g., clear button)
            # You'd need specific logic for that in the frontend and here (e.g., send 'null' for image)
            # For simplicity, if no file is uploaded, it defaults to the current image.
        
        # --- Update database with new metadata (including potentially new image path) ---
        cursor.execute("""
            UPDATE MusicHistory
            SET music_name=?, artist=?, cover_image=?
            WHERE music_id=? AND user_id=?
        """, (music_name, artist, new_cover_image_rel_path, music_id, session['user_id']))
        conn.commit()


        # --- Embed metadata into the MP3 file on the server ---
        if os.path.exists(audio_full_path):
            try:
                audio_mp3 = MP3(audio_full_path, ID3=ID3)

                # Update Title and Artist tags
                audio_mp3.tags.delall('TIT2') # Remove old title
                audio_mp3.tags.add(TIT2(encoding=3, text=music_name if music_name else u"Untitled"))
                
                audio_mp3.tags.delall('TPE1') # Remove old artist
                audio_mp3.tags.add(TPE1(encoding=3, text=artist if artist else u"Unknown Artist"))

                # Handle Cover Image embedding
                if new_cover_image_rel_path and os.path.exists(os.path.join('static', new_cover_image_rel_path)):
                    # Remove existing album art if any
                    if 'APIC:' in audio_mp3.tags:
                        del audio_mp3.tags['APIC:']

                    cover_full_path = os.path.join('static', new_cover_image_rel_path)
                    mime_type = f'image/{cover_full_path.split(".")[-1].lower()}'
                    
                    with open(cover_full_path, 'rb') as cover_f:
                        audio_mp3.tags.add(
                            APIC(
                                encoding=3,   # UTF-8
                                mime=mime_type,
                                type=3,       # 3 is for Front Cover
                                desc=u'Cover',
                                data=cover_f.read()
                            )
                        )
                else:
                    # If no cover image is specified or found, remove existing APIC tags
                    if 'APIC:' in audio_mp3.tags:
                        del audio_mp3.tags['APIC:']

                audio_mp3.save() # Save the ID3 tag changes to the MP3 file

            except Exception as e:
                print(f"Error embedding metadata into MP3 file: {e}")
                # This error doesn't prevent DB update but means file isn't fully updated
                # You might want to log this or notify the user.
        else:
            print(f"Audio file not found at {audio_full_path}. Metadata not embedded.")

        return jsonify({"success": True, "message": "Metadata updated successfully"})

    except Exception as e:
        print(f"Error updating music metadata: {e}")
        if conn: # Ensure connection exists before rolling back
            conn.rollback() # Rollback DB changes if an error occurs
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn: # Ensure the connection is closed
            conn.close() # Good practice to close DB connection if not using a context manager


@app.route('/test_ffmpeg')
def test_ffmpeg():
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return f"ffmpeg found at: {ffmpeg_path}"
    else:
        return "ffmpeg not found in PATH."
# ------------------ MAIN ------------------

if __name__ == '__main__':
    app.run(debug=True)