import asyncio
from random import randint

from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import obj_info, get_skills
from llm.engine import start_contest, generate_action, pick_winner
from tools import bot, send_messages


class UseSkillCallback(CallbackData, prefix="use_skill"):
    skill_index: int


class Director:
    def __init__(self, user_id: list[int], wizards, skills):
        self.casted = None
        self.user_id = user_id
        self.wizards = wizards
        self.skills = skills
        if self.wizards[0].speed > self.wizards[1].speed:
            self.turn = 0
        elif self.wizards[0].speed < self.wizards[1].speed:
            self.turn = 1
        else:
            self.turn = randint(0, 1)
        self.messages = start_contest(wizards=self.wizards)
        self.used = set()

    async def run(self):
        for _ in range(4):
            await self.send_skill_select_request()
            while not self.casted:
                await asyncio.sleep(1)
            self.casted = False
            self.turn = self.turn ^ 1
        await self.award_winner()

    async def send_skill_select_request(self):
        builder = InlineKeyboardBuilder()
        for index, skill in enumerate(self.skills[self.turn]):
            if skill.id not in self.used:
                builder.button(text=skill.name, callback_data=UseSkillCallback(skill_index=index))
        builder.button(text="Simple attack", callback_data=UseSkillCallback(skill_index=-1).pack())
        builder.adjust(1, True)
        tasks = [
            bot.send_message(chat_id=self.user_id[self.turn],
                             text="Choose skill to cast",
                             reply_markup=builder.as_markup()),
            bot.send_message(chat_id=self.user_id[self.turn ^ 1],
                             text="The opponent is choosing skill...")
        ]
        await asyncio.gather(*tasks)

    async def cast_skill(self, skill_index: int):
        skill = self.skills[self.turn][skill_index]
        self.used.add(skill.id)
        wizard_name = self.wizards[self.turn].name
        text = f"<b>{wizard_name}</b> casted <b>{skill.name}</b>!"
        await send_messages(*self.user_id, text=text)
        action = await generate_action(
            messages=self.messages,
            wizard_name=wizard_name,
            skill_name=skill.name,
            description=skill.description,
        )
        await send_messages(*self.user_id, text=action)
        self.casted = True

    async def award_winner(self):
        winner, is_tie = await pick_winner(messages=self.messages)
        if is_tie:
            await send_messages(*self.user_id, text="Tie!")
        else:
            await send_messages(*self.user_id, text=f"The winner is <b>{winner}</b>")


async def create_director(user_ids, wizard_ids) -> Director:
    tasks = [
        asyncio.create_task(obj_info(obj_type='wizard', obj_id=wizard_ids[0])),
        asyncio.create_task(get_skills(wizard_id=wizard_ids[0])),
        asyncio.create_task(obj_info(obj_type='wizard', obj_id=wizard_ids[1])),
        asyncio.create_task(get_skills(wizard_id=wizard_ids[1])),
    ]
    [wizard_1, skills_1, wizard_2, skills_2] = await asyncio.gather(*tasks)
    return Director(user_ids, [wizard_1, wizard_2], [skills_1, skills_2])


class MatchScene(Scene, state="matchmaking"):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, director: Director, state: FSMContext):
        await state.update_data(director=director)

    @on.callback_query(UseSkillCallback.filter())
    async def on_use_skill(self, query: CallbackQuery, callback_data: UseSkillCallback, state: FSMContext):
        data = await state.get_data()
        director = data['director']

        await bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        await director.cast_skill(callback_data.skill_index)
