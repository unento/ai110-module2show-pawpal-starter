from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def test_mark_complete_changes_status():
    task = Task("Morning walk", 30, "high", "walk")
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet("Rex", "dog", 4)
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task("Breakfast", 10, "high", "feeding"))

    assert len(pet.get_tasks()) == 1


def test_sort_by_time_orders_by_time_of_day_with_unset_last():
    owner = Owner("Sam", 120, preferences={"feeding": "morning"})
    scheduler = Scheduler(owner)
    evening = Task("Evening walk", 30, "high", "walk", preferred_time="evening")
    anytime = Task("Brush coat", 15, "low", "grooming")
    afternoon = Task("Puzzle toy", 20, "medium", "enrichment", preferred_time="afternoon")
    breakfast = Task("Breakfast", 10, "high", "feeding")  # morning via owner preference

    result = scheduler.sort_by_time([evening, anytime, afternoon, breakfast])

    assert result == [breakfast, afternoon, evening, anytime]


def test_filter_tasks_by_completion_and_pet_name():
    owner = Owner("Sam", 120)
    rex, milo = Pet("Rex", "dog", 4), Pet("Milo", "cat", 2)
    owner.add_pet(rex)
    owner.add_pet(milo)
    walk = Task("Walk", 30, "high", "walk")
    meds = Task("Meds", 5, "high", "meds")
    feed = Task("Feed", 10, "medium", "feeding")
    rex.add_task(walk)
    rex.add_task(meds)
    milo.add_task(feed)
    walk.mark_complete()
    scheduler = Scheduler(owner)

    assert scheduler.filter_tasks(completed=True) == [(rex, walk)]
    assert scheduler.filter_tasks(completed=False) == [(rex, meds), (milo, feed)]
    assert scheduler.filter_tasks(pet_name="rex") == [(rex, walk), (rex, meds)]
    assert scheduler.filter_tasks(completed=False, pet_name="Rex") == [(rex, meds)]
    assert scheduler.filter_tasks(pet_name="Nobody") == []
    assert len(scheduler.filter_tasks()) == 3


def test_completing_daily_task_creates_next_day_occurrence():
    pet = Pet("Rex", "dog", 4)
    walk = Task("Walk", 30, "high", "walk", frequency="daily", due_date=date(2026, 11, 1))
    pet.add_task(walk)
    scheduler = Scheduler(Owner("Sam", 60, pets=[pet]), today=date(2026, 11, 1))

    next_walk = scheduler.complete_task(pet, walk)

    assert walk.completed is True
    assert next_walk is not None and next_walk.completed is False
    assert next_walk.due_date == date(2026, 11, 2)
    assert next_walk.id != walk.id
    assert (next_walk.title, next_walk.duration_minutes) == ("Walk", 30)
    assert pet.get_tasks() == [walk, next_walk]
    # Tomorrow's walk is not part of today's plan, but is part of tomorrow's.
    assert scheduler.collect_tasks() == []
    assert Scheduler(scheduler.owner, today=date(2026, 11, 2)).collect_tasks() == [(pet, next_walk)]


def test_completing_weekly_task_creates_occurrence_one_week_later():
    task = Task("Bath", 20, "low", "grooming", frequency="weekly", due_date=date(2026, 11, 1))
    assert task.mark_complete().due_date == date(2026, 11, 8)


def test_once_task_and_repeat_completion_do_not_recur():
    pet = Pet("Rex", "dog", 4)
    vet = Task("Vet visit", 60, "high", "meds", frequency="once")
    walk = Task("Walk", 30, "high", "walk")
    pet.add_task(vet)
    pet.add_task(walk)
    scheduler = Scheduler(Owner("Sam", 60, pets=[pet]))

    assert scheduler.complete_task(pet, vet) is None
    scheduler.complete_task(pet, walk)
    assert scheduler.complete_task(pet, walk) is None  # already done: no duplicate
    assert len(pet.get_tasks()) == 3


def test_flexible_tasks_get_back_to_back_times_around_fixed_ones():
    rex = Pet("Rex", "dog", 4)
    vet = Task("Vet", 30, "high", "meds", start_time="08:15")
    walk = Task("Walk", 20, "high", "walk", preferred_time="morning")
    feed = Task("Feed", 10, "high", "feeding", preferred_time="morning")
    play = Task("Play", 15, "low", "enrichment", preferred_time="afternoon")
    for task in (vet, walk, feed, play):
        rex.add_task(task)

    plan = Scheduler(Owner("Sam", 120, pets=[rex])).generate_plan()

    # Walk can't fit in 08:00-08:15 before the vet, so it jumps to after it.
    assert [(i.task.title, i.start, i.end) for i in plan.scheduled] == [
        ("Vet", "08:15", "08:45"),
        ("Walk", "08:45", "09:05"),
        ("Feed", "09:05", "09:15"),
        ("Play", "13:00", "13:15"),
    ]
    assert plan.conflicts == []


def test_detect_conflicts_reports_real_overlaps_for_same_and_different_pets():
    rex, luna = Pet("Rex", "dog", 4), Pet("Luna", "cat", 2)
    rex.add_task(Task("Vet", 45, "high", "meds", start_time="09:00"))
    rex.add_task(Task("Bath", 20, "medium", "grooming", start_time="09:30"))
    luna.add_task(Task("Nail trim", 15, "medium", "grooming", start_time="09:40"))
    luna.add_task(Task("Dinner", 10, "high", "feeding", start_time="09:45"))  # starts as Vet ends

    plan = Scheduler(Owner("Sam", 180, pets=[rex, luna])).generate_plan()

    assert plan.conflicts == [
        "Vet (Rex, 09:00-09:45) overlaps Bath (Rex, 09:30-09:50); both for Rex",
        "Vet (Rex, 09:00-09:45) overlaps Nail trim (Luna, 09:40-09:55); different pets",
        "Bath (Rex, 09:30-09:50) overlaps Nail trim (Luna, 09:40-09:55); different pets",
        "Bath (Rex, 09:30-09:50) overlaps Dinner (Luna, 09:45-09:55); different pets",
        "Nail trim (Luna, 09:40-09:55) overlaps Dinner (Luna, 09:45-09:55); both for Luna",
    ]
    assert "Conflicts:" in plan.explain()


def test_add_task_warns_about_overlap_and_budget_but_still_adds():
    rex, luna = Pet("Rex", "dog", 4), Pet("Luna", "cat", 2)
    scheduler = Scheduler(Owner("Sam", 60, pets=[rex, luna]))

    assert scheduler.add_task(rex, Task("Vet", 30, "high", "meds", start_time="10:00")) == []
    assert scheduler.add_task(luna, Task("Walk", 10, "low", "walk")) == []  # no fixed time: nothing to clash
    warnings = scheduler.add_task(luna, Task("Groomer", 30, "medium", "grooming", start_time="10:15"))

    assert warnings == [
        "Groomer (Luna, 10:15-10:45) overlaps Vet (Rex, 10:00-10:30); different pets",
        f"Tasks due {date.today()} now need 70 min but only 60 are available; "
        "lower-priority tasks will be skipped.",
    ]
    assert len(luna.get_tasks()) == 2


def test_start_time_must_be_hh_mm():
    for bad in ("9:30", "24:00", "09:60", "noon"):
        try:
            Task("Walk", 10, "low", "walk", start_time=bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} should be rejected")


def test_two_tasks_at_exact_same_time_are_flagged():
    rex, luna = Pet("Rex", "dog", 4), Pet("Luna", "cat", 2)
    scheduler = Scheduler(Owner("Sam", 120, pets=[rex, luna]))
    scheduler.add_task(rex, Task("Vet checkup", 45, "high", "meds", start_time="09:00"))

    add_warnings = scheduler.add_task(luna, Task("Ear drops", 5, "high", "meds", start_time="09:00"))
    plan = scheduler.generate_plan()

    expected = "Vet checkup (Rex, 09:00-09:45) overlaps Ear drops (Luna, 09:00-09:05); different pets"
    assert add_warnings == ["Ear drops (Luna, 09:00-09:05) overlaps Vet checkup (Rex, 09:00-09:45); different pets"]
    assert plan.conflicts == [expected]
    assert expected in plan.explain()


# --- Sorting correctness ---


def test_plan_is_in_chronological_order_regardless_of_priority():
    rex = Pet("Rex", "dog", 4)
    rex.add_task(Task("Evening walk", 30, "high", "walk", preferred_time="evening"))
    rex.add_task(Task("Lunch meds", 5, "medium", "meds", start_time="12:00"))
    rex.add_task(Task("Brush coat", 15, "low", "grooming", preferred_time="morning"))
    rex.add_task(Task("Puzzle toy", 20, "low", "enrichment", preferred_time="afternoon"))

    plan = Scheduler(Owner("Sam", 120, pets=[rex])).generate_plan()

    assert [(i.task.title, i.start) for i in plan.scheduled] == [
        ("Brush coat", "08:00"),
        ("Lunch meds", "12:00"),
        ("Puzzle toy", "13:00"),
        ("Evening walk", "18:00"),
    ]
    starts = [i.start_minute for i in plan.scheduled]
    assert starts == sorted(starts)


def test_sort_by_priority_is_by_rank_not_alphabetical():
    scheduler = Scheduler(Owner("Sam", 60))
    rex = Pet("Rex", "dog", 4)
    low = Task("Brush", 10, "low", "grooming")
    high = Task("Meds", 5, "high", "meds")
    medium = Task("Feed", 10, "medium", "feeding")

    result = scheduler.sort_by_priority([(rex, low), (rex, high), (rex, medium)])

    assert [task for _, task in result] == [high, medium, low]


def test_priority_ties_keep_tasks_with_a_time_first_then_original_order():
    scheduler = Scheduler(Owner("Sam", 60, preferences={"walk": "morning"}))
    rex = Pet("Rex", "dog", 4)
    first = Task("Brush", 10, "high", "grooming")
    second = Task("Toy", 10, "high", "enrichment")
    timed = Task("Walk", 10, "high", "walk")  # morning via owner preference

    result = scheduler.sort_by_priority([(rex, first), (rex, second), (rex, timed)])

    assert [task for _, task in result] == [timed, first, second]


# --- Recurrence logic ---


def test_completed_daily_task_shows_up_in_tomorrows_plan():
    rex = Pet("Rex", "dog", 4)
    walk = Task("Walk", 30, "high", "walk", frequency="daily", due_date=date(2026, 11, 1))
    rex.add_task(walk)
    owner = Owner("Sam", 60, pets=[rex])

    next_walk = Scheduler(owner, today=date(2026, 11, 1)).complete_task(rex, walk)
    tomorrow = Scheduler(owner, today=date(2026, 11, 2)).generate_plan()

    assert next_walk.due_date == date(2026, 11, 2)
    assert [i.task for i in tomorrow.scheduled] == [next_walk]  # the completed walk is not repeated


def test_next_occurrence_keeps_the_tasks_settings():
    vet = Task("Vet", 30, "high", "meds", frequency="weekly", start_time="09:00", due_date=date(2026, 11, 1))

    nxt = vet.mark_complete()

    assert (nxt.title, nxt.priority, nxt.category, nxt.start_time, nxt.frequency) == (
        "Vet", "high", "meds", "09:00", "weekly",
    )
    assert nxt.completed is False and vet.completed is True


def test_completing_an_overdue_daily_task_does_not_put_it_back_in_todays_plan():
    rex = Pet("Rex", "dog", 4)
    walk = Task("Walk", 30, "high", "walk", frequency="daily", due_date=date(2026, 10, 25))
    rex.add_task(walk)
    scheduler = Scheduler(Owner("Sam", 60, pets=[rex]), today=date(2026, 11, 1))

    next_walk = scheduler.complete_task(rex, walk)

    assert next_walk.due_date == date(2026, 11, 2)  # counted from today, not from the old due date
    assert scheduler.collect_tasks() == []


# --- Conflict detection ---


def test_duplicate_times_for_the_same_pet_are_flagged():
    rex = Pet("Rex", "dog", 4)
    scheduler = Scheduler(Owner("Sam", 60, pets=[rex]))
    scheduler.add_task(rex, Task("Breakfast", 10, "high", "feeding", start_time="08:00"))

    warnings = scheduler.add_task(rex, Task("Breakfast", 10, "high", "feeding", start_time="08:00"))
    plan = scheduler.generate_plan()

    expected = "Breakfast (Rex, 08:00-08:10) overlaps Breakfast (Rex, 08:00-08:10); both for Rex"
    assert warnings == [expected]
    assert plan.conflicts == [expected]


def test_back_to_back_tasks_are_not_a_conflict():
    rex = Pet("Rex", "dog", 4)
    rex.add_task(Task("Walk", 30, "high", "walk", start_time="09:00"))
    rex.add_task(Task("Feed", 10, "high", "feeding", start_time="09:30"))

    plan = Scheduler(Owner("Sam", 60, pets=[rex])).generate_plan()

    assert plan.conflicts == []


def test_completed_task_at_same_time_is_not_a_conflict():
    rex = Pet("Rex", "dog", 4)
    scheduler = Scheduler(Owner("Sam", 60, pets=[rex]))
    done = Task("Vet", 30, "high", "meds", frequency="once", start_time="09:00")
    scheduler.add_task(rex, done)
    done.mark_complete()

    warnings = scheduler.add_task(rex, Task("Groomer", 30, "medium", "grooming", start_time="09:00"))

    assert warnings == []
    assert scheduler.generate_plan().conflicts == []


# --- Empty inputs and time budget boundaries ---


def test_owner_with_no_pets_and_pet_with_no_tasks_give_an_empty_plan():
    for owner in (Owner("Sam", 60), Owner("Sam", 60, pets=[Pet("Rex", "dog", 4)])):
        plan = Scheduler(owner).generate_plan()

        assert plan.scheduled == [] and plan.skipped == [] and plan.conflicts == []
        assert plan.total_time() == 0
        assert "Nothing could be scheduled." in plan.explain()


def test_zero_available_minutes_skips_everything():
    rex = Pet("Rex", "dog", 4)
    rex.add_task(Task("Meds", 5, "high", "meds"))

    plan = Scheduler(Owner("Sam", 0, pets=[rex])).generate_plan()

    assert plan.scheduled == []
    assert [i.task.title for i in plan.skipped] == ["Meds"]


def test_task_that_exactly_fills_remaining_time_is_scheduled():
    rex = Pet("Rex", "dog", 4)
    rex.add_task(Task("Walk", 30, "high", "walk"))
    rex.add_task(Task("Feed", 30, "low", "feeding"))

    plan = Scheduler(Owner("Sam", 60, pets=[rex])).generate_plan()

    assert plan.skipped == []
    assert plan.total_time() == 60


def test_smaller_task_still_fits_after_a_bigger_one_is_skipped():
    rex = Pet("Rex", "dog", 4)
    rex.add_task(Task("Long hike", 45, "high", "walk"))
    rex.add_task(Task("Feed", 20, "low", "feeding"))

    plan = Scheduler(Owner("Sam", 30, pets=[rex])).generate_plan()

    assert [i.task.title for i in plan.scheduled] == ["Feed"]
    assert [i.task.title for i in plan.skipped] == ["Long hike"]


def test_overdue_tasks_are_planned_and_future_tasks_are_not():
    rex = Pet("Rex", "dog", 4)
    overdue = Task("Meds", 5, "high", "meds", due_date=date(2026, 10, 31))
    future = Task("Bath", 20, "low", "grooming", due_date=date(2026, 11, 2))
    rex.add_task(overdue)
    rex.add_task(future)

    plan = Scheduler(Owner("Sam", 60, pets=[rex]), today=date(2026, 11, 1)).generate_plan()

    assert [i.task for i in plan.scheduled] == [overdue]


def test_scheduled_times_never_run_past_midnight():
    rex = Pet("Rex", "dog", 4)
    for n in range(8):
        rex.add_task(Task(f"Play {n}", 60, "low", "enrichment", preferred_time="evening"))

    plan = Scheduler(Owner("Sam", 600, pets=[rex])).generate_plan()

    # 18:00-24:00 holds six one-hour tasks; the other two are skipped, not given times like 25:00.
    assert all(i.end_minute <= 24 * 60 for i in plan.scheduled)
    assert len(plan.scheduled) == 6
    assert plan.scheduled[-1].end == "24:00"
    assert [i.task.title for i in plan.skipped] == ["Play 6", "Play 7"]
    assert all("past midnight" in i.reason for i in plan.skipped)
    assert plan.total_time() == 360


def test_shorter_task_still_fits_before_midnight_after_a_longer_one_is_dropped():
    rex = Pet("Rex", "dog", 4)
    rex.add_task(Task("Evening walk", 330, "high", "walk", preferred_time="evening"))  # 18:00-23:30
    rex.add_task(Task("Long chew", 60, "medium", "enrichment"))  # would end 00:30
    rex.add_task(Task("Treat", 10, "low", "feeding"))

    plan = Scheduler(Owner("Sam", 600, pets=[rex])).generate_plan()

    assert [(i.task.title, i.start, i.end) for i in plan.scheduled] == [
        ("Evening walk", "18:00", "23:30"),
        ("Treat", "23:30", "23:40"),
    ]
    assert [i.task.title for i in plan.skipped] == ["Long chew"]
