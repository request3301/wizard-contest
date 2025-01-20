from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import Wizard

from .parameters.power import power_names
from .parameters.speed import speed_names
from ..database.queries import delete_obj, get_wizard_with_spells
from ..utils import FunctionalCallback, bot


class WizardInfoScene(Scene, state='WizardInfoScene'):
    class Callback(CallbackData, prefix='wizard_info'):
        spell_id: int | None = None
        new_spell: bool = False
        speed: bool = False
        power: bool = False
        delete_wizard: bool = False

    async def show_info(self, state: FSMContext, chat_id: int, wizard_id: int | None, update: bool):
        if update:
            wizard = await state.get_value('wizard')
            wizard_id = wizard.id
        if wizard_id is not None:
            wizard = await get_wizard_with_spells(wizard_id)
            await state.update_data(wizard=wizard)
        else:
            wizard = await state.get_value('wizard')

        builder = InlineKeyboardBuilder()
        builder.button(
            text='⚡️ ' + speed_names[wizard.speed],
            callback_data=self.Callback(speed=True).pack(),
        )
        builder.button(
            text='💪 ' + power_names[wizard.power],
            callback_data=self.Callback(power=True).pack(),
        )

        for spell in wizard.spells:
            builder.button(text=spell.name, callback_data=self.Callback(spell_id=spell.id).pack())
        builder.button(text='🆕 New spell', callback_data=self.Callback(new_spell=True).pack())
        builder.button(
            text='💀 Delete wizard',
            callback_data=self.Callback(delete_wizard=True).pack(),
        )
        builder.button(text='🔙 Back', callback_data=FunctionalCallback(back=True).pack())
        builder.adjust(1, True)
        await bot.send_message(
            chat_id=chat_id,
            text=f'<b>{wizard.name}</b>\nRank: {wizard.rank}',
            reply_markup=builder.as_markup(),
        )

    @on.message.enter()
    async def on_enter_msg(self, message: Message, state: FSMContext, wizard_id: int | None = None,
                           update: bool = False):
        await self.show_info(state=state, chat_id=message.chat.id, wizard_id=wizard_id, update=update)

    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery, state: FSMContext, wizard_id: int | None = None,
                          update: bool = False):
        await self.show_info(state=state, chat_id=query.from_user.id, wizard_id=wizard_id, update=update)

    @on.callback_query(Callback.filter(F.spell_id != None))
    async def spell_info(self, query: CallbackQuery, callback_data: Callback, state: FSMContext):
        wizard: Wizard = await state.get_value('wizard')
        spell = wizard.get_spell(callback_data.spell_id)
        await self.wizard.goto(scene='SpellInfoScene', spell=spell)

    @on.callback_query(Callback.filter(F.new_spell))
    async def new_spell(self, query: CallbackQuery):
        await self.wizard.goto(scene='CreateSpellScene')

    @on.callback_query(Callback.filter(F.speed))
    async def change_speed(self, query: CallbackQuery):
        await self.wizard.goto(scene='ChooseSpeedScene')

    @on.callback_query(Callback.filter(F.power))
    async def change_power(self, query: CallbackQuery):
        await self.wizard.goto(scene='ChoosePowerScene')

    @on.callback_query(Callback.filter(F.delete_wizard))
    async def delete_wizard(self, query: CallbackQuery, state: FSMContext):
        wizard = await state.get_value('wizard')
        await delete_obj(obj_type='wizard', obj_id=wizard.id)
        await self.wizard.goto(scene='WizardsListScene')

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery):
        await self.wizard.goto(scene='WizardsListScene')
