import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    DATA_FOLDER = 'data'
    IMAGES_FOLDER = os.path.join('data', 'images')  # Folder permanen untuk gambar
    # Hapus batasan upload
    # MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # Batas upload 32 MB
    PROMPT_FILE_PATH = os.path.join('data', 'prompts.json')
    
    # Simple API Key Storage
    API_KEYS_FILE = os.path.join('data', 'api_keys.txt')