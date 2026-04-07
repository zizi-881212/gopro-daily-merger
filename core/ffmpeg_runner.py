import os
import subprocess
import json

class FFmpegRunner:
    def __init__(self, ffmpeg_path="ffmpeg.exe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")

    def get_video_info(self, reference_video):
        """利用 ffprobe 取得參考影片的解析度與幀率"""
        cmd = [
            self.ffprobe_path, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,pix_fmt",
            "-of", "json", reference_video
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            info = json.loads(result.stdout)
            stream = info['streams'][0]
            return {
                "width": stream.get('width', 1920),
                "height": stream.get('height', 1080),
                "fps": stream.get('r_frame_rate', '60/1'),
                "pix_fmt": stream.get('pix_fmt', 'yuvJ420p')
            }
        except Exception:
            # 預設保護機制
            return {"width": 1920, "height": 1080, "fps": "60/1", "pix_fmt": "yuvj420p"}

    def convert_image_to_video(self, image_path, ref_info, duration=3):
        """將照片轉為符合規格的 MP4 (含無聲音軌)"""
        temp_video_path = image_path + ".temp.mp4"
        cmd = [
            self.ffmpeg_path, "-y",
            "-loop", "1", "-i", image_path,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", str(duration),
            "-s", f"{ref_info['width']}x{ref_info['height']}",
            "-r", ref_info['fps'],
            "-pix_fmt", "yuvj420p", # 使用相容性最高的色彩空間
            "-c:v", "libx265",
            "-c:a", "aac",
            "-shortest",
            temp_video_path
        ]
        subprocess.run(cmd, capture_output=True)
        return temp_video_path

    def merge_videos(self, part_name, file_paths, output_folder):
        if not file_paths:
            return False
            
        output_filename = f"{part_name}_merged.mp4"
        output_path = os.path.join(output_folder, output_filename)
        list_path = os.path.join(output_folder, f"concat_{part_name}.txt")
        
        try:
            with open(list_path, 'w', encoding='utf-8') as f:
                for video_file in file_paths:
                    abs_path = os.path.abspath(video_file).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
                    
            cmd = [
                self.ffmpeg_path, "-y",                 
                "-f", "concat", "-safe", "0",         
                "-i", list_path, "-c", "copy",         
                output_path           
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return result.returncode == 0
                
        except Exception:
            return False
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)