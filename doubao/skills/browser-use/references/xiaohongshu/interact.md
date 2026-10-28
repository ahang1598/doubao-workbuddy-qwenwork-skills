# Xiaohongshu account interactions

Use this workflow for likes, favorites, follows, comments, and replies.

1. Resolve the exact note, account, or comment. Use a direct link when available; otherwise verify title, author, visible content, and page context. Do not guess among similar targets.
2. Read [../action-verification.md](../action-verification.md). Inspect the current like, favorite, or follow state before clicking so an already-active toggle is not reversed.
3. For comments or replies, confirm the exact text and ensure the input is attached to the intended note or comment. A reply must use the comment-level reply control, not the note-level comment field.
4. When user authorization or personal control is required, call `interaction.request_action` with `type="browserControl"`. Name the target, exact action, and prepared text when applicable.
5. After control returns or the action completes, re-observe the page and verify the state, visible comment/reply, or other authoritative signal.

For batches, process a bounded number sequentially, keep per-target results, avoid high-frequency repetitive activity, and stop immediately if focus moves to the wrong input, the layout changes, or anti-abuse controls appear.
