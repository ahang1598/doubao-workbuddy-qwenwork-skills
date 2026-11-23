# Teaching contract and model mapping

## A reusable spec

Follow the host's actual types. In a standalone figure this is a useful conceptual shape, not a new mandatory app schema:

```js
{
  id: "gear-ratio",
  anchor: "A smaller driving gear makes a larger driven gear turn more slowly.",
  title: "What changes when the driven gear gets larger?",
  lead: "Change the driven gear's tooth count, then turn the crank.",
  predict: [
    "The driven gear turns faster.",
    "The driven gear turns more slowly.",
    "Both gears always turn at the same speed."
  ],
  answer: 1,
  config: { driverTeeth: 12, drivenTeeth: 24, inputTurns: 1 },
  insight: "More driven teeth require more input rotation for one output turn.",
  caveat: "Ideal external gears; backlash and friction are omitted.",
  frame: "When the driven gear has ___ teeth, one input turn produces ___ output turns."
}
```

Learning-design fields (audience, prior knowledge and its source, schema link, focus plan, look sequence, dual-coding map, scaffolds and fading, feedback map) live in the design note beside this spec. See the checklist in [learning-design.md](learning-design.md) §9. Like the mechanical plan, they are author decisions, not new fields in a host schema.

Use the lesson's own numbers and scenario where available. `answer` is a zero-based index into the options in this example. A host may group options and answer differently; adapt to its real contract. Learner-facing copy uses every language the product ships; studied prompts, tokens and outputs stay in the study language.

Prediction is about a result learners can inspect. If movement alone is ambiguous, add a counter, paired plot, trace, before/after state, or highlighted contact. Reveal feedback after a meaningful try; a wrong prediction should trigger observation, not immediate correction that removes the experiment.

Define that try in a design note, such as completing one input turn and reading the output counter. State it in the UI so the learner knows what remains. Respect the host's existing reveal behavior rather than silently adding a lock.

Record two causal facts a satisfactory explanation must contain, a plausible incorrect explanation, and one new scenario to predict without the controls. These are author checks, not new required schema fields or an automatic grading system. For an idler gear, distinguish ratio magnitude from rotation direction and ask what changes when the final gear has more teeth.

## Truth model

Prefer a small pure module with `initialState`, `applyAction`, `step(dt)` when time matters, and `derive(state)`. Reuse an existing model if it already has these responsibilities. Model units and input bounds are explicit. Clamp invalid input and reject impossible states without manufacturing a plausible-looking result.

The same derived result feeds the picture, numerical readout, accessible summary and explanation. Keep display easing separate: a spring can soften a knob's movement, but it must not invent extra simulated energy or change a queue's semantic order. For stochastic lessons, use a seed/resettable generator and explain sampling uncertainty; layout is deterministic.

For stochastic comparisons, keep the underlying scores, prompt, and other settings fixed. Show expected probabilities separately from sampled counts. State the observable claim before collecting evidence and avoid treating one lucky batch as proof. Sampling temperature changes selection probabilities; it does not make scores into truth labels. Include a counterexample when a learner could replace the original misconception with another universal claim.

Label three different kinds of numbers correctly:

- Source facts: cited dimensions, specifications or measured data.
- Calculations: results of the stated equation or algorithm, with units and assumptions.
- Illustrative parameters: chosen for teaching and marked as such.

## Concept-to-object mapping

| Lesson | Possible object | Model behavior | Observation that challenges a misconception |
|---|---|---|---|
| LRU cache | Four-slot card rack | Hit moves a card to most-recent; full miss evicts least-recent | Frequently accessed older cards survive; insertion age alone does not decide eviction |
| Queue backpressure | Hopper, gate, output tray | Arrival rate, service rate, finite capacity | Faster arrivals grow backlog or rejected count rather than making the gate work faster |
| External gear ratio | Crank, two wheels, turn counters | `outputTurns = -inputTurns * driverTeeth / drivenTeeth` | A larger driven wheel turns less; the negative sign shows opposite rotation |
| Spring displacement | Probe, spring, gauge | In a static ideal linear regime, `x = F / k` | The same load compresses the stiffer spring less |
| Assembly constraint | Shaft, bearing, keyed hub | Fit or engagement depends on alignment and assembly order | A keyed hub cannot seat until the key and keyway align |

These are candidates, not required metaphors. Choose the actual object when the lesson concerns a real mechanism. A software analogy must explain what corresponds to the algorithm and what is only visual framing. Do not imply an LLM contains gears or that a mechanical toy reproduces its internals.

## State and view

Separate semantic state from view state:

- Semantic: cache entries, teeth counts, forces, joint limits, valve state.
- View: camera angle, selected part, cutaway visibility, exploded fraction, annotations.

Changing a view must not secretly change the answer. Exploding an assembly exposes its structure but does not run the machine in a physically disconnected state. Pause the mechanism while apart, or explicitly mark apart as an inspection display of coupled state.

For structure-only requests, pose a spatial or assembly prediction such as which surface becomes visible or which part blocks insertion. Requests mainly for a static figure are outside this skill's scope; redirect to an illustration approach rather than forcing an interactive app on the request.

## Language bridge

Use a short cause/effect frame in the user's study language. English examples: “When ___ increases, ___ decreases because ___.” or “This part prevents ___ by ___.” Outside language-learning products, a concise explanation prompt is sufficient; a compulsory English exercise is not a universal requirement.
