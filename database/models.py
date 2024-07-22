from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Annotated
from pydantic import BaseModel


intpk = Annotated[int, mapped_column(primary_key=True)]


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'user'

    id: Mapped[intpk]

    wizards: Mapped[List["Wizard"]] = relationship(
        back_populates='user', cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r})"


class UserData(BaseModel):
    id: int


class Wizard(Base):
    __tablename__ = 'wizard'

    id: Mapped[intpk]
    name: Mapped[str] = mapped_column()
    speed: Mapped[int] = mapped_column()
    power: Mapped[int] = mapped_column()

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="wizards")

    skills: Mapped[List["Skill"]] = relationship(
        back_populates='wizard', cascade='all, delete-orphan'
    )


class WizardData(BaseModel):
    id: int
    name: str
    speed: int
    power: int


class Skill(Base):
    __tablename__ = 'skill'

    id: Mapped[intpk]
    name: Mapped[str]
    description: Mapped[str]
    manacost: Mapped[int]

    wizard_id: Mapped[int] = mapped_column(ForeignKey("wizard.id"))
    wizard: Mapped["Wizard"] = relationship(back_populates="skills")


class SkillData(BaseModel):
    id: int
    name: str
    description: str
    manacost: int


