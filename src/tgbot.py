import aiohttp

class TgBot:
    url = 'https://api.telegram.org/bot7838663882:AAFSHUSyBbuI22GAwNlNzsC2C8wC5kFNsEs/sendMessage'

    @classmethod
    def get_body(cls, text: str) -> dict:
        return {"chat_id": "-4698292891", "text": text}
    
    @classmethod
    async def send_message(cls, text: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(cls.url, data=cls.get_body(text)) as response:
                data = await response.json()
                return data