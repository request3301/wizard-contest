import asyncio
import uuid

from commonlib.models import ContestAction, Wizard
from fastapi import APIRouter

from .director import Director

router = APIRouter()

directors: dict[int, Director] = {}


@router.post('/create_director')
async def create_director() -> int:
    director_id = uuid.uuid4().int
    directors[director_id] = Director()
    return director_id


@router.post('/set_wizard')
async def set_wizard(director_id: int, user_id: int, wizard: Wizard) -> None:
    director = directors[director_id]
    await director.set_wizard(user_id, wizard)
    # here response is returned only when everyone have set their wizard


@router.post('/get_user_to_make_turn')
async def get_user_to_make_turn(director_id: int) -> int:
    return await directors[director_id].get_user_to_make_turn()


@router.post('/get_available_spells')
async def get_available_spells(director_id: int, user_id: int) -> list[int]:
    return await directors[director_id].get_available_spells(user_id)


@router.post('/cast_spell')
async def cast_spell(director_id: int, user_id: int, spell_id: int) -> None:
    asyncio.create_task(directors[director_id].cast_spell(user_id, spell_id))


@router.post('/get_action')
async def get_action(director_id: int) -> ContestAction:
    return await directors[director_id].get_contest_action()
