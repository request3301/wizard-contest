import asyncio
import logging
import sys
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

from settings import Settings

from database.models import User, Wizard, SkillData
from database.queries import obj_info, delete_obj, checkin_user, get_wizards, add_wizard
from database.queries import get_skills, add_skill
from database.queries import set_wizard_param


TOKEN = Settings().TOKEN
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

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


def get_manapool(skills: list[SkillData]):
    manapool = 0
    for skill in skills:
        manapool += skill.manacost
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
        wizard_id: int = 0
        new: bool = False

    async def show_list(self, chat_id: int) -> Any:
        wizards = await get_wizards(user_id=chat_id)
        builder = InlineKeyboardBuilder()
        for wizard in wizards:
            builder.button(text=wizard.name, callback_data=self.Callback(wizard_id=wizard.id).pack())
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

    @on.callback_query(Callback.filter(F.wizard_id))
    async def edit_wizard(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=EditWizardScene, wizard_id=callback_data.wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await greetings(query.from_user.id)
        await self.wizard.exit()


class NewWizardScene(Scene, state="new"):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery):
        builder = InlineKeyboardBuilder()
        builder.button(text="🚫 Cancel", callback_data=FunctionalCallback(back=True))
        await bot(SendMessage(chat_id=query.from_user.id,
                              text="Enter name", reply_markup=builder.as_markup()))

    @on.message()
    async def set_name(self, message: Message):
        wizard_id = await add_wizard(user_id=message.chat.id, name=message.text)
        await self.wizard.goto(scene=EditWizardScene, wizard_id=wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery):
        await self.wizard.goto(scene=WizardsListScene)


class EditWizardScene(Scene, state="edit_wizard"):
    class Callback(CallbackData, prefix="editw"):
        wizard_id: int
        skill_id: int = 0
        new_skill: bool = False
        speed: bool = False
        power: bool = False
        delete_wizard: bool = False

    async def show_info(self, chat_id: int, wizard_id: int) -> Any:
        wizard = await obj_info(obj_type='wizard', obj_id=wizard_id)
        skills = await get_skills(wizard_id=wizard_id)
        rating = get_manapool(skills) * wizard.speed * wizard.power

        builder = InlineKeyboardBuilder()
        builder.button(text="⚡️ " + speednames[wizard.speed],
                       callback_data=self.Callback(wizard_id=wizard_id, speed=True).pack())
        builder.button(text="💪 " + powernames[wizard.power],
                       callback_data=self.Callback(wizard_id=wizard_id, power=True).pack())

        for skill in skills:
            builder.button(text=skill.name, callback_data=self.Callback(wizard_id=wizard_id, skill_id=skill.id).pack())
        builder.button(text="🆕 New skill",
                       callback_data=self.Callback(wizard_id=wizard_id, new_skill=True).pack())
        builder.button(text="💀 Delete wizard",
                       callback_data=self.Callback(wizard_id=wizard_id, delete_wizard=True).pack())
        builder.button(text="🔙 Back",
                       callback_data=FunctionalCallback(wizard_id=wizard_id, back=True).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=chat_id, text="<b>" + str(wizard.name) + "</b>\nRank: " + str(rating),
                              reply_markup=builder.as_markup()))

    @on.message.enter()
    async def on_enter_msg(self, message: Message, wizard_id: int) -> Any:
        await self.show_info(chat_id=message.chat.id, wizard_id=wizard_id)

    @on.callback_query.enter()
    async def on_enter_cb(self, query: CallbackQuery, wizard_id: int) -> Any:
        await self.show_info(query.from_user.id, wizard_id)

    @on.callback_query(Callback.filter(F.skill_id))
    async def edit_skill(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=SkillScene, wizard_id=callback_data.wizard_id, skill_id=callback_data.skill_id)

    @on.callback_query(Callback.filter(F.new_skill))
    async def new_skill(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=NewSkillScene, wizard_id=callback_data.wizard_id)

    @on.callback_query(Callback.filter(F.speed))
    async def change_speed(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=ChooseSpeedScene, wizard_id=callback_data.wizard_id)

    @on.callback_query(Callback.filter(F.power))
    async def change_power(self, query: CallbackQuery, callback_data: Callback) -> None:
        await self.wizard.goto(scene=ChoosePowerScene, wizard_id=callback_data.wizard_id)

    @on.callback_query(Callback.filter(F.delete_wizard))
    async def delete_wizard(self, query: CallbackQuery, callback_data: Callback) -> None:
        await delete_obj(obj_type="wizard", obj_id=callback_data.wizard_id)
        await self.wizard.goto(scene=WizardsListScene)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery) -> None:
        await self.wizard.goto(scene=WizardsListScene)


class ChooseSpeedScene(Scene, state="speed"):
    class Callback(CallbackData, prefix="speed"):
        wizard_id: int
        speed: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, wizard_id: int) -> Any:
        builder = InlineKeyboardBuilder()
        for speed, speed_name in speednames.items():
            builder.button(text=speed_name + " (" + str(speed) + ")",
                           callback_data=self.Callback(wizard_id=wizard_id, speed=speed).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=query.from_user.id, text="Select wizard's speed",
                              reply_markup=builder.as_markup()))

    @on.callback_query(Callback.filter(F.speed))
    async def set_speed(self, query: CallbackQuery, callback_data: Callback) -> None:
        await set_wizard_param(wizard_id=callback_data.wizard_id, param='speed', value=callback_data.speed)
        await self.wizard.goto(scene=EditWizardScene, wizard_id=callback_data.wizard_id)


class ChoosePowerScene(Scene, state="power"):
    class Callback(CallbackData, prefix="power"):
        wizard_id: int
        power: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, wizard_id: int) -> Any:
        builder = InlineKeyboardBuilder()
        for power, powername in powernames.items():
            builder.button(text=powername + " (" + str(power) + ")",
                           callback_data=self.Callback(wizard_id=wizard_id, power=power).pack())
        builder.adjust(1, True)
        await bot(SendMessage(chat_id=query.from_user.id, text="Select wizard's power",
                              reply_markup=builder.as_markup()))

    @on.callback_query(Callback.filter(F.power))
    async def set_power(self, query: CallbackQuery, callback_data: Callback) -> None:
        await set_wizard_param(wizard_id=callback_data.wizard_id, param='power', value=callback_data.power)
        await self.wizard.goto(scene=EditWizardScene, wizard_id=callback_data.wizard_id)


# todo make separate scenes: NewSkillScene, SkillDescriptionScene
class NewSkillScene(Scene, state="new_skill"):
    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, wizard_id: int) -> Any:
        builder = InlineKeyboardBuilder()
        builder.button(text="🚫 Cancel", callback_data=FunctionalCallback(back=True))
        await state.update_data(wizard_id=wizard_id, name_request=True)
        await bot(SendMessage(chat_id=query.from_user.id,
                              text="Enter skill's name.", reply_markup=builder.as_markup()))

    @on.message()
    async def on_message(self, message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        wizard_id = data['wizard_id']
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
            await message.answer(text="Power: " + str(manacost))
            await add_skill(wizard_id, name, description, manacost)

            await state.set_data({})
            await self.wizard.goto(scene=EditWizardScene, wizard_id=wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        wizard_id = data['wizard_id']
        await state.set_data({})
        await self.wizard.goto(scene=EditWizardScene, wizard_id=wizard_id)


class SkillScene(Scene, state="skill"):
    class Callback(CallbackData, prefix="skill"):
        delete: bool = False

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, skill_id: int, wizard_id: int) -> None:
        skill = await obj_info(obj_type='skill', obj_id=skill_id)

        await state.update_data(wizard_id=wizard_id, skill_id=skill.id)

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Back", callback_data=FunctionalCallback(back=True))
        builder.button(text="🗑 Delete skill", callback_data=self.Callback(delete=True))
        builder.adjust(1, True)

        await bot(SendMessage(chat_id=query.from_user.id,
                              text=skill.name + "\n\n" + skill.description + "\n\n" + str(skill.manacost),
                              reply_markup=builder.as_markup()))

    @on.callback_query(Callback.filter(F.delete))
    async def delete(self, query: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        skill_id = data['skill_id']
        wizard_id = data['wizard_id']
        await delete_obj(obj_type="skill", obj_id=skill_id)

        await state.set_data({})
        await self.wizard.goto(scene=EditWizardScene, wizard_id=wizard_id)

    @on.callback_query(FunctionalCallback.filter(F.back))
    async def exit(self, query: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        wizard_id = data['wizard_id']

        await state.set_data({})
        await self.wizard.goto(scene=EditWizardScene, wizard_id=wizard_id)


router = Router(name=__name__)
router.message.register(WizardsListScene.as_handler(), Command("wizards"))


@router.message(CommandStart())
async def command_start(message: Message, scenes: ScenesManager) -> None:
    await scenes.close()
    await checkin_user(user_id=message.chat.id)
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
        print("Shutting down")
