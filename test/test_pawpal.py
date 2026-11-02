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
