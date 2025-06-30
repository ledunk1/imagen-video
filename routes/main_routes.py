from flask import Blueprint, request, render_template, jsonify, send_from_directory, current_app
import os
import uuid
import traceback
from services import ai_service, video_service, prompt_service
from services.file_service import FileService

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main_bp.route('/env-manager', methods=['GET'])
def env_manager():
    return render_template('env_manager.html')

@main_bp.route('/file-manager', methods=['GET'])
def file_manager():
    return render_template('file_manager.html')

@main_bp.route('/test-gemini', methods=['GET'])
def test_gemini():
    """Test endpoint untuk mengecek koneksi Gemini API"""
    try:
        success, message = ai_service.test_gemini_connection()
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing Gemini: {str(e)}'
        }), 500

@main_bp.route('/save-api-key', methods=['POST'])
def save_api_key():
    """Simpan API key Gemini"""
    try:
        data = request.json
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'API key tidak boleh kosong'
            }), 400
        
        success, message = ai_service.save_gemini_api_key(api_key)
        
        if success:
            # Test connection after saving
            test_success, test_message = ai_service.test_gemini_connection()
            return jsonify({
                'success': True,
                'message': message,
                'test_success': test_success,
                'test_message': test_message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving API key: {str(e)}'
        }), 500

@main_bp.route('/generate', methods=['POST'])
def generate_video_route():
    try:
        print("🎬 Starting video generation process with QUEUE SYSTEM...")
        
        # 1. Ambil data form
        narration_file = request.files.get('narration_file')
        audio_file = request.files.get('audio_file')
        prompt_id = request.form.get('prompt_template')
        image_model = request.form.get('image_model', 'flux')
        gemini_model = request.form.get('gemini_model', 'gemini-2.0-flash')
        processing_mode = 'enhanced' if 'processing_mode' in request.form else 'normal'
        images_per_paragraph = int(request.form.get('images_per_paragraph', 3))
        use_gpu = 'gpu_enabled' in request.form
        image_delay = int(request.form.get('image_generation_delay', 6))
        effects_config = {
            'enabled': 'effects_enabled' in request.form,
            'zoom_in': int(request.form.get('zoom_in_prob', 20)),
            'zoom_out': int(request.form.get('zoom_out_prob', 20)),
            'still': int(request.form.get('still_prob', 40)),
            'fade_transition': int(request.form.get('fade_transition_prob', 20))
        }

        print(f"📋 Configuration:")
        print(f"   - Image model: {image_model}")
        print(f"   - Gemini model: {gemini_model}")
        print(f"   - Processing mode: {processing_mode}")
        print(f"   - Images per paragraph: {images_per_paragraph}")
        print(f"   - Image delay: {image_delay}s")
        print(f"   - Effects enabled: {effects_config['enabled']}")
        print(f"   - GPU enabled: {use_gpu}")

        if not narration_file or not audio_file or not prompt_id:
            return jsonify({'error': 'File narasi, audio, dan template prompt harus dipilih.'}), 400

        # 2. Test Gemini connection first
        print("🔍 Testing Gemini API connection...")
        gemini_success, gemini_message = ai_service.test_gemini_connection()
        if not gemini_success:
            print(f"⚠️ Gemini API warning: {gemini_message}")
            print("🔄 Will use fallback prompt generation if needed")

        # 3. Simpan file & dapatkan durasi audio
        session_id = str(uuid.uuid4())
        narration_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{session_id}_narration.txt")
        audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{session_id}_{audio_file.filename}")
        
        # Pastikan folder upload ada
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        narration_file.save(narration_path)
        audio_file.save(audio_path)
        
        print(f"💾 Files saved:")
        print(f"   - Narration: {narration_path}")
        print(f"   - Audio: {audio_path}")
        
        with open(narration_path, 'r', encoding='utf-8') as f:
            narration_text = f.read()
        
        print(f"📝 Narration length: {len(narration_text)} characters")
        
        audio_duration = video_service.get_audio_duration(audio_path)
        if audio_duration is None:
            return jsonify({'error': 'Gagal membaca durasi audio.'}), 500

        print(f"🎵 Audio duration: {audio_duration:.2f} seconds ({audio_duration/60:.1f} minutes)")

        # 4. Dapatkan prompt gaya dari template yang dipilih
        style_prompt = prompt_service.get_prompt_by_id(prompt_id)
        if not style_prompt:
            return jsonify({'error': 'Template prompt yang dipilih tidak valid.'}), 400

        print(f"🎨 Style prompt: {style_prompt[:50]}...")

        # 5. Buat folder permanen untuk gambar dengan session ID
        permanent_image_folder = os.path.join(current_app.config['IMAGES_FOLDER'], session_id)
        os.makedirs(permanent_image_folder, exist_ok=True)
        
        print(f"📁 Images will be saved permanently to: {permanent_image_folder}")

        # 6. 🎯 QUEUE SYSTEM: Generate prompt + download image secara bertahap
        print(f"🚀 Starting QUEUE SYSTEM for prompt generation and image download...")
        print(f"⏱️ This will process one prompt at a time to avoid rate limits")
        
        image_paths = ai_service.generate_prompts_with_queue_system(
            narration_text, 
            processing_mode, 
            gemini_model, 
            images_per_paragraph, 
            style_prompt,
            permanent_image_folder,
            image_model,
            image_delay
        )
        
        if not image_paths:
            return jsonify({'error': 'Gagal menghasilkan gambar apa pun dengan sistem antrian.'}), 500

        print(f"🎉 Queue system completed successfully!")
        print(f"✅ Total images generated: {len(image_paths)}")

        # 7. Buat video dengan MoviePy
        output_filename = f"video_{session_id}.mp4"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        print(f"🎬 Creating video with MoviePy: {output_path}")
        print(f"⏱️ Video duration will match audio: {audio_duration:.2f} seconds")
        
        # Pastikan folder output ada
        os.makedirs(current_app.config['OUTPUT_FOLDER'], exist_ok=True)
        
        success, message = video_service.create_video_with_effects(
            image_paths, 
            audio_path, 
            output_path, 
            audio_duration,  # Pass audio duration instead of duration per image
            use_gpu, 
            effects_config
        )

        # 8. Simpan metadata file
        if success:
            file_service = FileService(current_app.config['OUTPUT_FOLDER'])
            metadata = {
                'session_id': session_id,
                'prompt_template': prompt_id,
                'image_model': image_model,
                'gemini_model': gemini_model,
                'processing_mode': processing_mode,
                'images_per_paragraph': images_per_paragraph,
                'image_generation_delay': image_delay,
                'effects_enabled': effects_config['enabled'],
                'gpu_enabled': use_gpu,
                'total_images': len(image_paths),
                'audio_duration': audio_duration,
                'narration_length': len(narration_text),
                'queue_system_used': True,  # Flag untuk menandai penggunaan queue system
                'images_downloaded': len(image_paths),
                'image_folder': permanent_image_folder,  # Simpan path folder gambar
                'gemini_status': gemini_message
            }
            file_service.add_file_metadata(output_filename, metadata)
            print("💾 Metadata saved successfully")

        # 9. Bersihkan file sementara (HANYA file upload, BUKAN gambar)
        print("🧹 Cleaning up temporary upload files...")
        
        if os.path.exists(narration_path):
            try:
                os.remove(narration_path)
                print(f"🗑️ Removed: {narration_path}")
            except:
                pass
                
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"🗑️ Removed: {audio_path}")
            except:
                pass

        # GAMBAR TETAP DISIMPAN DI data/images/{session_id}/
        print(f"💾 Images preserved in: {permanent_image_folder}")

        if success:
            print(f"🎉 Video generation completed successfully with QUEUE SYSTEM: {output_filename}")
            return jsonify({
                'video_url': f"/outputs/{output_filename}",
                'image_folder': permanent_image_folder,
                'total_images': len(image_paths),
                'queue_system_used': True,
                'gemini_status': gemini_message
            })
        else:
            print(f"❌ Video generation failed: {message}")
            return jsonify({'error': f'Gagal membuat video: {message}'}), 500

    except Exception as e:
        print(f"💥 Critical error in video generation:")
        traceback.print_exc()
        return jsonify({'error': f'Terjadi kesalahan server: {str(e)}'}), 500

# Rute untuk menyajikan video
@main_bp.route('/outputs/<filename>')
def serve_video(filename):
    return send_from_directory(current_app.config['OUTPUT_FOLDER'], filename)

# Rute untuk menyajikan gambar dari data/images
@main_bp.route('/images/<session_id>/<filename>')
def serve_image(session_id, filename):
    image_folder = os.path.join(current_app.config['IMAGES_FOLDER'], session_id)
    return send_from_directory(image_folder, filename)

# --- Rute CRUD untuk Template Prompt ---
@main_bp.route('/prompts', methods=['GET'])
def api_get_prompts():
    return jsonify(prompt_service.get_prompts())

@main_bp.route('/prompts/add', methods=['POST'])
def api_add_prompt():
    data = request.json
    name = data.get('name')
    prompt_text = data.get('prompt')
    new_prompt, message = prompt_service.add_prompt(name, prompt_text)
    if new_prompt:
        return jsonify({'message': message, 'prompt': new_prompt}), 201
    return jsonify({'error': message}), 400

@main_bp.route('/prompts/update/<prompt_id>', methods=['POST'])
def api_update_prompt(prompt_id):
    data = request.json
    name = data.get('name')
    prompt_text = data.get('prompt')
    success, message = prompt_service.update_prompt(prompt_id, name, prompt_text)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400

@main_bp.route('/prompts/delete/<prompt_id>', methods=['POST'])
def api_delete_prompt(prompt_id):
    success, message = prompt_service.delete_prompt(prompt_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400