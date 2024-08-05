import asyncio

from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery

from database.queries import obj_info, get_skills
from tools import bot


class Director:
    def __init__(self, user: list[int], wizard, skills):
        self.user = user
        self.wizard = wizard
        self.skills = skills


async def create_director(user: list[int], wizard_id: list[int]) -> Director:
    tasks = [
        asyncio.create_task(obj_info(obj_type='wizard', obj_id=wizard_id[0])),
        asyncio.create_task(get_skills(wizard_id=wizard_id[0])),
        asyncio.create_task(obj_info(obj_type='wizard', obj_id=wizard_id[1])),
        asyncio.create_task(get_skills(wizard_id=wizard_id[1])),
    ]
    [wizard1, skills1, wizard2, skills2] = await asyncio.gather(*tasks)
    wizard = [wizard1, wizard2]
    skills = [skills1, skills2]
    return Director(user, wizard, skills)


class MatchScene(Scene, state="matchmaking"):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery):
        await bot.send_message(chat_id=query.from_user.id, text="YOU ARE CURRENTLY IN MATCH SCENE")
