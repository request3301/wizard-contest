import asyncio
import subprocess
import time
from pathlib import Path

import pytest
from commonlib.models import ContestAction, Spell, SpellType, Wizard
from commonlib.services import ContestClient


@pytest.fixture(scope='session', autouse=True)
def docker_compose_up():
    file = Path(__file__)

    # `llm` service will be started by `contest`
    subprocess.run(
        ['docker-compose', 'up', '-d', 'contest'],
        cwd=file.parent.parent.parent,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    time.sleep(2)
    yield

    subprocess.run(['docker-compose', 'logs', 'contest'], check=True)
    subprocess.run(['docker-compose', 'logs', 'llm'], check=True)

    subprocess.run(["docker-compose", "down", '--rmi', 'local'], check=True)


@pytest.fixture
def test_wizard_1() -> Wizard:
    return Wizard(
        id=3,
        name="Merlin",
        speed=1,
        power=4,
        spells=[
            Spell(id=1, type_=SpellType.ACTIVE, name="Fireball", description="Launches a fireball", manacost=4),
            Spell(id=2, type_=SpellType.ACTIVE, name="Ice Bolt", description="Fires ice bolt", manacost=3),
        ]
    )


@pytest.fixture
def test_wizard_2() -> Wizard:
    return Wizard(
        id=4,
        speed=3,
        power=3,
        name="Gandalf",
        spells=[
            Spell(id=3, type_=SpellType.ACTIVE, name="Lightning", description="Summons lightning", manacost=5),
            Spell(id=4, type_=SpellType.ACTIVE, name="Shield", description="Creates shield", manacost=2),
        ]
    )


async def test_all(test_wizard_1: Wizard, test_wizard_2: Wizard):
    contest_client = ContestClient('http://localhost:5001')

    director_id = await contest_client.create_director()

    set_1 = asyncio.create_task(contest_client.set_wizard(
        director_id=director_id,
        user_id=1,
        wizard=test_wizard_1,
    ))

    set_2 = asyncio.create_task(contest_client.set_wizard(
        director_id=director_id,
        user_id=2,
        wizard=test_wizard_2,
    ))

    await set_1
    await set_2

    while True:
        user_to_make_turn = await contest_client.get_user_to_make_turn(director_id=director_id)
        user_to_make_turn_repeat = await contest_client.get_user_to_make_turn(director_id=director_id)
        assert user_to_make_turn == user_to_make_turn_repeat

        get_action_task = asyncio.create_task(contest_client.get_action(director_id=director_id))

        available_spells = await contest_client.get_available_spells(
            director_id=director_id,
            user_id=user_to_make_turn
        )

        if not available_spells:
            spell_id = -1
        else:
            spell_id = available_spells[0]

        await contest_client.cast_spell(
            director_id=director_id,
            user_id=user_to_make_turn,
            spell_id=spell_id,
        )
        time.sleep(1)

        action: ContestAction = await get_action_task
        action_repeat = await contest_client.get_action(director_id=director_id)

        assert action == action_repeat

        assert action.action

        if action.result is not None:
            return
