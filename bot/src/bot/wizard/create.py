from aiogram import F
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import WizardCreate

from ..database.queries import add_wizard
from ..utils import FunctionalCallback, bot


class NewWizardScene(Scene, state='NewWizardScene'):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery):
        builder = InlineKeyboardBuilder()
        builder.button(text='🚫 Cancel', callback_data=FunctionalCallback(back=True))
        await bot.send_message(
            chat_id=query.from_user.id,
            text='Enter name',
            reply_markup=builder.as_markup(),
        )

    @on.message()
    async def set_name(self, message: Message):
        wizard_create = WizardCreate(
            user_id=message.from_user.id,
            name=message.text,
            speed=1,
            power=1,
        )
        wizard_id = await add_wizard(wizard_create)
        await self.wizard.goto(scene='WizardInfoScene', wizard_id=wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery):
        await self.wizard.goto(scene='WizardsListScene')
