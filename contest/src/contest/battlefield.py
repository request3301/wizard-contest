from commonlib.models import ContestResult, Message, Pair, Spell, SpellBase, SpellType, Wizard
from commonlib.services.llm import LLMClient

from .config import settings

llm_client = LLMClient(settings.LLM_SERVICE_URL)

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
        self._actions: list[Message] = []

    def set_wizard(self, user_id: int, wizard: Wizard):
        self._wizards[user_id] = wizard

    async def start_contest(self):
        wizards = Pair(self._wizards.values())
        await llm_client.start_contest(wizards)

    async def get_user_to_make_turn(self) -> int:
        """
        Determines the player that should act this turn based on happened events
        :return: user_id of player that should play this turn.
        """
        wizards = Pair(self._wizards.values())
        wizard_index = await llm_client.determine_turn(
            actions=self._actions,
            wizards=wizards.model_dump(),
        )
        for user_id, wizard in self._wizards.items():
            if wizard.id == wizards[wizard_index].id:
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
        winner_name = await llm_client.pick_winner(self._actions)
        if winner_name is None:
            return ContestResult(tie=True)
        for wizard in self._wizards.values():
            if wizard.name == winner_name:
                return ContestResult(winner=wizard)
        raise ValueError(f'No wizard named {winner_name}')

    async def _generate_action(self, wizard: Wizard, spell: SpellBase) -> str:
        response = await llm_client.generate_action(
            previous_actions=self._actions,
            wizard=wizard.model_dump(),
            spell=SpellBase(**spell.model_dump()).model_dump(),
        )
        self._actions += response.new_actions
        return response.description

    @staticmethod
    def _find_spell(wizard: Wizard, spell_id: int) -> Spell:
        for spell in wizard.spells:
            if spell.id == spell_id:
                return spell
        assert False, f'Not reachable. \n{wizard=} \n{spell_id=}'

    def _is_spell_available(self, spell: Spell) -> bool:
        return spell.id not in self._used_spells and spell.type_ == SpellType.ACTIVE
