import pytest

from coordinator.objects import Lobby, Player


@pytest.fixture
def player():
    return Player(
        user_id=1,
        rating=1500,
    )


@pytest.fixture
def lobby():
    players = {1: Player(user_id=1, rating=1500), 2: Player(user_id=2, rating=1600)}
    return Lobby(players=players)


def test_player_creation(player):
    assert player.user_id == 1
    assert player.rating == 1500
    assert not player.left_queue
    assert not player.ready
    assert not player.left_lobby


def test_lobby_all_ready(lobby):
    assert not lobby.all_ready()

    for player in lobby.players.values():
        player.ready = True

    assert lobby.all_ready()


def test_lobby_someone_left(lobby):
    assert not lobby.someone_left()

    lobby.players[1].left_lobby = True

    assert lobby.someone_left()
