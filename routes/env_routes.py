from flask import Blueprint, request, jsonify
from services.env_service import EnvService
import os

env_bp = Blueprint('env', __name__, url_prefix='/env')
env_service = EnvService()

@env_bp.route('/vars', methods=['GET'])
def get_env_vars():
    """Dapatkan semua environment variables"""
    try:
        env_vars = env_service.read_env_vars()
        
        # Mask sensitive values for display
        masked_vars = {}
        sensitive_keys = ['SECRET_KEY', 'GEMINI_API_KEY']
        
        for key, value in env_vars.items():
            if key in sensitive_keys and value and len(value) > 8:
                # Show first 4 and last 4 characters
                masked_vars[key] = f"{value[:4]}...{value[-4:]}"
            else:
                masked_vars[key] = value
        
        return jsonify({
            'success': True,
            'env_vars': masked_vars,
            'raw_count': len(env_vars)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@env_bp.route('/vars/<key>', methods=['GET'])
def get_env_var(key):
    """Dapatkan environment variable tertentu"""
    try:
        value = env_service.get_env_var(key)
        if value is None:
            return jsonify({
                'success': False,
                'error': f"Environment variable '{key}' tidak ditemukan."
            }), 404
        
        return jsonify({
            'success': True,
            'key': key,
            'value': value
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@env_bp.route('/vars', methods=['POST'])
def update_env_var():
    """Update atau tambah environment variable"""
    try:
        data = request.json
        key = data.get('key', '').strip()
        value = data.get('value', '').strip()
        
        if not key:
            return jsonify({
                'success': False,
                'error': 'Key tidak boleh kosong.'
            }), 400
        
        success, message = env_service.update_env_var(key, value)
        
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

@env_bp.route('/vars/<key>', methods=['DELETE'])
def delete_env_var(key):
    """Hapus environment variable"""
    try:
        success, message = env_service.delete_env_var(key)
        
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

@env_bp.route('/validate', methods=['GET'])
def validate_env_vars():
    """Validasi environment variables"""
    try:
        issues = env_service.validate_env_vars()
        
        return jsonify({
            'success': True,
            'valid': len(issues) == 0,
            'issues': issues
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@env_bp.route('/backup', methods=['POST'])
def backup_env_file():
    """Buat backup file .env"""
    try:
        success, message = env_service.backup_env_file()
        
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

@env_bp.route('/restart-required', methods=['GET'])
def check_restart_required():
    """Cek apakah aplikasi perlu restart"""
    # Untuk Flask development server, kita bisa memberikan informasi
    # bahwa beberapa perubahan memerlukan restart
    return jsonify({
        'success': True,
        'restart_required': True,
        'message': 'Beberapa perubahan environment variables memerlukan restart aplikasi untuk berlaku penuh.'
    })