"""Demo script: build an owner with two pets and print today's schedule."""

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner(
        name="Jordan",
        available_minutes=150,
        preferences={"walk": "morning", "feeding": "morning"},
    )

    rex = Pet(name="Rex", species="dog", age=4)
    luna = Pet(name="Luna", species="cat", age=2)
    owner.add_pet(rex)
    owner.add_pet(luna)

    # Added deliberately out of time-of-day order so the sorting below has work to do.
    rex.add_task(Task("Evening walk", 25, "medium", "walk", preferred_time="evening"))
    luna.add_task(Task("Brushing", 20, "low", "grooming"))
    luna.add_task(Task("Laser pointer play", 15, "low", "enrichment", preferred_time="afternoon"))
    rex.add_task(Task("Morning walk", 30, "high", "walk"))
    luna.add_task(Task("Thyroid meds", 5, "high", "meds", preferred_time="evening"))
    rex.add_task(Task("Breakfast", 10, "high", "feeding"))

    scheduler = Scheduler(owner)

    # Fixed-time appointments go through scheduler.add_task(), which warns about clashes.
    print("Booking appointments:")
    for pet, task in [
        (rex, Task("Vet checkup", 45, "high", "meds", frequency="once", start_time="09:00")),
        (luna, Task("Nail trim", 20, "medium", "grooming", frequency="once", start_time="09:30")),
        # Same start time as Rex's vet checkup: should be flagged as a conflict.
        (luna, Task("Ear drops", 5, "high", "meds", frequency="once", start_time="09:00")),
    ]:
        warnings = scheduler.add_task(pet, task)
        print(f"  {task.title} for {pet.name} at {task.start_time}: {'OK' if not warnings else ''}")
        for warning in warnings:
            print(f"    WARNING: {warning}")
    print()

    print("Tasks in the order they were added:")
    for pet, task in owner.get_all_tasks():
        print(f"  {scheduler.preferred_time_for(task) or 'anytime':<10} {pet.name:<5} {task.title}")

    print("\nTasks after sort_by_time():")
    pet_of = {task.id: pet for pet, task in owner.get_all_tasks()}
    all_tasks = [task for _, task in owner.get_all_tasks()]
    for task in scheduler.sort_by_time(all_tasks):
        print(f"  {scheduler.preferred_time_for(task) or 'anytime':<10} {pet_of[task.id].name:<5} {task.title}")
    print()

    plan = scheduler.generate_plan()

    print("=" * 62)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 62)
    print(f"{'Time':<13}{'Pet':<7}{'Task':<22}{'Min':>4}  Priority")
    print("-" * 62)
    for row in plan.to_table():
        print(f"{row['Time']:<13}{row['Pet']:<7}{row['Task']:<22}{row['Minutes']:>4}  {row['Priority']}")
    print("-" * 62)
    print(f"Total: {plan.total_time()} of {plan.available_minutes} minutes")

    print("\nWhy this plan:")
    print(plan.explain())

    # Pretend the morning is done, then use filter_tasks() to see what's left.
    # complete_task() also queues up the next occurrence of daily/weekly tasks.
    print("\nFinishing the morning:")
    for item in plan.scheduled:
        if item.time == "morning":
            next_task = scheduler.complete_task(item.pet, item.task)
            if next_task:
                print(f"  {item.task.title} done -> next one due {next_task.due_date}")

    print("\nCompleted so far:")
    for pet, task in scheduler.filter_tasks(completed=True):
        print(f"  {pet.name}: {task.title}")

    print("\nStill to do for Luna:")
    for pet, task in scheduler.filter_tasks(completed=False, pet_name="luna"):
        print(f"  {pet.name}: {task.title}")

    print("\nRex's tasks still to do today (tomorrow's copies are not included):")
    for pet, task in scheduler.collect_tasks():
        if pet is rex:
            print(f"  {task.title} (due {task.due_date})")


if __name__ == "__main__":
    main()
