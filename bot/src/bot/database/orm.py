from __future__ import annotations

import enum
from typing import Annotated

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

intpk = Annotated[int, mapped_column(primary_key=True)]


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    wizards: Mapped[list[Wizard]] = relationship(back_populates='user', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'User(id={self.id!r})'


class Wizard(Base):
    __tablename__ = 'wizard'

    id: Mapped[intpk]
    name: Mapped[str]
    speed: Mapped[int]
    power: Mapped[int]

    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    user: Mapped[User] = relationship(back_populates='wizards')

    spells: Mapped[list[Spell]] = relationship(back_populates='wizard', cascade='all, delete-orphan')

    @property
    def rank(self) -> int:
        return self._manapool * self.speed * self.power

    @property
    def _manapool(self) -> int:
        return sum(spell.manacost for spell in self.spells)


class SpellType(enum.StrEnum):
    ACTIVE = 'ACTIVE'
    PASSIVE = 'PASSIVE'


class Spell(Base):
    __tablename__ = 'spell'

    id: Mapped[intpk]
    type_: Mapped[SpellType]
    name: Mapped[str]
    description: Mapped[str]
    manacost: Mapped[int]

    wizard_id: Mapped[int] = mapped_column(ForeignKey('wizard.id'))
    wizard: Mapped[Wizard] = relationship(back_populates='spells')
