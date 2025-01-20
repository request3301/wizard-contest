from commonlib.models import SpellCreate, Wizard, WizardCreate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from . import orm
from ..config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)

session_factory = async_sessionmaker(engine)

type_to_class = {'wizard': orm.Wizard, 'spell': orm.Spell}


async def obj_info(obj_id: int, obj_type: str):
    async with session_factory() as session:
        obj_class = type_to_class[obj_type]

        obj = await session.get(obj_class, obj_id)
        return obj


async def delete_obj(obj_type: str, obj_id: int):
    async with session_factory() as session:
        obj_class = type_to_class[obj_type]
        obj = await session.get(obj_class, obj_id)
        await session.delete(obj)
        await session.commit()


async def get_wizards(user_id: int) -> list[orm.Wizard]:
    async with session_factory() as session:
        query = select(orm.Wizard).filter_by(user_id=user_id)
        res = await session.execute(query)
        result = res.scalars().all()
        return list(result)


async def add_wizard(wizard_create: WizardCreate) -> int:
    """
    :return: id of created wizard
    """
    async with session_factory() as session:
        orm_wizard = orm.Wizard(**wizard_create.model_dump())
        session.add(orm_wizard)
        await session.flush()
        wizard_id = orm_wizard.id
        await session.commit()
        return wizard_id


async def add_spell(spell_create: SpellCreate) -> None:
    async with session_factory() as session:
        spell = orm.Spell(**spell_create.model_dump())
        session.add(spell)
        await session.commit()


async def set_wizard_param(wizard_id: int, param: str, value: int) -> None:
    async with session_factory() as session:
        stmt = update(orm.Wizard).filter_by(id=wizard_id).values({param: value})
        await session.execute(stmt)
        await session.commit()


# TODO can be done better
async def checkin_user(user_id: int):
    async with session_factory() as session:
        user = await session.get(orm.User, user_id)
        if user is None:
            new_user = orm.User(id=user_id)
            session.add(new_user)
            await session.commit()


async def get_wizard_with_spells(wizard_id: int) -> Wizard:
    async with session_factory() as session:
        query = select(orm.Wizard).options(selectinload(orm.Wizard.spells)).filter_by(id=wizard_id)
        result = await session.execute(query)
        wizard = result.scalar_one_or_none()
        assert wizard is not None
        return Wizard.model_validate(wizard)
