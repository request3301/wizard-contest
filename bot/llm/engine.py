import json

from database.models import WizardData
from llm.client import client, model


def get_messages(filename: str, schema: bool = False, **replacements):
    with open(f"bot/llm/prompts/{filename}.json", "r") as f:
        prompt = f.read()
    for key, value in replacements.items():
        prompt = prompt.replace(f"<{key}>", value)
    messages = json.loads(prompt)
    if schema:
        with open(f"bot/llm/prompts/{filename}_schema.json", "r") as f:
            schema = f.read()
        for message in messages:
            message['content'] = message['content'].replace("<schema>", schema)
    return messages


async def calculate_manacost(description: str):
    response = await client.chat.completions.create(
        model=model,
        messages=get_messages("calculate_manacost", description=description),
    )
    return int(response.choices[0].message.content)


def start_contest(wizards: list[WizardData]):
    messages = get_messages("start_contest", wizard_name_0=wizards[0].name, wizard_name_1=wizards[1].name)
    return messages


async def generate_action(messages, wizard_name: str, skill_name: str, description: str):
    messages.append({
        'role': "user",
        'content': f"{wizard_name} uses {skill_name}. It's description: {description}",
    })
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    resp = response.choices[0].message.content
    messages.append({
        "role": "assistant",
        "content": resp,
    })
    return resp


async def determine_turn(messages, wizards: list[WizardData]) -> int:
    prompt = get_messages("determine_turn")
    temp = messages + prompt
    response = await client.chat.completions.create(
        model=model,
        messages=temp,
    )
    resp = response.choices[0].message.content
    if resp == wizards[0].name:
        return 0
    elif resp == wizards[1].name:
        return 1
    print(f"Turn determination failed. LLM response:\n{resp}")


async def pick_winner(messages) -> (str, bool):
    """
    :param messages: All contest messages
    :return: Name of the winner and whether it's a tie
    """
    messages.extend(get_messages("pick_winner", schema=True))
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    resp = response.choices[0].message.content
    schema = json.loads(resp)
    winner = schema["winner"]
    is_tie = schema["is_tie"]
    return winner, is_tie
