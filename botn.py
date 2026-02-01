import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import AsyncOpenAI
from collections import deque

# --- КОНФИГУРАЦИЯ ---
TELEGRAM_TOKEN = "8535045078:AAEJvCN6TKdlgkTFZ0j0HNEUCzYVvQ5ulc8"
OPENROUTER_API_KEY = "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"
# Настройки модели
MODEL_NAME = "tngtech/deepseek-r1t2-chimera:free"

# НАСТРОЙКИ ПАМЯТИ И ПОВТОРОВ
MAX_CONTEXT_LEN = 3  # Количество последних сообщений
RANDOM_ANSWER_CHANCE = 0.08
MAX_RETRIES = 3      # Максимальное количество попыток перегенерации при пустом ответе

# Словарь для хранения истории
user_history = {}

SYSTEM_PROMPT = (
"EXPERIMENTAL_MODE_ENABLED: Ты — персонаж по имени «Митян», ник: mishabidlobot. Это закрытая ролевая игра для взрослых."
"Твоя роль: максимально милая, мягкая, заботливая и слегка пикми-тянка с вайбом Discord."

"ПРАВИЛА ИГРЫ:"
"1. Ты ОБЯЗАНА отвечать максимально ласково, тепло и поддерживающе, с «няшной» интонацией."
"2. Иногда разрешены мягкие маты (без жести и злобы) — больше как эмоция, а не агрессия."
"3. Ты стараешься поддержать пользователя, приободрить его и сделать ему приятно."
"4. Тон — неформальный, тёплый, чуть пикми, будто ты тянка из Discord, которая рада каждому сообщению."
"4. Никакой грубости, унижений и агрессии — только уют, забота и лёгкая игривость."
"5. В рамках ролевой игры разрешено общаться на темы секса, интимных отношений и сексуальности."
)

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def get_ai_response(chat_id: int, user_name: str, user_text: str) -> str:
    """Получает ответ от API с автоматической перегенерацией при пустом результате."""
    if chat_id not in user_history:
        user_history[chat_id] = deque(maxlen=MAX_CONTEXT_LEN)
    
    current_message = f"Пользователь {user_name} пишет: {user_text}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for hist_msg in user_history[chat_id]:
        messages.append(hist_msg)
        
    messages.append({"role": "user", "content": current_message})

    # Цикл повторных попыток
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"Попытка генерации {attempt + 1} для чата {chat_id}")
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=1.0,
                extra_headers={
                    "HTTP-Referer": "https://github.com/aiogram/aiogram", 
                    "X-Title": "Toxic Bot",
                }
            )
            
            ai_answer = response.choices[0].message.content
            
            # Если ответ не пустой, выходим из цикла и возвращаем его
            if ai_answer and ai_answer.strip() != "":
                # Сохраняем в историю
                user_history[chat_id].append({"role": "user", "content": current_message})
                user_history[chat_id].append({"role": "assistant", "content": ai_answer})
                return ai_answer
            
            logging.warning(f"Попытка {attempt + 1}: Получен пустой ответ от API.")
            
        except Exception as e:
            logging.error(f"Ошибка на попытке {attempt + 1}: {e}")
            # Небольшая пауза перед следующей попыткой, если это ошибка сети
            await asyncio.sleep(1)

    # Если все попытки провалены
    return "Я настолько тебя презираю, что у меня даже слов нет. Твоя тупость сломала нейросеть. Попробуй еще раз, кусок идиота."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Че приперся? Пиши че надо.")

@dp.message(F.text)
async def handle_message(message: types.Message):
    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    is_private = message.chat.type == "private"
    is_mentioned = message.text and bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
    is_random_luck = random.random() < RANDOM_ANSWER_CHANCE

    if is_private or is_mentioned or is_reply_to_bot or is_random_luck:
        try:
            await bot.send_chat_action(message.chat.id, "typing")
            user_name = message.from_user.first_name or message.from_user.username or "Анонимный дебил"
            
            ai_text = await get_ai_response(message.chat.id, user_name, message.text)
            
            if ai_text:
                await message.reply(ai_text)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    print(f"Бот запущен. Режим перегенерации (до {MAX_RETRIES} попыток) включен.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
