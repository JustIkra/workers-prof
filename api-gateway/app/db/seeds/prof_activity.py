"""
Seed data for professional activities.

Provides deterministic identifiers and metadata for the `prof_activity` table.
"""

from __future__ import annotations

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class ProfActivitySeed:
    """Seed payload for a single professional activity entry."""

    id: uuid.UUID
    code: str
    name: str
    description: str | None = None


PROF_ACTIVITY_SEED_DATA: tuple[ProfActivitySeed, ...] = (
    ProfActivitySeed(
        id=uuid.UUID("22fdacda-0f53-44d2-aba5-49f9239fd383"),
        code="meeting_facilitation",
        name="Организация и проведение совещаний",
        description=(
            "Трудовая функция по планированию, ведению и сопровождению рабочих совещаний. "
            "Рассчитывается на развитые коммуникативные, организационные и аналитические "
            "компетенции сотрудника."
        ),
    ),
)
