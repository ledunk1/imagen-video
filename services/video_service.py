import subprocess
import os
import tempfile
import random
from moviepy.editor import *
from moviepy.video.fx import resize, fadein, fadeout
from moviepy.video.fx.all import crop
import numpy as np

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
    """Membuat video dari gambar dan audio menggunakan MoviePy dengan efek visual."""
    
    if not image_paths:
        return False, "Tidak ada gambar untuk dibuat video."
    
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
        
        # Create video clips from images
        video_clips = []
        
        for i, img_path in enumerate(valid_images):
            print(f"Processing image {i+1}/{len(valid_images)}: {os.path.basename(img_path)}")
            
            try:
                # Load image as video clip
                img_clip = ImageClip(img_path, duration=duration_per_image)
                
                # Resize to target resolution (1280x720)
                img_clip = img_clip.resize(height=720)
                
                # Center crop if needed to maintain aspect ratio
                if img_clip.w > 1280:
                    img_clip = img_clip.crop(x_center=img_clip.w/2, width=1280)
                
                # Apply effects based on configuration
                if effects_config.get('enabled', False):
                    img_clip = apply_visual_effects(img_clip, effects_config, i)
                
                # Add fade transitions
                if i > 0:  # Not first clip
                    img_clip = img_clip.crossfadein(0.5)
                if i < len(valid_images) - 1:  # Not last clip
                    img_clip = img_clip.crossfadeout(0.5)
                
                video_clips.append(img_clip)
                
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                # Create a black clip as fallback
                black_clip = ColorClip(size=(1280, 720), color=(0,0,0), duration=duration_per_image)
                video_clips.append(black_clip)
        
        if not video_clips:
            return False, "Gagal memproses gambar apa pun."
        
        print("Concatenating video clips...")
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
        
        print(f"Rendering video to: {output_path}")
        print(f"Final video duration: {final_video.duration:.2f} seconds")
        
        # Render video with appropriate codec
        codec = 'libx264'
        if use_gpu:
            # Try GPU acceleration
            try:
                final_video.write_videofile(
                    output_path,
                    codec='h264_nvenc',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    fps=30,
                    preset='fast',
                    ffmpeg_params=['-crf', '23']
                )
                print("Video rendered successfully with GPU acceleration")
            except Exception as e:
                print(f"GPU rendering failed: {e}")
                print("Falling back to CPU rendering...")
                codec = 'libx264'
        
        if codec == 'libx264':
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=30,
                preset='medium',
                ffmpeg_params=['-crf', '23']
            )
            print("Video rendered successfully with CPU")
        
        # Clean up
        final_video.close()
        audio_clip.close()
        for clip in video_clips:
            clip.close()
        
        return True, "Video berhasil dibuat dengan MoviePy."
        
    except Exception as e:
        print(f"Error in MoviePy video creation: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to simple method
        return create_simple_moviepy_video(valid_images, audio_path, output_path, audio_duration)

def apply_visual_effects(clip, effects_config, image_index):
    """Apply visual effects to image clip based on configuration."""
    
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
        # Zoom in effect
        return apply_zoom_in_effect(clip)
    elif rand_val <= zoom_in_prob + zoom_out_prob:
        # Zoom out effect
        return apply_zoom_out_effect(clip)
    elif rand_val <= zoom_in_prob + zoom_out_prob + fade_prob:
        # Fade effect
        return apply_fade_effect(clip)
    else:
        # Still image (no effect)
        return clip

def apply_zoom_in_effect(clip):
    """Apply zoom in effect to clip."""
    try:
        def zoom_in(get_frame, t):
            frame = get_frame(t)
            # Calculate zoom factor (1.0 to 1.3 over duration)
            zoom_factor = 1.0 + (t / clip.duration) * 0.3
            
            # Get frame dimensions
            h, w = frame.shape[:2]
            
            # Calculate crop dimensions
            crop_h = int(h / zoom_factor)
            crop_w = int(w / zoom_factor)
            
            # Calculate crop position (center)
            start_h = (h - crop_h) // 2
            start_w = (w - crop_w) // 2
            
            # Crop and resize
            cropped = frame[start_h:start_h+crop_h, start_w:start_w+crop_w]
            
            # Resize back to original size
            from PIL import Image
            pil_img = Image.fromarray(cropped)
            resized = pil_img.resize((w, h), Image.LANCZOS)
            
            return np.array(resized)
        
        return clip.fl(zoom_in, apply_to=['mask'])
    except Exception as e:
        print(f"Error applying zoom in effect: {e}")
        return clip

def apply_zoom_out_effect(clip):
    """Apply zoom out effect to clip."""
    try:
        def zoom_out(get_frame, t):
            frame = get_frame(t)
            # Calculate zoom factor (1.3 to 1.0 over duration)
            zoom_factor = 1.3 - (t / clip.duration) * 0.3
            
            # Get frame dimensions
            h, w = frame.shape[:2]
            
            # Calculate crop dimensions
            crop_h = int(h / zoom_factor)
            crop_w = int(w / zoom_factor)
            
            # Calculate crop position (center)
            start_h = (h - crop_h) // 2
            start_w = (w - crop_w) // 2
            
            # Crop and resize
            cropped = frame[start_h:start_h+crop_h, start_w:start_w+crop_w]
            
            # Resize back to original size
            from PIL import Image
            pil_img = Image.fromarray(cropped)
            resized = pil_img.resize((w, h), Image.LANCZOS)
            
            return np.array(resized)
        
        return clip.fl(zoom_out, apply_to=['mask'])
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

def create_simple_moviepy_video(image_paths, audio_path, output_path, audio_duration):
    """Simple fallback method using MoviePy."""
    try:
        print("Using simple MoviePy fallback method...")
        
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
        
        # Render
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=30,
            preset='fast'
        )
        
        # Clean up
        final_video.close()
        audio_clip.close()
        video_clip.close()
        
        return True, "Video berhasil dibuat dengan metode sederhana MoviePy."
        
    except Exception as e:
        print(f"Error in simple MoviePy method: {e}")
        return False, f"Gagal membuat video: {str(e)}"

def create_advanced_moviepy_video(image_paths, audio_path, output_path, audio_duration, effects_config):
    """Advanced MoviePy video creation with sophisticated effects."""
    try:
        print("Creating advanced MoviePy video with sophisticated effects...")
        
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        duration_per_image = audio_clip.duration / len(image_paths)
        
        clips = []
        
        for i, img_path in enumerate(image_paths):
            # Create image clip
            img_clip = ImageClip(img_path, duration=duration_per_image)
            img_clip = img_clip.resize(height=720)
            
            # Center crop if needed
            if img_clip.w > 1280:
                img_clip = img_clip.crop(x_center=img_clip.w/2, width=1280)
            
            # Apply random effects
            if effects_config.get('enabled', False):
                effect_type = random.choice(['zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'still'])
                
                if effect_type == 'zoom_in':
                    img_clip = img_clip.resize(lambda t: 1 + 0.02*t)
                elif effect_type == 'zoom_out':
                    img_clip = img_clip.resize(lambda t: 1.2 - 0.02*t)
                elif effect_type == 'pan_left':
                    img_clip = img_clip.set_position(lambda t: (-10*t, 'center'))
                elif effect_type == 'pan_right':
                    img_clip = img_clip.set_position(lambda t: (10*t, 'center'))
            
            # Add transitions
            if i > 0:
                img_clip = img_clip.crossfadein(0.5)
            
            clips.append(img_clip)
        
        # Concatenate clips
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip)
        
        # Render
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=30,
            preset='medium'
        )
        
        # Clean up
        final_video.close()
        audio_clip.close()
        for clip in clips:
            clip.close()
        
        return True, "Video berhasil dibuat dengan efek advanced MoviePy."
        
    except Exception as e:
        print(f"Error in advanced MoviePy method: {e}")
        return False, f"Gagal membuat video advanced: {str(e)}"
