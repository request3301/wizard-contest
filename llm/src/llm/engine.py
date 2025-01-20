import json
from pathlib import Path

from commonlib.models import ActionGenerationResponse, Message, Pair, SpellBase, SpellType, Wizard
from fastapi import APIRouter, status

from .client import LLMError, generate_response

router = APIRouter()

PROMPTS_PATH = Path(__file__).parent / 'prompts'


def get_messages(filename: str, has_schema: bool = False, **replacements):
    if has_schema:
        with open(PROMPTS_PATH / f'{filename}_schema.json', 'r') as f:
            schema = f.read()
        replacements['schema'] = schema
    with open(PROMPTS_PATH / f'{filename}.json', 'r') as f:
        prompt = f.read()
    messages = json.loads(prompt)
    for message in messages:
        if not isinstance(message['content'], str):
            message['content'] = json.dumps(message['content'])
        for key, value in replacements.items():
            message['content'] = message['content'].replace(f'<{key}>', str(value))
    return messages


@router.get('/spell/calculate_manacost', status_code=status.HTTP_200_OK)
async def calculate_manacost(type_: SpellType, description: str) -> int:
    messages = get_messages(
        'calculate_manacost',
        description=description,
        type_=type_,
    )
    response = await generate_response(messages)
    return int(response)


@router.post('/contest/start', status_code=status.HTTP_200_OK)
async def start_contest(wizards: Pair[Wizard]):
    active_spells = ['', '']
    passive_spells = ['', '']
    for wizard_n in [0, 1]:
        for spell in wizards[wizard_n].spells:
            if spell.type_ == SpellType.ACTIVE:
                active_spells[wizard_n] += f'**{spell.name}**: {spell.description}\n'
            elif spell.type_ == SpellType.PASSIVE:
                passive_spells[wizard_n] += f'**{spell.name}**: {spell.description}\n'
    messages = get_messages(
        'start_contest',
        wizard_name_0=wizards[0].name,
        wizard_name_1=wizards[1].name,
        passive_spells_0=passive_spells[0],
        passive_spells_1=passive_spells[1],
        active_spells_0=active_spells[0],
        active_spells_1=active_spells[1],
    )
    return messages


@router.get('/contest/generate_action', status_code=status.HTTP_200_OK)
async def generate_action(messages: list[Message], wizard: Wizard, spell: SpellBase) -> ActionGenerationResponse:
    messages.append(
        {
            'role': 'user',
            'content': f'{wizard.name} uses {spell.name}. ' f"It's description: {spell.description}",
        }
    )
    response = await generate_response(messages)
    messages.append(
        {
            'role': 'assistant',
            'content': response,
        }
    )
    return ActionGenerationResponse(new_messages=messages, action=response)


@router.post('/contest/determine_turn', status_code=status.HTTP_200_OK)
async def determine_turn(messages: list[Message], wizards: Pair[Wizard]) -> int:
    """
    :return: index of wizard in the pair
    """
    prompt = get_messages('determine_turn')
    request = messages + prompt
    response = await generate_response(request)
    for index, wizard in enumerate(wizards):
        if response == wizard.name:
            return index
    raise LLMError(f'Turn determination failed. LLM response:\n{response}')


@router.get('/contest/pick_winner', status_code=status.HTTP_200_OK)
async def pick_winner(messages: list[Message]) -> str | None:
    """
    :param messages: All contest messages
    :return: Name of winner or None in case of the tie
    """
    messages.extend(get_messages('pick_winner', has_schema=True))
    response = await generate_response(
        messages,
        response_format={'type': 'json_object'},
    )
    schema = json.loads(response)
    winner = schema['winner']
    is_tie = schema['is_tie']
    if is_tie:
        return None
    return winner
