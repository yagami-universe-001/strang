from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGODB_URI)
        self.db = self.client[Config.DB_NAME]
        self.users = self.db.users
        self.settings = self.db.settings
        self.premium = self.db.premium
        self.stats = self.db.stats
        
    async def add_user(self, user_id):
        """Add a new user to database"""
        try:
            user_data = {
                'user_id': user_id,
                'joined_date': datetime.now(),
                'last_used': datetime.now(),
                'total_encodes': 0,
                'is_banned': False
            }
            await self.users.update_one(
                {'user_id': user_id},
                {'$setOnInsert': user_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    async def get_user(self, user_id):
        """Get user data"""
        return await self.users.find_one({'user_id': user_id})
    
    async def is_user_exist(self, user_id):
        """Check if user exists"""
        user = await self.users.find_one({'user_id': user_id})
        return bool(user)
    
    async def total_users_count(self):
        """Get total users count"""
        return await self.users.count_documents({})
    
    async def get_all_users(self):
        """Get all users"""
        return self.users.find({})
    
    async def delete_user(self, user_id):
        """Delete a user"""
        await self.users.delete_one({'user_id': user_id})
    
    async def ban_user(self, user_id):
        """Ban a user"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$set': {'is_banned': True}}
        )
    
    async def unban_user(self, user_id):
        """Unban a user"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$set': {'is_banned': False}}
        )
    
    async def is_user_banned(self, user_id):
        """Check if user is banned"""
        user = await self.get_user(user_id)
        return user.get('is_banned', False) if user else False
    
    # User Settings
    async def get_user_settings(self, user_id):
        """Get user settings"""
        settings = await self.settings.find_one({'user_id': user_id})
        if not settings:
            # Default settings
            settings = {
                'user_id': user_id,
                'thumbnail': None,
                'watermark': Config.DEFAULT_WATERMARK_TEXT,
                'upload_as_doc': False,
                'spoiler_mode': False,
                'upload_destination': 'pm',  # pm or channel
                'media_type': 'video'
            }
            await self.settings.insert_one(settings)
        return settings
    
    async def update_user_settings(self, user_id, settings_dict):
        """Update user settings"""
        await self.settings.update_one(
            {'user_id': user_id},
            {'$set': settings_dict},
            upsert=True
        )
    
    async def set_thumbnail(self, user_id, file_id):
        """Set user thumbnail"""
        await self.settings.update_one(
            {'user_id': user_id},
            {'$set': {'thumbnail': file_id}},
            upsert=True
        )
    
    async def get_thumbnail(self, user_id):
        """Get user thumbnail"""
        settings = await self.settings.find_one({'user_id': user_id})
        return settings.get('thumbnail') if settings else None
    
    async def delete_thumbnail(self, user_id):
        """Delete user thumbnail"""
        await self.settings.update_one(
            {'user_id': user_id},
            {'$set': {'thumbnail': None}}
        )
    
    # Premium Users
    async def add_premium_user(self, user_id, days=30):
        """Add premium user"""
        expire_date = datetime.now() + timedelta(days=days)
        await self.premium.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'expire_date': expire_date,
                'added_date': datetime.now()
            }},
            upsert=True
        )
    
    async def remove_premium_user(self, user_id):
        """Remove premium user"""
        await self.premium.delete_one({'user_id': user_id})
    
    async def is_premium_user(self, user_id):
        """Check if user is premium"""
        if user_id in Config.ADMIN_ID:
            return True
        
        premium = await self.premium.find_one({'user_id': user_id})
        if not premium:
            return False
        
        if premium['expire_date'] < datetime.now():
            await self.remove_premium_user(user_id)
            return False
        
        return True
    
    async def get_premium_users(self):
        """Get all premium users"""
        return self.premium.find({})
    
    async def get_premium_user_count(self):
        """Get premium users count"""
        return await self.premium.count_documents({})
    
    # Stats
    async def update_encode_count(self, user_id):
        """Update user encode count"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$inc': {'total_encodes': 1}, '$set': {'last_used': datetime.now()}}
        )
    
    async def get_user_today_encodes(self, user_id):
        """Get user encodes for today"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await self.stats.count_documents({
            'user_id': user_id,
            'date': {'$gte': today}
        })
        return count
    
    async def add_encode_stat(self, user_id, quality, file_size):
        """Add encode statistics"""
        await self.stats.insert_one({
            'user_id': user_id,
            'quality': quality,
            'file_size': file_size,
            'date': datetime.now()
        })
    
    async def get_total_encodes(self):
        """Get total encodes count"""
        return await self.stats.count_documents({})
    
    # Force Sub Channels
    async def get_fsub_channels(self):
        """Get force subscription channels"""
        settings = await self.settings.find_one({'_id': 'fsub_channels'})
        return settings.get('channels', []) if settings else []
    
    async def add_fsub_channel(self, channel_id):
        """Add force subscription channel"""
        await self.settings.update_one(
            {'_id': 'fsub_channels'},
            {'$addToSet': {'channels': channel_id}},
            upsert=True
        )
    
    async def remove_fsub_channel(self, channel_id):
        """Remove force subscription channel"""
        await self.settings.update_one(
            {'_id': 'fsub_channels'},
            {'$pull': {'channels': channel_id}}
        )
    
    async def clear_fsub_channels(self):
        """Clear all force subscription channels"""
        await self.settings.delete_one({'_id': 'fsub_channels'})
    
    # Bot Settings (Admin)
    async def get_bot_settings(self):
        """Get bot settings"""
        settings = await self.settings.find_one({'_id': 'bot_settings'})
        if not settings:
            settings = {
                '_id': 'bot_settings',
                'preset': Config.DEFAULT_PRESET,
                'crf': Config.DEFAULT_CRF,
                'audio_bitrate': Config.DEFAULT_AUDIO_BITRATE,
                'video_codec': Config.DEFAULT_VIDEO_CODEC,
                'fsub_mode': 'request'  # request or force
            }
            await self.settings.insert_one(settings)
        return settings
    
    async def update_bot_settings(self, settings_dict):
        """Update bot settings"""
        await self.settings.update_one(
            {'_id': 'bot_settings'},
            {'$set': settings_dict},
            upsert=True
        )
