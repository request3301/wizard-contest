from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import Settings
from database.models import *

DATABASE_URL = Settings().DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)

session_factory = async_sessionmaker(engine)

type_to_class = {
    "wizard": Wizard,
    "skill": Skill
}

type_to_data = {
    "wizard": WizardData,
    "skill": SkillData
}


async def obj_info(obj_id: int, obj_type: str):
    async with session_factory() as session:
        obj_class = type_to_class[obj_type]
        obj_data = type_to_data[obj_type]

        query = select(obj_class).filter_by(id=obj_id)
        res = await session.execute(query)
        result_orm = res.scalars().all()
        result_data = [obj_data.model_validate(row, from_attributes=True) for row in result_orm]
        return result_data[0]


async def delete_obj(obj_type: str, obj_id: int):
    async with session_factory() as session:
        obj_class = type_to_class[obj_type]
        obj = await session.get(obj_class, obj_id)
        await session.delete(obj)
        await session.commit()


async def get_wizards(user_id: int) -> list[WizardData]:
    async with session_factory() as session:
        query = (select(Wizard).filter_by(user_id=user_id))
        res = await session.execute(query)
        result_orm = res.scalars().all()
        result_data = [WizardData.model_validate(row, from_attributes=True) for row in result_orm]
        return result_data


async def add_wizard(user_id: int, name: str) -> int:
    # returns wizard id
    async with session_factory() as session:
        wizard = Wizard(name=name, user_id=user_id, speed=1, power=1)
        session.add(wizard)
        await session.flush()
        wizard_id = wizard.id
        await session.commit()
        return wizard_id


async def get_skills(wizard_id: int) -> list[SkillData]:
    async with session_factory() as session:
        query = select(Skill).filter_by(wizard_id=wizard_id)
        res = await session.execute(query)
        result_orm = res.scalars().all()
        result_data = [SkillData.model_validate(row, from_attributes=True) for row in result_orm]
        return result_data


async def add_skill(wizard_id: int, name: str, description: str, manacost: int) -> None:
    async with session_factory() as session:
        skill = Skill(name=name, description=description, manacost=manacost, wizard_id=wizard_id)
        session.add(skill)
        await session.commit()


async def set_wizard_param(wizard_id: int, param: str, value: int) -> None:
    async with session_factory() as session:
        stmt = update(Wizard).filter_by(id=wizard_id).values({param: value})
        await session.execute(stmt)
        await session.commit()


# todo can be done better
async def checkin_user(user_id: int) -> None:
    async with session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            new_user = User(id=user_id)
            session.add(new_user)
            await session.commit()


def calc_manapool(skills: list[SkillData]) -> int:
    manapool = 0
    for skill in skills:
        manapool += skill.manacost
    return manapool


async def get_manapool(wizard_id: int) -> int:
    skills = await get_skills(wizard_id)
    return calc_manapool(skills)


def calc_rating(wizard: WizardData, skills: list[SkillData]) -> int:
    manapool = calc_manapool(skills)
    return manapool * wizard.speed * wizard.power


async def get_rating(wizard_id: int) -> int:
    wizard = await obj_info(obj_type='wizard', obj_id=wizard_id)
    skills = await get_skills(wizard_id)
    return calc_rating(wizard, skills)
