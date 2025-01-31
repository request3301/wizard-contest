import pytest
from commonlib.models import ActionMetadata, ContestResult

from contest.config import settings
from contest.director import Director


@pytest.fixture
def director():
    return Director()


@pytest.mark.asyncio
async def test_set_wizard(httpx_mock, director, test_wizard_1, test_wizard_2):
    # Mock contest start endpoint
    httpx_mock.add_response(status_code=200)
    # Mock first turn determination
    httpx_mock.add_response(text="0")

    # First wizard setup shouldn't start match
    await director.set_wizard(3, test_wizard_1)
    assert len(director._wizards) == 1
    assert director._match is None

    # Second wizard setup should start match
    await director.set_wizard(4, test_wizard_2)
    assert len(director._wizards) == 2
    assert director._match is not None


@pytest.mark.asyncio
async def test_match_flow(httpx_mock, director, test_wizard_1, test_wizard_2):
    # Mock all required endpoints
    httpx_mock.add_response(status_code=200)
    httpx_mock.add_response(text="0")
    httpx_mock.add_response(
        json={
            "action": "Merlin casts Fireball!",
            "new_messages": [{"role": "system", "content": "Spell cast"}]
        }
    )
    httpx_mock.add_response(text="1")

    # Setup match
    await director.set_wizard(3, test_wizard_1)
    await director.set_wizard(4, test_wizard_2)

    # Check first turn
    user_id = await director.get_user_to_make_turn()
    assert user_id == 3

    # Make turn
    await director.cast_spell(3, 1)
    assert director.action == "Merlin casts Fireball!"
    assert isinstance(director.action_metadata, ActionMetadata)
    assert director.action_metadata.caster_wizard == test_wizard_1
    assert director.action_metadata.spell.id == 1


@pytest.mark.asyncio
async def test_available_spells(httpx_mock, director, test_wizard_1):
    # httpx_mock.add_response(status_code=200)
    await director.set_wizard(3, test_wizard_1)
    spells = await director.get_available_spells(3)
    assert spells == [1, 2]


@pytest.mark.asyncio
async def test_match_completion(httpx_mock, director, test_wizard_1, test_wizard_2):
    # Mock contest start
    httpx_mock.add_response(status_code=200)

    # Mock turns and actions
    for _ in range(settings.TURNS_COUNT):
        httpx_mock.add_response(text="0")
        httpx_mock.add_response(
            json={
                "action": "Spell cast",
                "new_messages": []
            }
        )

    # Mock winner determination
    httpx_mock.add_response(text="Merlin")

    # Setup and play match
    await director.set_wizard(3, test_wizard_1)
    await director.set_wizard(4, test_wizard_2)

    for _ in range(settings.TURNS_COUNT):
        user_id = await director.get_user_to_make_turn()
        await director.cast_spell(user_id, -1)

    assert isinstance(director.result, ContestResult)
    assert director.result.winner == test_wizard_1


@pytest.mark.asyncio
async def test_tie_result(httpx_mock, director, test_wizard_1, test_wizard_2):
    # Setup mocks for complete match with tie
    httpx_mock.add_response(status_code=200)
    for _ in range(settings.TURNS_COUNT):
        httpx_mock.add_response(text="0")
        httpx_mock.add_response(
            json={
                "action": "Spell cast",
                "new_messages": []
            }
        )
    httpx_mock.add_response(text="")

    await director.set_wizard(3, test_wizard_1)
    await director.set_wizard(4, test_wizard_2)

    for _ in range(settings.TURNS_COUNT):
        user_id = await director.get_user_to_make_turn()
        await director.cast_spell(user_id, -1)

    assert director.result.tie is True
