import asyncio
import typing as tp
from dataclasses import dataclass

from commonlib.models import ActionMetadata, ContestAction, ContestResult, Wizard

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
    """
    There are four stages of match which repeat in a cycle.
    Stage 0. Users send their wizards (only in the beginning of the match)
    and the turn order is determined.
    Stage 1. Users request turn orders
    Stage 2. The caster requests available spells and sends the cast information.
    After that, the action is created.
    Stage 3. Users request the action.
    """

    def __init__(self, battlefield: Battlefield | None = None):
        self._wizards: dict[int, Wizard] = {}
        if battlefield is None:
            self._battlefield = Battlefield()
        else:
            self._battlefield = battlefield
        self._match: Match | None = None
        self._state: MatchState = MatchState()

        self._stage_0 = asyncio.Event()
        self._stage_1 = asyncio.Event()
        self._stage_2 = asyncio.Event()
        self._stage_3 = asyncio.Event()

        # stage 1
        self._turn_request_counter = 0
        self._action_request_counter = 0

    async def set_wizard(self, user_id: int, wizard: Wizard) -> None:
        self._battlefield.set_wizard(user_id, wizard)
        self._wizards[user_id] = wizard
        if len(self._wizards) == 2:
            await self._battlefield.start_contest()
            self._match = self._create_match()
            asyncio.create_task(anext(self._match))

    async def get_user_to_make_turn(self) -> int:
        await self._stage_0.wait()
        self._turn_request_counter += 1
        if self._turn_request_counter == 2:
            self._stage_1.set()
            self._turn_request_counter = 0
        return self._state.user_to_make_turn

    async def cast_spell(self, user_id: int, spell_id: int) -> None:
        assert len(self._wizards) == 2
        assert user_id == self._state.user_to_make_turn, "Not this player's turn"
        await self._match.asend(spell_id)

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

    async def get_contest_action(self) -> ContestAction:
        await self._stage_2.wait()
        self._action_request_counter += 1
        if self._action_request_counter == len(self._wizards):
            self._stage_3.set()
            self._action_request_counter = 0
        return ContestAction(
            action=self.action,
            metadata=self.action_metadata,
            result=self.result,
        )

    async def get_available_spells(self, user_id: int) -> list[int]:
        return await self._battlefield.get_available_spells(user_id)

    async def _create_match(self) -> Match:
        for step in range(settings.TURNS_COUNT):
            self._state.user_to_make_turn = await self._battlefield.get_user_to_make_turn()

            self._stage_2 = asyncio.Event()
            self._stage_3 = asyncio.Event()

            self._stage_0.set()
            await self._stage_1.wait()

            spell_id = yield

            assert spell_id is not None

            wizard = self._wizards[self._state.user_to_make_turn]
            if spell_id == -1:
                casted_spell = DUMMY_SPELL
            else:
                casted_spell = next(spell for spell in wizard.spells if spell.id == spell_id)
            self._state.action = await self._do_cast_spell(self._state.user_to_make_turn, spell_id)
            self._state.action_metadata = ActionMetadata(caster_wizard=wizard, spell=casted_spell)
            if step == settings.TURNS_COUNT - 1:
                self._state.result = await self._get_winner()

            self._stage_0 = asyncio.Event()
            self._stage_1 = asyncio.Event()

            self._stage_2.set()
            await self._stage_3.wait()
        yield

    async def _do_cast_spell(self, user_id: int, spell_id: int) -> str:
        return await self._battlefield.cast_spell(user_id, spell_id)

    async def _get_winner(self) -> ContestResult:
        return await self._battlefield.get_winner()
