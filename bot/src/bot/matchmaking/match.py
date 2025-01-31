import asyncio
import logging

from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, on
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from commonlib.models import ContestAction, ContestResult, Wizard
from commonlib.services import ContestClient

from ..config import settings
from ..utils import bot

contest_client = ContestClient(settings.CONTEST_SERVICE_URL)


class MatchScene(Scene, state='MatchScene'):
    class UseSpellCallback(CallbackData, prefix='use_spell'):
        spell_id: int

    @on.callback_query.enter()
    async def on_enter(self, query: CallbackQuery, state: FSMContext, director_id: int) -> None:
        await query.answer('Match started!')
        await state.update_data(director_id=director_id, user_id=query.from_user.id)

        user_id = query.from_user.id
        wizard: Wizard = await state.get_value('wizard')
        await contest_client.set_wizard(director_id=director_id, user_id=user_id, wizard=wizard)

        asyncio.create_task(self.start_match(user_id=user_id, state=state))

    async def start_match(self, user_id: int, state: FSMContext) -> None:
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

        user_to_make_turn = await contest_client.get_user_to_make_turn(director_id)

        if user_to_make_turn == user_id:
            await self.send_make_turn_message(state)
        else:
            (
                await bot.send_message(
                    chat_id=user_id,
                    text='The opponent is choosing spell...',
                ),
            )

        action: ContestAction = await contest_client.get_action(director_id)

        wizard = action.metadata.caster_wizard
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

        available_spells_ids = await contest_client.get_available_spells(director_id=director_id, user_id=user_id)

        spells_dict = {spell.id: spell for spell in wizard.spells}

        builder = InlineKeyboardBuilder()
        for spell_id in available_spells_ids:
            spell = spells_dict[spell_id]
            builder.button(text=spell.name, callback_data=self.UseSpellCallback(spell_id=spell.id).pack())
        builder.button(text='Simple attack', callback_data=self.UseSpellCallback(spell_id=-1).pack())
        builder.adjust(1, repeat=True)

        (
            await bot.send_message(
                chat_id=user_id,
                text='Choose spell to cast',
                reply_markup=builder.as_markup(),
            ),
        )

    @on.callback_query(UseSpellCallback.filter(F.spell_id))
    async def on_use_spell(self, query: CallbackQuery, callback_data: UseSpellCallback, state: FSMContext):
        logging.log(logging.INFO, f'Spell cast button pressed by user {query.from_user.id}')

        user_id = await state.get_value('user_id')
        director_id = await state.get_value('director_id')
        spell_id = callback_data.spell_id

        spell_selection_message = query.message
        assert spell_selection_message is not None

        await bot.delete_message(chat_id=query.from_user.id, message_id=spell_selection_message.message_id)
        await contest_client.cast_spell(director_id=director_id, user_id=user_id, spell_id=spell_id)
