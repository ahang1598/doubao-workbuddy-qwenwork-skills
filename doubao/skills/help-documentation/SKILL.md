---
name: help-documentation
description: 撰写产品帮助文档，包含快速上手、功能说明、常见问题与故障排除，面向终端用户。
---

# Help Documentation

The reader of a help article arrives stuck, impatient, and looking for one specific answer; the job is to get them unstuck fast. The costly failure this skill prevents is the feature tour - an article organized around what the product has instead of what the user is trying to do, which the stuck user scrolls, fails to match to their problem, and abandons for a support ticket.

## Operating procedure

### Step 1: Gather inputs

1. The task or problem the article addresses, in the user's words (required). One article = one task; if the request covers several tasks, split into linked articles now.
2. The exact UI labels, menu paths, and screens involved (required - ask for screenshots or the live product; guessing labels produces instructions that fail on contact).
3. Audience and prerequisites: what plan/role/permissions the reader needs.
4. Platform or version differences that change the steps (default: none noted).
5. The most common failure points, from support tickets if available.

### Step 2: Choose the article type

This maps to the Diátaxis quadrants - pick one per article, never blend:

- **How-to guide** (task-oriented; most common): the user has a goal and needs numbered steps.
- **Troubleshooting** (problem-oriented): the user has a symptom and needs the fix.
- **Conceptual overview** (understanding-oriented): the user needs to understand a model before tasks make sense. Keep rare; link from task articles.
- **FAQ**: short direct answers to real questions in the user's words, linking to fuller articles for depth.

### Step 3: Write the title verb-first

Start with the verb and name the task exactly as users search: "Reset your password," "Export a report." Front-load the title and first sentence with the search keywords. Titles like "Password management" or "About reports" fail the search-match test.

### Step 4: Draft to the type's skeleton

How-to guide:
1. One-sentence intro: what they will accomplish plus prerequisites.
2. Numbered steps - one action per step, each starting with the verb, naming the exact button or menu label in bold, matching on-screen capitalization precisely. Ceiling: about 10 steps; past that, split the article.
3. A note or tip at each known stuck point.
4. Result statement: what success looks like ("You'll see a confirmation message").
5. Next steps / related articles.

Troubleshooting: organize by symptom - "If you see X..." then the fix; most common cause first; every fix ends in an action, and every dead end points to the next fix or to support.

### Step 5: Mark visuals and accessibility

Note where a screenshot helps and exactly what it should show; supply alt-text guidance for each. Never rely on color or position alone ("the red button on the right") - name the label. Spell out acronyms on first use; define any unavoidable jargon once.

### Step 6: Run the stuck-user test

Follow the steps against the actual UI (or have the requester verify). Any step where the reader must infer, decide between unstated options, or "simply configure" something fails the test and gets rewritten.

## Skeleton: how-to article

Copy and replace the [FILL] fields.

```
# [FILL: Verb] [FILL: object - the task as users search it]

[FILL: One sentence: what you'll accomplish.] You need [FILL: prerequisite/role/plan].

1. [FILL: Verb] **[FILL: exact UI label]**.
2. [FILL: Verb] **[FILL: exact UI label]**.
   > Tip: [FILL: note at the known stuck point]
3. [FILL: Verb] **[FILL: exact UI label]**.
   [Screenshot: [FILL: what it shows] - alt text: [FILL]]

**Result:** [FILL: what the user sees when it worked].

## Related articles
- [FILL: adjacent task 1]
- [FILL: adjacent task 2]
```

Contrast for a single step:

**Bad:** "Simply configure your notification settings to your preference."
**Good:** "Click **Settings**, then click **Notifications**, then turn on **Email me about mentions**." (Three actions = three steps in the real article.)

## Deliverable

Produce the article with: a verb-led, keyword-front-loaded title; a one-sentence intro with prerequisites; numbered one-action steps using exact bolded UI labels; tips at known stuck points; screenshot placements with alt text; a result statement; and a list of related articles to cross-link.

## Do NOT

- Do not document features instead of tasks; users search for what they want to DO.
- Do not cram multiple actions into one step ("Click Settings, then Privacy, then toggle X") - scanning readers lose their place.
- Do not paraphrase UI labels; "the sharing menu" fails when the button says **Invite**.
- Do not write walls of text; the stuck user scans for their step and bounces off paragraphs.
- Do not assume knowledge the stuck user lacks; the person reading a reset-password article does not know where Settings is.
- Do not blend a conceptual overview into a how-to; link to it instead.

## Quality bar

- Title starts with a verb and matches search phrasing.
- One task per article; every step is one action with the exact on-screen label.
- A result statement tells the reader they succeeded.
- Steps verified against the actual UI, not memory.
- No jargon left undefined; no color/position-only references; alt text noted for every screenshot.
