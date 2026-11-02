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

The scheduler considers these constraints, roughly from strictest to softest:

- **Available time** (hard limit): the plan never uses more minutes than the owner has. Tasks that don't fit are skipped with a reason.
- **Priority** (decides what gets in): high → medium → low decides which tasks claim the time budget first.
- **Due date and completion**: only unfinished tasks due today or overdue are planned, so tomorrow's copy of a daily task stays out of today's plan.
- **Fixed start times**: an appointment like a vet visit at 09:00 keeps its time, and flexible tasks are moved around it.
- **Preferred time of day**: a task's own `preferred_time`, or else the owner's preference for its category (`{"walk": "morning"}`), decides *when* a task happens, not *whether* it happens. It only affects selection as a tie-breaker between tasks of equal priority.
- **End of day**: a flexible task that would run past midnight is skipped.

I ranked them by asking what goes wrong if each one is ignored. Ignoring the time budget gives the owner a plan they can't follow, and ignoring priority could drop a pet's meds in favour of a laser pointer session. Both of those hurt the pet or the owner's trust in the app. Getting a walk in the afternoon instead of the morning is only an inconvenience, so time-of-day preferences shape the order of the day but never knock a task out of it.

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

I used AI in every phase, but for a different job in each:

- **Design**: turning my UML into class skeletons, then reviewing the skeleton for missing relationships and logic bottlenecks before any method bodies were written. Most of the design changes in section 1b came out of that review.
- **Implementation**: building the scheduling logic in small steps (priority sorting, then time-of-day ordering, then clock times, conflicts and recurrence), checking each step with `main.py` before moving on.
- **Testing**: drafting the pytest suite and thinking up edge cases.
- **UI and docs**: wiring the logic into `app.py`, updating the UML to match the final code, and writing the README.

The most helpful prompts were specific and pointed at real code: "review this skeleton for missing relationships", "based on my final implementation, what should change in my UML?", or "what edge cases could break recurring tasks?". Prompts that asked the AI to compare the code against something (the UML, the requirements, an edge case) were more useful than open-ended "write this feature" prompts, because the answers were things I could check.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

The class skeleton gave `Scheduler` its own `tasks` list, passed into its constructor. It looked harmless, but the same tasks already lived on each `Pet`, so there would be two copies that could drift apart, and the scheduler would silently plan nothing if I forgot to pass the list. I removed it and made the pets the only place tasks are stored: the scheduler reads them through `Owner.get_all_tasks()`, which also keeps each task paired with its pet so the plan can say who a task is for.

To verify AI output I relied on running things rather than reading them:

- **Tests**: every scheduling behaviour has a test, and writing them caught two real bugs in code that had looked correct: overdue recurring tasks coming back already overdue, and start times like `25:00` being accepted.
- **The demo script**: `python main.py` prints the plan and its reasons, so I could check the schedule against what I expected by hand.
- **Docs against code**: when the AI wrote the README's example workflow, I had the steps run through the real scheduler. The first draft claimed the vet visit would be scheduled and the walk skipped; the actual output was the reverse, so the walkthrough was corrected before it went in.

**c. AI Strategy**

- Which AI coding assistant features were most effective for building your scheduler?
- Give one example of an AI suggestion you rejected or modified to keep your system design clean.
- How did using separate chat sessions for different phases help you stay organized?
- Summarize what you learned about being the "lead architect" when collaborating with powerful AI tools.

**Most effective features**

- **Design and UML review in chat** had the biggest impact on the final code. Asking for a review of the skeleton *before* implementing caught the flat task list, the reasons that weren't tied to their tasks, and the alphabetical priority sort while they were still cheap to fix.
- **Test generation** gave me a broad edge-case suite quickly (empty owners, exact time-budget boundaries, touching vs. overlapping appointments, late completions), and those tests found bugs I hadn't thought to look for.
- **Agent multi-file edits** were useful once the design was settled: a change like adding `start_time` touched `pawpal_system.py`, `app.py`, the tests and the README together, and the agent could keep them consistent.
- **Inline completion and "explain this code"** were handy for small things, like helper functions and Streamlit widget options, and for re-reading my own code after a break.

**A suggestion I rejected**

The skeleton's `Scheduler(owner, tasks)` constructor (described in 3b). I kept the scheduler but removed its task list, so tasks live only on pets and the scheduler always reads the current state through the owner. It was a one-line change, but it decided how every later feature worked: filtering by pet, conflict warnings that name the pet, and adding a recurring task's next copy to the right pet all depend on tasks staying attached to their pet.

**Separate chat sessions per phase**

I started a new chat for each phase: design/UML, implementing the logic, testing, and UI/docs. That helped in three ways:

- **Focused context**: each chat only had to hold one job, so the answers stayed on topic. The testing chat didn't drift into redesigning classes, and the docs chat didn't start rewriting the scheduler.
- **Fresh eyes on the code**: a new session had to read the code as it actually was, not as an earlier chat remembered it. That's how the UML review in the docs phase spotted relationships the original diagram was missing.
- **Clear checkpoints**: finishing a phase meant committing and moving on, so the git history follows the phases (skeleton → implementation → sorting/conflicts → tests), which made it easy to see what changed and why.

**Being the lead architect**

The AI is fast at producing code, but it doesn't own the design; I do. It will happily build on whatever structure it's given, including a flawed one, and its mistakes sound just as confident as its correct answers. So my job was to decide what the system should be (which class owns which data, which constraints are hard and which are soft, what happens on a conflict) and then hold every suggestion up against that. In practice that meant reviewing designs before writing code, asking for changes in small, checkable steps, and verifying with tests and real runs instead of trusting how plausible something looked. Used that way, the AI made me faster without taking the design decisions out of my hands.

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
