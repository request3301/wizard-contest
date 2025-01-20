from __future__ import annotations

import asyncio
import logging

import httpx
from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import Wizard

from ..config import settings
from ..utils import bot, greetings

on_match_message = 'Contest found!'


class QueueCallback(CallbackData, prefix='queue'):
    accept: bool = False
    reject: bool = False
    leave: bool = False

    def __post_init__(self):
        assert self.accept or self.reject or self.leave


class QueueScene(Scene, state='QueueScene'):
    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery, state: FSMContext) -> None:
        asyncio.create_task(self.enter_queue(query, state))

    async def enter_queue(self, query: CallbackQuery, state: FSMContext) -> None:
        wizard: Wizard = await state.get_value('wizard')
        builder = InlineKeyboardBuilder()
        builder.button(text='🔙 Leave', callback_data=QueueCallback(leave=True).pack())

        queue_entered_message = await bot.send_message(
            chat_id=query.from_user.id,
            text=f'Entered queue as <b>{wizard.name}</b>. Searching...',
            reply_markup=builder.as_markup(),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{settings.COORDINATOR_SERVICE_URL}/add_user_to_queue',
                json={
                    'rating': wizard.rank,
                    'user_id': query.from_user.id,
                },
                timeout=None,
            )
        await queue_entered_message.delete_reply_markup()
        if response.status_code == 204:
            return

        if response.status_code == 422:
            logging.log(logging.ERROR, response.text)

        builder = InlineKeyboardBuilder()
        builder.button(text='✅ Accept', callback_data=QueueCallback(accept=True).pack())
        builder.button(text='🚫 Abandon', callback_data=QueueCallback(reject=True).pack())

        await bot.send_message(chat_id=query.from_user.id, text=on_match_message, reply_markup=builder.as_markup())

    @on.callback_query(QueueCallback.filter(F.leave))
    async def leave_queue(self, query: CallbackQuery):
        user_id = query.from_user.id

        logging.log(logging.INFO, f'player {query.from_user.id} leaves the queue')
        async with httpx.AsyncClient() as client:
            await client.delete(f'{settings.COORDINATOR_SERVICE_URL}/queue/leave/{user_id}')

        await bot.send_message(user_id, 'Left queue')
        await greetings(user_id)
        await self.wizard.exit()

    @on.callback_query(QueueCallback.filter(F.accept))
    async def accept_match(self, query: CallbackQuery, state: FSMContext) -> None:
        user_id = query.from_user.id

        await bot.edit_message_text(
            chat_id=user_id, message_id=query.message.message_id, text=f'{on_match_message}\n\n✅ Accepted'
        )

        async with httpx.AsyncClient() as client:
            response = await client.put(f'{settings.COORDINATOR_SERVICE_URL}/lobby/accept/{user_id}', timeout=None)
            data = response.json()

        if data['created']:
            await bot.send_message(chat_id=user_id, text='Preparing the match...')
            await self.wizard.goto('MatchScene', director_id=data['director_id'])
        else:
            await bot.send_message(user_id, 'Opponent rejected the match')
            await self.wizard.retake()

    @on.callback_query(QueueCallback.filter(F.reject))
    async def reject_match(self, query: CallbackQuery):
        user_id = query.from_user.id

        async with httpx.AsyncClient() as client:
            await client.put(f'{settings.COORDINATOR_SERVICE_URL}/lobby/reject/{user_id}')

        await bot.edit_message_text(
            chat_id=user_id, message_id=query.message.message_id, text=f'{on_match_message}\n\n🚫 Abandoned'
        )
        await greetings(user_id)
        await self.wizard.exit()
