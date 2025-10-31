# bot.py - Main Bot File
import os
import asyncio
import time
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
from config import Config
from helpers.database import Database
from helpers.ffmpeg import FFmpegHelper
from helpers.progress import progress_message
from helpers.fsub import check_fsub
from helpers.utils import humanbytes
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "VideoEncoderBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=50
)

# Initialize database
db = Database()

# Global variables
user_videos = {}
encoding_queue = asyncio.Queue()
active_processes = {}
queue_counter = 0

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    user_id = message.from_user.id
    
    # Check force subscription
    if not await check_fsub(client, message, db):
        return
    
    # Add user to database
    await db.add_user(user_id)
    
    is_premium = await db.is_premium_user(user_id)
    
    text = f"""
👋 **Wᴇʟᴄᴏᴍᴇ {message.from_user.mention}!**

🎬 **Pʀᴏғᴇssɪᴏɴᴀʟ Vɪᴅᴇᴏ Eɴᴄᴏᴅᴇʀ Bᴏᴛ**

I'm a multifunctional video editor bot with advanced features!

✨ **Fᴇᴀᴛᴜʀᴇs:**
• Multi-quality encoding (144p - 2160p)
• Watermark support (Text & Logo)
• Video compression & cropping
• Merge, trim, and edit videos
• Subtitle & audio management
• Extract media components
• Queue-based processing

💎 **Sᴛᴀᴛᴜs:** {'Premium User 🌟' if is_premium else 'Free User'}

📤 **Sᴇɴᴅ ᴀ ᴠɪᴅᴇᴏ/ᴅᴏᴄᴜᴍᴇɴᴛ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ!**

📝 Use /help for all commands
"""
    
    buttons = [
        [
            InlineKeyboardButton("📚 Hᴇʟᴘ", callback_data="help"),
            InlineKeyboardButton("ℹ️ Aʙᴏᴜᴛ", callback_data="about")
        ],
        [
            InlineKeyboardButton("👨‍💻 Cʀᴇᴀᴛᴏʀ", url="https://t.me/YourUsername"),
            InlineKeyboardButton("📢 Uᴘᴅᴀᴛᴇs", url="https://t.me/YourChannel")
        ],
        [InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close")]
    ]
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

@app.on_message(filters.command("help") & filters.private)
async def help_handler(client, message: Message):
    if not await check_fsub(client, message, db):
        return
    
    help_text = """
📚 **Cᴏᴍᴍᴀɴᴅ Lɪsᴛ**

**📤 Sᴇᴛᴛɪɴɢs:**
/setthumb - Set custom thumbnail
/getthumb - View saved thumbnail
/delthumb - Delete thumbnail
/setwatermark - Set text watermark
/getwatermark - View watermark settings
/setmedia - Set upload as video/document
/spoiler - Toggle spoiler mode
/upload - Set upload destination

**🎬 Eɴᴄᴏᴅɪɴɢ Qᴜᴀʟɪᴛɪᴇs:**
/144p, /240p, /360p, /480p
/720p, /1080p, /2160p
/all - Encode all qualities
/compress - Compress video

**✂️ Eᴅɪᴛɪɴɢ:**
/cut - Trim video (start - end time)
/crop - Change aspect ratio
/merge - Merge multiple videos
/addwatermark - Add logo watermark

**📝 Sᴜʙᴛɪᴛʟᴇs:**
/sub - Add soft subtitles
/hsub - Burn-in hard subtitles
/rsub - Remove subtitles
/extract_sub - Extract subtitle file

**🔊 Aᴜᴅɪᴏ:**
/addaudio - Replace/add audio
/remaudio - Remove audio track
/extract_audio - Extract audio file
/extract_thumb - Extract thumbnail

**ℹ️ Iɴғᴏ:**
/mediainfo - Detailed media information

**👤 Usᴀɢᴇ:**
1. Send video/document
2. Choose action from buttons
3. Bot processes in queue
4. Receive encoded file

🎯 **Jᴜsᴛ sᴇɴᴅ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ sᴛᴀʀᴛ!**
"""
    
    buttons = [[InlineKeyboardButton("🏠 Hᴏᴍᴇ", callback_data="start")]]
    await message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(buttons))

# Handle video/document uploads - NO REPLY, JUST ADD BUTTONS
@app.on_message((filters.video | filters.document) & filters.private)
async def video_handler(client, message: Message):
    user_id = message.from_user.id
    
    if not await check_fsub(client, message, db):
        return
    
    # Check if user has active process
    if user_id in active_processes:
        await message.reply_text("⚠️ **Yᴏᴜ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ᴘʀᴏᴄᴇss!**\n\nPlease wait for it to complete.")
        return
    
    media = message.video or message.document
    
    # Store video info
    user_videos[user_id] = {
        'message_id': message.id,
        'file_id': media.file_id,
        'file_name': getattr(media, 'file_name', f'video_{int(time.time())}.mp4'),
        'file_size': media.file_size,
        'duration': getattr(media, 'duration', 0)
    }
    
    # Create inline buttons - ADD DIRECTLY TO USER'S MESSAGE
    buttons = [
        [
            InlineKeyboardButton("🎬 144p", callback_data="encode_144p"),
            InlineKeyboardButton("🎬 240p", callback_data="encode_240p"),
            InlineKeyboardButton("🎬 360p", callback_data="encode_360p")
        ],
        [
            InlineKeyboardButton("🎬 480p", callback_data="encode_480p"),
            InlineKeyboardButton("🎬 720p", callback_data="encode_720p"),
            InlineKeyboardButton("🎬 1080p", callback_data="encode_1080p")
        ],
        [
            InlineKeyboardButton("🎬 2160p", callback_data="encode_2160p"),
            InlineKeyboardButton("💫 ALL", callback_data="encode_all")
        ],
        [
            InlineKeyboardButton("📊 Media Info", callback_data="media_info"),
            InlineKeyboardButton("🗜 Compress", callback_data="compress")
        ],
        [
            InlineKeyboardButton("✂️ Cut", callback_data="cut"),
            InlineKeyboardButton("⬜ Crop", callback_data="crop"),
            InlineKeyboardButton("🔗 Merge", callback_data="merge")
        ],
        [
            InlineKeyboardButton("📝 Subtitles", callback_data="subtitles_menu"),
            InlineKeyboardButton("🔊 Audio", callback_data="audio_menu")
        ]
    ]
    
    # Edit the user's message to add buttons (no separate reply)
    try:
        await message.edit_reply_markup(InlineKeyboardMarkup(buttons))
    except:
        # If can't edit (maybe not own message), reply with buttons
        await message.reply_text(
            "🎯 **Cʜᴏᴏsᴇ ᴀɴ ᴀᴄᴛɪᴏɴ:**",
            reply_markup=InlineKeyboardMarkup(buttons),
            reply_to_message_id=message.id
        )

# Callback query handler for encoding
@app.on_callback_query(filters.regex("^encode_"))
async def encode_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    quality = callback.data.split("_")[1]
    
    if user_id not in user_videos:
        await callback.answer("⚠️ Please send a video first!", show_alert=True)
        return
    
    if user_id in active_processes:
        await callback.answer("⚠️ You have an active process!", show_alert=True)
        return
    
    await callback.answer()
    
    # Get original message
    video_data = user_videos[user_id]
    
    # Add to queue
    global queue_counter
    queue_counter += 1
    task_id = f"{user_id}_{queue_counter}"
    
    # Reply to original video with processing status
    status_msg = await callback.message.reply_text(
        f"✅ **Aᴅᴅᴇᴅ ᴛᴏ Qᴜᴇᴜᴇ!**\n\n"
        f"🎯 **Qᴜᴀʟɪᴛʏ:** {quality.upper()}\n"
        f"📊 **Qᴜᴇᴜᴇ Pᴏsɪᴛɪᴏɴ:** {encoding_queue.qsize() + 1}\n\n"
        f"⏳ **Pʀᴏᴄᴇssɪɴɢ ᴡɪʟʟ sᴛᴀʀᴛ sᴏᴏɴ...**"
    )
    
    # Add to encoding queue
    await encoding_queue.put({
        'user_id': user_id,
        'task_id': task_id,
        'quality': quality,
        'callback': callback,
        'status_msg': status_msg
    })

# Queue processor
async def queue_processor():
    while True:
        try:
            task = await encoding_queue.get()
            user_id = task['user_id']
            quality = task['quality']
            status_msg = task['status_msg']
            task_id = task['task_id']
            
            # Mark as active
            active_processes[user_id] = task_id
            
            # Start encoding
            await process_encoding(user_id, quality, task_id, status_msg)
            
            # Remove from active
            if user_id in active_processes:
                del active_processes[user_id]
            
            encoding_queue.task_done()
            
        except Exception as e:
            logger.error(f"Queue processor error: {e}")
            if user_id in active_processes:
                del active_processes[user_id]

async def process_encoding(user_id, quality, task_id, status_msg):
    try:
        video_data = user_videos.get(user_id)
        if not video_data:
            await status_msg.edit_text("❌ Video data not found!")
            return
        
        file_name = video_data['file_name']
        file_size = video_data['file_size']
        
        # Download video with progress
        start_time = time.time()
        
        await status_msg.edit_text(
            f"**1. Dᴏᴡɴʟᴏᴀᴅɪɴɢ**\n\n"
            f"`{file_name}`\n\n"
            f"╭──「 ●□□□□□□□□□ 」── 0%\n"
            f"├ **Sᴘᴇᴇᴅ:** Calculating...\n"
            f"├ **Sɪᴢᴇ:** 0 B / {humanbytes(file_size)}\n"
            f"├ **ETA:** Calculating...\n"
            f"├ **Eʟᴀᴘsᴇᴅ:** 00:00:00\n"
            f"├ **Tᴀsᴋ Bʏ:** User\n"
            f"╰ **Usᴇʀ ID:** `{user_id}`\n\n"
            f"`/stop{task_id}`"
        )
        
        download_path = f"downloads/{user_id}_{int(time.time())}.mp4"
        os.makedirs("downloads", exist_ok=True)
        
        # Simulate download with progress (replace with actual download)
        async def download_progress(current, total):
            percent = (current / total) * 100
            speed = current / (time.time() - start_time) if (time.time() - start_time) > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            elapsed = time.time() - start_time
            
            bar = "●" * int(percent / 10) + "□" * (10 - int(percent / 10))
            
            await status_msg.edit_text(
                f"**1. Dᴏᴡɴʟᴏᴀᴅɪɴɢ**\n\n"
                f"`{file_name}`\n\n"
                f"╭──「 {bar} 」── {percent:.1f}%\n"
                f"├ **Sᴘᴇᴇᴅ:** {humanbytes(speed)}/s\n"
                f"├ **Sɪᴢᴇ:** {humanbytes(current)} / {humanbytes(total)}\n"
                f"├ **ETA:** {int(eta)}s\n"
                f"├ **Eʟᴀᴘsᴇᴅ:** {int(elapsed)}s\n"
                f"├ **Tᴀsᴋ Bʏ:** User\n"
                f"╰ **Usᴇʀ ID:** `{user_id}`\n\n"
                f"`/stop{task_id}`"
            )
        
        # Download file
        downloaded_file = await app.download_media(
            video_data['file_id'],
            file_name=download_path,
            progress=download_progress
        )
        
        # Encoding phase
        encode_start = time.time()
        output_path = f"encoded/{user_id}_{quality}_{int(time.time())}.mp4"
        os.makedirs("encoded", exist_ok=True)
        
        await status_msg.edit_text(
            f"**2. Eɴᴄᴏᴅɪɴɢ** ⚙️\n\n"
            f"`{file_name}`\n\n"
            f"🎯 **Qᴜᴀʟɪᴛʏ:** {quality.upper()}\n"
            f"⏱ **Pʀᴏɢʀᴇss:** Starting...\n\n"
            f"╭ **Tᴀsᴋ Bʏ:** User\n"
            f"╰ **Usᴇʀ ID:** `{user_id}`\n\n"
            f"`/stop{task_id}`"
        )
        
        # Call FFmpeg encoding (implement in helpers/ffmpeg.py)
        ffmpeg = FFmpegHelper()
        success = await ffmpeg.encode_video(
            downloaded_file,
            output_path,
            quality,
            progress_callback=lambda p: update_encode_progress(status_msg, p, file_name, quality, user_id, task_id)
        )
        
        if not success:
            await status_msg.edit_text("❌ **Eɴᴄᴏᴅɪɴɢ Fᴀɪʟᴇᴅ!**")
            return
        
        # Upload phase
        await status_msg.edit_text(
            f"**3. Uᴘʟᴏᴀᴅɪɴɢ** 📤\n\n"
            f"`{file_name}`\n\n"
            f"╭──「 ●□□□□□□□□□ 」── 0%\n"
            f"├ **Sᴘᴇᴇᴅ:** Calculating...\n"
            f"├ **ETA:** Calculating...\n"
            f"╰ **Usᴇʀ ID:** `{user_id}`"
        )
        
        # Upload encoded file
        user_settings = await db.get_user_settings(user_id)
        thumb = user_settings.get('thumbnail') if user_settings else None
        
        await app.send_video(
            chat_id=user_id,
            video=output_path,
            caption=f"✅ **Eɴᴄᴏᴅᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!**\n\n🎯 **Qᴜᴀʟɪᴛʏ:** {quality.upper()}",
            thumb=thumb,
            progress=lambda c, t: upload_progress(status_msg, c, t, file_name, user_id)
        )
        
        # Cleanup
        os.remove(downloaded_file)
        os.remove(output_path)
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Encoding error: {e}")
        await status_msg.edit_text(f"❌ **Eʀʀᴏʀ:** {str(e)}")

async def update_encode_progress(msg, progress, file_name, quality, user_id, task_id):
    await msg.edit_text(
        f"**2. Eɴᴄᴏᴅɪɴɢ** ⚙️\n\n"
        f"`{file_name}`\n\n"
        f"🎯 **Qᴜᴀʟɪᴛʏ:** {quality.upper()}\n"
        f"⏱ **Pʀᴏɢʀᴇss:** {progress}%\n\n"
        f"╭ **Tᴀsᴋ Bʏ:** User\n"
        f"╰ **Usᴇʀ ID:** `{user_id}`\n\n"
        f"`/stop{task_id}`"
    )

async def upload_progress(msg, current, total, file_name, user_id):
    percent = (current / total) * 100
    bar = "●" * int(percent / 10) + "□" * (10 - int(percent / 10))
    
    await msg.edit_text(
        f"**3. Uᴘʟᴏᴀᴅɪɴɢ** 📤\n\n"
        f"`{file_name}`\n\n"
        f"╭──「 {bar} 」── {percent:.1f}%\n"
        f"├ **Sɪᴢᴇ:** {humanbytes(current)} / {humanbytes(total)}\n"
        f"╰ **Usᴇʀ ID:** `{user_id}`"
    )

# Start queue processor on bot start
@app.on_message(filters.command("run_queue") & filters.user(Config.ADMIN_ID))
async def start_queue(client, message):
    asyncio.create_task(queue_processor())
    await message.reply_text("✅ Queue processor started!")

# Run bot
if __name__ == "__main__":
    app.run()
