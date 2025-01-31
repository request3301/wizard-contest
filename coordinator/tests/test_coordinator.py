import asyncio

import pytest
from commonlib.models import LobbyStatus, Pair

from coordinator.coordinator import CONTEST_URL, Coordinator, LobbyManager, Queue
from coordinator.objects import Lobby, Player


@pytest.fixture
def player():
    return Player(user_id=1, rating=1500)


class TestQueue:
    @pytest.fixture
    def queue(self) -> Queue:
        return Queue()

    def test_add_player(self, queue, player):
        queue._add_player(player)
        assert queue.queue[player.user_id] == player

    def test_remove_user(self, queue, player):
        queue._add_player(player)
        queue._remove_player(player.user_id)
        assert player.user_id not in queue.queue
        assert player.left_queue
        assert player.exit_queue_event.is_set()

    def test_extract_pair(self, queue):
        p1 = Player(user_id=1, rating=1500)
        p2 = Player(user_id=2, rating=1600)

        queue._add_player(p1)
        assert queue.extract_pair() is None

        queue._add_player(p2)
        pair = queue.extract_pair()

        assert isinstance(pair, Pair)
        assert len(queue.queue) == 0
        assert p1 in pair
        assert p2 in pair


class TestLobbyManager:
    @pytest.fixture
    def lobby_manager(self):
        return LobbyManager()

    @pytest.fixture
    def player_pair(self):
        p1 = Player(user_id=1, rating=1500)
        p2 = Player(user_id=2, rating=1600)
        return Pair([p1, p2])

    @staticmethod
    def get_any_lobby(lobby_manager: LobbyManager) -> Lobby:
        return next(iter(lobby_manager.lobbies.values()))

    async def test_create_lobby(self, lobby_manager, player_pair):
        lobby_manager.create_lobby(player_pair)

        assert len(lobby_manager.lobbies) == 2
        lobby = self.get_any_lobby(lobby_manager)

        assert len(lobby.players) == 2
        assert all(p.exit_queue_event.is_set() for p in player_pair)
        assert all(p.user_id in lobby_manager.lobbies for p in player_pair)

    async def test_handle_abandoned_lobby(self, lobby_manager, player_pair):
        lobby_manager.create_lobby(player_pair)
        lobby = self.get_any_lobby(lobby_manager)

        await lobby_manager.user_abandon_lobby(player_pair[0].user_id)
        ready_request = asyncio.create_task(lobby_manager.user_ready_in_lobby(player_pair[1].user_id))
        await asyncio.sleep(0)

        await lobby_manager.process_lobbies()

        assert len(lobby_manager.lobbies) == 0
        assert lobby.created is False

        response = await ready_request
        lobby_status = LobbyStatus.model_validate_json(response.json())
        assert not lobby_status.created
        assert lobby_status.director_id is None

    async def test_handle_ready_lobby(self, lobby_manager, player_pair, httpx_mock):
        lobby_manager.create_lobby(player_pair)
        lobby = self.get_any_lobby(lobby_manager)

        expected_director_id = 42

        requests = [asyncio.create_task(lobby_manager.user_ready_in_lobby(user_id)) for user_id in player_pair.user_id]
        await asyncio.sleep(0)

        httpx_mock.add_response(url=CONTEST_URL + '/contest/create_director', text=f'{expected_director_id}')
        await lobby_manager.process_lobbies()

        assert len(lobby_manager.lobbies) == 0
        assert lobby.created
        assert lobby.director_id == expected_director_id
        responses = await asyncio.gather(*requests)
        for response in responses:
            lobby_status = LobbyStatus.model_validate_json(response.json())
            assert lobby_status.created
            assert lobby_status.director_id == expected_director_id


class TestCoordinator:
    @pytest.fixture
    def coordinator(self) -> Coordinator:
        return Coordinator()

    async def test_no_immediate_response(self, coordinator: Coordinator):
        join_task = asyncio.create_task(coordinator.queue.add_user_to_queue(
            user_id=1,
            rating=1000,
        ))

        asyncio.create_task(coordinator.start_polling())
        await asyncio.sleep(0)

        assert not join_task.done()

    async def test_both_accept(self, httpx_mock, coordinator: Coordinator):
        asyncio.create_task(coordinator.start_polling())

        join_task_1 = asyncio.create_task(coordinator.queue.add_user_to_queue(
            user_id=1,
            rating=1000,
        ))
        join_task_2 = asyncio.create_task(coordinator.queue.add_user_to_queue(
            user_id=2,
            rating=1000,
        ))

        await join_task_1
        await join_task_2

        expected_director_id = 42
        httpx_mock.add_response(url=CONTEST_URL + '/contest/create_director', text=f'{expected_director_id}')

        ready_task_1 = asyncio.create_task(coordinator.lobby_manager.user_ready_in_lobby(user_id=1))
        ready_task_2 = asyncio.create_task(coordinator.lobby_manager.user_ready_in_lobby(user_id=2))

        lobby_status: LobbyStatus = await ready_task_1
        assert lobby_status == await ready_task_2
        assert lobby_status.director_id == expected_director_id
        assert lobby_status.created
