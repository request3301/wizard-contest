from __future__ import annotations

import asyncio
import logging

import httpx
from commonlib.models import LobbyStatus, Pair
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from .objects import Lobby, Player

CONTEST_URL = 'http://contest:8000'

router = APIRouter()


class Queue:
    def __init__(self) -> None:
        self.queue: dict[int, Player] = {}

    def _add_player(self, player: Player) -> None:
        self.queue[player.user_id] = player

    def _remove_player(self, user_id: int) -> None:
        player = self.queue[user_id]
        player.left_queue = True
        player.exit_queue_event.set()
        del self.queue[user_id]

    def extract_pair(self) -> Pair[Player] | None:
        if len(self.queue) < 2:
            return None
        it = iter(self.queue.values())
        first, second = next(it), next(it)
        del self.queue[first.user_id]
        del self.queue[second.user_id]
        return Pair(first, second)


class PlayerItem(BaseModel):
    user_id: int
    rating: int


queue = Queue()


@router.post('/add_user_to_queue', status_code=status.HTTP_201_CREATED)
async def add_user_to_queue(player_item: PlayerItem):
    player = Player(user_id=player_item.user_id,
                    rating=player_item.rating)
    queue._add_player(player)
    await player.exit_queue_event.wait()

    if player.left_queue:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.delete('/queue/leave/{user_id}', status_code=status.HTTP_200_OK)
async def delete_user_from_queue(user_id: int) -> None:
    queue._remove_player(user_id)


class LobbyManager:
    def __init__(self) -> None:
        self.lobbies: dict[int, Lobby] = {}

    def create_lobby(self, players: Pair[Player]) -> None:
        lobby = Lobby({player.user_id: player for player in players})
        for player in players:
            self.lobbies[player.user_id] = lobby
            player.exit_queue_event.set()

    async def process_lobbies(self) -> None:
        if not self.lobbies:
            return
        lobby = next(iter(self.lobbies.values()))
        if lobby.someone_left():
            await self._handle_abandoned_lobby(lobby)
        elif lobby.all_ready():
            await self._handle_ready_lobby(lobby)

    async def _handle_abandoned_lobby(self, lobby: Lobby) -> None:
        logging.log(logging.INFO, 'LobbyManager::_handle_abandoned_lobby')
        lobby.created = False
        for player in lobby.players.values():
            del self.lobbies[player.user_id]
            player.match_created_event.set()

    async def _handle_ready_lobby(self, lobby: Lobby) -> None:
        logging.log(logging.INFO, 'LobbyManager::_handle_ready_lobby')
        lobby.created = True
        lobby.director_id = await self._create_director()
        for player in lobby.players.values():
            player.match_created_event.set()
            del self.lobbies[player.user_id]

    @staticmethod
    async def _create_director() -> int:
        async with httpx.AsyncClient() as client:
            response = await client.post(CONTEST_URL + '/create_director')
            return int(response.text)


lobby_manager = LobbyManager()


@router.put('/lobby/accept/{user_id}', status_code=status.HTTP_200_OK)
async def user_ready_in_lobby(user_id: int) -> LobbyStatus:
    if not user_id in lobby_manager.lobbies:
        return LobbyStatus(created=False)
    lobby = lobby_manager.lobbies[user_id]
    player = lobby.players[user_id]
    player.ready = True

    await player.match_created_event.wait()

    return LobbyStatus(created=lobby.created, director_id=lobby.director_id)


@router.put('/lobby/reject/{user_id}', status_code=status.HTTP_200_OK)
async def user_abandon_lobby(user_id: int) -> None:
    if not user_id in lobby_manager.lobbies:
        return
    lobby = lobby_manager.lobbies[user_id]
    lobby.players[user_id].left_lobby = True


class Coordinator:
    """
    Responsible for the matchmaking queue.
    Queue is implemented using dict, so it's very simple now.
    It handles only one match creation per second.
    """

    def __init__(self) -> None:
        self.queue = queue
        self.lobby_manager = lobby_manager

    async def start_polling(self) -> None:
        while await asyncio.sleep(1) or True:
            if pair := self.queue.extract_pair():
                self.lobby_manager.create_lobby(pair)
            await self.lobby_manager.process_lobbies()
            logging.log(logging.INFO, 'Coordinator finished iteration')
