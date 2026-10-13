---
name: cover-letter-writer
description: 根据简历与职位描述定制求职信，以简历证据匹配岗位核心要求。
---

# Cover Letter Writer

A cover letter has one job - earn a resume read from a screener who spends under thirty seconds on it - and most letters fail in the first sentence by opening with "I am writing to apply for" and then restating the resume the screener is about to read anyway. The costly mistake this skill prevents is the generic letter - one that could be sent to any company with a find-and-replace - because screeners detect those instantly and treat them as evidence of low interest. A tailored letter answers three specific questions the posting is asking and proves the candidate did homework the other applicants skipped.

## Operating procedure

Follow these steps in order. Requirement extraction comes before any writing, because the letter's entire structure hangs on which three requirements it answers - draft prose first and the letter drifts back into a resume summary.

1. **Collect the inputs.** Get the resume, the full job posting, and any company hook material (see Inputs below). Do not proceed on the posting title alone; the ranked requirements live in the body text.
2. **Extract the three requirements the posting cares most about.** Rank every stated requirement by three signals - repetition (appears in the summary and again in the bullet list), position (first three bullets outrank the last three), and specificity (a named tool, quota, or scale beats a soft trait like "team player"). Take the top three. Exactly three: fewer looks thin, more dilutes each into a mention instead of an argument.
3. **Mirror each requirement with resume evidence.** For each of the three, find the single strongest proof in the resume - an accomplishment with a number wherever one exists (revenue, users, percent improvement, team size, time saved). Use the posting's own vocabulary in the mirror sentence so a keyword-scanning reader ties evidence to requirement without effort. If the resume has no evidence for a requirement, say so to the user and pick the nearest adjacent proof - do not fabricate.
4. **Write the company-specific hook as the first line.** One sentence that could only be written to this company - a recent launch, a stated mission the candidate genuinely connects to, a product they actually use, a public challenge the role clearly exists to solve. If no hook material was provided, derive one from the posting itself and label it a guess for the user to confirm or replace.
5. **Assemble the letter.** Structure - hook line, one bridge sentence naming the role, one short paragraph (or tight two-sentence block) per mirrored requirement, and a closing line with a plain ask for a conversation. No "To Whom It May Concern"; use the hiring manager's name if known, otherwise the team name.
6. **Cut to under 300 words.** Target 150 to 250. Cut throat-clearing ("I believe that", "I am confident"), any sentence that restates a resume line without adding context, and all adjectives about the candidate's own character ("passionate", "driven") - evidence carries the claim or nothing does.
7. **Run the quality bar** below, then deliver the letter with the three extracted requirements listed so the user can sanity-check the targeting.

## Inputs to collect

- **Resume** (required) - full text, not a summary.
- **Job posting** (required) - full text including responsibilities and requirements sections.
- **Company hook material** (optional) - anything the candidate knows or feels about the company: news, products used, people met, mission connection. Default when absent - derive a hook from the posting and label it a guess.
- **Hiring manager name** (optional) - default to the team name ("Dear Data Platform team") when unknown.
- **Tone** (optional) - default to warm-professional; only shift for explicitly creative roles.

Label every inferred item - the hook, any guessed seniority or team context - as a guess in the draft so the user knows what to verify.

## Concrete thresholds

- Under 300 words total; 150-250 is the target zone. A letter over 300 words signals the writer could not prioritize.
- Exactly 3 requirements mirrored - not 2, not 5.
- The company name (or an unmistakable company-specific fact) appears in the first sentence.
- At least 2 of the 3 evidence points contain a number. If the resume genuinely has no numbers, flag that to the user and route them to resume-writer, because the letter is fighting uphill without them.
- Zero sentences that restate a resume bullet verbatim.

## Worked contrast - opening line

**Bad:**

```
I am writing to express my strong interest in the Senior Product Manager
position at Datachord, which I found on LinkedIn. With over eight years of
experience in product management, I believe I would be a great fit.
```

Why it fails - nothing in it is specific to Datachord; "strong interest," "great fit," and the experience count are claims without evidence; the screener has learned nothing they will not get from the resume.

**Good:**

```
When Datachord opened its ingestion API to third-party schemas last quarter,
you created exactly the integration-partner problem I spent three years
solving at Fivetran - growing a connector ecosystem from 40 to 300 partners
without letting support costs scale with it.
```

Why it works - it could only be written to this company, it names a real event, and it fuses the hook with quantified evidence against the posting's most likely top requirement in a single sentence.

## Deliverable

A finished cover letter under 300 words - company-specific hook first line, three requirement-mirroring paragraphs each anchored by resume evidence, and a plain closing ask - delivered alongside the list of the three extracted requirements and a note marking any guessed content for the user to verify.

## Do NOT

- **Do NOT restate the resume.** The letter's job is to interpret the resume against this posting, not to summarize it - a screener reading the same content twice concludes the candidate had nothing to add.
- **Do NOT open with "I am writing to apply for."** It wastes the only line guaranteed to be read on information the subject line already carried.
- **Do NOT mirror more than three requirements.** Coverage breadth reads as unfocused; three deep beats six shallow.
- **Do NOT use self-descriptive adjectives** ("passionate," "results-driven," "detail-oriented"). Unverifiable claims train the reader to discount the verifiable ones.
- **Do NOT fabricate hook material or evidence.** A false company fact or an inflated number is discoverable in the interview and fatal there.

## Quality bar

The finished letter passes only when all hold:

- Word count under 300.
- First sentence contains a company-specific fact that would be false if sent to a different company.
- Each of the three requirements is mirrored with distinct evidence, and at least two evidence points carry a number.
- The posting's own vocabulary appears in each mirror sentence.
- Reading the letter without the resume, a screener could name the three things the posting asked for.
- Every guessed element is labeled for the user.

## Escalation and neighbors

If the resume itself is the weak link - no numbers, buried accomplishments - route to resume-writer before polishing the letter. For which roles to target, sequencing applications, and follow-up strategy, route to job-application. Once the letter earns an interview, route to job-interview-prep for the preparation work.
