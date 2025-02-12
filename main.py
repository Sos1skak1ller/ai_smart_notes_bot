import os
import requests
import asyncio
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from aiogram.utils.executor import start_polling
from config import Config, load_config


HF_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
SEGMENT_DURATION_MS = 300 * 1000  # 5 минут
TEMP_FOLDER = "temp_audio"


config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token
HF_API_KEY: str = config.hf_api_key

# Создаем объекты бота и диспетчера
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

def split_audio(file_path):
    audio = AudioSegment.from_file(file_path)
    segments = []
    
    for i, start in enumerate(range(0, len(audio), SEGMENT_DURATION_MS)):
        segment_path = os.path.join(TEMP_FOLDER, f"segment_{i}.wav")
        audio[start:start + SEGMENT_DURATION_MS].export(segment_path, format="wav")
        segments.append(segment_path)
    
    return segments

def transcribe_audio(file_path):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    with open(file_path, "rb") as f:
        response = requests.post(HF_API_URL, headers=headers, files={"file": f})
    return response.json().get("text", "")

@dp.message_handler(content_types=types.ContentType.VOICE | types.ContentType.AUDIO)
async def handle_audio(message: types.Message):
    audio_file = await message.voice.download(destination_dir=TEMP_FOLDER)
    file_path = os.path.join(TEMP_FOLDER, audio_file.name)
    
    segments = split_audio(file_path)
    full_text = ""
    
    for segment in segments:
        text = transcribe_audio(segment)
        full_text += text + " "
    
    await message.reply(full_text.strip())
    
    for segment in segments:
        os.remove(segment)
    os.remove(file_path)

if __name__ == "__main__":
    start_polling(dp, skip_updates=True)
