import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask Secret Key for session management and security
    # IMPORTANT: Change this to a strong, randomly generated key in production.
    # It's best to get this from an environment variable (e.g., using python -c 'import os; print(os.urandom(24))')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_fallback_secret_key_that_is_long_and_random_for_dev_only'

    # Google OAuth Credentials
    # These should ideally be in your .env file and loaded via os.environ.get()
    # For local development, using provided values as fallbacks for simplicity.
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '792528799833-tafb5c8mdngola2r0hed15bhl0etfelv.apps.googleusercontent.com')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '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')

    # This will be overridden in app.py for consistency with local setup,
    # but it's good to define it here if you were to have different environments.
    # For local development, this exact URI MUST match Google Cloud Console.
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5000/auth/google/callback')

    # Enable debug mode for local development (important for detailed logging)
    DEBUG = True