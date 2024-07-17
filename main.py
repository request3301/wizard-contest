import asyncio
import logging
import sys
import sqlite3
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on, SceneRegistry, ScenesManager
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import Message, CallbackQuery
from aiogram.methods import SendMessage
from aiogram.utils.keyboard import InlineKeyboardBuilder

from gpt import calculate_manacost

from env import Settings


TOKEN = Settings().TOKEN
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


connection = sqlite3.connect("wizard-battle.db")
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
id INTEGER PRIMARY KEY,
wizard INTEGER
)
''')

# wizards (as well as skills) are stored in a forward list. "next" points to next wizard.
cursor.execute('''
CREATE TABLE IF NOT EXISTS Wizards (
id INTEGER PRIMARY KEY,
next INTEGER,
name TEXT NOT NULL,
speed INTEGER,
power INTEGER,
skill INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Skills (
id INTEGER PRIMARY KEY,
next INTEGER,
name TEXT NOT NULL,
description TEXT,
manacost INTEGER
)
''')

speednames = {
    1: "Human",
    2: "Panther",
    3: "Sonic",
    4: "Lightspeed",
    5: "Godspeed"
}

powernames = {
    1: "Human",
    2: "Strong",
    3: "Physical prowess",
    4: "Titan",
    5: "God"
}


def get_wizards(user: int):
    wizards = []
    cursor.execute('SELECT wizard FROM Users WHERE id = ?', (user,))
    result = cursor.fetchone()[0]
    while result is not None:
        wizards.append(result)
        cursor.execute('SELECT next FROM Wizards WHERE id = ?', (result,))
        result = cursor.fetchone()[0]
    return wizards


def delete_wizard(wizard: int):
    cursor.execute('SELECT next FROM Wizards WHERE id = ?', (wizard,))
    nxt = cursor.fetchone()[0]
    cursor.execute('SELECT id FROM Users WHERE wizard = ?', (wizard,))
    if cursor.fetchone() is None:
        cursor.execute('UPDATE Wizards SET next = ? WHERE next = ?', (nxt, wizard))
    else:
        cursor.execute('UPDATE Users SET wizard = ? WHERE wizard = ?', (nxt, wizard))
    cursor.execute('DELETE FROM Wizards WHERE id = ?', (wizard,))


def get_last_wizard(user: int):
    wizards = get_wizards(user)
    if not wizards:
        return -1
    return wizards[-1]


def add_wizard(user: int, name: str):
    last = get_last_wizard(user)
    cursor.execute('INSERT INTO Wizards (name, speed, power) VALUES (?, 1, 1)', (name,))
    cursor.execute('SELECT last_insert_rowid()')
    wizard = cursor.fetchone()[0]
    if last == -1:
        cursor.execute('UPDATE Users SET wizard = ? WHERE id = ?', (wizard, user,))
    else:
        cursor.execute('UPDATE Wizards SET next = ? WHERE id = ?', (wizard, last,))
    return wizard


def get_skills(wizard: int):
    skills = []
    cursor.execute('SELECT skill FROM Wizards WHERE id = ?', (wizard,))
    skill = cursor.fetchone()[0]
    while skill is not None:
        skills.append(skill)
        cursor.execute('SELECT next FROM Skills WHERE id = ?', (skill,))
        skill = cursor.fetchone()[0]
    return skills


def get_skills_names(wizard: int):
    skills = get_skills(wizard)
    names = []
    for skill in skills:
        cursor.execute('SELECT name FROM Skills WHERE id = ?', (skill,))
        names.append(str(cursor.fetchone()[0]))
    return names


def delete_skill(wizard: int, skill: int):
    cursor.execute('SELECT next FROM Skills WHERE id = ?', (skill,))
    nxt = cursor.fetchone()[0]
    cursor.execute('SELECT skill FROM Wizards WHERE id = ?', (wizard,))
    if skill == cursor.fetchone()[0]:
        cursor.execute('UPDATE Wizards SET skill = ? WHERE id = ?', (nxt, wizard))
    else:
        cursor.execute('UPDATE Skills SET next = ? WHERE next = ?', (nxt, skill))
    cursor.execute('DELETE FROM Skills WHERE id = ?', (skill,))


def get_last_skill(wizard: int):
    skills = get_skills(wizard)
    if not skills:
        return -1
    return skills[-1]


def add_skill(wizard: int, name: str, description: str, manacost: int):
    last = get_last_skill(wizard)
    cursor.execute('INSERT INTO Skills (name, description, manacost) VALUES (?, ?, ?)',
                   (name, description, manacost))
    cursor.execute('SELECT last_insert_rowid()')
    skill = cursor.fetchone()[0]
    if last == -1:
        cursor.execute('UPDATE Wizards SET skill = ? WHERE id = ?', (skill, wizard,))
    else:
        cursor.execute('UPDATE Skills SET next = ? WHERE id = ?', (skill, last,))


def get_manapool(wizards: int):
    skills = get_skills(wizards)
    manapool = 0
    for skill in skills:
        cursor.execute('SELECT manacost FROM Skills WHERE id = ?', (skill,))
        manapool += cursor.fetchone()[0]
    return manapool


async def greetings(chat_id: int) -> None:
    await bot(SendMessage(chat_id=chat_id, text="Hewo :3"))


class FunctionalCallback(CallbackData, prefix="func"):
    back: bool


class WizardsListScene(Scene, state="list"):
    """
    Scene for choosing wizard to edit or for creating a new one.
    """

    class Callback(CallbackData, prefix="list"):
        wizard: int = 0
        new: bool = False

    async def show_list(self, chat_id: int) -> Any:
        wizards = get_wizards(chat_id)
        # print(wizards)
        builder = InlineKeyboardBuilder()
        for wizard in wizards:
            cursor.execute('SELECT name FROM Wizards WHERE id = ?', (wizard,))
            name = cursor.fetchone()[0]
            builder.button(text=name, callback_data=self.Callback(wizard=wizard).pack())
        builder.button(text="🆕 New wizard", callback_data=self.Callback(new=True).pack())
        builder.button(text="🔙 Back", callback_data=FunctionalCallback(back=True).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=chat_id,
                              text="Select wizard", reply_markup=builder.as_markup()))

    @on.message.enter()
    async def on_enter_msg(self, message: Message) -> Any:
        await self.show_list(message.chat.id)

    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery) -> Any:
        await self.show_list(query.from_user.id)

    @on.callback_query(Callback.filter(F.new))
    async def create_wizard(self, query: CallbackQuery) -> None:
        await self.wizard.goto(scene=NewWizardScene)

    @on.callback_query(Callback.filter(F.wizard))
    async def edit_wizard(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=EditWizardScene, wizard=callback_data.wizard)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await greetings(query.from_user.id)
        await self.wizard.exit()


class NewWizardScene(Scene, state="new"):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery) -> Any:
        builder = InlineKeyboardBuilder()
        builder.button(text="🚫 Cancel", callback_data=FunctionalCallback(back=True))
        await bot(SendMessage(chat_id=query.from_user.id,
                              text="Enter name", reply_markup=builder.as_markup()))

    @on.message()
    async def set_name(self, message: Message):
        wizard = add_wizard(message.chat.id, message.text)
        await self.wizard.goto(scene=EditWizardScene, wizard=wizard)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await self.wizard.goto(scene=WizardsListScene)


class EditWizardScene(Scene, state="edit_wizard"):

    class Callback(CallbackData, prefix="editw"):
        wizard: int
        skill: int = 0
        new_skill: bool = False
        speed: bool = False
        power: bool = False
        delete_wizard: bool = False

    async def show_info(self, chat_id: int, wizard: int) -> Any:
        cursor.execute('SELECT name, speed, power FROM Wizards WHERE id = ?', (wizard,))
        [name, speed, power] = cursor.fetchone()
        skills = get_skills(wizard)
        skills_names = get_skills_names(wizard)
        rating = get_manapool(wizard) * speed * power

        builder = InlineKeyboardBuilder()
        builder.button(text="⚡️ "+speednames[speed],
                       callback_data=self.Callback(wizard=wizard, speed=True).pack())
        builder.button(text="💪 "+powernames[power],
                       callback_data=self.Callback(wizard=wizard, power=True).pack())
        for [skill, sname] in zip(skills, skills_names):
            builder.button(text=sname, callback_data=self.Callback(wizard=wizard, skill=skill).pack())
        builder.button(text="🆕 New skill",
                       callback_data=self.Callback(wizard=wizard, new_skill=True).pack())
        builder.button(text="💀 Delete wizard",
                       callback_data=self.Callback(wizard=wizard, delete_wizard=True).pack())
        builder.button(text="🔙 Back",
                       callback_data=FunctionalCallback(wizard=wizard, back=True).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=chat_id, text="<b>"+str(name)+"</b>\nRank: "+str(rating),
                              reply_markup=builder.as_markup()))

    @on.message.enter()
    async def on_enter_msg(self, message: Message, wizard: int) -> Any:
        await self.show_info(message.chat.id, wizard)

    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery, wizard: int) -> Any:
        await self.show_info(query.from_user.id, wizard)

    @on.callback_query(Callback.filter(F.skill))
    async def edit_skill(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=SkillScene, wizard=callback_data.wizard, skill=callback_data.skill)

    @on.callback_query(Callback.filter(F.new_skill))
    async def new_skill(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=NewSkillScene, wizard=callback_data.wizard)

    @on.callback_query(Callback.filter(F.speed))
    async def change_speed(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=ChooseSpeedScene, wizard=callback_data.wizard)

    @on.callback_query(Callback.filter(F.power))
    async def change_power(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=ChoosePowerScene, wizard=callback_data.wizard)

    @on.callback_query(Callback.filter(F.delete_wizard))
    async def delete_wizard(self, query: CallbackQuery, callback_data: Callback) -> None:
        delete_wizard(callback_data.wizard)
        await self.wizard.goto(scene=WizardsListScene)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await self.wizard.goto(scene=WizardsListScene)


class ChooseSpeedScene(Scene, state="speed"):

    class Callback(CallbackData, prefix="speed"):
        wizard: int
        speed: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, wizard: int) -> Any:
        builder = InlineKeyboardBuilder()
        for speed, speedname in speednames.items():
            builder.button(text=speedname+" ("+str(speed)+")",
                           callback_data=self.Callback(wizard=wizard, speed=speed).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=query.from_user.id, text="Select wizard's speed",
                              reply_markup=builder.as_markup()))

    @on.callback_query(Callback.filter(F.speed))
    async def set_speed(self, query: CallbackQuery, callback_data: Callback) -> None:
        cursor.execute('UPDATE Wizards SET speed = ? WHERE id = ?',
                       (callback_data.speed, callback_data.wizard))
        await self.wizard.goto(scene=EditWizardScene, wizard=callback_data.wizard)


class ChoosePowerScene(Scene, state="power"):

    class Callback(CallbackData, prefix="power"):
        wizard: int
        power: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, wizard: int) -> Any:
        builder = InlineKeyboardBuilder()
        for power, powername in powernames.items():
            builder.button(text=powername+" ("+str(power)+")",
                           callback_data=self.Callback(wizard=wizard, power=power).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=query.from_user.id, text="Select wizard's power",
                              reply_markup=builder.as_markup()))

    @on.callback_query(Callback.filter(F.power))
    async def set_power(self, query: CallbackQuery, callback_data: Callback) -> None:
        cursor.execute('UPDATE Wizards SET power = ? WHERE id = ?',
                       (callback_data.power, callback_data.wizard))
        await self.wizard.goto(scene=EditWizardScene, wizard=callback_data.wizard)


class NewSkillScene(Scene, state="new_skill"):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, wizard: int) -> Any:
        builder = InlineKeyboardBuilder()
        builder.button(text="🚫 Cancel", callback_data=FunctionalCallback(back=True))
        await state.update_data(wizard=wizard, name_request=True)
        await bot(SendMessage(chat_id=query.from_user.id,
                              text="Enter skill's name.", reply_markup=builder.as_markup()))

    @on.message()
    async def on_message(self, message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        wizard = data['wizard']
        name_request = data['name_request']
        if name_request:
            await state.update_data(name=message.text)
            builder = InlineKeyboardBuilder()
            builder.button(text="🚫 Cancel", callback_data=FunctionalCallback(back=True))
            await state.update_data(name_request=False)
            await message.answer(text="Write description.", reply_markup=builder.as_markup())
        else:
            name = data['name']
            description = message.text
            # todo merge coroutines
            await message.answer(text="Calculating power of the skill...")
            manacost = await calculate_manacost(description)
            await message.answer(text="Power: "+str(manacost))
            add_skill(wizard, name, description, manacost)

            await state.set_data({})
            await self.wizard.goto(scene=EditWizardScene, wizard=wizard)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        wizard = data['wizard']
        await state.set_data({})
        await self.wizard.goto(scene=EditWizardScene, wizard=wizard)


class SkillScene(Scene, state="skill"):

    class Callback(CallbackData, prefix="skill"):
        delete: bool = False

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, skill: int, wizard: int) -> None:
        cursor.execute('SELECT name, description, manacost FROM Skills WHERE id = ?', (skill,))
        [name, description, manacost] = cursor.fetchone()

        await state.update_data(wizard=wizard, skill=skill)

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Back", callback_data=FunctionalCallback(back=True))
        builder.button(text="🗑 Delete skill", callback_data=self.Callback(delete=True))
        builder.adjust(1, True)

        await bot(SendMessage(chat_id=query.from_user.id, text=name+"\n\n"+description+"\n\n"+str(manacost),
                              reply_markup=builder.as_markup()))

    @on.callback_query(Callback.filter(F.delete))
    async def delete(self, query: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        skill = data['skill']
        wizard = data['wizard']
        delete_skill(skill=skill, wizard=wizard)

        await state.set_data({})
        await self.wizard.goto(scene=EditWizardScene, wizard=wizard)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        wizard = data['wizard']

        await state.set_data({})
        await self.wizard.goto(scene=EditWizardScene, wizard=wizard)


router = Router(name=__name__)
router.message.register(WizardsListScene.as_handler(), Command("wizards"))


@router.message(CommandStart())
async def command_start(message: Message, scenes: ScenesManager) -> None:
    await scenes.close()
    cursor.execute('SELECT * FROM Users WHERE id = ?', (message.from_user.id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO Users (id) VALUES (?)', (message.chat.id,))
    await greetings(message.chat.id)


def create_dispatcher():
    dispatcher = Dispatcher(
        events_isolation=SimpleEventIsolation(),
    )
    dispatcher.include_router(router)

    scene_registry = SceneRegistry(dispatcher)

    scene_registry.add(WizardsListScene)
    scene_registry.add(NewWizardScene)
    scene_registry.add(EditWizardScene)
    scene_registry.add(ChooseSpeedScene)
    scene_registry.add(ChoosePowerScene)
    scene_registry.add(NewSkillScene)
    scene_registry.add(SkillScene)

    return dispatcher


async def main() -> None:
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        connection.commit()
        connection.close()
        print("Shutting down")
