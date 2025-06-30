import subprocess
import os
import tempfile
import random
import multiprocessing
import psutil
from moviepy.editor import *
from moviepy.video.fx import resize, fadein, fadeout
from moviepy.video.fx.all import crop
import numpy as np

def get_optimal_threads():
    """Auto-detect optimal thread count untuk rendering"""
    try:
        # Get CPU info
        cpu_count = multiprocessing.cpu_count()
        
        # Get available memory in GB
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Get CPU usage percentage (average over 1 second)
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Calculate optimal threads based on system specs
        if memory_gb >= 16 and cpu_count >= 8:
            # High-end system: use 75% of cores
            optimal_threads = max(1, int(cpu_count * 0.75))
        elif memory_gb >= 8 and cpu_count >= 4:
            # Mid-range system: use 60% of cores
            optimal_threads = max(1, int(cpu_count * 0.6))
        else:
            # Low-end system: use 50% of cores
            optimal_threads = max(1, int(cpu_count * 0.5))
        
        # Adjust based on current CPU usage
        if cpu_usage > 80:
            optimal_threads = max(1, optimal_threads - 2)
        elif cpu_usage < 30:
            optimal_threads = min(cpu_count, optimal_threads + 1)
        
        print(f"🖥️ System Info:")
        print(f"   - CPU Cores: {cpu_count}")
        print(f"   - Memory: {memory_gb:.1f} GB")
        print(f"   - CPU Usage: {cpu_usage:.1f}%")
        print(f"   - Optimal Threads: {optimal_threads}")
        
        return optimal_threads
        
    except Exception as e:
        print(f"⚠️ Error detecting optimal threads: {e}")
        # Fallback to safe default
        return max(1, multiprocessing.cpu_count() // 2)

def get_system_performance_profile():
    """Get detailed system performance profile"""
    try:
        profile = {
            'cpu_count': multiprocessing.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'available_memory_gb': psutil.virtual_memory().available / (1024**3),
            'cpu_usage': psutil.cpu_percent(interval=0.5),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
        }
        
        # Determine system tier
        if profile['memory_gb'] >= 16 and profile['cpu_count'] >= 8:
            profile['tier'] = 'high-end'
            profile['recommended_quality'] = 'high'
        elif profile['memory_gb'] >= 8 and profile['cpu_count'] >= 4:
            profile['tier'] = 'mid-range'
            profile['recommended_quality'] = 'medium'
        else:
            profile['tier'] = 'low-end'
            profile['recommended_quality'] = 'fast'
        
        return profile
        
    except Exception as e:
        print(f"⚠️ Error getting system profile: {e}")
        return {
            'cpu_count': 2,
            'memory_gb': 4,
            'tier': 'low-end',
            'recommended_quality': 'fast'
        }

def get_audio_duration(filepath):
    """Mendapatkan durasi file audio menggunakan moviepy."""
    try:
        audio_clip = AudioFileClip(filepath)
        duration = audio_clip.duration
        audio_clip.close()
        return duration
    except Exception as e:
        print(f"Error getting audio duration with MoviePy: {e}")
        # Fallback ke ffprobe
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e2:
            print(f"Error getting audio duration with ffprobe: {e2}")
            return None

def create_video_with_effects(image_paths, audio_path, output_path, audio_duration, use_gpu, effects_config):
    """Membuat video dari gambar dan audio menggunakan MoviePy dengan auto-threading optimization."""
    
    if not image_paths:
        return False, "Tidak ada gambar untuk dibuat video."
    
    # Get system performance profile
    system_profile = get_system_performance_profile()
    optimal_threads = get_optimal_threads()
    
    print(f"🚀 Starting optimized video creation:")
    print(f"   - System Tier: {system_profile['tier']}")
    print(f"   - Recommended Quality: {system_profile['recommended_quality']}")
    print(f"   - Using {optimal_threads} threads for rendering")
    print(f"   - Available Memory: {system_profile['available_memory_gb']:.1f} GB")
    
    # Validasi semua file gambar ada
    valid_images = []
    for img_path in image_paths:
        if os.path.exists(img_path):
            valid_images.append(img_path)
        else:
            print(f"Warning: Image not found: {img_path}")
    
    if not valid_images:
        return False, "Tidak ada gambar yang valid ditemukan."
    
    print(f"Creating video with MoviePy: {len(valid_images)} images for {audio_duration:.2f} seconds")
    
    try:
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        actual_duration = audio_clip.duration
        print(f"Audio duration: {actual_duration:.2f} seconds")
        
        # Hitung durasi per gambar agar total video = durasi audio
        duration_per_image = actual_duration / len(valid_images)
        print(f"Duration per image: {duration_per_image:.2f} seconds")
        
        # Set MoviePy threading based on system capabilities
        os.environ['MOVIEPY_NTHREADS'] = str(optimal_threads)
        
        # Adjust quality settings based on system tier
        if system_profile['tier'] == 'high-end':
            target_fps = 30
            preset = 'medium'
            crf = '20'  # Higher quality
            resize_method = 'lanczos'
        elif system_profile['tier'] == 'mid-range':
            target_fps = 25
            preset = 'fast'
            crf = '23'  # Balanced quality
            resize_method = 'bilinear'
        else:
            target_fps = 20
            preset = 'ultrafast'
            crf = '28'  # Lower quality for speed
            resize_method = 'fast_bilinear'
        
        print(f"🎬 Rendering settings:")
        print(f"   - FPS: {target_fps}")
        print(f"   - Preset: {preset}")
        print(f"   - CRF: {crf}")
        print(f"   - Resize method: {resize_method}")
        
        # Create video clips from images with optimized processing
        video_clips = []
        
        print(f"📸 Processing {len(valid_images)} images with {optimal_threads} threads...")
        
        for i, img_path in enumerate(valid_images):
            print(f"Processing image {i+1}/{len(valid_images)}: {os.path.basename(img_path)}")
            
            try:
                # Load image as video clip
                img_clip = ImageClip(img_path, duration=duration_per_image)
                
                # Resize to target resolution (1280x720) with optimized method
                img_clip = img_clip.resize(height=720, method=resize_method)
                
                # Center crop if needed to maintain aspect ratio
                if img_clip.w > 1280:
                    img_clip = img_clip.crop(x_center=img_clip.w/2, width=1280)
                
                # Apply effects based on configuration and system capability
                if effects_config.get('enabled', False):
                    img_clip = apply_visual_effects_optimized(img_clip, effects_config, i, system_profile)
                
                # Add fade transitions (lighter for low-end systems)
                if system_profile['tier'] != 'low-end':
                    if i > 0:  # Not first clip
                        img_clip = img_clip.crossfadein(0.5)
                    if i < len(valid_images) - 1:  # Not last clip
                        img_clip = img_clip.crossfadeout(0.5)
                else:
                    # Simple fade for low-end systems
                    if i > 0:
                        img_clip = img_clip.fadein(0.2)
                    if i < len(valid_images) - 1:
                        img_clip = img_clip.fadeout(0.2)
                
                video_clips.append(img_clip)
                
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                # Create a black clip as fallback
                black_clip = ColorClip(size=(1280, 720), color=(0,0,0), duration=duration_per_image)
                video_clips.append(black_clip)
        
        if not video_clips:
            return False, "Gagal memproses gambar apa pun."
        
        print("🎬 Concatenating video clips with optimized threading...")
        # Concatenate all video clips
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # Ensure video duration matches audio duration
        if final_video.duration > actual_duration:
            final_video = final_video.subclip(0, actual_duration)
        elif final_video.duration < actual_duration:
            # Extend last frame if needed
            last_frame = final_video.get_frame(final_video.duration - 0.1)
            extension = ImageClip(last_frame, duration=actual_duration - final_video.duration)
            final_video = concatenate_videoclips([final_video, extension])
        
        # Set audio
        final_video = final_video.set_audio(audio_clip)
        
        print(f"🚀 Rendering video with {optimal_threads} threads to: {output_path}")
        print(f"Final video duration: {final_video.duration:.2f} seconds")
        
        # Render video with optimized settings
        codec = 'libx264'
        if use_gpu and system_profile['tier'] in ['high-end', 'mid-range']:
            # Try GPU acceleration for capable systems
            try:
                final_video.write_videofile(
                    output_path,
                    codec='h264_nvenc',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    fps=target_fps,
                    preset='fast',
                    ffmpeg_params=['-crf', crf, '-threads', str(optimal_threads)],
                    threads=optimal_threads,
                    verbose=False,
                    logger=None
                )
                print(f"✅ Video rendered successfully with GPU acceleration ({optimal_threads} threads)")
            except Exception as e:
                print(f"⚠️ GPU rendering failed: {e}")
                print("🔄 Falling back to CPU rendering...")
                codec = 'libx264'
        
        if codec == 'libx264':
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=target_fps,
                preset=preset,
                ffmpeg_params=['-crf', crf, '-threads', str(optimal_threads)],
                threads=optimal_threads,
                verbose=False,
                logger=None
            )
            print(f"✅ Video rendered successfully with CPU ({optimal_threads} threads)")
        
        # Clean up
        final_video.close()
        audio_clip.close()
        for clip in video_clips:
            clip.close()
        
        # Performance summary
        print(f"🎉 Rendering completed successfully!")
        print(f"   - Used {optimal_threads} threads")
        print(f"   - System tier: {system_profile['tier']}")
        print(f"   - Quality preset: {preset}")
        print(f"   - Final file: {output_path}")
        
        return True, f"Video berhasil dibuat dengan {optimal_threads} threads (MoviePy optimized)."
        
    except Exception as e:
        print(f"Error in MoviePy video creation: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to simple method
        return create_simple_moviepy_video_optimized(valid_images, audio_path, output_path, audio_duration, optimal_threads)

def apply_visual_effects_optimized(clip, effects_config, image_index, system_profile):
    """Apply visual effects optimized for system performance."""
    
    # Skip heavy effects on low-end systems
    if system_profile['tier'] == 'low-end':
        return clip
    
    # Get effect probabilities
    zoom_in_prob = effects_config.get('zoom_in', 20)
    zoom_out_prob = effects_config.get('zoom_out', 20)
    still_prob = effects_config.get('still', 40)
    fade_prob = effects_config.get('fade_transition', 20)
    
    # Normalize probabilities
    total_prob = zoom_in_prob + zoom_out_prob + still_prob + fade_prob
    if total_prob == 0:
        return clip
    
    # Random selection based on probabilities
    rand_val = random.randint(1, 100)
    
    if rand_val <= zoom_in_prob:
        # Zoom in effect (optimized)
        return apply_zoom_in_effect_optimized(clip, system_profile)
    elif rand_val <= zoom_in_prob + zoom_out_prob:
        # Zoom out effect (optimized)
        return apply_zoom_out_effect_optimized(clip, system_profile)
    elif rand_val <= zoom_in_prob + zoom_out_prob + fade_prob:
        # Fade effect
        return apply_fade_effect(clip)
    else:
        # Still image (no effect)
        return clip

def apply_zoom_in_effect_optimized(clip, system_profile):
    """Apply optimized zoom in effect."""
    try:
        if system_profile['tier'] == 'high-end':
            # Smooth zoom for high-end systems
            zoom_factor = 0.3
            zoom_function = lambda t: 1 + (t / clip.duration) * zoom_factor
        else:
            # Lighter zoom for mid-range systems
            zoom_factor = 0.2
            zoom_function = lambda t: 1 + (t / clip.duration) * zoom_factor
        
        return clip.resize(zoom_function)
    except Exception as e:
        print(f"Error applying zoom in effect: {e}")
        return clip

def apply_zoom_out_effect_optimized(clip, system_profile):
    """Apply optimized zoom out effect."""
    try:
        if system_profile['tier'] == 'high-end':
            # Smooth zoom for high-end systems
            zoom_factor = 0.3
            zoom_function = lambda t: 1.3 - (t / clip.duration) * zoom_factor
        else:
            # Lighter zoom for mid-range systems
            zoom_factor = 0.2
            zoom_function = lambda t: 1.2 - (t / clip.duration) * zoom_factor
        
        return clip.resize(zoom_function)
    except Exception as e:
        print(f"Error applying zoom out effect: {e}")
        return clip

def apply_fade_effect(clip):
    """Apply fade in/out effect to clip."""
    try:
        fade_duration = min(0.5, clip.duration / 4)  # Max 0.5s or 1/4 of clip duration
        return clip.fadein(fade_duration).fadeout(fade_duration)
    except Exception as e:
        print(f"Error applying fade effect: {e}")
        return clip

def create_simple_moviepy_video_optimized(image_paths, audio_path, output_path, audio_duration, optimal_threads):
    """Optimized simple fallback method using MoviePy."""
    try:
        print(f"🔄 Using optimized simple MoviePy fallback method with {optimal_threads} threads...")
        
        # Set threading
        os.environ['MOVIEPY_NTHREADS'] = str(optimal_threads)
        
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        
        # Use first image for entire duration
        first_image = image_paths[0]
        video_clip = ImageClip(first_image, duration=audio_clip.duration)
        video_clip = video_clip.resize(height=720)
        
        # Center crop if needed
        if video_clip.w > 1280:
            video_clip = video_clip.crop(x_center=video_clip.w/2, width=1280)
        
        # Set audio
        final_video = video_clip.set_audio(audio_clip)
        
        # Render with threading
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=25,
            preset='fast',
            ffmpeg_params=['-threads', str(optimal_threads)],
            threads=optimal_threads,
            verbose=False,
            logger=None
        )
        
        # Clean up
        final_video.close()
        audio_clip.close()
        video_clip.close()
        
        print(f"✅ Simple video rendered successfully with {optimal_threads} threads")
        return True, f"Video berhasil dibuat dengan metode sederhana MoviePy ({optimal_threads} threads)."
        
    except Exception as e:
        print(f"Error in optimized simple MoviePy method: {e}")
        return False, f"Gagal membuat video: {str(e)}"

def create_advanced_moviepy_video_optimized(image_paths, audio_path, output_path, audio_duration, effects_config, optimal_threads):
    """Advanced MoviePy video creation with sophisticated effects and threading optimization."""
    try:
        print(f"🚀 Creating advanced MoviePy video with {optimal_threads} threads and sophisticated effects...")
        
        # Set threading
        os.environ['MOVIEPY_NTHREADS'] = str(optimal_threads)
        
        # Get system profile for optimization
        system_profile = get_system_performance_profile()
        
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        duration_per_image = audio_clip.duration / len(image_paths)
        
        clips = []
        
        print(f"📸 Processing {len(image_paths)} images with advanced effects...")
        
        for i, img_path in enumerate(image_paths):
            # Create image clip
            img_clip = ImageClip(img_path, duration=duration_per_image)
            img_clip = img_clip.resize(height=720)
            
            # Center crop if needed
            if img_clip.w > 1280:
                img_clip = img_clip.crop(x_center=img_clip.w/2, width=1280)
            
            # Apply random effects based on system capability
            if effects_config.get('enabled', False):
                effect_type = random.choice(['zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'still'])
                
                if system_profile['tier'] != 'low-end':
                    if effect_type == 'zoom_in':
                        img_clip = img_clip.resize(lambda t: 1 + 0.02*t)
                    elif effect_type == 'zoom_out':
                        img_clip = img_clip.resize(lambda t: 1.2 - 0.02*t)
                    elif effect_type == 'pan_left':
                        img_clip = img_clip.set_position(lambda t: (-10*t, 'center'))
                    elif effect_type == 'pan_right':
                        img_clip = img_clip.set_position(lambda t: (10*t, 'center'))
            
            # Add transitions
            if i > 0 and system_profile['tier'] != 'low-end':
                img_clip = img_clip.crossfadein(0.5)
            
            clips.append(img_clip)
        
        # Concatenate clips
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip)
        
        # Render with optimal settings
        preset = 'medium' if system_profile['tier'] == 'high-end' else 'fast'
        
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=30 if system_profile['tier'] == 'high-end' else 25,
            preset=preset,
            ffmpeg_params=['-threads', str(optimal_threads)],
            threads=optimal_threads,
            verbose=False,
            logger=None
        )
        
        # Clean up
        final_video.close()
        audio_clip.close()
        for clip in clips:
            clip.close()
        
        print(f"✅ Advanced video rendered successfully with {optimal_threads} threads")
        return True, f"Video berhasil dibuat dengan efek advanced MoviePy ({optimal_threads} threads)."
        
    except Exception as e:
        print(f"Error in advanced MoviePy method: {e}")
        return False, f"Gagal membuat video advanced: {str(e)}"
