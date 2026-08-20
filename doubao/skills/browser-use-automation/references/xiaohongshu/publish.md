# Xiaohongshu drafting and publishing

Use this workflow to create a note draft, fill the publishing UI, and publish after user handoff.

## Prepare the content

1. Establish the audience, purpose, factual source material, tone, prohibited claims, and desired media.
2. Build an original structure around concrete value: conclusion and audience, steps or comparison, limitations or pitfalls, and a useful next action.
3. Summarize and transform source notes; do not reproduce another creator's wording or images without permission.
4. Prepare title, body, topics/tags, mentions, location, media order, and visibility as distinct fields. Avoid medicalized, absolute, or unsupported promotional claims.

## Fill and review

1. Open the correct account's publishing page and observe the current mode and fields.
2. If the user must select local images or video, call `interaction.request_action` with `type="fileUpload"`. Ask them to upload the intended files and return control after the previews appear.
3. Re-observe and verify the media count and order. Fill title, body, topics/tags, mentions, location, and visibility using fresh refs.
4. Review the complete preview for truncation, duplicated text, wrong account, wrong media, missing attribution, or unintended visibility.

## Publish

Before the final publish control, call `interaction.request_action` with `type="browserControl"`. The message must identify the account, summarize the note, mention visibility, and ask the user to review and publish or return control without publishing.

After control returns, take a fresh observation. Report success only if the site shows an authoritative published state; capture the direct note link when available. A filled editor or disabled publish button is not proof of publication.
