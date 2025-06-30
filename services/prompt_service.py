import json
import uuid
import os
from config import Config

def get_prompts():
    """Membaca semua prompt dari file JSON."""
    if not os.path.exists(Config.PROMPT_FILE_PATH):
        # Buat file default jika tidak ada
        default_prompts = [
            {"id": "default-cinematic-1", "name": "Default: Cinematic Shot", "prompt": "cinematic shot, dramatic lighting, high detail, 8k, photorealistic", "is_deletable": False},
            {"id": "default-anime-2", "name": "Default: Anime Style", "prompt": "anime style, vibrant colors, detailed background, key visual, by makoto shinkai", "is_deletable": False},
            {"id": "default-fantasy-3", "name": "Default: Digital Painting (Fantasy)", "prompt": "epic fantasy digital painting, beautiful landscape, detailed, trending on artstation, by greg rutkowski", "is_deletable": False}
        ]
        with open(Config.PROMPT_FILE_PATH, 'w') as f:
            json.dump(default_prompts, f, indent=2)
        return default_prompts
        
    with open(Config.PROMPT_FILE_PATH, 'r') as f:
        return json.load(f)

def save_prompts(prompts):
    """Menyimpan daftar prompt ke file JSON."""
    with open(Config.PROMPT_FILE_PATH, 'w') as f:
        json.dump(prompts, f, indent=2)

def get_prompt_by_id(prompt_id):
    """Mendapatkan teks prompt berdasarkan ID-nya."""
    prompts = get_prompts()
    for p in prompts:
        if p['id'] == prompt_id:
            return p['prompt']
    return None

def add_prompt(name, prompt_text):
    """Menambahkan prompt baru."""
    if not name or not prompt_text:
        return None, "Nama dan teks prompt tidak boleh kosong."
    prompts = get_prompts()
    new_prompt = {
        "id": str(uuid.uuid4()),
        "name": name,
        "prompt": prompt_text,
        "is_deletable": True
    }
    prompts.append(new_prompt)
    save_prompts(prompts)
    return new_prompt, "Prompt berhasil ditambahkan."

def update_prompt(prompt_id, name, prompt_text):
    """Memperbarui prompt yang sudah ada."""
    if not name or not prompt_text:
        return False, "Nama dan teks prompt tidak boleh kosong."
    prompts = get_prompts()
    for p in prompts:
        if p['id'] == prompt_id:
            if not p.get('is_deletable', True):
                return False, "Prompt default tidak dapat diubah."
            p['name'] = name
            p['prompt'] = prompt_text
            save_prompts(prompts)
            return True, "Prompt berhasil diperbarui."
    return False, "Prompt tidak ditemukan."

def delete_prompt(prompt_id):
    """Menghapus prompt."""
    prompts = get_prompts()
    prompt_to_delete = None
    for p in prompts:
        if p['id'] == prompt_id:
            if not p.get('is_deletable', True):
                return False, "Prompt default tidak dapat dihapus."
            prompt_to_delete = p
            break
    
    if prompt_to_delete:
        prompts.remove(prompt_to_delete)
        save_prompts(prompts)
        return True, "Prompt berhasil dihapus."
    return False, "Prompt tidak ditemukan."