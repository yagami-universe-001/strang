import math
import time
import os
from datetime import datetime

def humanbytes(size):
    """Convert bytes to human readable format"""
    if not size:
        return "0 B"
    
    power = 2**10
    n = 0
    units = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    
    while size > power:
        size /= power
        n += 1
    
    return f"{round(size, 2)} {units[n]}B"

def time_formatter(seconds):
    """Format seconds to human readable time"""
    if seconds is None or seconds == 0:
        return "Unknown"
    
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def progress_bar(percentage):
    """Generate progress bar"""
    filled = int(percentage / 10)
    empty = 10 - filled
    return "●" * filled + "□" * empty

async def progress_message(current, total, status_msg, start_time, text="Processing"):
    """Update progress message"""
    try:
        now = time.time()
        diff = now - start_time
        
        if diff < 3:  # Update every 3 seconds
            return
        
        percentage = (current / total) * 100
        speed = current / diff if diff > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        
        elapsed_time = time_formatter(diff)
        eta_time = time_formatter(eta)
        
        progress_str = progress_bar(percentage)
        
        text_msg = (
            f"**{text}**\n\n"
            f"╭──「 {progress_str} 」── {percentage:.1f}%\n"
            f"├ **Sᴘᴇᴇᴅ:** {humanbytes(speed)}/s\n"
            f"├ **Sɪᴢᴇ:** {humanbytes(current)} / {humanbytes(total)}\n"
            f"├ **ETA:** {eta_time}\n"
            f"╰ **Eʟᴀᴘsᴇᴅ:** {elapsed_time}"
        )
        
        await status_msg.edit_text(text_msg)
        
    except Exception as e:
        pass

async def progress_for_pyrogram(current, total, ud_type, message, start):
    """Progress callback for Pyrogram"""
    now = time.time()
    diff = now - start
    
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = time_formatter(elapsed_time)
        estimated_total_time = time_formatter(estimated_total_time)

        progress = progress_bar(percentage)

        tmp = (
            f"**{ud_type}**\n\n"
            f"╭──「 {progress} 」── {percentage:.1f}%\n"
            f"├ **Sᴘᴇᴇᴅ:** {humanbytes(speed)}/s\n"
            f"├ **Pʀᴏᴄᴇssᴇᴅ:** {humanbytes(current)}\n"
            f"├ **Tᴏᴛᴀʟ:** {humanbytes(total)}\n"
            f"├ **ETA:** {estimated_total_time}\n"
            f"╰ **Eʟᴀᴘsᴇᴅ:** {elapsed_time}"
        )
        
        try:
            await message.edit_text(text=tmp)
        except:
            pass

def get_file_info(message):
    """Extract file information from message"""
    if message.video:
        media = message.video
        media_type = "Video"
    elif message.document:
        media = message.document
        media_type = "Document"
    elif message.audio:
        media = message.audio
        media_type = "Audio"
    else:
        return None
    
    file_name = getattr(media, 'file_name', f'file_{int(time.time())}')
    file_size = media.file_size
    duration = getattr(media, 'duration', 0)
    
    return {
        'type': media_type,
        'file_name': file_name,
        'file_size': file_size,
        'file_size_human': humanbytes(file_size),
        'duration': duration,
        'duration_human': time_formatter(duration) if duration else "Unknown",
        'mime_type': getattr(media, 'mime_type', 'Unknown')
    }

def format_media_info(info_dict):
    """Format media info for display"""
    if not info_dict:
        return "Unable to extract media information"
    
    format_info = info_dict.get('format', {})
    video_stream = None
    audio_stream = None
    
    for stream in info_dict.get('streams', []):
        if stream['codec_type'] == 'video' and not video_stream:
            video_stream = stream
        elif stream['codec_type'] == 'audio' and not audio_stream:
            audio_stream = stream
    
    text = "📊 **Mᴇᴅɪᴀ Iɴғᴏʀᴍᴀᴛɪᴏɴ**\n\n"
    
    # General Info
    text += "**📁 Gᴇɴᴇʀᴀʟ:**\n"
    text += f"├ **Fɪʟᴇ Nᴀᴍᴇ:** `{format_info.get('filename', 'Unknown')}`\n"
    text += f"├ **Fᴏʀᴍᴀᴛ:** {format_info.get('format_name', 'Unknown').upper()}\n"
    text += f"├ **Sɪᴢᴇ:** {humanbytes(int(format_info.get('size', 0)))}\n"
    text += f"├ **Dᴜʀᴀᴛɪᴏɴ:** {time_formatter(float(format_info.get('duration', 0)))}\n"
    text += f"╰ **Bɪᴛʀᴀᴛᴇ:** {int(int(format_info.get('bit_rate', 0))/1000)} Kbps\n\n"
    
    # Video Info
    if video_stream:
        text += "**🎬 Vɪᴅᴇᴏ:**\n"
        text += f"├ **Cᴏᴅᴇᴄ:** {video_stream.get('codec_name', 'Unknown').upper()}\n"
        text += f"├ **Rᴇsᴏʟᴜᴛɪᴏɴ:** {video_stream.get('width')}x{video_stream.get('height')}\n"
        text += f"├ **FPS:** {eval(video_stream.get('r_frame_rate', '0/1')):.2f}\n"
        text += f"╰ **Bɪᴛʀᴀᴛᴇ:** {int(int(video_stream.get('bit_rate', 0))/1000)} Kbps\n\n"
    
    # Audio Info
    if audio_stream:
        text += "**🔊 Aᴜᴅɪᴏ:**\n"
        text += f"├ **Cᴏᴅᴇᴄ:** {audio_stream.get('codec_name', 'Unknown').upper()}\n"
        text += f"├ **Sᴀᴍᴘʟᴇ Rᴀᴛᴇ:** {audio_stream.get('sample_rate', 'Unknown')} Hz\n"
        text += f"├ **Cʜᴀɴɴᴇʟs:** {audio_stream.get('channels', 'Unknown')}\n"
        text += f"╰ **Bɪᴛʀᴀᴛᴇ:** {int(int(audio_stream.get('bit_rate', 0))/1000)} Kbps\n"
    
    return text

def parse_time_string(time_str):
    """Parse time string (HH:MM:SS) to seconds"""
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(parts[0])
    except:
        return 0

def seconds_to_time_string(seconds):
    """Convert seconds to time string (HH:MM:SS)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def clean_filename(filename):
    """Clean filename by removing invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def sizeof_fmt(num, suffix='B'):
    """Format file size"""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def get_readable_time(seconds):
    """Get readable time from seconds"""
    count = 0
    readable_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "d"]
    
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    
    if len(time_list) == 4:
        readable_time += time_list.pop() + ", "
    
    time_list.reverse()
    readable_time += ":".join(time_list)
    
    return readable_time

async def get_video_duration(file_path):
    """Get video duration using ffprobe"""
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return float(stdout.decode().strip())
    except:
        return 0

async def get_video_resolution(file_path):
    """Get video resolution"""
    try:
        cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "{file_path}"'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip()
    except:
        return "Unknown"

def is_admin(user_id, admin_list):
    """Check if user is admin"""
    return user_id in admin_list

def generate_random_string(length=10):
    """Generate random string"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
