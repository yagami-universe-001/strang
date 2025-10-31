import asyncio
import os
import re
import subprocess
import time
from config import Config
import logging

logger = logging.getLogger(__name__)

class FFmpegHelper:
    def __init__(self):
        self.preset = Config.DEFAULT_PRESET
        self.crf = Config.DEFAULT_CRF
        self.audio_bitrate = Config.DEFAULT_AUDIO_BITRATE
        self.video_codec = Config.DEFAULT_VIDEO_CODEC
    
    async def get_media_info(self, file_path):
        """Get media information using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                return json.loads(stdout.decode())
            else:
                logger.error(f"FFprobe error: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return None
    
    async def get_duration(self, file_path):
        """Get video duration in seconds"""
        info = await self.get_media_info(file_path)
        if info and 'format' in info:
            return float(info['format'].get('duration', 0))
        return 0
    
    async def encode_video(self, input_file, output_file, quality, progress_callback=None):
        """Encode video to specified quality"""
        try:
            quality_settings = Config.QUALITIES.get(quality, Config.QUALITIES['480p'])
            resolution = quality_settings['resolution']
            bitrate = quality_settings['bitrate']
            
            # Get video duration for progress calculation
            duration = await self.get_duration(input_file)
            
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', self.video_codec,
                '-preset', self.preset,
                '-crf', str(self.crf),
                '-vf', f'scale={resolution}:force_original_aspect_ratio=decrease',
                '-b:v', bitrate,
                '-c:a', 'aac',
                '-b:a', self.audio_bitrate,
                '-movflags', '+faststart',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor progress
            if progress_callback and duration > 0:
                asyncio.create_task(
                    self._monitor_encoding_progress(process, duration, progress_callback)
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully encoded: {output_file}")
                return True
            else:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error encoding video: {e}")
            return False
    
    async def _monitor_encoding_progress(self, process, total_duration, callback):
        """Monitor FFmpeg encoding progress"""
        pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
        last_update = 0
        
        while True:
            try:
                line = await process.stderr.readline()
                if not line:
                    break
                
                line = line.decode()
                match = pattern.search(line)
                
                if match:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    progress = (current_time / total_duration) * 100
                    
                    # Update progress every 3 seconds
                    current_time_check = time.time()
                    if current_time_check - last_update >= 3:
                        await callback(min(progress, 99))
                        last_update = current_time_check
                        
            except Exception as e:
                logger.error(f"Progress monitoring error: {e}")
                break
    
    async def compress_video(self, input_file, output_file, target_size_mb, progress_callback=None):
        """Compress video to target file size"""
        try:
            duration = await self.get_duration(input_file)
            if duration == 0:
                return False
            
            # Calculate bitrate for target size
            target_size_bits = target_size_mb * 8 * 1024 * 1024
            audio_bitrate_bits = 128 * 1024  # 128k
            video_bitrate = int((target_size_bits / duration) - audio_bitrate_bits)
            
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', self.video_codec,
                '-b:v', f'{video_bitrate}',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            if progress_callback:
                asyncio.create_task(
                    self._monitor_encoding_progress(process, duration, progress_callback)
                )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error compressing video: {e}")
            return False
    
    async def add_text_watermark(self, input_file, output_file, text, position='bottom_right'):
        """Add text watermark to video"""
        try:
            positions = {
                'top_left': 'x=10:y=10',
                'top_right': 'x=w-tw-10:y=10',
                'bottom_left': 'x=10:y=h-th-10',
                'bottom_right': 'x=w-tw-10:y=h-th-10',
                'center': 'x=(w-tw)/2:y=(h-th)/2'
            }
            
            pos = positions.get(position, positions['bottom_right'])
            
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-vf', f"drawtext=text='{text}':fontsize=24:fontcolor=white:borderw=2:bordercolor=black:{pos}",
                '-c:a', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            return False
    
    async def add_logo_watermark(self, input_file, output_file, logo_file, position='bottom_right'):
        """Add logo watermark to video"""
        try:
            positions = {
                'top_left': 'overlay=10:10',
                'top_right': 'overlay=W-w-10:10',
                'bottom_left': 'overlay=10:H-h-10',
                'bottom_right': 'overlay=W-w-10:H-h-10',
                'center': 'overlay=(W-w)/2:(H-h)/2'
            }
            
            overlay = positions.get(position, positions['bottom_right'])
            
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-i', logo_file,
                '-filter_complex', overlay,
                '-c:a', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding logo: {e}")
            return False
    
    async def trim_video(self, input_file, output_file, start_time, end_time):
        """Trim video from start_time to end_time (format: HH:MM:SS)"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-ss', start_time,
                '-to', end_time,
                '-c', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error trimming video: {e}")
            return False
    
    async def merge_videos(self, video_files, output_file):
        """Merge multiple videos"""
        try:
            # Create concat file
            concat_file = 'concat_list.txt'
            with open(concat_file, 'w') as f:
                for video in video_files:
                    f.write(f"file '{video}'\n")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            # Clean up
            os.remove(concat_file)
            
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error merging videos: {e}")
            return False
    
    async def extract_audio(self, input_file, output_file):
        """Extract audio from video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-vn',
                '-acodec', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return False
    
    async def remove_audio(self, input_file, output_file):
        """Remove audio from video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-an',
                '-c:v', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error removing audio: {e}")
            return False
    
    async def add_audio_to_video(self, video_file, audio_file, output_file):
        """Add/Replace audio in video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-i', audio_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding audio: {e}")
            return False
    
    async def extract_subtitles(self, input_file, output_file, stream_index=0):
        """Extract subtitles from video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-map', f'0:s:{stream_index}',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error extracting subtitles: {e}")
            return False
    
    async def add_soft_subtitle(self, video_file, subtitle_file, output_file):
        """Add soft subtitle to video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-i', subtitle_file,
                '-c', 'copy',
                '-c:s', 'mov_text',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding subtitle: {e}")
            return False
    
    async def add_hard_subtitle(self, video_file, subtitle_file, output_file):
        """Burn subtitle into video"""
        try:
            subtitle_file = subtitle_file.replace('\\', '/').replace(':', '\\:')
            
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-vf', f"subtitles='{subtitle_file}'",
                '-c:a', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding hard subtitle: {e}")
            return False
    
    async def remove_subtitles(self, input_file, output_file):
        """Remove all subtitles from video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c', 'copy',
                '-sn',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error removing subtitles: {e}")
            return False
    
    async def generate_thumbnail(self, video_file, output_file, timestamp='00:00:01'):
        """Generate thumbnail from video"""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-ss', timestamp,
                '-vframes', '1',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return False
    
    async def change_aspect_ratio(self, input_file, output_file, aspect='16:9'):
        """Change video aspect ratio"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-aspect', aspect,
                '-c', 'copy',
                '-y',
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error changing aspect ratio: {e}")
            return False
