import typing as tp
from dataclasses import dataclass

from commonlib.models import ActionMetadata, ContestResult, Wizard

from .battlefield import Battlefield, DUMMY_SPELL
from .config import settings


@dataclass
class MatchState:
    """Represents the current state of a match"""
    user_to_make_turn: int | None = None
    action: str | None = None
    action_metadata: ActionMetadata | None = None
    result: ContestResult | None = None


Match = tp.AsyncGenerator[int, int]


class Director:
    def __init__(self, battlefield: Battlefield | None = None):
        self._wizards: dict[int, Wizard] = {}
        if battlefield is None:
            self._battlefield = Battlefield()
        else:
            self._battlefield = battlefield
        self._match: Match | None = None
        self._state: MatchState = MatchState()

    async def set_wizard(self, user_id: int, wizard: Wizard) -> None:
        self._battlefield.set_wizard(user_id, wizard)
        self._wizards[user_id] = wizard
        if len(self._wizards) == 2:
            await self._battlefield.start_contest()
            self._match = self._create_match()
            await anext(self._match)

    async def get_user_to_make_turn(self) -> int:
        return self._state.user_to_make_turn

    async def make_turn(self, user_id: int, spell_id: int) -> None:
        assert len(self._wizards) == 2
        assert user_id == self._state.user_to_make_turn, "Not this player's turn"
        await self._match.asend(spell_id)
        # await anext(self._match)

    @property
    def action(self) -> str:
        assert self._state.action is not None, "No action available"
        return self._state.action

    @property
    def action_metadata(self) -> ActionMetadata:
        assert self._state.action_metadata is not None
        return self._state.action_metadata

    @property
    def result(self) -> ContestResult | None:
        return self._state.result

    async def get_available_spells(self, user_id: int) -> list[int]:
        return await self._battlefield.get_available_spells(user_id)

    async def _create_match(self) -> Match:
        for step in range(settings.TURNS_COUNT):
            self._state.user_to_make_turn = await self._battlefield.get_turn()
            print(f'{step=}\n{settings.TURNS_COUNT=}')
            spell_id = yield
            assert spell_id is not None
            self._state.action = await self._do_cast_spell(self._state.user_to_make_turn, spell_id)

            wizard = self._wizards[self._state.user_to_make_turn]
            if spell_id == -1:
                casted_spell = DUMMY_SPELL
            else:
                casted_spell = next(spell for spell in wizard.spells if spell.id == spell_id)
            self._state.action_metadata = ActionMetadata(caster_wizard=wizard, spell=casted_spell)

        self._state.result = await self._get_winner()
        yield

    async def _do_cast_spell(self, user_id: int, spell_id: int) -> str:
        return await self._battlefield.cast_spell(user_id, spell_id)

    async def _get_winner(self) -> ContestResult:
        return await self._battlefield.get_winner()
