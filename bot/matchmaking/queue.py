import asyncio

from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import get_wizards, get_rating, obj_info
from matchmaking.match import create_director, MatchScene
from tools import FunctionalCallback, greetings, bot, remove_markup

on_match_message = "Contest found!"


class QueueCallback(CallbackData, prefix="queue"):
    pass


class Coordinator:
    """
    Responsible for matchmaking queue
    """

    def __init__(self):
        self.queue = {}

    def add(self, user_id: int, wizard_id: int, rating: int, msg_id: int):
        self.queue[user_id] = {
            'rating': rating,
            'wizard_id': wizard_id,
            'status': "in_queue",
            'msg_id': msg_id,
            "director": None
        }

    async def abandon(self, user_id: int):
        await bot.edit_message_text(chat_id=user_id, message_id=self.queue[user_id]['msg_id'],
                                    text=f"{on_match_message}\n\n🚫 Abandoned")
        del self.queue[user_id]

    async def accept(self, user_id: int):
        self.queue[user_id]['status'] = 'accepted'
        await bot.edit_message_text(chat_id=user_id, message_id=self.queue[user_id]['msg_id'],
                                    text=f"{on_match_message}\n\n✅ Accepted")

    async def start_polling(self):
        while True:
            opp = 0
            for user_id in list(self.queue.keys()):
                if self.queue[user_id]['status'] != 'in_queue':
                    continue
                if opp == 0:
                    opp = user_id
                    continue
                match_established = await self.notify(opp, user_id)
                if match_established:
                    director = await create_director([opp, user_id],
                                                     [self.queue[opp]['wizard_id'], self.queue[user_id]['wizard_id']])
                    for i in [opp, user_id]:
                        self.queue[i]['status'] = "established"
                        self.queue[i]['director'] = director
                    await director.run()
                opp = 0

            await asyncio.sleep(1)

    async def notify(self, user_id_1: int, user_id_2: int) -> bool:
        # remove "Back" option in queue message
        await remove_markup(chat_id=user_id_1, message_id=self.queue[user_id_1]['msg_id'])
        await remove_markup(chat_id=user_id_2, message_id=self.queue[user_id_2]['msg_id'])
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Accept", callback_data=QueueCallback().pack())
        builder.button(text="🚫 Abandon", callback_data=FunctionalCallback(back=True).pack())
        message = await bot.send_message(chat_id=user_id_1, text=on_match_message, reply_markup=builder.as_markup())
        self.queue[user_id_1]['msg_id'] = message.message_id
        message = await bot.send_message(chat_id=user_id_2, text=on_match_message, reply_markup=builder.as_markup())
        self.queue[user_id_2]['msg_id'] = message.message_id
        while True:
            if user_id_1 not in self.queue or user_id_2 not in self.queue:
                if user_id_1 in self.queue:
                    self.queue[user_id_1]['status'] = 'abandoned'
                if user_id_2 in self.queue:
                    self.queue[user_id_2]['status'] = 'abandoned'
                return False
            if self.queue[user_id_1]['status'] == 'accepted' and self.queue[user_id_2]['status'] == 'accepted':
                return True
            await asyncio.sleep(1)

    def get_director(self, user_id: int):
        return self.queue[user_id]['director']

    def get_status(self, user_id: int):
        return self.queue[user_id]['status']


coordinator = Coordinator()


class SelectWizardScene(Scene, state="select_wizard"):
    # select wizard for a matchmaking

    class Callback(CallbackData, prefix="list"):
        wizard_id: int = 0
        new: bool = False

    @on.message.enter()
    async def on_enter_msg(self, message: Message):
        wizards = await get_wizards(user_id=message.chat.id)
        builder = InlineKeyboardBuilder()
        for wizard in wizards:
            builder.button(text=wizard.name, callback_data=self.Callback(wizard_id=wizard.id).pack())
        builder.button(text="🔙 Back", callback_data=FunctionalCallback(back=True).pack())
        builder.adjust(1, True)
        await message.answer(text="Select wizard", reply_markup=builder.as_markup())

    @on.callback_query(Callback.filter(F.wizard_id))
    async def edit_wizard(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=QueueScene, wizard_id=callback_data.wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await greetings(query.from_user.id)
        await self.wizard.exit()


class QueueScene(Scene, state="queue"):
    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery, wizard_id: int, state: FSMContext):
        await state.update_data(wizard_id=wizard_id)
        wizard = await obj_info(obj_type='wizard', obj_id=wizard_id)
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Leave", callback_data=FunctionalCallback(back=True).pack())
        message = await bot.send_message(chat_id=query.from_user.id,
                                         text=f"Entered queue as <b>{wizard.name}</b>. Searching...",
                                         reply_markup=builder.as_markup())

        rating = await get_rating(wizard_id=wizard_id)
        coordinator.add(user_id=query.from_user.id, wizard_id=wizard_id, rating=rating, msg_id=message.message_id)

    @on.callback_query(QueueCallback.filter())
    async def accept(self, query: CallbackQuery, state: FSMContext):
        user_id = query.from_user.id
        print(f"accept from {user_id}")

        status = coordinator.get_status(user_id=user_id)
        await coordinator.accept(user_id=user_id)
        while status != "established":
            if status == "abandoned":
                await bot.send_message(chat_id=user_id, text="Failed")
                data = await state.get_data()
                wizard_id = data['wizard_id']
                await self.wizard.retake(wizard_id=wizard_id)
                return
            await asyncio.sleep(1)
            status = coordinator.get_status(user_id=user_id)

        print(f"preparing the match...")
        director = coordinator.get_director(user_id=user_id)
        await self.wizard.goto(scene=MatchScene, director=director)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery):
        print(f"abandon or exit from {query.from_user.id}")
        await coordinator.abandon(query.from_user.id)
        await greetings(query.from_user.id)
        await self.wizard.exit()
