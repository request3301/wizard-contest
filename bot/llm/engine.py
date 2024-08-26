import json

from database.models import WizardData
from llm.client import client, model


def get_prompt(filename: str, **replacements):
    with open(f"bot/llm/prompts/{filename}.md", "r") as f:
        prompt = f.read()
    for key, value in replacements.items():
        prompt = prompt.replace(f"<{key}>", value)
    return prompt


def get_messages(filename: str, **replacements):
    with open(f"bot/llm/prompts/{filename}.json", "r") as f:
        prompt = f.read()
    for key, value in replacements.items():
        prompt = prompt.replace(f"<{key}>", value)
    messages = json.loads(prompt)
    return messages


async def calculate_manacost(description: str):
    response = await client.chat.completions.create(
        model=model,
        messages=get_prompt("calculate_manacost", description=description),
    )
    return int(response.choices[0].message.content)


def start_contest(wizards: list[WizardData]):
    messages = [{
        'role': "system",
        'content': get_prompt("start_contest", wizard_name_0=wizards[0].name, wizard_name_1=wizards[1].name)
    }]
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


async def pick_winner(messages) -> (str, bool):
    """
    :param messages: All contest messages
    :return: Name of the winner and whether it's a tie
    """
    messages.append({
        "role": "user",
        "content": get_prompt("pick_winner"),
    })
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
