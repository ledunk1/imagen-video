from flask import Blueprint, request, jsonify, send_from_directory, current_app
import os
from services.file_service import FileService

file_bp = Blueprint('files', __name__, url_prefix='/files')

@file_bp.route('/list', methods=['GET'])
def get_file_list():
    """Dapatkan daftar semua file video"""
    try:
        file_service = FileService(current_app.config['OUTPUT_FOLDER'])
        files = file_service.get_file_list()
        storage_info = file_service.get_storage_info()
        
        return jsonify({
            'success': True,
            'files': files,
            'storage_info': storage_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/delete', methods=['POST'])
def delete_file():
    """Hapus file tunggal"""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Filename tidak boleh kosong.'
            }), 400
        
        file_service = FileService(current_app.config['OUTPUT_FOLDER'])
        success, message = file_service.delete_file(filename)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple_files():
    """Hapus multiple files"""
    try:
        data = request.json
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({
                'success': False,
                'error': 'Daftar filename tidak boleh kosong.'
            }), 400
        
        file_service = FileService(current_app.config['OUTPUT_FOLDER'])
        success, message = file_service.delete_multiple_files(filenames)
        
        return jsonify({
            'success': success,
            'message': message
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/create-zip', methods=['POST'])
def create_zip_archive():
    """Buat ZIP archive dari file yang dipilih"""
    try:
        data = request.json
        filenames = data.get('filenames', [])
        zip_name = data.get('zip_name')
        
        if not filenames:
            return jsonify({
                'success': False,
                'error': 'Daftar filename tidak boleh kosong.'
            }), 400
        
        file_service = FileService(current_app.config['OUTPUT_FOLDER'])
        success, message, zip_filename = file_service.create_zip_archive(filenames, zip_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'zip_filename': zip_filename,
                'download_url': f'/outputs/{zip_filename}'
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/cleanup', methods=['POST'])
def cleanup_old_files():
    """Bersihkan file lama"""
    try:
        data = request.json
        days_old = data.get('days_old', 30)
        
        file_service = FileService(current_app.config['OUTPUT_FOLDER'])
        success, message = file_service.cleanup_old_files(days_old)
        
        return jsonify({
            'success': success,
            'message': message
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/storage-info', methods=['GET'])
def get_storage_info():
    """Dapatkan informasi storage"""
    try:
        file_service = FileService(current_app.config['OUTPUT_FOLDER'])
        storage_info = file_service.get_storage_info()
        
        return jsonify({
            'success': True,
            'storage_info': storage_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500