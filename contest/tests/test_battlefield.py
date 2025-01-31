import pytest
from commonlib.models import Message

from contest.battlefield import Battlefield


@pytest.fixture
def battlefield(test_wizard_1, test_wizard_2):
    battlefield = Battlefield()
    battlefield.set_wizard(3, test_wizard_1)
    battlefield.set_wizard(4, test_wizard_2)
    return battlefield


@pytest.mark.asyncio
async def test_cast_spell(httpx_mock, battlefield, test_wizard_1):
    response_data = {
        "action": "Merlin casts a powerful fireball!",
        "new_messages": [{"role": "system", "content": "Fireball cast"}]
    }
    httpx_mock.add_response(json=response_data)

    action = await battlefield.cast_spell(3, 1)
    assert action == "Merlin casts a powerful fireball!"
    assert battlefield._messages == [Message(role="system", content="Fireball cast")]
    assert 1 in battlefield._used_spells


@pytest.mark.asyncio
async def test_start_contest(httpx_mock, battlefield):
    httpx_mock.add_response(status_code=200)

    await battlefield.start_contest()
    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/contest/start"


@pytest.mark.asyncio
async def test_get_turn(httpx_mock, battlefield):
    httpx_mock.add_response(text="0")

    turn_user_id = await battlefield.get_user_to_make_turn()
    assert turn_user_id == 3


@pytest.mark.asyncio
async def test_get_available_spells(battlefield):
    available_spells = await battlefield.get_available_spells(3)
    assert available_spells == [1, 2]  # Both spells are active and available

    battlefield._used_spells.add(1)
    available_spells = await battlefield.get_available_spells(3)
    assert available_spells == [2]  # Only second spell available after using first


@pytest.mark.asyncio
async def test_get_winner(httpx_mock, battlefield, test_wizard_1):
    httpx_mock.add_response(text="Merlin")

    result = await battlefield.get_winner()
    assert result.winner == test_wizard_1


@pytest.mark.asyncio
async def test_get_winner_tie(httpx_mock, battlefield):
    httpx_mock.add_response(text="")

    result = await battlefield.get_winner()
    assert result.tie is True
