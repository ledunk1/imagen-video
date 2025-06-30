import google.generativeai as genai
import requests
import re
import os
import uuid
import time
from PIL import Image
from services.simple_api_service import SimpleAPIService

# Available Gemini models
AVAILABLE_MODELS = [
    'gemini-2.0-flash-exp',
    'gemini-2.0-flash',
    'gemini-2.0-flash-001',
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash',
    'gemini-1.5-pro-latest',
    'gemini-1.5-pro'
]

# Global API service instance
api_service = SimpleAPIService()

def get_gemini_api_key():
    """Ambil API key dari berbagai sumber"""
    # 1. Coba dari file API keys
    api_key = api_service.get_api_key('GEMINI_API_KEY')
    if api_key:
        print(f"✓ API key loaded from file: {api_key[:10]}...")
        return api_key
    
    # 2. Coba dari environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        print(f"✓ API key loaded from env: {api_key[:10]}...")
        return api_key
    
    print("❌ No valid API key found")
    return None

def configure_gemini():
    """Konfigurasi Gemini API dengan error handling yang lebih baik"""
    api_key = get_gemini_api_key()
    
    if not api_key:
        print("WARNING: GEMINI_API_KEY belum diset!")
        print("Silakan set API key di halaman utama atau gunakan Environment Manager")
        return False
    
    try:
        genai.configure(api_key=api_key)
        print("✓ Gemini API berhasil dikonfigurasi")
        return True
    except Exception as e:
        print(f"✗ Error configuring Gemini API: {e}")
        return False

def init_gemini(model_name='gemini-2.0-flash-exp'):
    """Initialize Gemini model dengan validasi"""
    if model_name not in AVAILABLE_MODELS:
        print(f"WARNING: Model {model_name} tidak tersedia, menggunakan gemini-2.0-flash-exp")
        model_name = 'gemini-2.0-flash-exp'
    
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✓ Gemini model '{model_name}' berhasil diinisialisasi")
        return model
    except Exception as e:
        print(f"✗ Error initializing Gemini model: {e}")
        return None

def test_gemini_connection():
    """Test koneksi Gemini API"""
    if not configure_gemini():
        return False, "Konfigurasi API key gagal"
    
    try:
        model = init_gemini('gemini-2.0-flash-exp')
        if not model:
            return False, "Gagal menginisialisasi model"
        
        # Test simple prompt
        response = model.generate_content("Hello, test connection")
        if response and response.text:
            print(f"✓ Test Gemini berhasil: {response.text[:50]}...")
            return True, "Koneksi Gemini berhasil"
        else:
            return False, "Response kosong dari Gemini"
            
    except Exception as e:
        print(f"✗ Test Gemini gagal: {e}")
        return False, f"Error: {str(e)}"

def save_gemini_api_key(api_key):
    """Simpan API key Gemini"""
    return api_service.save_api_key('GEMINI_API_KEY', api_key)

def generate_single_prompt_from_text(text_segment, style_prompt, model_name='gemini-2.0-flash-exp'):
    """Generate single prompt dari satu segmen teks menggunakan Gemini AI"""
    if not text_segment.strip() or not style_prompt:
        print("ERROR: Text segment atau style prompt kosong")
        return None

    print(f"🤖 Generating single prompt for text: {text_segment[:50]}...")

    # Check if Gemini is properly configured
    if not configure_gemini():
        print("❌ Gemini API tidak dikonfigurasi. Menggunakan fallback prompt...")
        return f"{text_segment.strip()}, {style_prompt}"

    try:
        model = init_gemini(model_name)
        if not model:
            print("❌ Gagal menginisialisasi model Gemini. Menggunakan fallback prompt...")
            return f"{text_segment.strip()}, {style_prompt}"
        
        system_prompt = f"""
        You are an expert AI assistant for creating prompts for a text-to-image generator.
        Your task is to read a text segment and convert it into ONE descriptive visual prompt.
        The prompt MUST incorporate the following visual style for consistency: '{style_prompt}'.
        
        IMPORTANT RULES:
        - Output ONLY ONE prompt, no numbering or "Prompt:" prefix
        - Keep the prompt under 200 characters
        - Focus on visual elements, not abstract concepts
        - Make it descriptive and dramatic
        - Ensure it's suitable for image generation
        """

        user_prompt = f"Text: '{text_segment.strip()}'\n\nCreate ONE highly descriptive and dramatic image prompt based on this text."
        
        try:
            response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
            if response and response.text:
                clean_prompt = response.text.strip()
                # Remove numbering if present
                clean_prompt = re.sub(r'^\d+\.\s*', '', clean_prompt).strip()
                # Remove "Prompt:" prefix if present
                clean_prompt = re.sub(r'^Prompt:\s*', '', clean_prompt, flags=re.IGNORECASE).strip()
                print(f"✓ Generated prompt: {clean_prompt[:50]}...")
                return clean_prompt
            else:
                fallback_prompt = f"{text_segment.strip()}, {style_prompt}"
                print(f"⚠️ Empty response, using fallback: {fallback_prompt[:50]}...")
                return fallback_prompt
        except Exception as e:
            print(f"❌ Error Gemini API: {e}")
            fallback_prompt = f"{text_segment.strip()}, {style_prompt}"
            print(f"🔄 Using fallback: {fallback_prompt[:50]}...")
            return fallback_prompt
        
    except Exception as e:
        print(f"💥 Critical error with Gemini API: {e}")
        return f"{text_segment.strip()}, {style_prompt}"

def generate_prompts_with_queue_system(narration, mode, model_name, images_per_paragraph, style_prompt, image_folder, image_model, image_delay=6):
    """
    Generate prompts dan download images menggunakan sistem antrian
    Satu prompt -> satu gambar -> prompt berikutnya
    """
    if not narration.strip() or not style_prompt:
        print("ERROR: Narasi atau style prompt kosong")
        return []

    print(f"🎯 Starting QUEUE SYSTEM for prompt generation and image download")
    print(f"📝 Mode: {mode}, Images per paragraph: {images_per_paragraph}")
    print(f"🎨 Style prompt: {style_prompt[:50]}...")
    print(f"⏱️ Image delay: {image_delay} seconds")

    # Prepare text segments based on mode
    text_segments = []
    
    if mode == 'enhanced':
        print("🔍 Enhanced mode: Processing per sentence...")
        sentences = re.split(r'(?<=[.!?])\s+', narration)
        text_segments = [s.strip() for s in sentences if s.strip()]
        print(f"📊 Total sentences to process: {len(text_segments)}")
    else:
        print("📝 Normal mode: Processing per paragraph...")
        paragraphs = [p for p in narration.split('\n\n') if len(p.strip()) > 20]
        print(f"📊 Total paragraphs: {len(paragraphs)}")
        
        # Create multiple segments per paragraph
        for para in paragraphs:
            for i in range(images_per_paragraph):
                # Add variation to each segment from same paragraph
                segment = f"{para.strip()}"
                if i > 0:
                    segment += f" (variation {i+1})"
                text_segments.append(segment)
        
        print(f"📊 Total segments created: {len(text_segments)}")

    # Queue processing: Generate prompt -> Download image -> Next
    successful_images = []
    total_segments = len(text_segments)
    
    print(f"\n🚀 Starting queue processing for {total_segments} segments...")
    print("=" * 60)
    
    for i, text_segment in enumerate(text_segments):
        print(f"\n📋 QUEUE ITEM {i+1}/{total_segments}")
        print(f"📝 Text: {text_segment[:100]}...")
        
        # Step 1: Generate prompt using Gemini
        print(f"🤖 Step 1: Generating prompt with Gemini...")
        prompt = generate_single_prompt_from_text(text_segment, style_prompt, model_name)
        
        if not prompt:
            print(f"❌ Failed to generate prompt for segment {i+1}, skipping...")
            continue
        
        print(f"✅ Prompt generated: {prompt[:80]}...")
        
        # Step 2: Download image immediately
        print(f"🖼️ Step 2: Downloading image...")
        img_path = os.path.join(image_folder, f"image_{i:03d}.jpg")
        
        download_success = download_image_from_pollinations(
            prompt, 1280, 720, image_model, img_path, image_delay
        )
        
        if download_success and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
            successful_images.append(img_path)
            print(f"✅ Image {i+1} downloaded successfully: {os.path.getsize(img_path)} bytes")
            print(f"📁 Saved to: {img_path}")
        else:
            print(f"❌ Image {i+1} download failed")
        
        # Step 3: Progress update
        progress = ((i + 1) / total_segments) * 100
        print(f"📊 Progress: {progress:.1f}% ({i+1}/{total_segments})")
        
        # Step 4: Small delay between queue items (additional to image delay)
        if i < total_segments - 1:  # Not the last item
            queue_delay = 2  # 2 seconds between queue items
            print(f"⏳ Queue delay: {queue_delay} seconds before next item...")
            time.sleep(queue_delay)
        
        print("-" * 40)
    
    print("=" * 60)
    print(f"🎉 Queue processing completed!")
    print(f"✅ Successfully processed: {len(successful_images)}/{total_segments} images")
    print(f"📁 Images saved in: {image_folder}")
    
    return successful_images

def generate_prompts_from_narration(narration, mode, model_name, images_per_paragraph, style_prompt):
    """
    Legacy function untuk backward compatibility
    Sekarang hanya generate prompts tanpa download images
    """
    if not narration.strip() or not style_prompt:
        print("ERROR: Narasi atau style prompt kosong")
        return []

    print(f"🤖 Legacy prompt generation mode")
    print(f"📝 Mode: {mode}, Images per paragraph: {images_per_paragraph}")

    # Check if Gemini is properly configured
    if not configure_gemini():
        print("❌ Gemini API tidak dikonfigurasi dengan benar. Menggunakan fallback prompts...")
        return generate_fallback_prompts(narration, mode, images_per_paragraph, style_prompt)

    try:
        model = init_gemini(model_name)
        if not model:
            print("❌ Gagal menginisialisasi model Gemini. Menggunakan fallback prompts...")
            return generate_fallback_prompts(narration, mode, images_per_paragraph, style_prompt)
        
        prompts = []
        
        system_prompt = f"""
        You are an expert AI assistant for creating prompts for a text-to-image generator.
        Your task is to read a narration and convert it into a series of descriptive visual prompts.
        Each prompt MUST incorporate the following visual style for consistency: '{style_prompt}'.
        
        IMPORTANT RULES:
        - Do not add numbering or "Prompt:" at the beginning
        - Only output the raw prompts, one per line
        - Each prompt should be descriptive and visual
        - Ensure the prompts are varied and visually interesting
        - Keep prompts under 200 characters each
        - Focus on visual elements, not abstract concepts
        """

        if mode == 'enhanced':
            print("🔍 Enhanced mode: Processing per sentence...")
            sentences = re.split(r'(?<=[.!?])\s+', narration)
            total_sentences = len([s for s in sentences if s.strip()])
            print(f"📊 Total sentences to process: {total_sentences}")
            
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    print(f"⏳ Processing sentence {i+1}/{total_sentences}...")
                    user_prompt = f"Narration: '{sentence.strip()}'\n\nCreate one highly descriptive and dramatic image prompt based on this narration."
                    
                    try:
                        response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
                        if response and response.text:
                            clean_prompt = response.text.strip()
                            prompts.append(clean_prompt)
                            print(f"✓ Generated: {clean_prompt[:50]}...")
                        else:
                            fallback_prompt = f"{sentence.strip()}, {style_prompt}"
                            prompts.append(fallback_prompt)
                            print(f"⚠️ Empty response, using fallback: {fallback_prompt[:50]}...")
                    except Exception as e:
                        print(f"❌ Error Gemini API for sentence {i+1}: {e}")
                        fallback_prompt = f"{sentence.strip()}, {style_prompt}"
                        prompts.append(fallback_prompt)
                        print(f"🔄 Using fallback: {fallback_prompt[:50]}...")
        else:
            print("📝 Normal mode: Processing per paragraph...")
            paragraphs = [p for p in narration.split('\n\n') if len(p.strip()) > 20]
            total_paragraphs = len(paragraphs)
            print(f"📊 Total paragraphs to process: {total_paragraphs}")
            
            for i, para in enumerate(paragraphs):
                print(f"⏳ Processing paragraph {i+1}/{total_paragraphs}...")
                user_prompt = f"Narration: '{para.strip()}'\n\nCreate {images_per_paragraph} different but related image prompts based on this narration."
                
                try:
                    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
                    if response and response.text:
                        generated_prompts = response.text.strip().split('\n')
                        clean_prompts = [p.strip() for p in generated_prompts if p.strip()]
                        prompts.extend(clean_prompts)
                        print(f"✓ Generated {len(clean_prompts)} prompts for paragraph {i+1}")
                    else:
                        fallback_prompts = [f"{para.strip()[:100]}..., {style_prompt}" for _ in range(images_per_paragraph)]
                        prompts.extend(fallback_prompts)
                        print(f"⚠️ Empty response, using {len(fallback_prompts)} fallback prompts")
                except Exception as e:
                    print(f"❌ Error Gemini API for paragraph {i+1}: {e}")
                    fallback_prompts = [f"{para.strip()[:100]}..., {style_prompt}" for _ in range(images_per_paragraph)]
                    prompts.extend(fallback_prompts)
                    print(f"🔄 Using {len(fallback_prompts)} fallback prompts")
        
        # Clean up prompts
        cleaned_prompts = []
        for p in prompts:
            if p.strip():
                # Remove numbering if present
                clean_p = re.sub(r'^\d+\.\s*', '', p).strip()
                # Remove "Prompt:" prefix if present
                clean_p = re.sub(r'^Prompt:\s*', '', clean_p, flags=re.IGNORECASE).strip()
                cleaned_prompts.append(clean_p)
        
        print(f"🎉 Successfully generated {len(cleaned_prompts)} prompts using Gemini!")
        return cleaned_prompts if cleaned_prompts else generate_fallback_prompts(narration, mode, images_per_paragraph, style_prompt)
        
    except Exception as e:
        print(f"💥 Critical error with Gemini API: {e}")
        print("🔄 Falling back to simple prompt generation...")
        return generate_fallback_prompts(narration, mode, images_per_paragraph, style_prompt)

def generate_fallback_prompts(narration, mode, images_per_paragraph, style_prompt):
    """Generate fallback prompts when Gemini API is not available"""
    print("🔄 Using fallback prompt generation...")
    prompts = []
    
    if mode == 'enhanced':
        sentences = re.split(r'(?<=[.!?])\s+', narration)
        for sentence in sentences:
            if sentence.strip():
                prompts.append(f"{sentence.strip()}, {style_prompt}")
    else:
        paragraphs = narration.split('\n\n')
        for para in paragraphs:
            if len(para.strip()) > 20:
                for i in range(images_per_paragraph):
                    prompts.append(f"{para.strip()[:100]}..., {style_prompt}")
    
    print(f"📝 Generated {len(prompts)} fallback prompts")
    return prompts

def download_image_from_pollinations(prompt, width, height, model, output_path, delay_seconds=6):
    """Mengunduh gambar dari Pollinations.ai dengan model yang dipilih dan delay."""
    try:
        encoded_prompt = requests.utils.quote(prompt)
        # Tambahkan parameter nologo=true untuk menghilangkan watermark
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&seed={uuid.uuid4().int & (1<<32)-1}&nologo=true"
        print(f"🌐 Requesting image from: {url[:100]}...")
        
        response = requests.get(url, timeout=300) # Timeout lebih lama untuk file besar
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        # Validate image file
        try:
            with Image.open(output_path) as img:
                # Verify it's a valid image and has reasonable dimensions
                if img.size[0] < 100 or img.size[1] < 100:
                    print(f"⚠️ Warning: Image too small: {img.size}")
                    return False
                print(f"✅ Image downloaded successfully: {output_path} ({img.size}) - {os.path.getsize(output_path)} bytes")
        except Exception as e:
            print(f"❌ Invalid image file: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
        
        # Add delay to avoid rate limiting
        if delay_seconds > 0:
            print(f"⏳ Waiting {delay_seconds} seconds before next request...")
            time.sleep(delay_seconds)
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading image for prompt '{prompt[:50]}...': {e}")
        return False
    except Exception as e:
        print(f"💥 Unexpected error downloading image: {e}")
        return False

def download_images_batch(prompts, width, height, model, temp_image_folder, delay_seconds=6):
    """Download multiple images with delay between requests"""
    image_paths = []
    total_images = len(prompts)
    
    print(f"📦 Starting batch download of {total_images} images...")
    print(f"⏱️ Delay between requests: {delay_seconds} seconds")
    
    for i, prompt in enumerate(prompts):
        print(f"🖼️ Downloading image {i+1}/{total_images}...")
        img_path = os.path.join(temp_image_folder, f"image_{i:03d}.jpg")
        
        if download_image_from_pollinations(prompt, width, height, model, img_path, delay_seconds):
            image_paths.append(img_path)
            print(f"✅ Image {i+1} downloaded successfully")
        else:
            print(f"❌ Failed to download image {i+1}, skipping...")
    
    print(f"🎉 Batch download completed: {len(image_paths)}/{total_images} images successful")
    return image_paths