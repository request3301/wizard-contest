from __future__ import annotations

from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..database.queries import get_wizard_with_spells, get_wizards
from ..utils import FunctionalCallback, greetings


class SelectWizardScene(Scene, state='SelectWizardScene'):
    class Callback(CallbackData, prefix='list'):
        wizard_id: int = 0

    @on.message.enter()
    async def on_enter_msg(self, message: Message):
        wizards = await get_wizards(user_id=message.chat.id)
        builder = InlineKeyboardBuilder()
        for wizard in wizards:
            builder.button(
                text=wizard.name,
                callback_data=self.Callback(wizard_id=wizard.id).pack(),
            )
        builder.button(text='🔙 Back', callback_data=FunctionalCallback(back=True).pack())
        builder.adjust(1, True)
        await message.answer(text='Select wizard', reply_markup=builder.as_markup())

    @on.callback_query(Callback.filter(F.wizard_id))
    async def select_wizard(self, query: CallbackQuery, callback_data: Callback, state: FSMContext):
        wizard = await get_wizard_with_spells(callback_data.wizard_id)
        await state.update_data(wizard=wizard)
        await self.wizard.goto(scene='QueueScene')

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery):
        await greetings(query.from_user.id)
        await self.wizard.exit()
