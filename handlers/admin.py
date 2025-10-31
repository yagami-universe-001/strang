from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from helpers.database import Database
from helpers.utils import humanbytes
import os
import sys
import asyncio
import subprocess

db = Database()

def admin_filter(func):
    """Decorator to check if user is admin"""
    async def wrapper(client, message):
        if message.from_user.id not in Config.ADMIN_ID:
            await message.reply_text("⛔ **Aᴄᴄᴇss Dᴇɴɪᴇᴅ!**\n\nThis command is only for administrators.")
            return
        return await func(client, message)
    return wrapper

# Restart Command
@Client.on_message(filters.command("restart") & filters.private)
@admin_filter
async def restart_handler(client, message: Message):
    msg = await message.reply_text("🔄 **Rᴇsᴛᴀʀᴛɪɴɢ...**")
    await msg.edit_text("✅ **Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!**")
    os.execl(sys.executable, sys.executable, *sys.argv)

# Queue Management
@Client.on_message(filters.command("queue") & filters.private)
@admin_filter
async def queue_handler(client, message: Message):
    from bot import encoding_queue, active_processes
    
    queue_size = encoding_queue.qsize()
    active_count = len(active_processes)
    
    text = f"""
📊 **Qᴜᴇᴜᴇ Sᴛᴀᴛᴜs**

📝 **Pᴇɴᴅɪɴɢ Tᴀsᴋs:** {queue_size}
⚙️ **Aᴄᴛɪᴠᴇ Tᴀsᴋs:** {active_count}
"""
    
    if active_processes:
        text += "\n**Aᴄᴛɪᴠᴇ Usᴇʀs:**\n"
        for user_id in active_processes.keys():
            text += f"• User ID: `{user_id}`\n"
    
    await message.reply_text(text)

@Client.on_message(filters.command("clear") & filters.private)
@admin_filter
async def clear_queue_handler(client, message: Message):
    from bot import encoding_queue, active_processes
    
    # Clear queue
    while not encoding_queue.empty():
        try:
            encoding_queue.get_nowait()
        except:
            break
    
    # Clear active processes
    active_processes.clear()
    
    await message.reply_text("✅ **Qᴜᴇᴜᴇ Cʟᴇᴀʀᴇᴅ!**")

# Settings Commands
@Client.on_message(filters.command("audio") & filters.private)
@admin_filter
async def audio_bitrate_handler(client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_bot_settings()
        await message.reply_text(
            f"🔊 **Cᴜʀʀᴇɴᴛ Aᴜᴅɪᴏ Bɪᴛʀᴀᴛᴇ:** `{settings.get('audio_bitrate', '128k')}`\n\n"
            f"**Usᴀɢᴇ:** `/audio <bitrate>`\n"
            f"**Exᴀᴍᴘʟᴇ:** `/audio 192k`"
        )
        return
    
    bitrate = message.command[1]
    await db.update_bot_settings({'audio_bitrate': bitrate})
    await message.reply_text(f"✅ **Aᴜᴅɪᴏ ʙɪᴛʀᴀᴛᴇ sᴇᴛ ᴛᴏ:** `{bitrate}`")

@Client.on_message(filters.command("codec") & filters.private)
@admin_filter
async def codec_handler(client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_bot_settings()
        await message.reply_text(
            f"🎬 **Cᴜʀʀᴇɴᴛ Vɪᴅᴇᴏ Cᴏᴅᴇᴄ:** `{settings.get('video_codec', 'libx264')}`\n\n"
            f"**Usᴀɢᴇ:** `/codec <codec_name>`\n"
            f"**Exᴀᴍᴘʟᴇ:** `/codec libx265`\n\n"
            f"**Aᴠᴀɪʟᴀʙʟᴇ Cᴏᴅᴇᴄs:**\n"
            f"• libx264 (H.264)\n"
            f"• libx265 (H.265/HEVC)\n"
            f"• libvpx-vp9 (VP9)"
        )
        return
    
    codec = message.command[1]
    await db.update_bot_settings({'video_codec': codec})
    await message.reply_text(f"✅ **Vɪᴅᴇᴏ ᴄᴏᴅᴇᴄ sᴇᴛ ᴛᴏ:** `{codec}`")

@Client.on_message(filters.command("preset") & filters.private)
@admin_filter
async def preset_handler(client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_bot_settings()
        await message.reply_text(
            f"⚙️ **Cᴜʀʀᴇɴᴛ Pʀᴇsᴇᴛ:** `{settings.get('preset', 'medium')}`\n\n"
            f"**Usᴀɢᴇ:** `/preset <preset_name>`\n\n"
            f"**Aᴠᴀɪʟᴀʙʟᴇ Pʀᴇsᴇᴛs:**\n"
            f"• ultrafast (Fastest, lowest quality)\n"
            f"• superfast\n"
            f"• veryfast\n"
            f"• faster\n"
            f"• fast\n"
            f"• medium (Balanced) ⭐\n"
            f"• slow\n"
            f"• slower\n"
            f"• veryslow (Slowest, best quality)"
        )
        return
    
    preset = message.command[1]
    valid_presets = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']
    
    if preset not in valid_presets:
        await message.reply_text("⚠️ **Invalid preset!** Choose from: " + ", ".join(valid_presets))
        return
    
    await db.update_bot_settings({'preset': preset})
    await message.reply_text(f"✅ **Pʀᴇsᴇᴛ sᴇᴛ ᴛᴏ:** `{preset}`")

@Client.on_message(filters.command("crf") & filters.private)
@admin_filter
async def crf_handler(client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_bot_settings()
        await message.reply_text(
            f"🎯 **Cᴜʀʀᴇɴᴛ CRF Vᴀʟᴜᴇ:** `{settings.get('crf', 28)}`\n\n"
            f"**Usᴀɢᴇ:** `/crf <value>`\n"
            f"**Rᴀɴɢᴇ:** 0-51\n"
            f"**Rᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ:** 18-28\n\n"
            f"• Lower value = Better quality, larger size\n"
            f"• Higher value = Lower quality, smaller size"
        )
        return
    
    try:
        crf = int(message.command[1])
        if crf < 0 or crf > 51:
            await message.reply_text("⚠️ **CRF value must be between 0-51!**")
            return
        
        await db.update_bot_settings({'crf': crf})
        await message.reply_text(f"✅ **CRF ᴠᴀʟᴜᴇ sᴇᴛ ᴛᴏ:** `{crf}`")
    except ValueError:
        await message.reply_text("⚠️ **Invalid CRF value! Must be a number.**")

# Force Subscription Management
@Client.on_message(filters.command("addchnl") & filters.private)
@admin_filter
async def add_fsub_channel(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "**Usᴀɢᴇ:** `/addchnl <channel_id>`\n"
            "**Exᴀᴍᴘʟᴇ:** `/addchnl -1001234567890`"
        )
        return
    
    try:
        channel_id = int(message.command[1])
        await db.add_fsub_channel(channel_id)
        await message.reply_text(f"✅ **Cʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ ᴛᴏ ғsᴜʙ!**\n\nChannel ID: `{channel_id}`")
    except ValueError:
        await message.reply_text("⚠️ **Invalid channel ID!**")

@Client.on_message(filters.command("delchnl") & filters.private)
@admin_filter
async def del_fsub_channel(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "**Usᴀɢᴇ:** `/delchnl <channel_id>`\n"
            "**Exᴀᴍᴘʟᴇ:** `/delchnl -1001234567890`"
        )
        return
    
    try:
        channel_id = int(message.command[1])
        await db.remove_fsub_channel(channel_id)
        await message.reply_text(f"✅ **Cʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ғsᴜʙ!**\n\nChannel ID: `{channel_id}`")
    except ValueError:
        await message.reply_text("⚠️ **Invalid channel ID!**")

@Client.on_message(filters.command("listchnl") & filters.private)
@admin_filter
async def list_fsub_channels(client, message: Message):
    channels = await db.get_fsub_channels()
    
    if not channels:
        await message.reply_text("📝 **Nᴏ ғsᴜʙ ᴄʜᴀɴɴᴇʟs ᴄᴏɴғɪɢᴜʀᴇᴅ!**")
        return
    
    text = "📢 **Fsᴜʙ Cʜᴀɴɴᴇʟs:**\n\n"
    for channel_id in channels:
        try:
            chat = await client.get_chat(channel_id)
            text += f"• {chat.title} (`{channel_id}`)\n"
        except:
            text += f"• Channel ID: `{channel_id}`\n"
    
    await message.reply_text(text)

# Premium User Management
@Client.on_message(filters.command("addpaid") & filters.private)
@admin_filter
async def add_premium_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "**Usᴀɢᴇ:** `/addpaid <user_id> [days]`\n"
            "**Exᴀᴍᴘʟᴇ:** `/addpaid 123456789 30`\n"
            "**Dᴇғᴀᴜʟᴛ:** 30 days"
        )
        return
    
    try:
        user_id = int(message.command[1])
        days = int(message.command[2]) if len(message.command) > 2 else 30
        
        await db.add_premium_user(user_id, days)
        await message.reply_text(
            f"✅ **Pʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ɢʀᴀɴᴛᴇᴅ!**\n\n"
            f"**Usᴇʀ ID:** `{user_id}`\n"
            f"**Dᴜʀᴀᴛɪᴏɴ:** {days} days"
        )
    except ValueError:
        await message.reply_text("⚠️ **Invalid user ID or days!**")

@Client.on_message(filters.command("rempaid") & filters.private)
@admin_filter
async def remove_premium_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "**Usᴀɢᴇ:** `/rempaid <user_id>`\n"
            "**Exᴀᴍᴘʟᴇ:** `/rempaid 123456789`"
        )
        return
    
    try:
        user_id = int(message.command[1])
        await db.remove_premium_user(user_id)
        await message.reply_text(f"✅ **Pʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʀᴇᴍᴏᴠᴇᴅ!**\n\nUser ID: `{user_id}`")
    except ValueError:
        await message.reply_text("⚠️ **Invalid user ID!**")

@Client.on_message(filters.command("listpaid") & filters.private)
@admin_filter
async def list_premium_users(client, message: Message):
    premium_users = await db.get_premium_users()
    
    text = "💎 **Pʀᴇᴍɪᴜᴍ Usᴇʀs:**\n\n"
    count = 0
    
    async for user in premium_users:
        count += 1
        expire = user['expire_date'].strftime("%Y-%m-%d")
        text += f"{count}. User ID: `{user['user_id']}`\n   Expires: {expire}\n\n"
    
    if count == 0:
        text = "💎 **Nᴏ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs!**"
    
    await message.reply_text(text)

# Update Command
@Client.on_message(filters.command("update") & filters.private)
@admin_filter
async def update_handler(client, message: Message):
    msg = await message.reply_text("🔄 **Cʜᴇᴄᴋɪɴɢ ғᴏʀ ᴜᴘᴅᴀᴛᴇs...**")
    
    try:
        result = subprocess.run(
            ['git', 'pull'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            if "Already up to date" in output:
                await msg.edit_text("✅ **Bᴏᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴜᴘ ᴛᴏ ᴅᴀᴛᴇ!**")
            else:
                await msg.edit_text(f"✅ **Uᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**\n\n```\n{output}\n```\n\nRestarting...")
                os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            await msg.edit_text(f"❌ **Uᴘᴅᴀᴛᴇ ғᴀɪʟᴇᴅ!**\n\n```\n{result.stderr}\n```")
    except Exception as e:
        await msg.edit_text(f"❌ **Eʀʀᴏʀ:** `{str(e)}`")

# Statistics
@Client.on_message(filters.command("stats") & filters.private)
@admin_filter
async def stats_handler(client, message: Message):
    total_users = await db.total_users_count()
    premium_users = await db.get_premium_user_count()
    total_encodes = await db.get_total_encodes()
    
    text = f"""
📊 **Bᴏᴛ Sᴛᴀᴛɪsᴛɪᴄs**

👥 **Tᴏᴛᴀʟ Usᴇʀs:** {total_users}
💎 **Pʀᴇᴍɪᴜᴍ Usᴇʀs:** {premium_users}
🎬 **Tᴏᴛᴀʟ Eɴᴄᴏᴅᴇs:** {total_encodes}
"""
    
    await message.reply_text(text)

# Broadcast
@Client.on_message(filters.command("broadcast") & filters.private)
@admin_filter
async def broadcast_handler(client, message: Message):
    if message.reply_to_message:
        msg = await message.reply_text("📢 **Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ...**")
        
        users = await db.get_all_users()
        success = 0
        failed = 0
        
        async for user in users:
            try:
                await message.reply_to_message.copy(user['user_id'])
                success += 1
            except:
                failed += 1
            
            if (success + failed) % 20 == 0:
                await msg.edit_text(
                    f"📢 **Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ...**\n\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}"
                )
        
        await msg.edit_text(
            f"✅ **Bʀᴏᴀᴅᴄᴀsᴛ Cᴏᴍᴘʟᴇᴛᴇᴅ!**\n\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}"
        )
    else:
        await message.reply_text("⚠️ **Reply to a message to broadcast it!**")
