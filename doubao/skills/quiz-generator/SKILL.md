---
name: quiz-generator
description: 根据学习主题生成不同难度的测验题目，包括选择题、判断题与简答题，附带答案与解析。
---

# Quiz Generator

A well-constructed quiz is a learning event, not just a measuring event. The costly failure this skill prevents is the all-recall quiz with throwaway distractors: it reports high scores while misconceptions calcify undetected, and the teacher learns nothing actionable from the results.

## Operating procedure

### Step 1: Gather inputs

Collect before writing any question. Where the user cannot answer, use the default and label assumptions as guesses.

1. Topic and the specific objectives or content covered (required).
2. Grade or level (required).
3. Purpose: formative check, unit exam, or review/performance task (default: formative).
4. Question count and time budget (default: 10 questions; budget roughly 1 minute per multiple-choice item, 3-5 per short answer, 10+ per constructed response).
5. Known misconceptions in this topic (ask - these become distractors; if none supplied, derive them from typical partial understandings and label them as guesses).
6. Format constraints: paper vs digital, calculator allowed, open notes.

### Step 2: State the Bloom's distribution before writing questions

Bloom's six levels, lower to higher order: Remember, Understand, Apply, Analyze, Evaluate, Create. Declare the target mix first; do not drift toward all-recall by default.

- Formative quiz: covers Remember through Apply - roughly 40% Remember/Understand, 60% Apply.
- Unit exam: must reach Analyze and Evaluate - no more than 50% of points on Remember/Understand.
- Performance/review task: Evaluate and Create dominate.

Red line: if every question is Remember-level, the quiz measures memorization only - rebalance before proceeding.

### Step 3: Match question type to level

- Multiple choice: efficient for Remember and Understand; use sparingly for Apply and above.
- Short answer: versatile across Apply, Analyze, Evaluate.
- Constructed response / scenario-based: best for Analyze and above.
- True/false: low signal - diagnostic pre-checks only, never graded summative work.

### Step 4: Write stems, then distractors from misconceptions

Lower-order stems are direct and simple: define, identify, list. Higher-order stems use scenarios, data sets, or documents as stimulus - kept concise and free of culturally specific references that create construct-irrelevant difficulty.

Every multiple-choice distractor must be the answer a student with a specific partial understanding would choose. Rules: the correct answer must be unambiguously correct (if a second option survives a defensible interpretation, rewrite the stem, not the option); no "all of the above" / "none of the above" except in carefully controlled contexts; keep options parallel in length and grammar, since the longest option telegraphs the answer.

### Step 5: Build the answer key with rationales

For each question: the correct answer, a one-sentence rationale for why it is correct, and - for multiple choice - the misconception each distractor represents. This is part of the deliverable, not an extra.

### Step 6: Assemble and check the summary table

Group questions by cognitive level, labeled. Produce the table (question number, level, type, points) and verify the actual point distribution matches the Step 2 declaration. If it drifted, fix questions, not the declaration.

## Worked contrast: distractor quality

Topic: photosynthesis, Understand level.

**Bad:**
"What do plants need for photosynthesis? A) sunlight, water, CO2  B) rocks  C) music  D) darkness"
B, C, D are jokes no partially-informed student would pick; the item measures test-taking, not understanding.

**Good:**
"Where does most of the mass of a growing tree come from? A) carbon dioxide in the air (correct)  B) minerals absorbed from the soil  C) water pulled up by the roots  D) energy from sunlight converted to matter"
Distractor analysis: B is the classic "plants eat soil" misconception; C confuses the reactant present in largest volume with the mass source; D reflects the common energy-becomes-matter confusion. A student choosing B tells the teacher exactly what to re-teach.

## Deliverable

Produce: (1) the question set grouped and labeled by Bloom's level, with total points stated; (2) the summary table - question number, cognitive level, question type, point value; (3) the answer key with per-question rationale and per-distractor misconception notes. Offer a student-facing version (instructions, no key) and a teacher version as separate documents.

## Do NOT

- Do not default to all-recall; a quiz that never reaches Apply cannot distinguish understanding from memorization.
- Do not write filler distractors - every wrong option a student would never choose wastes an opportunity to detect a misconception.
- Do not use true/false on graded summative work; a coin flip scores 50%.
- Do not let one question test two things at once; a wrong answer becomes undiagnosable.
- Do not ship a key without rationales; "B" alone forces the teacher to re-derive every answer during grading.

## Quality bar

- The Bloom's distribution was declared before writing and the final table matches it.
- Every MC distractor maps to a named misconception; no joke options.
- Every correct answer survives the "could a well-prepared student defend a different option?" test.
- Stimulus material is concise and construct-relevant.
- Total points and per-question values are stated and sum correctly.
