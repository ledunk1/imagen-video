import os
from config import Config

class SimpleAPIService:
    def __init__(self):
        self.api_keys_file = Config.API_KEYS_FILE
        self.ensure_api_file_exists()
    
    def ensure_api_file_exists(self):
        """Pastikan file API keys ada"""
        os.makedirs(os.path.dirname(self.api_keys_file), exist_ok=True)
        if not os.path.exists(self.api_keys_file):
            with open(self.api_keys_file, 'w') as f:
                f.write("# API Keys Configuration\n")
                f.write("# Format: KEY_NAME=your_api_key_here\n")
                f.write("GEMINI_API_KEY=\n")
    
    def get_api_key(self, key_name):
        """Ambil API key dari file"""
        try:
            if not os.path.exists(self.api_keys_file):
                return None
                
            with open(self.api_keys_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key_name}="):
                        value = line.split('=', 1)[1].strip()
                        return value if value else None
            return None
        except Exception as e:
            print(f"Error reading API key: {e}")
            return None
    
    def save_api_key(self, key_name, key_value):
        """Simpan API key ke file"""
        try:
            lines = []
            key_found = False
            
            if os.path.exists(self.api_keys_file):
                with open(self.api_keys_file, 'r') as f:
                    lines = f.readlines()
            
            # Update existing key or add new one
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key_name}="):
                    lines[i] = f"{key_name}={key_value}\n"
                    key_found = True
                    break
            
            if not key_found:
                lines.append(f"{key_name}={key_value}\n")
            
            with open(self.api_keys_file, 'w') as f:
                f.writelines(lines)
            
            return True, "API key berhasil disimpan"
        except Exception as e:
            return False, f"Error saving API key: {str(e)}"
    
    def get_all_keys(self):
        """Ambil semua API keys"""
        keys = {}
        try:
            if os.path.exists(self.api_keys_file):
                with open(self.api_keys_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            keys[key.strip()] = value.strip()
            return keys
        except Exception as e:
            print(f"Error reading all keys: {e}")
            return {}