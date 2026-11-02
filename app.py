import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
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
    st.table([{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.get_tasks())} for p in pets])
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
            warnings = Scheduler(owner).add_task(pets[pet_index], task)
            st.success(f"Added '{task.title}' for {pets[pet_index].name}.")
            for warning in warnings:
                st.warning(warning)

all_tasks = owner.get_all_tasks()
if all_tasks:
    st.write("Current tasks:")
    st.table(
        [
            {
                "Pet": pet.name,
                "Task": task.title,
                "Minutes": task.duration_minutes,
                "Priority": task.priority,
                "Category": task.category,
                "Preferred time": task.preferred_time or "any",
                "Fixed start": task.start_time or "-",
                "Frequency": task.frequency,
            }
            for pet, task in all_tasks
        ]
    )
elif pets:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

if st.button("Generate schedule"):
    plan = Scheduler(owner).generate_plan()
    if plan.scheduled:
        st.success(f"Scheduled {plan.total_time()} of {plan.available_minutes} available minutes.")
        st.table(plan.to_table())
    else:
        st.warning("Nothing could be scheduled. Add tasks or increase your available minutes.")
    for warning in plan.conflicts:
        st.warning(f"Time conflict: {warning}")
    if plan.skipped:
        st.markdown("**Skipped today:**")
        for item in plan.skipped:
            st.markdown(f"- {item.task.title} ({item.pet.name}): {item.reason}")
    with st.expander("Why this plan?"):
        st.text(plan.explain())
