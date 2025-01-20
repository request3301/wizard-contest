import asyncio

import httpx
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import ContestAction, ContestResult, Wizard

from ..config import settings
from ..utils import bot


class MatchScene(Scene, state='MatchScene'):
    class UseSpellCallback(CallbackData, prefix='use_spell'):
        spell_index: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, director_id: int) -> None:
        await query.answer('Match started!')
        await state.update_data(director_id=director_id)

        async with httpx.AsyncClient() as client:
            user_id = query.from_user.id
            wizard: Wizard = await state.get_value('wizard')
            url = settings.CONTEST_SERVICE_URL + f'/director/{director_id}/user/{user_id}/wizard/set'
            await client.post(url=url, json=wizard.model_dump())

        while (result := await self.do_match_iteration(state)) is None:
            pass
        if result.tie:
            await bot.send_message(
                chat_id=user_id,
                text='Tie!',
            )
            return

        await bot.send_message(chat_id=user_id, text=f'The winner is <b>{result.winner.name}</b>')

    async def do_match_iteration(self, state: FSMContext) -> ContestResult | None:
        user_id = await state.get_value('user_id')
        director_id = await state.get_value('director_id')

        async with httpx.AsyncClient() as client:
            url = settings.CONTEST_SERVICE_URL + f'/director/{director_id}/get_turn'
            response = await client.get(url=url)
            user_to_make_turn = int(response.text)

        action_happened = asyncio.Event()
        await state.update_data(action_happened=action_happened)

        if user_to_make_turn == user_id:
            await self.send_make_turn_message(state)
        else:
            (
                await bot.send_message(
                    chat_id=user_id,
                    text='The opponent is choosing spell...',
                ),
            )

        await action_happened.wait()

        async with httpx.AsyncClient() as client:
            url = settings.CONTEST_SERVICE_URL + f'/director/{director_id}/action'
            response = await client.get(url=url)
            action = ContestAction.model_validate(response.json())

        wizard = action.metadata.wizard
        spell = action.metadata.spell

        await bot.send_message(chat_id=user_id, text=f'<b>{wizard.name}</b> casted <b>{spell.name}</b>!')

        await bot.send_message(
            chat_id=user_id,
            text=action.action,
        )

        return action.result

    async def send_make_turn_message(self, state) -> None:
        user_id = await state.get_value('user_id')
        director_id = await state.get_value('director_id')
        wizard = await state.get_value('wizard')

        async with httpx.AsyncClient() as client:
            url = settings.CONTEST_SERVICE_URL + f'/director/{director_id}/get_available_spells/{user_id}'
            response = await client.get(url=url)
            available_spells_ids = response.json()

        spells_dict = {spell.id: spell for spell in wizard.spells}

        builder = InlineKeyboardBuilder()
        for spell_id in available_spells_ids:
            spell = spells_dict[spell_id]
            builder.button(text=spell.name, callback_data=self.UseSpellCallback(spell_index=spell.id))
        builder.button(text='Simple attack', callback_data=self.UseSpellCallback(spell_index=-1).pack())
        builder.adjust(1, repeat=True)

        (
            await bot.send_message(
                chat_id=user_id,
                text='Choose spell to cast',
                reply_markup=builder.as_markup(),
            ),
        )

    @on.callback_query(UseSpellCallback.filter())
    async def on_use_spell(self, query: CallbackQuery, callback_data: UseSpellCallback, state: FSMContext):
        data = await state.get_data()
        match = data['match']

        spell_selection_message = query.message
        assert spell_selection_message is not None

        await bot.delete_message(chat_id=query.from_user.id, message_id=spell_selection_message.message_id)
        await match.asend(callback_data.spell_index)
