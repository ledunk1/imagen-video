from flask import Flask
from dotenv import load_dotenv
from config import Config
from routes.main_routes import main_bp
from routes.env_routes import env_bp
from routes.file_routes import file_bp
import os

# Muat environment variables
load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Pastikan folder upload, output, data, dan images ada
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
    os.makedirs(app.config['IMAGES_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['PROMPT_FILE_PATH']), exist_ok=True)

    # Daftarkan blueprint
    app.register_blueprint(main_bp)
    app.register_blueprint(env_bp)
    app.register_blueprint(file_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)