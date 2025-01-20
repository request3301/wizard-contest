from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import Wizard

from ...database.queries import set_wizard_param
from ...utils import bot

power_names = {1: 'Human', 2: 'Strong', 3: 'Physical prowess', 4: 'Titan', 5: 'God'}


class ChoosePowerScene(Scene, state='ChoosePowerScene'):
    class Callback(CallbackData, prefix='power'):
        power: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext):
        builder = InlineKeyboardBuilder()
        for power, power_name in power_names.items():
            builder.button(
                text=f'{power_name} ({power})',
                callback_data=self.Callback(power=power).pack(),
            )
        builder.adjust(1, True)
        await bot.send_message(
            chat_id=query.from_user.id,
            text="Select wizard's power",
            reply_markup=builder.as_markup(),
        )

    @on.callback_query(Callback.filter(F.power))
    async def set_power(self, query: CallbackQuery, callback_data: Callback, state: FSMContext):
        wizard: Wizard = await state.get_value('wizard')
        power = callback_data.power
        await set_wizard_param(wizard_id=wizard.id, param='power', value=power)
        await self.wizard.goto(scene='WizardInfoScene')
