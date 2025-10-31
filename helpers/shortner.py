import aiohttp
import logging
from config import Config

logger = logging.getLogger(__name__)

async def get_shortlink(url, api_key, api_url):
    """Generate short link"""
    try:
        if not api_key or not api_url:
            return url
        
        async with aiohttp.ClientSession() as session:
            params = {
                'api': api_key,
                'url': url
            }
            
            async with session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        return data.get('shortenedUrl', url)
                return url
                
    except Exception as e:
        logger.error(f"Error generating shortlink: {e}")
        return url

async def shorten_url(url, shortener_num=1):
    """Shorten URL using configured shortener"""
    if shortener_num == 1:
        return await get_shortlink(url, Config.SHORTENER_API_1, Config.SHORTENER_URL_1)
    elif shortener_num == 2:
        return await get_shortlink(url, Config.SHORTENER_API_2, Config.SHORTENER_URL_2)
    else:
        return url
