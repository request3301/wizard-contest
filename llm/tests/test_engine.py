import pytest
from commonlib.models import Pair, Spell, SpellType, Wizard

from llm.client import LLMError
from llm.engine import calculate_manacost, determine_turn, generate_action, pick_winner, start_contest

test_wizard_1 = Wizard(
    id=3,
    name="Merlin",
    description="Powerful wizard",
    speed=1,
    power=4,
    spells=[
        Spell(id=1, type_=SpellType.ACTIVE, name="Fireball", description="Launches a fireball", manacost=4),
        Spell(id=2, type_=SpellType.ACTIVE, name="Ice Bolt", description="Fires ice bolt", manacost=3),
    ]
)

test_wizard_2 = Wizard(
    id=4,
    speed=3,
    power=3,
    name="Gandalf",
    description="Grey wizard",
    spells=[
        Spell(id=3, type_=SpellType.ACTIVE, name="Lightning", description="Summons lightning", manacost=5),
        Spell(id=4, type_=SpellType.ACTIVE, name="Shield", description="Creates shield", manacost=2),
    ]
)

wizard_pair = Pair([test_wizard_1, test_wizard_2])


@pytest.mark.asyncio
async def test_calculate_manacost(mocker, mock_groq_response):
    mock_create = mocker.patch('llm.client.client.chat.completions.create')
    mock_create.return_value = mock_groq_response('5')

    result = await calculate_manacost(type_=SpellType.ACTIVE, description='test spell')

    assert result == 5
    mock_create.assert_called_once_with(
        messages=mocker.ANY,
        model='llama-3.1-70b-versatile'
    )


@pytest.mark.asyncio
async def test_start_contest():
    messages = await start_contest(wizard_pair)

    assert isinstance(messages, list)
    assert all(isinstance(m, dict) for m in messages)
    assert all("role" in m and "content" in m for m in messages)


@pytest.mark.asyncio
async def test_generate_action(mocker, mock_groq_response):
    mock_create = mocker.patch('llm.client.client.chat.completions.create')
    mock_create.return_value = mock_groq_response("Merlin casts a powerful spell!")

    test_messages = [{"role": "user", "content": "test"}]
    result = await generate_action(test_messages.copy(), test_wizard_1, test_wizard_1.spells[0])

    assert len(result.new_messages) == len(test_messages) + 2
    assert result.action == "Merlin casts a powerful spell!"


@pytest.mark.asyncio
async def test_determine_turn(mocker, mock_groq_response):
    mock_create = mocker.patch('llm.client.client.chat.completions.create')
    mock_create.return_value = mock_groq_response(wizard_pair[0].name)

    result = await determine_turn(
        [{"role": "user", "content": "test"}],
        wizard_pair
    )

    assert result == 0


@pytest.mark.asyncio
async def test_determine_turn_error(mocker, mock_groq_response):
    mock_create = mocker.patch('llm.client.client.chat.completions.create')
    mock_create.return_value = mock_groq_response("Invalid")

    with pytest.raises(LLMError):
        await determine_turn(
            [{"role": "user", "content": "test"}],
            [test_wizard_1, test_wizard_2]
        )


@pytest.mark.asyncio
async def test_pick_winner(mocker, mock_groq_response):
    mock_create = mocker.patch('llm.client.client.chat.completions.create')
    mock_create.return_value = mock_groq_response('{"winner": "Merlin", "is_tie": false}')

    result = await pick_winner([{"role": "user", "content": "test"}])

    assert result == "Merlin"


@pytest.mark.asyncio
async def test_pick_winner_tie(mocker, mock_groq_response):
    mock_create = mocker.patch('llm.client.client.chat.completions.create')
    mock_create.return_value = mock_groq_response('{"winner": null, "is_tie": true}')

    result = await pick_winner([{"role": "user", "content": "test"}])

    assert result is None
