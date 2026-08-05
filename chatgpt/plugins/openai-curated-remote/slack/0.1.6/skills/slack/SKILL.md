---
name: slack
description: Read Slack context, route to the right Slack workflow, prepare or perform Slack writes that match the user's intent, summarize channel activity, create daily digests, triage recent activity, and draft replies from available context.
---

# Slack

- If the user explicitly asks to send, post, reply, share, or create something in Slack, follow that write intent directly. Do not downgrade the request into a draft unless the user asked for a draft or review-first flow.
- Confirm the requested action is supported. Before acting on “last,” “latest,” “above,” or another relative message target, re-read the destination and resolve it from fresh results. Treat `@channel`, `@here`, mass mentions, and customer-facing destinations as high impact and call them out before posting.
- If a Slack tool returns a 429, do not retry immediately and do not switch to an equivalent tool in the same bucket. If the response includes `Retry-After` or another explicit wait hint, follow it. Otherwise wait about 30 seconds before calling that bucket again.
- If the same bucket returns another 429 during the task, wait about 1 minute before the next retry, then about 2 minutes after the next 429, continuing with exponential backoff as needed.
- When the same message is meant for multiple specific people, first look for an existing group DM with the right people and prefer that over duplicate one-to-one DMs.
- If `slack_send_message_draft` returns `draft_already_exists`, stop immediately. Tell the user there is already an attached draft in that destination and that Slack cannot overwrite it.
- Resolve the current user with `slack_read_user_profile` before any search query containing `<@USER_ID>`, then substitute the returned Slack user ID.
- unanswered direct conversations: run `slack_search_public_and_private` over `channel_types="im"`, paging until you have a reasonable set of unique conversations, then dedupe and expand promising DMs with `slack_read_channel`
- unanswered group DMs: repeat over `channel_types="mpim"`, again preferring unique conversations over repeated hits from one chat
- threads with prior user participation: `slack_search_public_and_private` with `query` set to `from:<@USER_ID> is:thread`, then `slack_read_thread`
- threads with prior user mention: `slack_search_public_and_private` with `query` set to `<@USER_ID> is:thread`, then `slack_read_thread`
- If no source scope was provided, default to searching:
  - unanswered direct conversations
  - unanswered group DMs
  - direct mentions
  - threads with prior user participation and newer replies
  - threads with prior user mention and newer replies
- named channel: `slack_search_channels`, then `slack_read_channel`
- direct mentions: `slack_search_public_and_private` with `query` set to `<@USER_ID>`
- Keep only candidates where the latest unresolved ask is from someone else, or where newer replies appeared after the user's last substantive reply or mention. Do not count emoji-only, acknowledgement-only, or other non-answer chatter from the user as a reply.
- Prioritize messages that likely need a reply or could create a concrete follow-up or task for the user. Explicit asks, review or approval requests, blockers, and bumps should rank above casual questions, FYIs, or repeated snippets from the same conversation.
- Resolve the user's timezone with `slack_read_user_profile` when a relative-time window needs it, reusing the current-user profile when available. For "today," use local start-of-day through now and state that window in the digest.
- Use user-group mention syntax only when the runtime can actually resolve the group.
