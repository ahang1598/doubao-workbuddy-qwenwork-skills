# LaTeX templates for revision correspondence

Use this file when the user asks for a LaTeX cover letter, LaTeX response-to-reviewers
letter, rebuttal `.tex`, red-marked revised manuscript, or a complete revision
package in LaTeX.

## Templates

| Template | Use for |
|---|---|
| `templates/cover-letter.tex` | Editor-facing revision cover letter |
| `templates/response-to-reviewers.tex` | Point-by-point response to editor/reviewer comments |
| `templates/revised-manuscript-redline.tex` | Backed-up manuscript copy with changed text marked in red |

## Filling rules

1. Copy the relevant template content and replace placeholders only when the user
   supplied the fact.
2. Keep visible placeholders such as `Manuscript ID to be supplied` for unknown
   manuscript ID, editor name, author list, line numbers, figure panels, dates,
   or unresolved manuscript changes.
3. Escape LaTeX-sensitive characters in user content: `&`, `%`, `$`, `#`, `_`,
   `{`, `}`, `~`, `^`, and backslash.
4. Keep reviewer comments faithful. If comments are long, preserve the quoted
   comment in the response document and summarize only in tracker tables.
5. Use `\ReviewerComment{...}` and `\AuthorResponse{...}` blocks in the response
   template for each numbered item.
6. After answering a reviewer comment, put any pasted revised manuscript text in
   `\RevisedExcerpt{...}` so it appears in italics.
7. Start each new reviewer block on a new page. In the response template, use
   `\ReviewerSection{1}`, `\ReviewerSection{2}`, etc. when switching reviewers.
8. When editing manuscript text, work on a backup/copy of the original manuscript
   and wrap changed text in `\revised{...}` so it appears in red.
9. Do not move unresolved issues into LaTeX comments; they must remain visible in
   the compiled document.

## Output options

- If the user asks for files, create filled `.tex` files based on the templates.
- If the user asks only for a template, return the template path and summarize
  what placeholders need to be filled.
- If the user asks for cover letter, response, and marked manuscript together,
  use all relevant templates and keep manuscript metadata synchronized.

## QA before delivery

- No invented manuscript ID, editor name, line numbers, figure panels, data
  values, or author facts.
- Every reviewer comment ID in the tracker appears in the response text.
- The cover letter summarizes the revision but does not replace the detailed
  point-by-point response.
- Revised manuscript excerpts pasted in the response letter are italic.
- Each new reviewer response starts on a new page in LaTeX/print-oriented outputs.
- Manuscript changes in the backed-up manuscript copy are marked in red.
- LaTeX-sensitive characters from user-provided text are escaped.
- If LaTeX compilation is available, compile once and report any errors.
