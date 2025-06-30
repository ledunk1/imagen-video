import os
import re
from typing import Dict, Optional, Tuple

class EnvService:
    def __init__(self, env_file_path: str = '.env'):
        self.env_file_path = env_file_path
        self.ensure_env_file_exists()
    
    def ensure_env_file_exists(self):
        """Pastikan file .env ada, jika tidak buat dari .env.example"""
        if not os.path.exists(self.env_file_path):
            if os.path.exists('.env.example'):
                # Copy dari .env.example
                with open('.env.example', 'r') as example_file:
                    content = example_file.read()
                with open(self.env_file_path, 'w') as env_file:
                    env_file.write(content)
            else:
                # Buat file .env kosong dengan template dasar
                default_content = """# Flask Video Generator AI - Environment Variables
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_flask_secret_key_here

# Optional Settings
DEFAULT_IMAGE_MODEL=flux
DEFAULT_GEMINI_MODEL=gemini-1.5-flash-latest
DEFAULT_TIMEOUT=300
"""
                with open(self.env_file_path, 'w') as env_file:
                    env_file.write(default_content)
    
    def read_env_vars(self) -> Dict[str, str]:
        """Membaca semua environment variables dari file .env"""
        env_vars = {}
        
        if not os.path.exists(self.env_file_path):
            return env_vars
            
        with open(self.env_file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
        
        return env_vars
    
    def update_env_var(self, key: str, value: str) -> Tuple[bool, str]:
        """Update atau tambah environment variable"""
        try:
            # Read current content
            lines = []
            key_found = False
            
            if os.path.exists(self.env_file_path):
                with open(self.env_file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
            
            # Update existing key or mark for addition
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#'):
                    if '=' in line:
                        existing_key = line.split('=', 1)[0].strip()
                        if existing_key == key:
                            lines[i] = f"{key}={value}\n"
                            key_found = True
                            break
            
            # Add new key if not found
            if not key_found:
                lines.append(f"{key}={value}\n")
            
            # Write back to file
            with open(self.env_file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            
            return True, f"Environment variable '{key}' berhasil diperbarui."
            
        except Exception as e:
            return False, f"Error updating environment variable: {str(e)}"
    
    def delete_env_var(self, key: str) -> Tuple[bool, str]:
        """Hapus environment variable"""
        try:
            if not os.path.exists(self.env_file_path):
                return False, "File .env tidak ditemukan."
            
            lines = []
            key_found = False
            
            with open(self.env_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Remove the key
            new_lines = []
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    if '=' in line:
                        existing_key = line.split('=', 1)[0].strip()
                        if existing_key == key:
                            key_found = True
                            continue  # Skip this line (delete it)
                new_lines.append(line)
            
            if not key_found:
                return False, f"Environment variable '{key}' tidak ditemukan."
            
            # Write back to file
            with open(self.env_file_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)
            
            return True, f"Environment variable '{key}' berhasil dihapus."
            
        except Exception as e:
            return False, f"Error deleting environment variable: {str(e)}"
    
    def get_env_var(self, key: str) -> Optional[str]:
        """Dapatkan nilai environment variable tertentu"""
        env_vars = self.read_env_vars()
        return env_vars.get(key)
    
    def validate_env_vars(self) -> Dict[str, str]:
        """Validasi environment variables yang penting"""
        env_vars = self.read_env_vars()
        issues = {}
        
        # Check required variables
        required_vars = ['GEMINI_API_KEY', 'SECRET_KEY']
        for var in required_vars:
            if var not in env_vars or not env_vars[var] or env_vars[var] == f'your_{var.lower()}_here':
                issues[var] = f"Variable '{var}' belum diset atau masih menggunakan nilai default."
        
        return issues
    
    def backup_env_file(self) -> Tuple[bool, str]:
        """Buat backup file .env"""
        try:
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f".env.backup_{timestamp}"
            
            shutil.copy2(self.env_file_path, backup_path)
            return True, f"Backup berhasil dibuat: {backup_path}"
            
        except Exception as e:
            return False, f"Error creating backup: {str(e)}"