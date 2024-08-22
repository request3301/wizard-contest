import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData

from config import Settings


class FunctionalCallback(CallbackData, prefix="func"):
    back: bool


TOKEN = Settings().TOKEN
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def greetings(chat_id: int):
    await bot.send_message(chat_id=chat_id, text="Hewo :3")


async def remove_markup(chat_id: int, message_id: int):
    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id)


async def send_messages(*user_ids, text):
    """Sends messages to multiple users concurrently."""
    tasks = [bot.send_message(chat_id=user_id, text=text) for user_id in user_ids]
    await asyncio.gather(*tasks)
