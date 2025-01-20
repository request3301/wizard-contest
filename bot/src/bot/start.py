from datetime import datetime

from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.scene import SceneRegistry, ScenesManager
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import Message

from .database.queries import checkin_user
from .matchmaking.match import MatchScene
from .matchmaking.queue import QueueScene
from .matchmaking.wizard_selection import SelectWizardScene
from .spell.create import (
    CreateSpellScene,
    EnterSpellDescriptionScene,
    EnterSpellNameScene,
    EnterSpellTypeScene,
)
from .spell.info import SpellInfoScene
from .utils import greetings
from .wizard.create import NewWizardScene
from .wizard.info import WizardInfoScene
from .wizard.list import WizardsListScene
from .wizard.parameters.power import ChoosePowerScene
from .wizard.parameters.speed import ChooseSpeedScene

router = Router(name=__name__)
router.message.register(WizardsListScene.as_handler(), Command('wizards'))
router.message.register(SelectWizardScene.as_handler(), Command('contest'))


@router.message(CommandStart())
async def command_start(message: Message, scenes: ScenesManager):
    await scenes.close()
    await checkin_user(user_id=message.chat.id)
    await greetings(message.chat.id)


bot_start_time = datetime.now()


@router.message(Command('test'))
async def command_test(message: Message):
    await message.answer(text=f'build {bot_start_time.strftime("%d/%m/%Y %H:%M:%S")}')


def create_dispatcher():
    dispatcher = Dispatcher(
        events_isolation=SimpleEventIsolation(),
    )
    dispatcher.include_router(router)

    scene_registry = SceneRegistry(dispatcher, register_on_add=True)

    scene_registry.add(
        WizardsListScene,
        NewWizardScene,
        WizardInfoScene,
        ChooseSpeedScene,
        ChoosePowerScene,
        CreateSpellScene,
        EnterSpellNameScene,
        EnterSpellTypeScene,
        EnterSpellDescriptionScene,
        SpellInfoScene,
        SelectWizardScene,
        QueueScene,
        MatchScene,
    )

    return dispatcher
