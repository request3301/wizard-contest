import uuid

from commonlib.models import ContestAction, Wizard
from fastapi import APIRouter, status

from .director import Director

router = APIRouter()

directors: dict[int, Director] = {}


@router.post('/director/create', status_code=status.HTTP_201_CREATED)
async def create_director() -> int:
    director_id = uuid.uuid4().int
    directors[director_id] = Director()
    return director_id


@router.post('/director/{director_id}/user/{user_id}/wizard/set', status_code=status.HTTP_201_CREATED)
async def set_wizard_for_player(director_id: int, user_id: int, wizard: Wizard) -> None:
    await directors[director_id].set_wizard(user_id, wizard)


@router.get('/director/{director_id}/get_turn', status_code=status.HTTP_200_OK)
async def get_user_to_make_turn(director_id: int) -> int:
    return await directors[director_id].get_user_to_make_turn()


@router.get('/director/{director_id}/get_available_spells/{user_id}', status_code=status.HTTP_200_OK)
async def get_available_spells(director_id: int, user_id: int) -> list[int]:
    return await directors[director_id].get_available_spells(user_id)


@router.post('/director/{director_id}/user/{user_id}/cast/{spell_id}', status_code=status.HTTP_200_OK)
async def cast_spell(director_id: int, user_id: int, spell_id: int) -> None:
    await directors[director_id].make_turn(user_id, spell_id)


@router.get('/director/{director_id}/action', status_code=status.HTTP_200_OK)
async def get_action(director_id: int) -> ContestAction:
    director = directors[director_id]
    return ContestAction(
        action=director.action,
        metadata=director.action_metadata,
        result=director.result,
    )
