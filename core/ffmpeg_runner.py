import os
import subprocess
import json
import time

class FFmpegRunner:
    def __init__(self, ffmpeg_path="ffmpeg.exe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
        self.current_process = None # 新增：用來追蹤目前的子進程

    def cancel(self):
        """強制終止目前的 FFmpeg 任務"""
        if self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass

    def get_video_info(self, reference_video):
        cmd = [
            self.ffprobe_path, "-v", "error", "-select_streams", "v:0",
            # 新增讀取 codec_name (編碼格式)
            "-show_entries", "stream=width,height,r_frame_rate,pix_fmt,codec_name",
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
                "pix_fmt": stream.get('pix_fmt', 'yuvj420p'),
                "codec_name": stream.get('codec_name', 'hevc') # 預設假設為 hevc
            }
        except Exception:
            return {"width": 1920, "height": 1080, "fps": "60/1", "pix_fmt": "yuvj420p", "codec_name": "hevc"}

    def verify_video_compatibility(self, file_paths, ref_info):
        """事前檢查所有影片規格是否與基準影片一致，並排除損毀或 0 秒異常檔"""
        for f in file_paths:
            # 照片會被我們動態轉碼成跟基準影片一樣，所以直接 Pass
            if f.upper().endswith(('.JPG', '.PNG', '.JPEG')):
                continue
                
            info = self.get_video_info(f)
            filename = os.path.basename(f)
            
            # 檢查 1：影片長度是否異常 (防禦 0 秒快門或損毀檔)
            duration = self.get_video_duration(f)
            if duration <= 0:
                return False, f"偵測到異常檔案 (長度為 0 秒或檔案損毀): {filename}"
            
            # 檢查 2：解析度是否一致
            if info['width'] != ref_info['width'] or info['height'] != ref_info['height']:
                return False, f"解析度不符: {filename} ({info['width']}x{info['height']} vs 基準 {ref_info['width']}x{ref_info['height']})"
            
            # 檢查 3：編碼器是否一致 (例如 h264 不能跟 hevc 直接無損合併)
            if info['codec_name'] != ref_info['codec_name']:
                return False, f"編碼格式不符: {filename} ({info['codec_name']} vs 基準 {ref_info['codec_name']})"
            
        return True, ""

    def get_video_duration(self, video_path):
        cmd = [
            self.ffprobe_path, "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def convert_image_to_video(self, image_path, ref_info, duration=3):
        temp_video_path = image_path + ".temp.mp4"
        cmd = [
            self.ffmpeg_path, "-y",
            "-loop", "1", "-i", image_path,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", str(duration),
            "-s", f"{ref_info['width']}x{ref_info['height']}",
            "-r", ref_info['fps'],
            "-pix_fmt", "yuvj420p",
            "-c:v", "libx265",
            "-c:a", "aac",
            "-shortest",
            temp_video_path
        ]
        # 使用 Popen 並紀錄進程，確保隨時可被終止
        self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.current_process.communicate()
        return temp_video_path

    def merge_videos(self, part_name, file_paths, output_folder, total_duration=0, progress_callback=None, metadata_path=None):
        if not file_paths:
            return False, "無檔案可合併"
            
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
                "-i", list_path
            ]
            
            if metadata_path and os.path.exists(metadata_path):
                cmd.extend(["-i", metadata_path, "-map_metadata", "1"])
                
            cmd.extend([
                "-map", "0:v", 
                "-map", "0:a", 
                "-c", "copy",
                "-progress", "-", "-nostats",
                output_path
            ])
            
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            
            start_time = time.time()
            last_few_lines = []
            
            for line in self.current_process.stdout:
                if "out_time_us=" in line:
                    try:
                        out_time_us = int(line.split("=")[1].strip())
                        current_sec = out_time_us / 1000000.0
                        
                        if total_duration > 0 and progress_callback:
                            percent = min(100, int((current_sec / total_duration) * 100))
                            elapsed_time = time.time() - start_time
                            
                            if current_sec > 0:
                                speed = current_sec / elapsed_time
                                eta_seconds = (total_duration - current_sec) / speed if speed > 0 else 0
                                progress_callback(percent, eta_seconds)
                    except ValueError:
                        pass
                else:
                    if line.strip():
                        last_few_lines.append(line.strip())
                        if len(last_few_lines) > 10:
                            last_few_lines.pop(0)

            self.current_process.wait()
            
            if self.current_process.returncode != 0:
                error_reason = "\n".join(last_few_lines)
                # 💡 修正：不再用 print，而是直接把錯誤訊息 return 給上層
                return False, f"FFmpeg 底層崩潰:\n{error_reason}"
            
            return True, ""
                
        except Exception as e:
            return False, f"Python 執行期例外錯誤: {str(e)}"
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)