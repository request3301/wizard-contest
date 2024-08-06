from groq import AsyncGroq

from settings import Settings

client = AsyncGroq(api_key=Settings().GROQ_API_KEY)


async def calculate_manacost(description: str):
    response = await client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {'role': "system", 'content': "You are a machine which takes description of a magic spell as an "
                                          "input. As output, you give power of that spell in a single number "
                                          "ranging from 1 to 5. THE ONLY THING YOU WRITE IS A SINGLE NUMBER. "
                                          "If input doesn't sound like a skill, the output should be -1."},
            {"role": "user", "content": "It creates a massive ball of energy which draws in nearby matter and "
                                        "destroys it."},
            {"role": "assistant", "content": "4"},
            {"role": "user", "content": "User can connect a wodoo doll with the opponent. Hereby some degree of "
                                        "damage dealt to the doll will transfer to the opponent"},
            {"role": "assistant", "content": "2"},
            {"role": "user", "content": "User can clap and change places with the opponent"},
            {"role": "assistant", "content": "1"},
            {"role": "user", "content": "bip bip bop"},
            {"role": "assistant", "content": "-1"},
            {"role": "user", "content": "It deploys a territory around the user. It's radius is 10 meters. Everything "
                                        "in it's radius will be subject to constant cutting attacks."},
            {"role": "assistant", "content": "5"},
            {"role": "user", "content": "It summons a giant frog which can pierce through enemies with it's tongue"},
            {"role": "assistant", "content": "3"},
            {"role": "user", "content": description},
        ],
    )
    return int(response.choices[0].message.content)
    # return 5
