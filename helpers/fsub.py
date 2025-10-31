from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from config import Config
import logging

logger = logging.getLogger(__name__)

async def check_fsub(client, message, db):
    """Check if user is subscribed to force sub channels"""
    try:
        user_id = message.from_user.id
        
        # Admins bypass fsub
        if user_id in Config.ADMIN_ID:
            return True
        
        # Get fsub channels from database
        fsub_channels = await db.get_fsub_channels()
        
        if not fsub_channels:
            return True
        
        not_subscribed = []
        buttons = []
        
        for channel_id in fsub_channels:
            try:
                # Check if user is member of channel
                member = await client.get_chat_member(channel_id, user_id)
                
                if member.status in ["kicked", "left"]:
                    not_subscribed.append(channel_id)
                    
            except UserNotParticipant:
                not_subscribed.append(channel_id)
            except Exception as e:
                logger.error(f"Error checking fsub for {channel_id}: {e}")
                continue
        
        if not_subscribed:
            # Create join buttons
            for channel_id in not_subscribed:
                try:
                    chat = await client.get_chat(channel_id)
                    invite_link = chat.invite_link
                    
                    if not invite_link:
                        invite_link = await client.export_chat_invite_link(channel_id)
                    
                    buttons.append([InlineKeyboardButton(
                        f"📢 Jᴏɪɴ {chat.title}",
                        url=invite_link
                    )])
                except Exception as e:
                    logger.error(f"Error getting invite link for {channel_id}: {e}")
            
            # Add try again button
            buttons.append([InlineKeyboardButton("🔄 Tʀʏ Aɢᴀɪɴ", callback_data="check_fsub")])
            
            await message.reply_text(
                "⚠️ **Fᴏʀᴄᴇ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ**\n\n"
                "Yᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ(s) ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ!\n\n"
                "Pʟᴇᴀsᴇ ᴊᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ(s) ʙᴇʟᴏᴡ ᴀɴᴅ ᴄʟɪᴄᴋ '🔄 Tʀʏ Aɢᴀɪɴ'",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error in check_fsub: {e}")
        return True

async def handle_fsub_callback(client, callback, db):
    """Handle force subscription callback"""
    user_id = callback.from_user.id
    
    # Get fsub channels
    fsub_channels = await db.get_fsub_channels()
    
    if not fsub_channels:
        await callback.answer("✅ No force subscription required!", show_alert=True)
        await callback.message.delete()
        return True
    
    not_subscribed = []
    
    for channel_id in fsub_channels:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ["kicked", "left"]:
                not_subscribed.append(channel_id)
        except UserNotParticipant:
            not_subscribed.append(channel_id)
        except:
            continue
    
    if not_subscribed:
        await callback.answer(
            "⚠️ You haven't joined all channels yet!",
            show_alert=True
        )
        return False
    else:
        await callback.answer("✅ Thank you for joining!", show_alert=True)
        await callback.message.delete()
        return True
