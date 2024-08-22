from groq import AsyncGroq

from config import Settings

client = AsyncGroq(api_key=Settings().GROQ_API_KEY)

model = "llama3-8b-8192"
