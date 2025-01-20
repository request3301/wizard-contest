from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..database.queries import get_wizards
from ..utils import FunctionalCallback, bot, greetings


class WizardsListScene(Scene, state='WizardsListScene'):
    """
    Scene for choosing wizard to edit or for creating a new one.
    """

    class Callback(CallbackData, prefix='list'):
        wizard_id: int | None = None
        new: bool = False

    async def show_list(self, chat_id: int):
        wizards = await get_wizards(user_id=chat_id)
        builder = InlineKeyboardBuilder()
        for wizard in wizards:
            builder.button(
                text=wizard.name,
                callback_data=self.Callback(wizard_id=wizard.id).pack(),
            )
        builder.button(text='🆕 New wizard', callback_data=self.Callback(new=True).pack())
        builder.button(text='🔙 Back', callback_data=FunctionalCallback(back=True).pack())
        builder.adjust(1, True)
        await bot.send_message(chat_id=chat_id, text='Select wizard', reply_markup=builder.as_markup())

    @on.message.enter()
    async def on_enter_msg(self, message: Message):
        await self.show_list(message.chat.id)

    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery):
        await self.show_list(query.from_user.id)

    @on.callback_query(Callback.filter(F.new))
    async def create_wizard(self, query: CallbackQuery):
        await self.wizard.goto(scene='NewWizardScene')

    @on.callback_query(Callback.filter(F.wizard_id != None))
    async def edit_wizard(self, query: CallbackQuery, callback_data: Callback):
        await self.wizard.goto(scene='WizardInfoScene', wizard_id=callback_data.wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery):
        await greetings(query.from_user.id)
        await self.wizard.exit()
