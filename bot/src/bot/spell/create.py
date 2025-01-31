from __future__ import annotations

import asyncio

import httpx
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import SpellCreate

from ..config import settings
from ..database.orm import SpellType
from ..database.queries import add_spell
from ..utils import FunctionalCallback, bot


class _BaseSpellScene(Scene):
    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await bot.send_message(
            chat_id=query.message.chat.id,
            text='Cancelled 🚫',
            reply_markup=ReplyKeyboardRemove(),
        )
        await self.wizard.goto(scene='WizardInfoScene')


class CreateSpellScene(_BaseSpellScene, state='CreateSpellScene'):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext):
        builder = InlineKeyboardBuilder()
        builder.button(text='🚫', callback_data=FunctionalCallback(back=True))
        await bot.send_message(
            chat_id=query.from_user.id,
            text='Press here to cancel',
            reply_markup=builder.as_markup(),
        )

        await self.wizard.goto(EnterSpellNameScene)


class EnterSpellNameScene(_BaseSpellScene, state='EnterSpellNameScene'):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext):
        await bot.send_message(chat_id=query.from_user.id, text="Enter spell's name")

    @on.message()
    async def get_name(self, message: Message, state: FSMContext):
        await state.update_data(name=message.text)

        await self.wizard.goto(EnterSpellTypeScene)


class EnterSpellTypeScene(_BaseSpellScene, state='EnterSpellTypeScene'):
    @on.message.enter()
    async def on_enter(self, message: Message, state: FSMContext):
        markup = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Active'), KeyboardButton(text='Passive')]])
        assert message.from_user is not None
        await message.answer(text='Select spell type', reply_markup=markup)

    @on.message()
    async def get_type(self, message: Message, state: FSMContext):
        match message.text:
            case 'Active':
                await state.update_data(type_=SpellType.ACTIVE)
            case 'Passive':
                await state.update_data(type_=SpellType.PASSIVE)
            case _:
                await message.answer(text='Incorrect spell type')
                return

        await self.wizard.goto(EnterSpellDescriptionScene)


class EnterSpellDescriptionScene(_BaseSpellScene, state='EnterSpellDescriptionScene'):
    @on.message.enter()
    async def on_enter(self, message: Message, state: FSMContext):
        await message.answer(
            text='Write spell description',
            reply_markup=ReplyKeyboardRemove(),
        )

    @on.message()
    async def get_description(self, message: Message, state: FSMContext):
        params = await state.get_data()
        description = message.text
        await self.create_spell(state, message.chat.id, description=description, **params)

    async def create_spell(self, state: FSMContext, chat_id: int, **params):
        _ = asyncio.create_task(bot.send_message(chat_id=chat_id, text='Calculating power of the spell...'))
        params['manacost'] = await self.calculate_manacost(**params)

        if params['manacost'] == -1:
            await bot.send_message(chat_id=chat_id, text='Something went wrong... Please try again.')
            await self.wizard.retake()
            return

        params['wizard_id'] = params['wizard'].id

        spell_create = SpellCreate.model_validate(params)

        await bot.send_message(chat_id=chat_id, text=f'Power: {params['manacost']}')
        await add_spell(spell_create)

        await self.wizard.goto(scene='WizardInfoScene', update=True)

    @staticmethod
    async def calculate_manacost(type_: SpellType, description: str, **_) -> int:
        async with httpx.AsyncClient() as client:
            query = {
                'type_': type_,
                'description': description,
            }
            response = await client.get(settings.LLM_SERVICE_URL + '/spell/calculate_manacost', params=query)
            return int(response.text)
