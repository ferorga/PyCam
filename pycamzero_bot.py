import asyncio
import json
import telegram

async def pycamzero_bot(path):    
    with open('telegram_config.json', 'r') as file:
        config = json.load(file)
        token = config["token"]
        channel_id = config["channel_id"]
    
    bot = telegram.Bot(token=token)
    await bot.send_message(chat_id=channel_id, text='Alarma activada. Video:')
    await bot.send_video(chat_id=channel_id, video=open(path, 'rb'))
