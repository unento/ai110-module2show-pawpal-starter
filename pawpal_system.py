"""PawPal+ core classes: owners, pets, care tasks, and the daily scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """One care activity, e.g. a morning walk or a dose of meds."""

    title: str
    duration_minutes: int
    priority: str  # "high", "medium", or "low"
    category: str  # walk, feeding, meds, grooming, enrichment
    preferred_time: Optional[str] = None  # e.g. "morning"

    def edit(self, **fields) -> None:
        """Update one or more fields on this task."""
        pass

    def is_high_priority(self) -> bool:
        """Return True if this task is high priority."""
        pass


@dataclass
class Pet:
    """The animal being cared for."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        pass

    def get_tasks(self) -> list[Task]:
        """Return all of this pet's tasks."""
        pass


@dataclass
class Owner:
    """The person using the app."""

    name: str
    available_minutes: int
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def get_pets(self) -> list[Pet]:
        """Return all of this owner's pets."""
        pass


@dataclass
class DailyPlan:
    """The schedule the user sees: what made it in, what didn't, and why."""

    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def total_time(self) -> int:
        """Return the total minutes of all scheduled tasks."""
        pass

    def explain(self) -> str:
        """Return a readable explanation of how the plan was built."""
        pass

    def to_table(self) -> list[dict]:
        """Return scheduled tasks as rows for display in Streamlit."""
        pass


class Scheduler:
    """The brain that turns an owner's pets and tasks into a DailyPlan."""

    def __init__(self, owner: Owner, tasks: Optional[list[Task]] = None):
        self.owner = owner
        self.tasks = tasks if tasks is not None else []

    def sort_by_priority(self) -> list[Task]:
        """Return tasks ordered from highest to lowest priority."""
        pass

    def fits_in_time(self, task: Task, minutes_left: int) -> bool:
        """Return True if the task fits in the remaining minutes."""
        pass

    def generate_plan(self) -> DailyPlan:
        """Build and return a DailyPlan within the owner's available time."""
        pass
