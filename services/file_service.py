import os
import zipfile
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json

class FileService:
    def __init__(self, output_folder: str = 'outputs'):
        self.output_folder = output_folder
        self.images_folder = os.path.join('data', 'images')
        self.metadata_file = os.path.join(output_folder, 'metadata.json')
        self.ensure_folders()
    
    def ensure_folders(self):
        """Pastikan folder output dan images ada"""
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.images_folder, exist_ok=True)
    
    def get_file_list(self) -> List[Dict]:
        """Dapatkan daftar semua file (video dan gambar) dengan metadata"""
        files = []
        metadata = self.load_metadata()
        
        # Get video files from outputs folder
        if os.path.exists(self.output_folder):
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            
            for filename in os.listdir(self.output_folder):
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in video_extensions and not filename.startswith('.'):
                    filepath = os.path.join(self.output_folder, filename)
                    file_stats = os.stat(filepath)
                    
                    file_info = {
                        'filename': filename,
                        'file_type': 'video',
                        'extension': file_ext,
                        'size': file_stats.st_size,
                        'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
                        'created_at': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'modified_at': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'metadata': metadata.get(filename, {}),
                        'url': f'/outputs/{filename}'
                    }
                    files.append(file_info)
        
        # Get image files from data/images folder
        if os.path.exists(self.images_folder):
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            
            for session_folder in os.listdir(self.images_folder):
                session_path = os.path.join(self.images_folder, session_folder)
                if os.path.isdir(session_path):
                    for filename in os.listdir(session_path):
                        file_ext = os.path.splitext(filename)[1].lower()
                        
                        if file_ext in image_extensions and not filename.startswith('.'):
                            filepath = os.path.join(session_path, filename)
                            file_stats = os.stat(filepath)
                            
                            # Create unique display name with session prefix
                            display_name = f"{session_folder}_{filename}"
                            
                            file_info = {
                                'filename': display_name,
                                'original_filename': filename,
                                'session_id': session_folder,
                                'file_type': 'image',
                                'extension': file_ext,
                                'size': file_stats.st_size,
                                'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
                                'created_at': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                                'modified_at': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                'metadata': {},
                                'url': f'/images/{session_folder}/{filename}'
                            }
                            files.append(file_info)
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x['created_at'], reverse=True)
        return files
    
    def load_metadata(self) -> Dict:
        """Load metadata file"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_metadata(self, metadata: Dict):
        """Save metadata file"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def add_file_metadata(self, filename: str, metadata: Dict):
        """Tambah metadata untuk file tertentu"""
        all_metadata = self.load_metadata()
        all_metadata[filename] = {
            **metadata,
            'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.save_metadata(all_metadata)
    
    def delete_file(self, filename: str) -> Tuple[bool, str]:
        """Hapus file (video/gambar) dan metadata-nya"""
        try:
            # Check if it's a video file
            video_path = os.path.join(self.output_folder, filename)
            if os.path.exists(video_path):
                os.remove(video_path)
                
                # Remove metadata
                metadata = self.load_metadata()
                if filename in metadata:
                    del metadata[filename]
                    self.save_metadata(metadata)
                
                return True, f"Video '{filename}' berhasil dihapus."
            
            # Check if it's an image file (format: session_id_filename)
            if '_' in filename:
                parts = filename.split('_', 1)
                if len(parts) == 2:
                    session_id, original_filename = parts
                    image_path = os.path.join(self.images_folder, session_id, original_filename)
                    
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        
                        # Check if session folder is empty and remove it
                        session_folder = os.path.join(self.images_folder, session_id)
                        if os.path.exists(session_folder) and not os.listdir(session_folder):
                            os.rmdir(session_folder)
                        
                        return True, f"Gambar '{filename}' berhasil dihapus."
            
            return False, "File tidak ditemukan."
            
        except Exception as e:
            return False, f"Error menghapus file: {str(e)}"
    
    def delete_multiple_files(self, filenames: List[str]) -> Tuple[bool, str]:
        """Hapus multiple files sekaligus"""
        try:
            deleted_count = 0
            errors = []
            
            for filename in filenames:
                success, message = self.delete_file(filename)
                if success:
                    deleted_count += 1
                else:
                    errors.append(f"{filename}: {message}")
            
            if deleted_count == len(filenames):
                return True, f"Berhasil menghapus {deleted_count} file."
            elif deleted_count > 0:
                return True, f"Berhasil menghapus {deleted_count} dari {len(filenames)} file. Errors: {'; '.join(errors)}"
            else:
                return False, f"Gagal menghapus file. Errors: {'; '.join(errors)}"
                
        except Exception as e:
            return False, f"Error menghapus multiple files: {str(e)}"
    
    def create_zip_archive(self, filenames: List[str], zip_name: str = None) -> Tuple[bool, str, str]:
        """Buat ZIP archive dari file-file yang dipilih"""
        try:
            if not zip_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                zip_name = f"files_archive_{timestamp}.zip"
            
            zip_path = os.path.join(self.output_folder, zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in filenames:
                    # Check if it's a video file
                    video_path = os.path.join(self.output_folder, filename)
                    if os.path.exists(video_path):
                        zipf.write(video_path, filename)
                        continue
                    
                    # Check if it's an image file
                    if '_' in filename:
                        parts = filename.split('_', 1)
                        if len(parts) == 2:
                            session_id, original_filename = parts
                            image_path = os.path.join(self.images_folder, session_id, original_filename)
                            if os.path.exists(image_path):
                                zipf.write(image_path, filename)
            
            return True, f"ZIP archive '{zip_name}' berhasil dibuat.", zip_name
            
        except Exception as e:
            return False, f"Error membuat ZIP archive: {str(e)}", ""
    
    def get_storage_info(self) -> Dict:
        """Dapatkan informasi storage untuk semua file"""
        try:
            total_size = 0
            video_count = 0
            image_count = 0
            
            # Count videos
            if os.path.exists(self.output_folder):
                for filename in os.listdir(self.output_folder):
                    if not filename.startswith('.'):
                        filepath = os.path.join(self.output_folder, filename)
                        if os.path.isfile(filepath):
                            file_ext = os.path.splitext(filename)[1].lower()
                            if file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                                total_size += os.path.getsize(filepath)
                                video_count += 1
            
            # Count images
            if os.path.exists(self.images_folder):
                for session_folder in os.listdir(self.images_folder):
                    session_path = os.path.join(self.images_folder, session_folder)
                    if os.path.isdir(session_path):
                        for filename in os.listdir(session_path):
                            if not filename.startswith('.'):
                                filepath = os.path.join(session_path, filename)
                                if os.path.isfile(filepath):
                                    file_ext = os.path.splitext(filename)[1].lower()
                                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                                        total_size += os.path.getsize(filepath)
                                        image_count += 1
            
            return {
                'total_files': video_count + image_count,
                'video_files': video_count,
                'image_files': image_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2)
            }
            
        except Exception as e:
            return {
                'total_files': 0,
                'video_files': 0,
                'image_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'total_size_gb': 0,
                'error': str(e)
            }
    
    def cleanup_old_files(self, days_old: int = 30) -> Tuple[bool, str]:
        """Bersihkan file lama (video dan gambar)"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            deleted_count = 0
            
            # Cleanup videos
            if os.path.exists(self.output_folder):
                for filename in os.listdir(self.output_folder):
                    if not filename.startswith('.'):
                        file_ext = os.path.splitext(filename)[1].lower()
                        if file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                            filepath = os.path.join(self.output_folder, filename)
                            if os.path.getmtime(filepath) < cutoff_time:
                                os.remove(filepath)
                                deleted_count += 1
            
            # Cleanup images
            if os.path.exists(self.images_folder):
                for session_folder in os.listdir(self.images_folder):
                    session_path = os.path.join(self.images_folder, session_folder)
                    if os.path.isdir(session_path):
                        session_deleted = False
                        for filename in os.listdir(session_path):
                            if not filename.startswith('.'):
                                filepath = os.path.join(session_path, filename)
                                if os.path.getmtime(filepath) < cutoff_time:
                                    os.remove(filepath)
                                    deleted_count += 1
                                    session_deleted = True
                        
                        # Remove empty session folder
                        if session_deleted and not os.listdir(session_path):
                            os.rmdir(session_path)
            
            return True, f"Berhasil menghapus {deleted_count} file lama (>{days_old} hari)."
            
        except Exception as e:
            return False, f"Error cleanup: {str(e)}"
    
    def delete_session_images(self, session_id: str) -> Tuple[bool, str]:
        """Hapus semua gambar dalam satu session"""
        try:
            session_path = os.path.join(self.images_folder, session_id)
            if os.path.exists(session_path):
                shutil.rmtree(session_path)
                return True, f"Session images '{session_id}' berhasil dihapus."
            else:
                return False, f"Session folder '{session_id}' tidak ditemukan."
        except Exception as e:
            return False, f"Error menghapus session images: {str(e)}"