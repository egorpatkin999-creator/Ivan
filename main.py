# bot.py
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI

# Загрузка настроек
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ Проверь .env файл! Не найдены ключи.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================================================================================
# 🔥 ЗАГРУЗКА ПРОМПТА ИЗ ФАЙЛА
# ====================================================================================

def load_system_prompt():
    try:
        with open("system_prompt_ivan.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("❌ Файл system_prompt_ivan.txt не найден!")
        return "Ты — полезный ассистент." # Фолбэк, если файл не найден

SYSTEM_PROMPT = load_system_prompt()

user_contexts = {}

# Хэндлер /start
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_contexts[user_id] = []
    
    # Приветствие тоже разбиваем для естественности
    await message.answer("Приветствую👋")
    await asyncio.sleep(1)
    await message.answer("Я — Иван, эксперт по автоматизации продаж The-Manager)")
    await asyncio.sleep(1.5)
    await message.answer("Помогаю бизнесу не терять клиентов и спать спокойно по ночам. Расскажите, чем занимаетесь?)")

# Обработка сообщений
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in user_contexts:
        user_contexts[user_id] = []

    # Сохраняем сообщение юзера
    user_contexts[user_id].append({"role": "user", "content": message.text})
    
    # Храним больше истории, чтобы бот помнил контекст "разведки"
    if len(user_contexts[user_id]) > 20:
        user_contexts[user_id] = user_contexts[user_id][-20:]

    await bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # или gpt-4o для еще большего ума
            messages=messages,
            max_tokens=1000, # Увеличили токенов, т.к. промпт большой
            temperature=0.75
        )

        full_text = response.choices[0].message.content
        user_contexts[user_id].append({"role": "assistant", "content": full_text})

        # Разделение сообщений через |||
        split_messages = full_text.split("|||")

        for msg in split_messages:
            clean_msg = msg.strip()
            if clean_msg:
                if len(split_messages) > 1:
                    await bot.send_chat_action(chat_id=chat_id, action="typing")
                    # Динамическая задержка чтения
                    delay = min(len(clean_msg) / 20, 3.5)
                    await asyncio.sleep(delay)
                
                await message.answer(clean_msg)

    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("⚠️ Что-то пошло не так. Попробуйте еще раз)")

async def main():
    dp = Dispatcher()
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(handle_message)

    await bot.delete_my_commands()

    logger.info("🚀 Иван (The-Manager) запущен с базой знаний из 50 сфер!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
