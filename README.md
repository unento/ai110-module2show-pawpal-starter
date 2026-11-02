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

## ✨ Features

- **Priority-first selection**: tasks are ranked high → medium → low using a numeric rank (not alphabetical order), and the scheduler keeps each task that still fits in the owner's remaining minutes. A task that doesn't fit is skipped with a reason, and the scheduler keeps going, so a smaller, lower-priority task can still use the leftover time.
- **Priority tie-breaking**: among tasks with the same priority, ones with a preferred time of day are considered first; otherwise the original order is kept.
- **Sorting by time of day**: tasks are ordered morning → afternoon → evening, with "anytime" tasks last. A task's part of the day comes from its fixed start time, then its own preferred time, then the owner's preference for its category (e.g. walks in the morning).
- **Clock-time scheduling**: every scheduled task gets a real start and end time. Flexible tasks are packed back to back, starting no earlier than 08:00 (morning), 13:00 (afternoon) or 18:00 (evening).
- **Fixed-time appointments**: a task can have a set start time like `09:30`. It keeps that time, and flexible tasks jump past it instead of overlapping it.
- **Midnight cutoff**: a flexible task that would run past midnight is skipped with an explanation, and a shorter task after it can still take the slot.
- **Conflict warnings**: overlapping appointments are flagged both when a task is added and in the finished plan. Each warning names both tasks and their times and says whether they're for the same pet or different pets. Tasks that only touch (one ends at 09:30, the next starts at 09:30) are not conflicts. Warnings never block a task, so the owner always gets a plan.
- **Time budget warnings**: adding a task warns right away if the tasks due that day now need more minutes than the owner has.
- **Daily and weekly recurrence**: marking a recurring task done creates its next copy, due 1 or 7 days later. A task done late is counted from the day it was finished, so the next copy is never already overdue. One-time tasks don't come back, and completing a task twice can't create a duplicate.
- **Due-date filtering**: today's plan includes overdue and due-today tasks but not future ones, so tomorrow's copy of a daily walk doesn't appear today.
- **Filtering by pet and status**: list tasks for one pet (case-insensitive) and/or by done / to do.
- **Plan explanations**: every scheduled and skipped task comes with a reason, such as "high priority; 30 min fit in the 150 min remaining; placed in the morning".
- **Input validation**: invalid priorities, categories, durations, frequencies or start times (e.g. `25:00`) are rejected with a clear message.

## 🧪 Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
```

The tests live in [`test/test_pawpal.py`](test/test_pawpal.py) (28 tests). They cover:

- **Sorting correctness**: the final plan comes out in clock order even when priority says otherwise; priority sorts high → medium → low (not alphabetically); ties put tasks with a preferred time first and otherwise keep their original order; `sort_by_time()` puts tasks with no time last.
- **Recurrence logic**: completing a daily task creates a new one due the next day that appears in tomorrow's plan (and not today's); weekly tasks come back 7 days later; `"once"` tasks and repeat completions create nothing; the new copy keeps the task's settings; an overdue task completed late is next due after today, not still in the past.
- **Conflict detection**: two tasks at the exact same time are flagged, for the same pet or for different pets, both when added and in the plan; partial overlaps are flagged; tasks that touch end-to-start (09:00–09:30, then 09:30) and completed tasks are not.
- **Scheduling around fixed times**: flexible tasks are placed back to back and jump past fixed appointments; no flexible task runs past midnight (it is skipped instead, and a shorter task can still use the slot).
- **Edge cases**: an owner with no pets, a pet with no tasks, a budget of 0 minutes, a task that exactly fills the remaining time, a small task fitting after a big one is skipped, overdue vs. future tasks, invalid `start_time` values, and filtering by pet name and completion.

Output of a successful run:

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\unent\Documents\codepath\ai110-module2show-pawpal-starter
plugins: anyio-4.15.1
collected 28 items

test\test_pawpal.py ............................                         [100%]

============================= 28 passed in 0.14s ==============================
```

### Confidence Level: ★★★★☆ (4/5)

All 28 tests pass, and they cover the main scheduling behaviors plus the edge cases most likely to break: empty inputs, exact time-budget boundaries, same-time conflicts, and recurring tasks. Writing these tests found two real bugs (overdue tasks coming back the same day, and times past midnight like `25:00`), and both are now fixed and tested. It isn't 5 stars because:

- the Streamlit UI in `app.py` has no automated tests;
- a fixed appointment that crosses midnight (e.g. 23:50 for 30 min) is still scheduled as-is;
- the scheduler plans one day at a time with a simple greedy pass, so it won't always find the best possible fit for the time available.

## 📐 Smarter Scheduling

All scheduling logic lives in [`pawpal_system.py`](pawpal_system.py). `Scheduler.generate_plan()` ties it together: collect the tasks due today, sort by priority, keep each task that fits the time budget, give the kept tasks clock times, then check for overlaps.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_priority()`, `Scheduler.sort_by_time()`, `Scheduler.assign_clock_times()` | Priority decides what makes the plan; time of day and clock time decide the order |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.collect_tasks()`, `Scheduler.fits_in_time()` | By pet name and/or completion status; only tasks due today; skip tasks that don't fit |
| Conflict handling | `Scheduler.detect_conflicts()`, `Scheduler.add_task()` | Real clock-time overlaps, for the same pet or different pets; returns warnings, never crashes |
| Recurring tasks | `Task.mark_complete()`, `Scheduler.complete_task()` | Completing a daily or weekly task creates the next one, due 1 or 7 days later (counted from today if it was done late) |

### Sorting

- **`Scheduler.sort_by_priority(pairs)`**: orders tasks high → medium → low. It uses a `PRIORITY_RANK` lookup because sorting the raw strings would put "low" above "medium" alphabetically. When two tasks have the same priority, the one with a preferred time comes first. This is the order the scheduler uses to decide which tasks make it into the plan.
- **`Scheduler.sort_by_time(tasks)`**: orders `Task` objects morning → afternoon → evening, with tasks that have no time last. Each task's part of the day comes from `Scheduler.preferred_time_for()`:
  1. a fixed `start_time`, if it has one
  2. otherwise its own `preferred_time`
  3. otherwise the owner's preference for its category, e.g. `{"walk": "morning"}`

  The sort is stable, so tasks in the same part of the day keep their original order.
- **`Scheduler.assign_clock_times(items)`**: puts the final plan in real clock order. Tasks with a fixed `start_time` keep it. Every other task is placed back to back, starting at 08:00 for morning, 13:00 for afternoon and 18:00 for evening. If one would run into a fixed appointment, it moves to just after it. A flexible task that would run past midnight is skipped instead, with the reason shown in the plan.

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
  - If you pass `completed_on` and it's later than the due date (the task was done late), the gap is counted from `completed_on` instead, so the copy is never already overdue.
  - The copy keeps every other field but gets its own id, so it's a separate task.
  - Completing a task that's already done returns `None`, so it can't create a duplicate.
- **`Scheduler.complete_task(pet, task)`**: the method to call in practice. It runs `mark_complete(completed_on=today)` and adds the new copy to the same pet, which `Task` can't do because it doesn't know which pet it belongs to.

`collect_tasks()` only includes tasks due today or earlier, so the next copy appears in the plan on the day it's due.

## 📸 Demo Walkthrough

### Running the app

```bash
streamlit run app.py
```

### Main UI features

The app is a single page, read top to bottom:

| Section | What you can do |
|---------|-----------------|
| **Owner** | Set the owner's name and how many minutes they have for pet care today (0–1440). |
| **Add a Pet** | Enter a name, species (dog, cat, other) and age, then click **Add pet**. Blank and duplicate names are rejected. Your pets are listed in a table with how many tasks each has. |
| **Schedule a Task** | Pick a pet and fill in the task: title, duration, priority, category, preferred time (any / morning / afternoon / evening), frequency (daily / weekly / once) and an optional fixed start time (`HH:MM`). Click **Add task**. Invalid input shows an error; clashes or going over your time budget show yellow warnings, but the task is still added. |
| **Current Tasks** | Shows counts for tasks due today and tasks done, plus minutes needed vs. available, and a warning if today's tasks won't all fit. Filter the task table by pet and status (To do / Done / All), sort by time of day or priority, and use **Mark done** to complete a task. A recurring task's next copy appears automatically, with a message saying when it's due. |
| **Build Schedule** | Click **Generate schedule** to see counts of scheduled, skipped and conflicting tasks, a bar showing minutes used, any conflict warnings (shown first), the day's plan in clock order, a "Why each task was chosen" section, a table of skipped tasks with reasons, and the full plain-text explanation. |

### Example workflow

1. **Set up the owner.** Enter "Jordan" and set **Minutes available today** to 60.
2. **Add a pet.** Add "Mochi", a 3-year-old dog. Mochi appears in the pets table with 0 tasks.
3. **Schedule tasks.**
   - "Morning walk", 30 min, high, walk, morning, daily → added with no warnings.
   - "Vet visit", 45 min, high, meds, once, fixed start `09:00` → added, with a warning that today's tasks now need 75 min but only 60 are available.
   - "Brushing", 15 min, low, grooming, fixed start `09:30` → added, with two warnings: it overlaps the vet visit (both for Mochi), and today's tasks now need 90 min.
4. **Check current tasks.** The metrics show 3 due today and 90 / 60 minutes needed, with a warning that lower-priority tasks will be skipped. Switch **Sort by** to Priority to see the two high-priority tasks above brushing.
5. **Generate the schedule.** The walk and the vet visit are both high priority, so they keep the order they were added: the walk (30 min) is kept first, leaving 30 min. The vet visit needs 45, so it's skipped. Brushing (low, 15 min) still fits in what's left. The plan shows the walk at 08:00–08:30 and brushing at 09:30–09:45, and the skipped table explains that the vet visit needed 45 min but only 30 were left.
6. **Fix it and re-plan.** Raise the available minutes to 90 and generate again. All three tasks fit (90 of 90 minutes): the walk at 08:00–08:30, the vet visit at 09:00–09:45 and brushing at 09:30–09:45. Now that both appointments are in the plan, a conflict warning appears above the schedule. Since both have fixed times, it stays until you change one of them.
7. **Mark a task done.** Choose "Morning walk (Mochi, …)" in **Mark a task done** and click **Mark done**. The message says the next walk is due tomorrow, and the table now shows the finished walk as ✅ Done and a new ⏳ To do walk due tomorrow. Tomorrow's walk won't appear in today's schedule.

### Key scheduler behaviors shown

- **Priority decides what fits**: high-priority tasks claim the time budget first; tasks with the same priority keep the order they were added (step 5).
- **Skip and continue**: a task that doesn't fit doesn't stop the scheduler, so a smaller, lower-priority task further down the list can still use the time that's left (brushing in step 5).
- **Sorting**: the finished plan is always in clock order, while the task table can be sorted by time of day or by priority (step 4).
- **Working around fixed appointments**: flexible tasks are placed around fixed ones, so the walk lands at 08:00, before the 09:00 appointment (step 6).
- **Time budget and conflict warnings**: going over the budget or overlapping another appointment is flagged as soon as a task is added (step 3), and overlaps are flagged again in any plan that contains both tasks (step 6). Warnings never block a task.
- **Recurrence**: completing a daily task creates tomorrow's copy, which stays out of today's plan (step 7).

### Sample CLI output

[`main.py`](main.py) runs the same logic without the UI: an owner with 150 minutes, two pets (Rex the dog and Luna the cat), six flexible tasks, and three fixed-time appointments, two of which clash with Rex's vet checkup. It then marks the morning tasks done to show recurrence and filtering. Output of `python main.py` (dates depend on the day you run it):

```
Booking appointments:
  Vet checkup for Rex at 09:00: OK
  Nail trim for Luna at 09:30:
    WARNING: Nail trim (Luna, 09:30-09:50) overlaps Vet checkup (Rex, 09:00-09:45); different pets
    WARNING: Tasks due 2026-11-01 now need 170 min but only 150 are available; lower-priority tasks will be skipped.
  Ear drops for Luna at 09:00:
    WARNING: Ear drops (Luna, 09:00-09:05) overlaps Vet checkup (Rex, 09:00-09:45); different pets
    WARNING: Tasks due 2026-11-01 now need 175 min but only 150 are available; lower-priority tasks will be skipped.

Tasks in the order they were added:
  evening    Rex   Evening walk
  morning    Rex   Morning walk
  morning    Rex   Breakfast
  morning    Rex   Vet checkup
  anytime    Luna  Brushing
  afternoon  Luna  Laser pointer play
  evening    Luna  Thyroid meds
  morning    Luna  Nail trim
  morning    Luna  Ear drops

Tasks after sort_by_time():
  morning    Rex   Morning walk
  morning    Rex   Breakfast
  morning    Rex   Vet checkup
  morning    Luna  Nail trim
  morning    Luna  Ear drops
  afternoon  Luna  Laser pointer play
  evening    Rex   Evening walk
  evening    Luna  Thyroid meds
  anytime    Luna  Brushing

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

Finishing the morning:
  Morning walk done -> next one due 2026-11-02
  Breakfast done -> next one due 2026-11-02

Completed so far:
  Rex: Morning walk
  Rex: Breakfast
  Rex: Vet checkup
  Luna: Nail trim
  Luna: Ear drops

Still to do for Luna:
  Luna: Brushing
  Luna: Laser pointer play
  Luna: Thyroid meds

Rex's tasks still to do today (tomorrow's copies are not included):
  Evening walk (due 2026-11-01)
```
