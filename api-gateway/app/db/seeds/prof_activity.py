"""Seed data for professional activities."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ProfActivitySeed:
    """Seed data structure for professional activity."""

    id: uuid.UUID
    code: str
    name: str
    description: str | None = None


# Default professional activities seed data
PROF_ACTIVITY_SEED_DATA: list[ProfActivitySeed] = [
    ProfActivitySeed(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        code="developer",
        name="Разработчик",
        description="Профессиональная деятельность в области разработки программного обеспечения",
    ),
    ProfActivitySeed(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        code="analyst",
        name="Аналитик",
        description="Профессиональная деятельность в области анализа и проектирования систем",
    ),
    ProfActivitySeed(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        code="manager",
        name="Менеджер",
        description="Профессиональная деятельность в области управления проектами и командами",
    ),
]

