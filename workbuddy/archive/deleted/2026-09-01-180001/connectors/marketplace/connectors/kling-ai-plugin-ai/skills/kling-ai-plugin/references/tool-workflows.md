# Remote tool workflow

1. Read `tools/list` from remote `kling-ai-plugin` at `https://kling.ai/mcp`. Before generation, call `who_am_i` and use only the target model's declared arguments, defaults, allowed values, and media inputs.
2. For attached media, call the remote upload tool and pass its returned reference to the generation request.
3. Once materially missing inputs are resolved, call the selected remote generation tool once with `{model, arguments[], inputs[], rationale, taskTraceId}` and preserve its `generationId`. Reuse one UUIDv7 `taskTraceId` throughout the objective. Do not add a credit warning or separate confirmation step.
4. If submission is not terminal, poll with the status tool declared by the live schema at provider-allowed intervals until success or failure. On user cancellation or current-turn timeout, return the state and task number.
5. Present the returned image, video, text, or one primary output link when complete.

Never retry a generation automatically.
