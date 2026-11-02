import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Shared labels so every table shows priority and status the same way.
PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
STATUS_BADGE = {True: "✅ Done", False: "⏳ To do"}

st.title("🐾 PawPal+")
st.caption("Plan your pets' day: add care tasks, and PawPal+ fits them into the time you have.")

with st.expander("Scenario"):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build"):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")

# Create the Owner once and reuse it on every rerun, so pets and tasks persist.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=60)
owner = st.session_state.owner
# Rebuilt each rerun (it's cheap) so it always plans for today; every section below uses it.
scheduler = Scheduler(owner)

col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = int(
        st.number_input("Minutes available today", min_value=0, max_value=1440, value=owner.available_minutes)
    )

st.markdown("### Add a Pet")

col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with col3:
    age = st.number_input("Age", min_value=0, max_value=40, value=3)

if st.button("Add pet"):
    if not pet_name.strip():
        st.error("Please enter a pet name.")
    elif any(p.name == pet_name.strip() for p in owner.get_pets()):
        st.error(f"{owner.name} already has a pet named {pet_name.strip()}.")
    else:
        owner.add_pet(Pet(name=pet_name.strip(), species=species, age=int(age)))
        st.success(f"Added {pet_name.strip()}.")

pets = owner.get_pets()
if pets:
    st.dataframe(
        [{"Name": p.name, "Species": p.species.capitalize(), "Age": p.age, "Tasks": len(p.get_tasks())} for p in pets],
        hide_index=True,
    )
else:
    st.info("No pets yet. Add one above.")

st.markdown("### Schedule a Task")

if not pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    pet_index = st.selectbox(
        "For which pet?", range(len(pets)), format_func=lambda i: f"{pets[i].name} ({pets[i].species})"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        category = st.selectbox("Category", ["walk", "feeding", "meds", "grooming", "enrichment"])
    with col2:
        preferred_time = st.selectbox("Preferred time", ["any", "morning", "afternoon", "evening"])
    with col3:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
    with col4:
        start_time = st.text_input("Fixed start (HH:MM)", value="", help="Leave blank to let PawPal+ pick a time.")

    if st.button("Add task"):
        try:
            task = Task(
                title=task_title.strip(),
                duration_minutes=int(duration),
                priority=priority,
                category=category,
                preferred_time=None if preferred_time == "any" else preferred_time,
                frequency=frequency,
                start_time=start_time.strip() or None,
            )
        except ValueError as e:
            st.error(str(e))
        else:
            warnings = scheduler.add_task(pets[pet_index], task)
            st.success(f"Added '{task.title}' for {pets[pet_index].name}.")
            for warning in warnings:
                st.warning(warning)

if owner.get_all_tasks():
    st.markdown("### Current Tasks")
    if "done_message" in st.session_state:
        st.success(st.session_state.pop("done_message"), icon="🎉")

    # At-a-glance numbers, then whether today's tasks fit the owner's time.
    due_today = scheduler.collect_tasks()
    minutes_due = sum(task.duration_minutes for _, task in due_today)
    col1, col2, col3 = st.columns(3)
    col1.metric("Due today", len(due_today))
    col2.metric("Done", len(scheduler.filter_tasks(completed=True)))
    col3.metric("Minutes needed", f"{minutes_due} / {owner.available_minutes}")
    if minutes_due > owner.available_minutes:
        st.warning(
            f"Today's tasks need {minutes_due - owner.available_minutes} more minutes than you have. "
            "Lower-priority tasks will be skipped.",
            icon="⏱️",
        )
    elif due_today:
        st.success(f"Everything due today fits, with {owner.available_minutes - minutes_due} minutes to spare.", icon="✅")

    col1, col2, col3 = st.columns(3)
    with col1:
        pet_filter = st.selectbox("Pet", ["All pets"] + [p.name for p in pets])
    with col2:
        status_filter = st.selectbox("Status", ["To do", "Done", "All"])
    with col3:
        sort_choice = st.selectbox("Sort by", ["Time of day", "Priority"])

    # filter_tasks() treats None as "don't filter on this".
    shown = scheduler.filter_tasks(
        completed={"To do": False, "Done": True, "All": None}[status_filter],
        pet_name=None if pet_filter == "All pets" else pet_filter,
    )
    if sort_choice == "Priority":
        shown = scheduler.sort_by_priority(shown)
    else:
        # sort_by_time() works on Task objects, so look each task's pet back up by id.
        pet_of = {task.id: pet for pet, task in shown}
        shown = [(pet_of[task.id], task) for task in scheduler.sort_by_time([task for _, task in shown])]

    if shown:
        st.caption(f"Showing {len(shown)} of {len(owner.get_all_tasks())} tasks, sorted by {sort_choice.lower()}.")
        st.dataframe(
            [
                {
                    "Status": STATUS_BADGE[task.completed],
                    "Pet": pet.name,
                    "Task": task.title,
                    # A fixed start time is more useful than its part of the day, so show it when there is one.
                    "When": task.start_time or (scheduler.preferred_time_for(task) or "anytime").capitalize(),
                    "Minutes": task.duration_minutes,
                    "Priority": PRIORITY_BADGE[task.priority],
                    "Repeats": task.frequency.capitalize(),
                    "Due": task.due_date,
                }
                for pet, task in shown
            ],
            hide_index=True,
            column_config={
                "Minutes": st.column_config.NumberColumn(format="%d min"),
                "Due": st.column_config.DateColumn(format="ddd, MMM D"),
            },
        )
    else:
        st.info("No tasks match these filters. Try another pet or status.", icon="🔍")

    todo = scheduler.filter_tasks(completed=False)
    if todo:
        col1, col2 = st.columns([3, 1])
        with col1:
            done_index = st.selectbox(
                "Mark a task done",
                range(len(todo)),
                format_func=lambda i: f"{todo[i][1].title} ({todo[i][0].name}, due {todo[i][1].due_date})",
            )
        with col2:
            st.write("")  # line the button up with the selectbox
            mark_done = st.button("Mark done")
        if mark_done:
            done_pet, done_task = todo[done_index]
            next_task = scheduler.complete_task(done_pet, done_task)
            if next_task:
                message = f"Done! Next '{next_task.title}' for {done_pet.name} is due {next_task.due_date}."
            else:
                message = f"Done! '{done_task.title}' was a one-time task."
            # Rerun so the table above shows the change; the message is shown after the rerun.
            st.session_state.done_message = message
            st.rerun()
elif pets:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

if st.button("Generate schedule"):
    plan = scheduler.generate_plan()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Scheduled", len(plan.scheduled))
    col2.metric("Skipped", len(plan.skipped))
    col3.metric("Conflicts", len(plan.conflicts))
    col4.metric("Minutes used", f"{plan.total_time()} / {plan.available_minutes}")
    if plan.available_minutes:
        st.progress(plan.total_time() / plan.available_minutes)

    # Conflicts come first so the owner sees them before reading the plan.
    if plan.conflicts:
        st.error(
            f"{len(plan.conflicts)} time conflict(s) between fixed appointments. "
            "Change one of the start times or remove a task to fix it.",
            icon="🚨",
        )
        for warning in plan.conflicts:
            st.warning(warning, icon="⚠️")

    if plan.scheduled:
        st.success("Here's your day, in clock order.", icon="📅")
        rows = plan.to_table()
        for row in rows:
            row["Priority"] = PRIORITY_BADGE[row["Priority"]]
            row["Part of day"] = row["Part of day"].capitalize()
        st.dataframe(
            rows,
            hide_index=True,
            column_order=["Time", "Pet", "Task", "Part of day", "Minutes", "Priority"],
            column_config={"Minutes": st.column_config.NumberColumn(format="%d min")},
        )
        with st.expander("Why each task was chosen"):
            st.dataframe(
                [{"Task": f"{row['Task']} ({row['Pet']})", "Reason": row["Reason"]} for row in rows],
                hide_index=True,
            )
    else:
        st.warning("Nothing could be scheduled. Add tasks or increase your available minutes.", icon="📭")

    if plan.skipped:
        st.info(f"{len(plan.skipped)} task(s) didn't make it into today's plan:", icon="⏭️")
        st.dataframe(
            [
                {
                    "Pet": item.pet.name,
                    "Task": item.task.title,
                    "Priority": PRIORITY_BADGE[item.task.priority],
                    "Why skipped": item.reason,
                }
                for item in plan.skipped
            ],
            hide_index=True,
        )

    with st.expander("Full plan explanation"):
        st.text(plan.explain())
