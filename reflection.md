# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

1. Enter basic info about themselves and their pet (name, species, etc.).
2. Add or edit care tasks like walks, feeding, or meds, with a duration and priority for each.
3. Generate a daily schedule that fits their available time, prioritizes the important tasks, and explains why it was arranged that way.

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

My initial design has five classes that separate the data (owner, pets, tasks) from the logic that builds a schedule and the output the user sees. An Owner has many Pets, and each Pet owns its list of Tasks. A Scheduler reads the owner's available time and the tasks, then produces a DailyPlan.

- **Owner**: the person using the app. Stores their name, how many minutes they have today, and preferences (like "walks in the morning"). Responsible for keeping track of their pets (`add_pet`, `get_pets`).
- **Pet**: the animal being cared for. Stores name, species, and age, and is responsible for managing its own care tasks (`add_task`, `remove_task`, `get_tasks`).
- **Task**: a single care activity, with a title, duration, priority, category (walk, feeding, meds, grooming, enrichment), and an optional preferred time. It can update its own fields (`edit`) and report whether it is high priority.
- **Scheduler**: the "brain" of the app. Takes the owner and all the tasks, sorts them by priority, checks whether each one fits in the remaining time, and generates the plan.
- **DailyPlan**: the result shown to the user. Holds the scheduled tasks in order, the tasks that were skipped, and the reasons behind each decision. It can total the scheduled time, explain its reasoning in plain language, and convert itself to a table for display in Streamlit.

I used dataclasses for Owner, Pet, Task, and DailyPlan because they mainly hold data, and kept Scheduler as a regular class since its job is behavior rather than storage.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. After drafting the skeleton, I reviewed it for missing relationships and logic bottlenecks before writing any method bodies, and made these changes:

**Relationships**
- **Tasks now stay linked to their pet.** In the original design the Scheduler held one flat list of tasks, so the plan couldn't say which pet a task was for. The Scheduler now collects `(pet, task)` pairs instead.
- **One source of truth for tasks.** The Scheduler used to take its own `tasks` list, which duplicated the tasks already stored on each Pet and would be empty if I forgot to pass it. I removed it. The Scheduler now calls `collect_tasks()`, which uses a new `Owner.get_all_tasks()` that walks `get_pets()` and each pet's `get_tasks()`.
- **Reasons are stored with their task.** `DailyPlan.reasons` was a separate list of strings with no link to the task it explained. I replaced it with a small `PlanItem` dataclass (pet, task, reason), and the plan now has `scheduled` and `skipped` lists of `PlanItem`s, so skipped tasks get a reason too.
- **DailyPlan knows the time budget.** I added `available_minutes` to `DailyPlan` so `explain()` can report minutes used vs. available.
- **Structured preferences.** Owner preferences changed from free text ("walks in the morning") to a dict like `{"walk": "morning"}`, using the same time words as `Task.preferred_time`, so the Scheduler can actually compare them.

**Scheduling logic**
- **Priority uses a lookup.** Sorting the raw strings would put "low" above "medium" alphabetically, so I added `PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}`.
- **Skip and keep going.** If a task doesn't fit in the remaining time, the scheduler skips it and keeps checking the rest, so smaller tasks can still use the leftover minutes.
- **Tie-breaker.** Among tasks with the same priority, ones with a preferred time (from the task or the owner's preferences) come first.
- **Time-of-day order.** The final plan is ordered morning → afternoon → evening, with no-preference tasks last, so it reads like a real day instead of a priority list.
- **Task ids.** Dataclasses treat two tasks with identical fields as equal, so removing one of two identical "Feeding" tasks could remove the wrong one. Each task now gets a unique `id`, and `remove_task` matches by id.
- **Input validation.** `Task` checks its fields when created and in `edit()` (non-empty title, positive duration, allowed priority/category/time) and rejects unknown field names, so a typo like `edit(durration=5)` raises an error instead of silently doing nothing. `Owner` checks its available minutes and preferences.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**Tradeoff: priority always wins over fitting in the most tasks.** The scheduler is *greedy*: it sorts tasks by priority and takes each one that still fits, highest priority first. It never goes back to ask whether a different combination would use the time better. For example, with 60 minutes free, a 50-minute high-priority walk and three 20-minute medium tasks, it schedules the walk and then nothing else fits in the 10 minutes left. That's one task done when three medium tasks would have filled the full hour. An optimal approach (the "knapsack" algorithm) could find the best combination, but it would sometimes drop a high-priority task to fit in several smaller ones.

I think the greedy approach is the right choice for a pet owner:
- **Important care comes first.** Priority stands for things like meds, feeding, and walks that a pet actually needs. An owner would rather get the meds done than cross off more low-stakes tasks, so a high-priority task should never be dropped just to raise the task count.
- **It's predictable and easy to explain.** Every decision has a simple reason, like "high priority; 30 min fit in the 90 min remaining" or "needs 20 min and only 5 min were left", which `explain()` shows to the owner. An optimal algorithm's choices would be much harder to justify in one sentence.
- **The worst case is softened.** Because the scheduler skips a task that doesn't fit and keeps checking the rest, smaller tasks further down the list still use up leftover minutes instead of being wasted.
- **Speed isn't a concern either way.** With 5–20 tasks a day, both approaches run instantly, so the choice came down to behaviour and readability, not performance.

The cost is that some days the plan leaves time unused that a smarter combination could have filled. If owners complained about that, a middle ground would be to keep priority as the main rule but, among tasks of the *same* priority, prefer shorter ones so more of them fit.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
