from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData

from .config import settings


class FunctionalCallback(CallbackData, prefix='func'):
    back: bool


bot = Bot(token=settings.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


# Should probably be replaced with its own scene
async def greetings(chat_id: int):
    await bot.send_message(chat_id=chat_id, text='Hewo :3')
