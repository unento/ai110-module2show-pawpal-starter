"""PawPal+ core classes: owners, pets, care tasks, and the daily scheduler."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields, replace
from datetime import date, timedelta
from typing import Optional
from uuid import uuid4

# Higher number = more important. Used for sorting instead of the raw strings,
# since "high" < "low" < "medium" alphabetically.
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}

CATEGORIES = {"walk", "feeding", "meds", "grooming", "enrichment"}

FREQUENCIES = {"once", "daily", "weekly"}

# How far ahead the next occurrence of a recurring task is due. "once" never recurs.
RECURRENCE_GAP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}

# Order of the day. Tasks with no preferred time go after all of these.
TIME_OF_DAY_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}

# Clock time (minutes after midnight) that each part of the day starts at.
TIME_OF_DAY_START = {"morning": 8 * 60, "afternoon": 13 * 60, "evening": 18 * 60}

# Midnight, in minutes after midnight. Flexible tasks must end by then.
END_OF_DAY = 24 * 60

CLOCK_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")  # zero-padded 24h "HH:MM"


def to_minutes(clock: str) -> int:
    """Convert an "HH:MM" string to minutes after midnight."""
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def to_clock(minutes: int) -> str:
    """Convert minutes after midnight to an "HH:MM" string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_of_day_for(clock: str) -> str:
    """Return the part of the day an "HH:MM" time falls in."""
    minutes = to_minutes(clock)
    if minutes < TIME_OF_DAY_START["afternoon"]:
        return "morning"
    if minutes < TIME_OF_DAY_START["evening"]:
        return "afternoon"
    return "evening"


def _overlaps(start_a: int, minutes_a: int, start_b: int, minutes_b: int) -> bool:
    """Return True if two blocks (start in minutes after midnight) overlap; touching end-to-start is fine."""
    return start_a < start_b + minutes_b and start_b < start_a + minutes_a


def _span(start: int, minutes: int) -> str:
    """Return a block as "HH:MM-HH:MM"."""
    return f"{to_clock(start)}-{to_clock(start + minutes)}"


def _overlap_warning(pet_a: Pet, task_a: Task, start_a: int, pet_b: Pet, task_b: Task, start_b: int) -> str:
    """Describe two overlapping tasks, noting whether they're for the same pet."""
    who = f"both for {pet_a.name}" if pet_a is pet_b else "different pets"
    return (
        f"{task_a.title} ({pet_a.name}, {_span(start_a, task_a.duration_minutes)}) overlaps "
        f"{task_b.title} ({pet_b.name}, {_span(start_b, task_b.duration_minutes)}); {who}"
    )


def _validate_task_field(name: str, value) -> None:
    """Raise ValueError if value is not allowed for the given Task field."""
    if name == "title" and (not isinstance(value, str) or not value.strip()):
        raise ValueError("title must be a non-empty string")
    if name == "duration_minutes" and (not isinstance(value, int) or value <= 0):
        raise ValueError("duration_minutes must be a positive integer")
    if name == "priority" and value not in PRIORITY_RANK:
        raise ValueError(f"priority must be one of {sorted(PRIORITY_RANK)}")
    if name == "category" and value not in CATEGORIES:
        raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
    if name == "preferred_time" and value is not None and value not in TIME_OF_DAY_ORDER:
        raise ValueError(f"preferred_time must be None or one of {list(TIME_OF_DAY_ORDER)}")
    if name == "frequency" and value not in FREQUENCIES:
        raise ValueError(f"frequency must be one of {sorted(FREQUENCIES)}")
    if name == "completed" and not isinstance(value, bool):
        raise ValueError("completed must be True or False")
    if name == "due_date" and not isinstance(value, date):
        raise ValueError("due_date must be a datetime.date")
    if name == "start_time" and value is not None and (not isinstance(value, str) or not CLOCK_PATTERN.match(value)):
        raise ValueError('start_time must be None or a 24-hour "HH:MM" string, e.g. "09:30"')


@dataclass
class Task:
    """One care activity, e.g. a morning walk or a dose of meds."""

    title: str
    duration_minutes: int
    priority: str  # "high", "medium", or "low"
    category: str  # walk, feeding, meds, grooming, enrichment
    preferred_time: Optional[str] = None  # "morning", "afternoon", "evening"
    frequency: str = "daily"  # "once", "daily", or "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    # Fixed clock time like "09:30" for appointments. None lets the scheduler pick a time.
    start_time: Optional[str] = None
    # Unique id so two otherwise identical tasks are never equal to each other.
    # A random uuid (not a counter) stays unique even if Streamlit reloads this module.
    id: str = field(default_factory=lambda: uuid4().hex, init=False)

    def __post_init__(self) -> None:
        """Validate every field as soon as the task is created."""
        for f in fields(self):
            _validate_task_field(f.name, getattr(self, f.name))

    def edit(self, **changes) -> None:
        """Update one or more fields on this task, rejecting unknown or invalid values."""
        editable = {f.name for f in fields(self)} - {"id"}
        unknown = set(changes) - editable
        if unknown:
            raise ValueError(f"cannot edit unknown field(s): {sorted(unknown)}")
        # Validate everything before changing anything, so a bad edit leaves the task untouched.
        for name, value in changes.items():
            _validate_task_field(name, value)
        for name, value in changes.items():
            setattr(self, name, value)

    def is_high_priority(self) -> bool:
        """Return True if this task is high priority."""
        return self.priority == "high"

    def mark_complete(self, completed_on: Optional[date] = None) -> Optional[Task]:
        """Mark this task as done and return its next occurrence, or None if it doesn't recur.

        A "daily" task comes back due one day after this one, a "weekly" task one
        week after. If it was done late (completed_on is after its due date), the
        gap is counted from completed_on instead, so the next occurrence is never
        already overdue. Completing an already-completed task returns None, so
        calling this twice can't create a duplicate next occurrence.
        """
        if self.completed:
            return None
        self.completed = True
        gap = RECURRENCE_GAP.get(self.frequency)
        if gap is None:
            return None
        base = max(self.due_date, completed_on) if completed_on else self.due_date
        # replace() builds a new Task, so it gets a fresh id and is validated again.
        return replace(self, completed=False, due_date=base + gap)


@dataclass
class Pet:
    """The animal being cared for."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet, ignoring it if it's already been added."""
        if any(t.id == task.id for t in self.tasks):
            return
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet, matching by task id."""
        remaining = [t for t in self.tasks if t.id != task.id]
        if len(remaining) == len(self.tasks):
            raise ValueError(f"{self.name} has no task '{task.title}' (id {task.id})")
        self.tasks = remaining

    def get_tasks(self) -> list[Task]:
        """Return all of this pet's tasks."""
        return list(self.tasks)


@dataclass
class Owner:
    """The person using the app."""

    name: str
    available_minutes: int
    # Maps a task category to a time of day, e.g. {"walk": "morning"}.
    preferences: dict[str, str] = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate available minutes and that preferences use known categories and times."""
        if not isinstance(self.available_minutes, int) or self.available_minutes < 0:
            raise ValueError("available_minutes must be a non-negative integer")
        for category, time in self.preferences.items():
            if category not in CATEGORIES:
                raise ValueError(f"unknown preference category: {category}")
            if time not in TIME_OF_DAY_ORDER:
                raise ValueError(f"unknown preference time for {category}: {time}")

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner, ignoring it if it's already been added."""
        if any(p is pet for p in self.pets):
            return
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all of this owner's pets."""
        return list(self.pets)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return every (pet, task) pair across all of this owner's pets."""
        return [(pet, task) for pet in self.get_pets() for task in pet.get_tasks()]


@dataclass
class PlanItem:
    """One task in a plan, with the pet it belongs to and why it was scheduled or skipped."""

    pet: Pet
    task: Task
    reason: str
    # Time of day the scheduler placed it in (task's own time or the owner's preference).
    time: Optional[str] = None
    # Start in minutes after midnight, set by the scheduler for scheduled items only.
    start_minute: Optional[int] = None

    @property
    def end_minute(self) -> Optional[int]:
        """End in minutes after midnight, derived from the start and the task's duration."""
        return None if self.start_minute is None else self.start_minute + self.task.duration_minutes

    @property
    def start(self) -> Optional[str]:
        """Start as "HH:MM", or None if no time has been assigned."""
        return None if self.start_minute is None else to_clock(self.start_minute)

    @property
    def end(self) -> Optional[str]:
        """End as "HH:MM", or None if no time has been assigned."""
        return None if self.start_minute is None else to_clock(self.end_minute)


@dataclass
class DailyPlan:
    """The schedule the user sees: what made it in, what didn't, and why."""

    available_minutes: int
    scheduled: list[PlanItem] = field(default_factory=list)  # in clock-time order
    skipped: list[PlanItem] = field(default_factory=list)
    # Warnings about scheduled tasks whose clock times overlap (see Scheduler.detect_conflicts).
    conflicts: list[str] = field(default_factory=list)

    def total_time(self) -> int:
        """Return the total minutes of all scheduled tasks."""
        return sum(item.task.duration_minutes for item in self.scheduled)

    def explain(self) -> str:
        """Return a readable explanation of how the plan was built, including minutes used vs. available."""
        lines = [f"Scheduled {self.total_time()} of {self.available_minutes} available minutes."]
        if self.scheduled:
            lines.append("Scheduled:")
            lines += [
                f"  - {item.start}-{item.end} {item.task.title} ({item.pet.name}): {item.reason}"
                for item in self.scheduled
            ]
        else:
            lines.append("Nothing could be scheduled.")
        if self.skipped:
            lines.append("Skipped:")
            lines += [f"  - {item.task.title} ({item.pet.name}): {item.reason}" for item in self.skipped]
        if self.conflicts:
            lines.append("Conflicts:")
            lines += [f"  - {warning}" for warning in self.conflicts]
        return "\n".join(lines)

    def to_table(self) -> list[dict]:
        """Return scheduled items as rows (pet, task, time, minutes, reason) for display in Streamlit."""
        return [
            {
                "Time": f"{item.start}-{item.end}" if item.start_minute is not None else "unassigned",
                "Part of day": item.time or "anytime",
                "Pet": item.pet.name,
                "Task": item.task.title,
                "Category": item.task.category,
                "Minutes": item.task.duration_minutes,
                "Priority": item.task.priority,
                "Reason": item.reason,
            }
            for item in self.scheduled
        ]


class Scheduler:
    """The brain that turns an owner's pets and tasks into a DailyPlan."""

    def __init__(self, owner: Owner, today: Optional[date] = None):
        """Create a scheduler that plans the given owner's day (today unless another date is given)."""
        self.owner = owner
        self.today = today or date.today()

    def collect_tasks(self) -> list[tuple[Pet, Task]]:
        """Gather every not-yet-completed (pet, task) pair that is due today or overdue."""
        return [
            (pet, task)
            for pet, task in self.owner.get_all_tasks()
            if not task.completed and task.due_date <= self.today
        ]

    def complete_task(self, pet: Pet, task: Task) -> Optional[Task]:
        """Mark the pet's task complete and add its next occurrence (if any) to the same pet.

        The task counts as completed on the scheduler's day, so an overdue task's
        next occurrence is due after today rather than still in the past.
        Returns the new task so callers can show it, or None for a "once" task.
        """
        next_task = task.mark_complete(completed_on=self.today)
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def filter_tasks(
        self, completed: Optional[bool] = None, pet_name: Optional[str] = None
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs matching every filter given; a filter left as None is ignored.

        pet_name is matched case-insensitively, so "rex" finds a pet named "Rex".
        """
        return [
            (pet, task)
            for pet, task in self.owner.get_all_tasks()
            if (completed is None or task.completed == completed)
            and (pet_name is None or pet.name.casefold() == pet_name.casefold())
        ]

    def preferred_time_for(self, task: Task) -> Optional[str]:
        """Return the part of the day for a task.

        A fixed start_time decides it; otherwise the task's own preferred_time,
        falling back to the owner's preference for its category.
        """
        if task.start_time:
            return time_of_day_for(task.start_time)
        return task.preferred_time or self.owner.preferences.get(task.category)

    def sort_by_priority(self, pairs: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return pairs ordered by PRIORITY_RANK (high first).

        Ties are broken by putting tasks that have a preferred time (from the task
        or the owner's preferences) ahead of tasks that don't.
        """
        return sorted(
            pairs,
            key=lambda pair: (
                -PRIORITY_RANK[pair[1].priority],
                self.preferred_time_for(pair[1]) is None,
            ),
        )

    def fits_in_time(self, task: Task, minutes_left: int) -> bool:
        """Return True if the task fits in the remaining minutes."""
        return task.duration_minutes <= minutes_left

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered morning -> afternoon -> evening, with no-preference tasks last.

        Uses preferred_time_for(), so a task with no preferred_time of its own is
        placed by the owner's preference for its category. The sort is stable, so
        tasks in the same time of day keep their original order.
        """
        no_preference = len(TIME_OF_DAY_ORDER)
        return sorted(
            tasks,
            key=lambda task: TIME_OF_DAY_ORDER.get(self.preferred_time_for(task), no_preference),
        )

    def order_by_time_of_day(self, items: list[PlanItem]) -> list[PlanItem]:
        """Return scheduled items ordered morning -> afternoon -> evening, with no-preference tasks last."""
        no_preference = len(TIME_OF_DAY_ORDER)
        return sorted(
            items,
            key=lambda item: TIME_OF_DAY_ORDER.get(item.time, no_preference),
        )

    def assign_clock_times(self, items: list[PlanItem]) -> list[PlanItem]:
        """Give every item a start/end clock time and return them in clock order.

        Tasks with a fixed start_time keep it. The rest are packed back to back,
        morning -> afternoon -> evening -> anytime, each starting no earlier than
        its part of the day (e.g. 13:00 for afternoon) and jumping past any fixed
        task it would overlap. So only two fixed tasks can ever overlap each other.

        A flexible task that would end after midnight is left with no start time
        and is not returned; the caller decides what to do with it.
        """
        fixed = [item for item in items if item.task.start_time]
        flexible = [item for item in items if not item.task.start_time]

        for item in fixed:
            item.start_minute = to_minutes(item.task.start_time)
        busy = sorted((item.start_minute, item.task.duration_minutes) for item in fixed)

        cursor = TIME_OF_DAY_START["morning"]
        for item in self.order_by_time_of_day(flexible):
            # No earlier than the cursor or the start of its part of the day ("anytime" has no limit).
            start = max(cursor, TIME_OF_DAY_START.get(item.time, 0))
            # busy is sorted by start, so one pass pushing forward is enough.
            for busy_start, busy_minutes in busy:
                if _overlaps(start, item.task.duration_minutes, busy_start, busy_minutes):
                    start = busy_start + busy_minutes  # move to just after the fixed task
            if start + item.task.duration_minutes > END_OF_DAY:
                continue  # leave the cursor alone so a shorter task after it may still fit
            item.start_minute = start
            cursor = item.end_minute

        timed = [item for item in items if item.start_minute is not None]
        return sorted(timed, key=lambda item: item.start_minute)

    def detect_conflicts(self, items: list[PlanItem]) -> list[str]:
        """Return one warning for each pair of items whose clock times overlap.

        Warnings say whether the two tasks are for the same pet or different pets.
        Items without a start time are ignored. Returns warnings instead of raising,
        so a plan with clashes is still shown to the owner.
        """
        timed = sorted(
            (item for item in items if item.start_minute is not None), key=lambda item: item.start_minute
        )
        warnings = []
        for i, a in enumerate(timed):
            for b in timed[i + 1:]:
                # Sorted by start: once b starts after a ends, no later item can overlap a.
                if b.start_minute >= a.end_minute:
                    break
                warnings.append(_overlap_warning(a.pet, a.task, a.start_minute, b.pet, b.task, b.start_minute))
        return warnings

    def add_task(self, pet: Pet, task: Task) -> list[str]:
        """Add a task to a pet and return warnings about it; never refuses the task.

        Warns if the task's fixed start_time overlaps another unfinished fixed-time
        task due the same day (for any pet), or if the tasks due that day now need
        more minutes than the owner has, so some will be skipped.
        """
        warnings = []
        if task.start_time:
            start = to_minutes(task.start_time)
            for other_pet, other in self.owner.get_all_tasks():
                if other.id == task.id or not other.start_time or other.completed or other.due_date != task.due_date:
                    continue
                other_start = to_minutes(other.start_time)
                if _overlaps(start, task.duration_minutes, other_start, other.duration_minutes):
                    warnings.append(_overlap_warning(pet, task, start, other_pet, other, other_start))

        pet.add_task(task)

        needed = sum(
            t.duration_minutes
            for _, t in self.owner.get_all_tasks()
            if not t.completed and t.due_date == task.due_date
        )
        if needed > self.owner.available_minutes:
            warnings.append(
                f"Tasks due {task.due_date} now need {needed} min but only "
                f"{self.owner.available_minutes} are available; lower-priority tasks will be skipped."
            )
        return warnings

    def generate_plan(self) -> DailyPlan:
        """Build and return a DailyPlan within the owner's available time.

        Walks the priority-sorted tasks once. A task that doesn't fit is added to
        `skipped` and the loop keeps going, so smaller tasks later in the list can
        still use the remaining time. Scheduled items are then given clock times
        and checked for overlaps.
        """
        plan = DailyPlan(available_minutes=self.owner.available_minutes)
        minutes_left = self.owner.available_minutes

        for pet, task in self.sort_by_priority(self.collect_tasks()):
            if self.fits_in_time(task, minutes_left):
                reason = (
                    f"{task.priority} priority; {task.duration_minutes} min fit in the "
                    f"{minutes_left} min remaining"
                )
                time = self.preferred_time_for(task)
                if task.start_time:
                    reason += f"; fixed at {task.start_time}"
                elif time:
                    reason += f"; placed in the {time}"
                plan.scheduled.append(PlanItem(pet, task, reason, time))
                minutes_left -= task.duration_minutes
            else:
                reason = (
                    f"{task.priority} priority, but needs {task.duration_minutes} min "
                    f"and only {minutes_left} min were left"
                )
                plan.skipped.append(PlanItem(pet, task, reason))

        timed = self.assign_clock_times(plan.scheduled)
        for item in plan.scheduled:
            if item.start_minute is None:
                item.reason = (
                    f"{item.task.priority} priority, but its {item.task.duration_minutes} min "
                    "would run past midnight"
                )
                plan.skipped.append(item)
        plan.scheduled = timed
        plan.conflicts = self.detect_conflicts(plan.scheduled)
        return plan
