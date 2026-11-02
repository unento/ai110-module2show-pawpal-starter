# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Output from running `python main.py` (an owner with 150 minutes, two pets, six flexible tasks, and three fixed-time appointments, two of which clash with the vet checkup):

```
Booking appointments:
  Vet checkup for Rex at 09:00: OK
  Nail trim for Luna at 09:30:
    WARNING: Nail trim (Luna, 09:30-09:50) overlaps Vet checkup (Rex, 09:00-09:45); different pets
    WARNING: Tasks due 2026-11-01 now need 170 min but only 150 are available; lower-priority tasks will be skipped.
  Ear drops for Luna at 09:00:
    WARNING: Ear drops (Luna, 09:00-09:05) overlaps Vet checkup (Rex, 09:00-09:45); different pets
    WARNING: Tasks due 2026-11-01 now need 175 min but only 150 are available; lower-priority tasks will be skipped.

==============================================================
Today's Schedule for Jordan
==============================================================
Time         Pet    Task                   Min  Priority
--------------------------------------------------------------
08:00-08:30  Rex    Morning walk            30  high
08:30-08:40  Rex    Breakfast               10  high
09:00-09:45  Rex    Vet checkup             45  high
09:00-09:05  Luna   Ear drops                5  high
09:30-09:50  Luna   Nail trim               20  medium
18:00-18:05  Luna   Thyroid meds             5  high
18:05-18:30  Rex    Evening walk            25  medium
--------------------------------------------------------------
Total: 140 of 150 minutes

Why this plan:
Scheduled 140 of 150 available minutes.
Scheduled:
  - 08:00-08:30 Morning walk (Rex): high priority; 30 min fit in the 150 min remaining; placed in the morning
  - 08:30-08:40 Breakfast (Rex): high priority; 10 min fit in the 120 min remaining; placed in the morning
  - 09:00-09:45 Vet checkup (Rex): high priority; 45 min fit in the 110 min remaining; fixed at 09:00
  - 09:00-09:05 Ear drops (Luna): high priority; 5 min fit in the 60 min remaining; fixed at 09:00
  - 09:30-09:50 Nail trim (Luna): medium priority; 20 min fit in the 30 min remaining; fixed at 09:30
  - 18:00-18:05 Thyroid meds (Luna): high priority; 5 min fit in the 65 min remaining; placed in the evening
  - 18:05-18:30 Evening walk (Rex): medium priority; 25 min fit in the 55 min remaining; placed in the evening
Skipped:
  - Laser pointer play (Luna): low priority, but needs 15 min and only 10 min were left
  - Brushing (Luna): low priority, but needs 20 min and only 10 min were left
Conflicts:
  - Vet checkup (Rex, 09:00-09:45) overlaps Ear drops (Luna, 09:00-09:05); different pets
  - Vet checkup (Rex, 09:00-09:45) overlaps Nail trim (Luna, 09:30-09:50); different pets
```

The full script also prints the tasks before and after `sort_by_time()`, then completes the morning tasks to show recurring tasks and filtering.

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

All scheduling logic lives in [`pawpal_system.py`](pawpal_system.py). `Scheduler.generate_plan()` ties it together: collect the tasks due today, sort by priority, keep each task that fits the time budget, give the kept tasks clock times, then check for overlaps.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_priority()`, `Scheduler.sort_by_time()`, `Scheduler.assign_clock_times()` | Priority decides what makes the plan; time of day and clock time decide the order |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.collect_tasks()`, `Scheduler.fits_in_time()` | By pet name and/or completion status; only tasks due today; skip tasks that don't fit |
| Conflict handling | `Scheduler.detect_conflicts()`, `Scheduler.add_task()` | Real clock-time overlaps, for the same pet or different pets; returns warnings, never crashes |
| Recurring tasks | `Task.mark_complete()`, `Scheduler.complete_task()` | Completing a daily or weekly task creates the next one, due 1 or 7 days later |

### Sorting

- **`Scheduler.sort_by_priority(pairs)`**: orders tasks high → medium → low. It uses a `PRIORITY_RANK` lookup because sorting the raw strings would put "low" above "medium" alphabetically. When two tasks have the same priority, the one with a preferred time comes first. This is the order the scheduler uses to decide which tasks make it into the plan.
- **`Scheduler.sort_by_time(tasks)`**: orders `Task` objects morning → afternoon → evening, with tasks that have no time last. Each task's part of the day comes from `Scheduler.preferred_time_for()`:
  1. a fixed `start_time`, if it has one
  2. otherwise its own `preferred_time`
  3. otherwise the owner's preference for its category, e.g. `{"walk": "morning"}`

  The sort is stable, so tasks in the same part of the day keep their original order.
- **`Scheduler.assign_clock_times(items)`**: puts the final plan in real clock order. Tasks with a fixed `start_time` keep it. Every other task is placed back to back, starting at 08:00 for morning, 13:00 for afternoon and 18:00 for evening. If one would run into a fixed appointment, it moves to just after it.

### Filtering

- **`Scheduler.filter_tasks(completed=None, pet_name=None)`**: returns `(pet, task)` pairs that match every filter you pass.
  - Leave a filter as `None` to ignore it.
  - Pet names ignore case, so `"rex"` finds "Rex".
  - A name that matches no pet returns an empty list.

  For example, `filter_tasks(completed=False, pet_name="Luna")` returns Luna's unfinished tasks.
- **`Scheduler.collect_tasks()`**: the scheduler's own filter. It keeps only unfinished tasks that are due on or before the scheduler's `today` date, so tomorrow's copy of a daily task doesn't show up in today's plan.
- **`Scheduler.fits_in_time()`** inside **`generate_plan()`**: if a task doesn't fit in the remaining minutes, it goes to `skipped` with a reason, and the scheduler keeps checking smaller tasks further down the list.

### Conflict detection

Tasks can have a fixed clock time through `Task.start_time` (e.g. `"09:30"`). The scheduler checks for clashes in two places, and in both it **returns warning messages instead of raising errors**, so the owner always gets a plan.

- **`Scheduler.detect_conflicts(items)`**: runs inside `generate_plan()` and stores its warnings in `DailyPlan.conflicts`. `explain()` prints them under "Conflicts:", and the Streamlit app shows each one as a warning box.
  - It sorts the tasks by start time and compares each task with the ones after it, stopping as soon as a later task starts after the current one ends.
  - Each pair of overlapping tasks gets a warning that says whether they're for the same pet or different pets.
  - Two tasks only clash if their times actually overlap. One ending at 09:45 and another starting at 09:45 is fine.
- **`Scheduler.add_task(pet, task)`**: checks as soon as a task is added, before any plan is generated. It always adds the task and returns a list of warnings about:
  - its fixed time overlapping another unfinished appointment due the same day, for any pet
  - the tasks due that day needing more minutes than the owner has

Because `assign_clock_times()` moves flexible tasks out of the way of fixed appointments, a conflict always means two fixed appointments overlap.

### Recurring tasks

Each task has a `frequency` (`"once"`, `"daily"` or `"weekly"`) and a `due_date`, which defaults to today.

- **`Task.mark_complete()`**: marks the task done and returns a new copy for the next occurrence, or `None` for a `"once"` task.
  - A daily task's copy is due 1 day after the original's due date, and a weekly task's 7 days after.
  - The copy keeps every other field but gets its own id, so it's a separate task.
  - Completing a task that's already done returns `None`, so it can't create a duplicate.
- **`Scheduler.complete_task(pet, task)`**: the method to call in practice. It runs `mark_complete()` and adds the new copy to the same pet, which `Task` can't do because it doesn't know which pet it belongs to.

`collect_tasks()` only includes tasks due today or earlier, so the next copy appears in the plan on the day it's due.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
