import os
import requests
import asyncio
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from aiogram.enums import ContentType
from config import Config, load_config

HF_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
SEGMENT_DURATION_MS = 300 * 1000  # 5 минут
TEMP_FOLDER = "temp_audio"

config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token
HF_API_KEY: str = config.hf_api_key

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

def convert_to_wav(input_path):
    """ Конвертирует аудиофайл в WAV """
    output_path = os.path.splitext(input_path)[0] + ".wav"
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format="wav")
    return output_path

def split_audio(file_path):
    """ Разбивает аудиофайл на фрагменты по 5 минут """
    audio = AudioSegment.from_file(file_path)
    segments = []

    for i, start in enumerate(range(0, len(audio), SEGMENT_DURATION_MS)):
        segment_path = os.path.join(TEMP_FOLDER, f"segment_{i}.wav")
        audio[start:start + SEGMENT_DURATION_MS].export(segment_path, format="wav")
        segments.append(segment_path)

    return segments

def transcribe_audio(file_path):
    """ Отправляет аудиофайл в Hugging Face API и получает текст """
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    with open(file_path, "rb") as f:
        response = requests.post(HF_API_URL, headers=headers, files={"file": f})
    
    if response.status_code == 200:
        return response.json().get("text", "")
    else:
        return f"Ошибка API: {response.status_code} - {response.text}"

@dp.message(F.content_type.in_([ContentType.VOICE, ContentType.AUDIO, ContentType.DOCUMENT]))
async def handle_audio(message: types.Message):
    """ Обрабатывает голосовые и аудиофайлы, конвертирует и распознает текст """
    if message.voice:
        file = message.voice
    elif message.audio:
        file = message.audio
    else:  # Если файл отправлен как документ
        file = message.document
    
    file_id = file.file_id
    tg_file = await bot.get_file(file_id)
    
    if not tg_file.file_path:
        await message.answer("Не удалось получить файл. Попробуйте снова.")
        return
    
    file_ext = os.path.splitext(tg_file.file_path)[-1]  # Определяем расширение файла
    temp_path = os.path.join(TEMP_FOLDER, f"{file_id}{file_ext}")
    
    await bot.download_file(tg_file.file_path, temp_path)

    # Конвертация в WAV (если необходимо)
    if file_ext != ".wav":
        temp_path_wav = convert_to_wav(temp_path)
        os.remove(temp_path)  # Удаляем оригинал после конвертации
    else:
        temp_path_wav = temp_path

    segments = split_audio(temp_path_wav)
    full_text = ""

    for segment in segments:
        text = transcribe_audio(segment)
        full_text += text + " "

    if full_text.strip():
        await message.answer(full_text.strip())
    else:
        await message.answer("Не удалось распознать аудио.")

    # Удаление временных файлов
    os.remove(temp_path_wav)
    for segment in segments:
        os.remove(segment)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
