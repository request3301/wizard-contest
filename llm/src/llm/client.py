from commonlib.models import Message
from groq import AsyncGroq

from .config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

model = 'llama-3.3-70b-versatile'


async def generate_response(messages: list[Message], **kwargs) -> str:
    response = await client.chat.completions.create(
        messages=messages,
        model=model,
        **kwargs,
    )
    response_text = response.choices[0].message.content
    if response_text is None:
        raise LLMError
    return response_text


class LLMError(Exception):
    pass
