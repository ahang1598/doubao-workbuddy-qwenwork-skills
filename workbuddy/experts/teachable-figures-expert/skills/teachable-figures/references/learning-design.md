# Learning design: audience, schema, load, attention, dual coding

A teachable figure is a **learning exercise or illustration, not teaching**. In this skill, *teaching* means presenting or lecturing an explanation. *Learning* is what the learner does: predicting, operating a cause, noticing the effect, making sense of it, and explaining it. The figure scaffolds that sensemaking. It does not replace the person who teaches, and it is not evidence that anyone learned.

The principles below are well-established design heuristics from learning-science research. They shape the build; they do not guarantee an outcome for a particular learner. A figure that follows them is a better-designed exercise, not a tested one.

## 1. Audience decides the build

Ask who will use the artifact before deciding how much scaffolding it carries.

| | Teacher or parent (presenter) | Solo self-learner |
| --- | --- | --- |
| Already has | Goals, a content sequence, a knowledge path; watches the learner live | A goal and some background; nobody watching |
| Who scaffolds | The presenter: voiceover, questioning, pointing, pacing | The artifact itself |
| Default build | **Illustration / classroom exercise** | **Self-guided exercise** |
| Copy on the page | Minimal: short labels, the prediction prompt, a one-line caveat | Full: probe, feedback, explanation, practice, transfer |
| Figure | Large and legible at projector distance; labels readable at the back of a room | Normal size, readable alongside the panel |
| Attention aids | Focus guide the presenter toggles; ordered highlights to step through while talking | Focus guide on by default, following the learner's current step |
| Prediction | A class prompt (show of hands, mini-whiteboards); no answer key shown until the presenter reveals it | Saved prediction with misconception-specific feedback |
| Fading / practice | Optional; the presenter decides | Required: independent practice with scaffolds removed, then transfer |
| Prior knowledge | Stated by the presenter (class profile) | Probed with 2–4 diagnostic questions first |

Do not add an explanation layer to a presenter build because it "might help": it competes with the presenter's voice (redundancy, §4). Do not strip feedback from a self-learner build: without a presenter, unexplained failure becomes confusion, not learning.

### The "teach" layer — only on request

If the user asks the artifact itself to teach, add a **look sequence** (ordered highlights, §5): "Look here → you see this. Now look there → you see that." Tie the final step to the learner's schema ("this is the same squaring you met in the cone lesson"). Keep it learner-driven: never autoplay through it before the prediction.

## 2. Schema: connect, then change

People understand new material by fitting it into what they already know: an existing **schema**. Bartlett (1932) showed recall bends towards existing schemas. Piaget described *assimilation* (fitting in) and *accommodation* (restructuring the schema). Rumelhart (1980) framed schemata as the building blocks of comprehension.

Design rules:
- **Name the starting schema.** Use the learner workspace (`LEARNER.md`, `LEARNING-PLAN.md`; see [learner-workspace.md](learner-workspace.md)). For a presenter, ask what the class has already covered. Record the source: "probed", "stated by teacher", or "assumed".
- **Name the schema change.** Say what the learner should believe afterwards that they did not believe before. A misconception is usually an over-applied schema ("bigger cause, proportionally bigger effect"). The figure should make that schema fail visibly, which is accommodation, not just add a fact.
- **Bridge from something known.** Start the figure from a familiar case: the default state, the first preset, or a reference already in the plan. Link explicitly to earlier lessons in `LESSONS.md` when they share a mechanism.
- **Missing prerequisites:** if the probe shows a prerequisite is absent, either add a short bridge step, or recommend the prerequisite point from the plan first. Do not silently build on air.

## 3. Scaffolding and fading

Scaffolding is temporary support that lets a learner do what they could not do alone. Wood, Bruner & Ross (1976) described the tutor's functions: recruiting interest, reducing degrees of freedom, marking critical features, controlling frustration, and demonstrating. Support is then withdrawn as competence grows: **fading**.

Design rules:
- Map each scaffold to a function. Focus guide → marking critical features. Locked controls and one variable at a time → reducing degrees of freedom. Feedback → controlling frustration. Worked step → demonstration.
- **Fade explicitly.** After the explanation, an independent-practice step hides or locks the supports: labels, readouts, plots, focus guide. The learner then answers new cases. State in the UI what was removed.
- **Restore on struggle.** After repeated misses, bring back one support or a worked solution, not everything.
- **Transfer is not fading.** A transfer question changes the situation or representation, not just the hints.

## 4. Cognitive load

Working memory is small. Cognitive load theory (Sweller, 1988; Sweller, van Merriënboer & Paas, 1998) distinguishes three kinds of load:
- **intrinsic**: the inherent complexity of the material, given what the learner already knows;
- **extraneous**: load caused by poor design;
- **germane**: effort spent building the schema.

Cut extraneous load, manage intrinsic load, and leave room for germane effort. Mayer's multimedia principles (Mayer, 2009/2021) turn this into layout rules.

Design rules:
- **One variable at a time** for the first comparison (intrinsic). Add more controls only after the first discovery.
- **Segment.** Steps the learner advances, not one long scroll (*segmenting principle*). The two-pane shell keeps the figure visible while the panel moves on.
- **Show only what the current step needs** (*coherence principle*). At the predict stage, hide readouts and parts that would give the answer away or that the prediction does not use. Reveal them as the steps advance (progressive disclosure).
- **Labels beside the parts they name**, not in a distant legend (*spatial contiguity*, avoiding *split attention*). A legend is acceptable when it sits next to the component and is linked (§6).
- **Do not narrate the screen in text when a presenter narrates it aloud** (*redundancy principle*). This is why presenter builds carry less copy.
- **Decorative motion and ornament are extraneous load.** Every moving thing should be a cause or an effect.
- **Expertise reversal** (Kalyuga, Ayres, Chandler & Sweller, 2003): supports that help novices can hinder learners who already know the material. Use the probe result: experienced learners get fewer steps, earlier fading, and more open exploration.

## 5. Attention and signaling

A large figure updates many things at once; a learner cannot attend to all of them. Mayer's *signaling principle*: cue what matters.

Design rules:
- **Focus plan per step.** For each panel step, list the figure parts the learner should look at. Mark them with `data-focus`, and the shell dims everything else (§8).
- **Predict stage shows only what the prediction needs**, plus the control the learner will use.
- **Ordered highlights** (`<ol class="look">`) for a sequence of observations: "1 · the radius doubles → 2 · now count the squares → 3 · the area went ×4". Use this when an insight needs looking at things *in order*, typically in the teach layer or the explanation step.
- **Colour codes meaning, consistently.** One accent for the focal part; the same colour for the same quantity across the figure, readouts and text. Never use colour as the only cue: pair it with a label, shape, or pattern.
- **Motion attracts attention.** Animate only the effect the learner should notice, and only after their action.
- **Presenter control:** in presenter builds the focus guide is a toggle the presenter drives, because the presenter's voice is the main signal.

## 6. Dual coding

Information encoded both verbally and visually is easier to retrieve (Paivio, 1971/1986). Mayer's *multimedia principle* is the design consequence: words and pictures together, linked.

Design rules:
- **Every named part has a word, and every key term has a part.** Build a dual-coding map: term → figure part id → readout.
- **Link them both ways.**
  - Hovering or focusing a term in the text (`data-ref`) highlights its part.
  - Hovering or focusing a part (`data-part`) highlights the matching terms and shows the part's label.
  - Keyboard focus must work as well as hover.
- **Legends sit next to their components** and use `data-ref`, so pointing at a legend item lights up the component.
- **Readouts carry units and a short "what this is" subline**, so the number and its meaning are coded together.

## 7. Prediction, retrieval, self-explanation, feedback

- **Predict first.** Committing to a prediction makes the result informative and exposes the misconception. Keep options short and include the misconception as an option.
- **Retrieval.** Independent practice and transfer questions ask the learner to produce an answer from memory, without the figure. This is retrieval practice, which supports retention better than re-reading (Roediger & Karpicke, 2006).
- **Self-explanation.** Prompting learners to explain why, in their own words, improves understanding (Chi, de Leeuw, Chiu & LaVancher, 1994). Use the writing frame, and ask "why", not "what".
- **Worked examples vs problem solving.** Novices benefit from studying worked examples before solving (the worked-example effect, Sweller & Cooper, 1985). Fade from worked to completion to independent. For experienced learners this reverses (§4).
- **Misconception-targeted feedback.** Map each plausible wrong answer to the misconception that produces it, and say so: "You multiplied the probability, not the odds." Correct/incorrect alone is weaker. Compute answer keys from the model, not by hand.

## 8. Shell attention API (examples/ lesson shell)

The shared lesson shell implements these hooks. Author them in the page; the shell does the rest.

| Hook | Where | Effect |
| --- | --- | --- |
| `data-part="id"` | Any element inside `#experiment` (SVG group, readout, legend) | Declares a nameable figure part. Optional `data-zh-label` / `data-en-label` give its label for tooltips. |
| `data-focus="id1 id2"` | A panel `.step` (or other panel element) | When that step is the learner's active step, the other parts dim behind a shadow overlay and the listed parts are emphasised. |
| Focus guide toggle | Added by the shell to the figure pane | Learner- or presenter-controllable; **on by default**. Turning it off removes all dimming. |
| `<ol class="look"><li data-focus="ids">…</li></ol>` | Panel | Rendered as numbered step buttons with Prev/Next; each step focuses its parts. Learner-driven, never autoplays; Esc clears. |
| `data-ref="id"` | Text terms, legend items | Hovering or focusing highlights part `id`. Hovering a part highlights its terms and shows its label tooltip. Non-interactive `[data-ref]` elements are made focusable by the shell. |

Rules:
- Dimming respects `prefers-reduced-motion`: there is no transition, only the stable state.
- Focus is a cue, not a lock. Dimmed parts stay operable and readable enough to stay in context.
- The accessible summary and readouts are never hidden by the focus guide.
- Keep part ids stable and semantic (`radius`, `slice-area`, `positives`), because the spec's focus plan and dual-coding map refer to them.
- At least one part must be in the static HTML (readouts are enough). The shell turns attention on only if `#experiment` already contains a `[data-part]` when it starts, before the lesson script draws. Parts drawn later still work.
- Don't nest parts. When a figure part is split by depth (for example an orbit drawn behind and in front of a globe), give both pieces the same id.
- Canvas or WebGL figures can't carry DOM parts. Make the viewport and readouts parts, and have the page itself redraw a highlight when a term is hovered (see `data-organ` in `examples/human-anatomy.html`). The redraw must not change lesson state or readouts.
- 3D views: turning the camera changes only the drawing, never the model or its readouts. Test this.

## 9. Spec checklist

Answer these in the design note, alongside the teaching spec in [teaching-and-spec.md](teaching-and-spec.md):

- [ ] **Audience:** presenter (teacher/parent) or self-learner; class or individual.
- [ ] **Prior knowledge:** assumed prerequisites, each with its source (probed / stated / assumed) and confidence.
- [ ] **Schema link:** the existing schema used, and the schema change the figure targets.
- [ ] **Load plan:** the first comparison's single variable, the steps (segments), and what is hidden at the predict stage.
- [ ] **Focus plan:** for each step, the `data-focus` part ids.
- [ ] **Look sequence** (teach layer only, if requested): an ordered list of "look at X → notice Y".
- [ ] **Dual-coding map:** term ↔ part id ↔ readout, and which legends are linked.
- [ ] **Scaffolds and fading:** each scaffold's function, when it is removed, and what restores it.
- [ ] **Feedback map:** each wrong option or answer → the misconception → the message.
- [ ] **Retrieval and transfer:** the independent practice cases and one transfer case in a new situation.
- [ ] **Workspace update:** which `LESSONS.md`, `LEARNER.md` and `LEARNING-PLAN.md` entries change after delivery.

## References

- Bartlett, F. C. (1932). *Remembering: A study in experimental and social psychology.* Cambridge University Press.
- Chi, M. T. H., de Leeuw, N., Chiu, M.-H., & LaVancher, C. (1994). Eliciting self-explanations improves understanding. *Cognitive Science, 18*(3), 439–477.
- Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise reversal effect. *Educational Psychologist, 38*(1), 23–31.
- Mayer, R. E. (2009; 3rd ed. 2021). *Multimedia learning.* Cambridge University Press.
- Paivio, A. (1971). *Imagery and verbal processes.* Holt, Rinehart & Winston; (1986). *Mental representations: A dual coding approach.* Oxford University Press.
- Piaget, J. (1952). *The origins of intelligence in children.* International Universities Press.
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning. *Psychological Science, 17*(3), 249–255.
- Rumelhart, D. E. (1980). Schemata: The building blocks of cognition. In R. J. Spiro, B. C. Bruce, & W. F. Brewer (Eds.), *Theoretical issues in reading comprehension* (pp. 33–58). Erlbaum.
- Sweller, J. (1988). Cognitive load during problem solving: Effects on learning. *Cognitive Science, 12*(2), 257–285.
- Sweller, J., & Cooper, G. A. (1985). The use of worked examples as a substitute for problem solving in learning algebra. *Cognition and Instruction, 2*(1), 59–89.
- Sweller, J., van Merriënboer, J. J. G., & Paas, F. G. W. C. (1998). Cognitive architecture and instructional design. *Educational Psychology Review, 10*(3), 251–296.
- Wood, D., Bruner, J. S., & Ross, G. (1976). The role of tutoring in problem solving. *Journal of Child Psychology and Psychiatry, 17*(2), 89–100.
