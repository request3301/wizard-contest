import httpx
from commonlib.models import ActionGenerationResponse, ContestResult, Message, Pair, Spell, SpellBase, SpellType, Wizard

from .config import settings

API_ENDPOINT = settings.LLM_SERVICE_URL + '/contest'

DUMMY_SPELL = Spell(
    id=-1,
    type_=SpellType.ACTIVE,
    name='Simple attack',
    description='Just a simple attack. Nothing special about it.',
    manacost=0,
)


class Battlefield:
    def __init__(self):
        self._wizards: dict[int, Wizard] = {}
        self._used_spells: set[int] = set()
        self._messages: list[Message] | None = None

    def set_wizard(self, user_id: int, wizard: Wizard):
        self._wizards[user_id] = wizard

    async def start_contest(self):
        wizards = Pair(self._wizards.values())
        async with httpx.AsyncClient() as client:
            await client.post(API_ENDPOINT + '/start', json=wizards.model_dump())

    async def get_turn(self) -> int:
        """
        Determines the player that should act this turn based on happened events
        :return: user_id of player that should play this turn.
        """
        async with httpx.AsyncClient() as client:
            wizards = Pair(self._wizards.values())
            query = {
                'messages': self._messages,
                'wizards': wizards.model_dump(),
            }
            response = await client.post(API_ENDPOINT + '/determine_turn', json=query)
        for user_id, wizard in self._wizards.items():
            if wizard.id == wizards[int(response.text)].id:
                return user_id
        assert False

    async def get_available_spells(self, user_id: int) -> list[int]:
        """
        :return: List of spell indexes
        """
        wizard = self._wizards[user_id]
        return [spell.id for spell in wizard.spells if self._is_spell_available(spell)]

    async def cast_spell(self, user_id: int, spell_id: int) -> str:
        wizard = self._wizards[user_id]

        if spell_id == -1:
            spell = DUMMY_SPELL
        else:
            assert spell_id not in self._used_spells

            spell = self._find_spell(wizard, spell_id)
            self._used_spells.add(spell.id)

        action = await self._generate_action(wizard, spell)
        return action

    async def get_winner(self) -> ContestResult:
        async with httpx.AsyncClient() as client:
            query = {
                'messages': self._messages,
            }
            response = await client.get(API_ENDPOINT + '/pick_winner', params=query)
            if not response.text:
                return ContestResult(tie=True)
            wizard_name = response.text
            for wizard in self._wizards.values():
                if wizard.name == wizard_name:
                    return ContestResult(winner=wizard)
            raise ValueError(f'No wizard named {wizard_name}')

    async def _generate_action(self, wizard: Wizard, spell: SpellBase) -> str:
        async with httpx.AsyncClient() as client:
            query = {
                'messages': self._messages,
                'wizard': wizard,
                'spell': spell.model_dump(),
            }
            response = await client.get(API_ENDPOINT + '/start', params=query)
            action_generation_response = ActionGenerationResponse.model_validate(response.json())
            self._messages = action_generation_response.new_messages
            return action_generation_response.action

    @staticmethod
    def _find_spell(wizard: Wizard, spell_id: int) -> Spell:
        for spell in wizard.spells:
            if spell.id == spell_id:
                return spell
        assert False, f'Not reachable. \n{wizard=} \n{spell_id=}'

    def _is_spell_available(self, spell: Spell) -> bool:
        return spell.id not in self._used_spells and spell.type_ == SpellType.ACTIVE
