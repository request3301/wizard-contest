from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.methods import SendMessage
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import Wizard

from ...database.queries import set_wizard_param
from ...utils import bot

speed_names = {1: 'Human', 2: 'Panther', 3: 'Sonic', 4: 'Lightspeed', 5: 'Godspeed'}


class ChooseSpeedScene(Scene, state='ChooseSpeedScene'):
    class Callback(CallbackData, prefix='speed'):
        speed: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext):
        builder = InlineKeyboardBuilder()
        for speed, speed_name in speed_names.items():
            builder.button(
                text=f'{speed_name} ({speed})',
                callback_data=self.Callback(speed=speed).pack(),
            )
        builder.adjust(1, True)
        await bot(
            SendMessage(
                chat_id=query.from_user.id,
                text="Select wizard's speed",
                reply_markup=builder.as_markup(),
            )
        )

    @on.callback_query(Callback.filter(F.speed))
    async def set_power(self, query: CallbackQuery, callback_data: Callback, state: FSMContext):
        wizard: Wizard = await state.get_value('wizard')
        speed = callback_data.speed
        await set_wizard_param(wizard_id=wizard.id, param='speed', value=speed)
        await self.wizard.goto(scene='WizardInfoScene', wizard_id=wizard.id)
