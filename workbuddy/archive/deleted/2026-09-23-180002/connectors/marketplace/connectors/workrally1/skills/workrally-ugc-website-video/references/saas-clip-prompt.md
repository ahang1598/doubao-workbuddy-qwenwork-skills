# SaaS clip prompt — ONE continuous talking-head shot (no board, no cuts, no Angle Lock)

Write the video prompt for a **single, continuous talking-head clip** of the creator speaking one
beat of the monologue to camera. There is **no storyboard**, **no intra-clip cut** and **no Angle
Lock** — one take, one framing, one continuous shot. The site and the product are added LATER in the
composite (real screenshot insets); they are **never rendered inside the clip**.

Write the prompt and the spoken line in **Simplified Chinese**; the English structure below is a
template, not the output language.

Submission (per SKILL.md 步骤 5) — the model comes from `canvas_video_provider_config`, picked for
`support_audio: true` plus a long-enough `max_video_duration`; never hardcode a provider ID:

```jsonc
canvas_generate_video({
  mode: "SubjectToVideo",                // 达人形象保持一致
  model: "<canvas_video_provider_config → support_audio:true 的 provider>",
  prompt: "<one-shot prompt>",
  count: 1,
  duration: <this clip's seconds>,
  aspect_ratio: "9:16",
  resolution: 4,                         // 1080P，取值须来自该 provider 的 resolution_options
  enable_sound: true,                    // 原生音轨 + 口型，不要另做 TTS
  reference_assets: [{ type: "image", url: "<达人形象URL>" }]
})
```

The physical-product closer appends the real product image as a second `reference_assets` entry
and refers to it as 「第二张图片」in the prompt. Submit one call per clip and poll each `task_id`
with `canvas_get_task` every 3-5s.

## Prompt structure (one shot)

Compose each clip prompt from these parts, in this order:

1. **Subject + identity** — the creator (seeded by the SAME `character_media_id` every clip; never
   re-describe a new person).
2. **Framing** — vertical **9:16**, **medium shot, creator ~2/3 of the frame, head CENTERED in the
   frame — horizontally AND vertically** (the head sits in the middle; no top headroom, do not push
   the head high). Eyeline into the lens (phone-camera / selfie energy). Hands kept out of the bottom
   ~15% (caption safe-zone).
3. **Setting** — the locked self-film scene (phone propped up, real home — couch / desk), natural
   light. The same setting in every clip.
4. **Action + delivery** — talking to camera, natural hand gestures; **自然口语普通话，不要播音腔 /
   配音腔** (or the accent the user named);
   **~4.5–5.5 汉字/秒 (natural, lively — never crammed) with the speed VARYING within the take**
   (quicker on connective lines, slower to land a number / price / CTA — never a flat, even read).
5. **Spoken line** — the beat's monologue segment, verbatim, in the script's language (Chinese by default).
6. **Audio** — recorded on the scene's **iPhone front-camera mic**; ambient = the **natural sound of
   what the scene shows** (living room / kitchen / café / office / outdoors — no preset), low under the
   voice; **no background music**.
7. **The two hard bans** (below) — include the relevant ban line in EVERY clip.

## Anti-slop

- **No AI-tells, no generic praise.** Ban `literally`, `obsessed`, `game-changer`, `holy grail`, `hits
  different` and corporate filler `elevate / seamless / effortless / synergy / leverage / unlock /
  supercharge / revolutionary`. Every claim carries one concrete (a number, a time, a named
  comparison) — praise without a concrete is cut.
- **Write spoken, not written** — contractions (`they're / it's / that's`), clipped conversational
  syntax, varied sentence length (see `saas-monologue.md`).
- **Phrase splitting (write fresh).** Break the beat into short spoken phrases the way a person
  actually talks: one idea per phrase, a natural micro-breath between phrases, the payload word
  (number / price / result) at the END of its phrase so the delivery can land on it. Keep phrases
  short enough to say in one breath; never run two ideas into one long clause.

## Bug D — the product appears ONLY at the end

Seedance renders whatever the visual description mentions. If a body clip's VISUAL mentions the
product with **no real input image**, the model **invents a fake product** (e.g. random sunglasses).

- **Body clips (every clip except the closer): the VISUAL description does NOT mention the product at
  all.** No object in the creator's hands, no "holding / wearing / opening / showing" anything. The
  creator only talks to camera. (The spoken line may reference the product; the VISUAL must not.)
- **The product is named or shown ONLY in the closer clip**, and there it arrives as a **real image fed
  as a second `image` media** — never described for the model to invent.

## Bug E — never render a website / UI

The site is shown ONLY as real screenshot overlays in the composite. Inside the generation it is
**never** rendered. In EVERY clip include an explicit ban:

> *No website, no web interface, no app UI, no screen / monitor / browser / rendered content on any
> phone or device screen anywhere in the shot.*

- Video models render UI text as gibberish — a generated "website" is always fake and off-brand.
- **SaaS / service closer:** the creator may act on a phone (pick it up, tap, gesture), but the
  **screen is turned away or blank — no rendered UI**. The real site never lives inside the clip.

## Pre-submit self-check (reject & rewrite before generating)

Verify EACH clip prompt; grep it and rewrite on any hit:

- `Hard cut`, `Cut 1`, `Cut 2`, `slot`, `board` → present ⇒ it is a board / multi-shot; rewrite to one
  continuous shot.
- The **product name** in a **body** clip's visual ⇒ remove it (Bug D) — product only in the closer.
- `website` / `UI` / `screen` / `browser` in ANY clip's visual ⇒ remove or convert to the Bug-E ban.
- Framing (2/3, head centered), 自然口语普通话（无播音腔）, varied ~4.5–5.5 汉字/秒 (lively, never
  crammed), phone-mic + scene ambient, no music — present in every clip.

Fail any check → rewrite before submitting.
