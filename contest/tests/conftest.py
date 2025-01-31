import pytest
from commonlib.models import Spell, SpellType, Wizard


@pytest.fixture
def test_wizard_1() -> Wizard:
    return Wizard(
        id=3,
        name="Merlin",
        speed=1,
        power=4,
        spells=[
            Spell(id=1, type_=SpellType.ACTIVE, name="Fireball", description="Launches a fireball", manacost=4),
            Spell(id=2, type_=SpellType.ACTIVE, name="Ice Bolt", description="Fires ice bolt", manacost=3),
        ]
    )


@pytest.fixture
def test_wizard_2() -> Wizard:
    return Wizard(
        id=4,
        speed=3,
        power=3,
        name="Gandalf",
        spells=[
            Spell(id=3, type_=SpellType.ACTIVE, name="Lightning", description="Summons lightning", manacost=5),
            Spell(id=4, type_=SpellType.ACTIVE, name="Shield", description="Creates shield", manacost=2),
        ]
    )
