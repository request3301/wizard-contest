from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import Spell

from ..database.queries import delete_obj
from ..utils import FunctionalCallback, bot


class SpellInfoScene(Scene, state='SpellInfoScene'):
    class Callback(CallbackData, prefix='spell_info'):
        delete: bool = False

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, spell: Spell):
        await state.update_data(spell=spell)

        builder = InlineKeyboardBuilder()
        builder.button(text='🔙 Back', callback_data=FunctionalCallback(back=True))
        builder.button(text='🗑 Delete spell', callback_data=self.Callback(delete=True))
        builder.adjust(1, True)

        await bot.send_message(
            chat_id=query.from_user.id,
            text=f'{spell.name}\n\n{spell.description}\n\n{spell.manacost}',
            reply_markup=builder.as_markup(),
        )

    @on.callback_query(Callback.filter(F.delete))
    async def delete(self, query: CallbackQuery, state: FSMContext):
        spell = await state.get_value('spell')
        await delete_obj(obj_type='spell', obj_id=spell.id)

        await self.wizard.goto(scene='WizardInfoScene', update=True)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery, state: FSMContext):
        await self.wizard.goto(scene='WizardInfoScene')
