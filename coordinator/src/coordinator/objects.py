import asyncio
from dataclasses import dataclass, field


@dataclass
class Player:
    user_id: int
    rating: int

    # used to respond to /queue/join API call
    exit_queue_event: asyncio.Event = field(default_factory=asyncio.Event)
    left_queue: bool = False

    # lobby only
    match_created_event: asyncio.Event = field(default_factory=asyncio.Event)
    ready: bool = False
    left_lobby: bool = False


@dataclass
class Lobby:
    players: dict[int, Player]

    created: bool | None = None
    director_id: int | None = None

    def all_ready(self) -> bool:
        return all(player.ready for player in self.players.values())

    def someone_left(self) -> bool:
        return any(player.left_lobby for player in self.players.values())
