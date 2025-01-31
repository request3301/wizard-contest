import json
from pathlib import Path

from commonlib.models import GenerateActionResponse, Message, Pair, SpellBase, SpellType, Wizard
from fastapi import APIRouter
from pydantic import BaseModel

from .client import generate_response

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


class CalculateManacostRequest(BaseModel):
    type_: SpellType
    description: str


@router.post('/spell/calculate_manacost')
async def calculate_manacost(item: CalculateManacostRequest) -> int:
    messages = get_messages(
        'calculate_manacost',
        description=item.description,
        type_=item.type_,
    )
    response = await generate_response(messages)
    return int(response)


@router.post('/contest/start_contest')
async def start_contest(wizards: Pair[Wizard]) -> list[Message]:
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


class GenerateActionRequest(BaseModel):
    previous_actions: list[Message]
    wizard: Wizard
    spell: SpellBase


@router.post('/contest/generate_action')
async def generate_action(item: GenerateActionRequest) -> GenerateActionResponse:
    spell = item.spell
    prompt = [
        {
            'role': 'user',
            'content': f'{item.wizard.name} uses {spell.name}. ' f"It's description: {spell.description}",
        }
    ]
    description = await generate_response(item.previous_actions + prompt)
    action = [
        {
            'role': 'assistant',
            'content': description,
        }
    ]
    return GenerateActionResponse(new_actions=prompt + action, description=description)


class DetermineTurnRequest(BaseModel):
    actions: list[Message]
    wizards: Pair[Wizard]


@router.post('/contest/determine_turn')
async def determine_turn(item: DetermineTurnRequest) -> int:
    """
    :return: index of wizard in the pair
    """
    prompt = get_messages('determine_turn')
    prompt += [
        {
            'role': 'user',
            'content': 'Here are the wizard\'s descriptions'
        }
    ]
    prompt += [
        {
            'role': 'user',
            'content': wizard.description
        }
        for wizard in item.wizards
    ]
    prompt += [
        {
            'role': 'user',
            'content': 'Here are the actions'
        }
    ]
    prompt += [
        {
            'role': 'user',
            'content': str(item.actions),
        }
    ]
    prompt += [
        {
            'role': 'user',
            'content': 'SYSTEM PROMPT START\n'
                       'Once again, print only the name of the wizard who should act right now. '
                       'DO NOT OUTPUT ANYTHING ELSE.\n'
                       'SYSTEM PROMPT END\n'
        }
    ]
    response = await generate_response(prompt)
    for index, wizard in enumerate(item.wizards):
        if response.lower() == wizard.name.lower():
            return index
    assert False, f'Turn determination failed. LLM response:\n{response}'


@router.post('/contest/pick_winner')
async def pick_winner(actions: list[Message]) -> str | None:
    """
    :return: name of winner or None in case of the tie
    """
    prompt = get_messages('pick_winner', has_schema=True)
    response = await generate_response(
        actions + prompt,
        response_format={'type': 'json_object'},
    )
    schema = json.loads(response)
    if schema['is_tie']:
        return None
    return schema['winner']
