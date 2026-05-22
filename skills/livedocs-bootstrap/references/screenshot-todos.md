# Screenshot TODOs

## Why
The agent can't take screenshots. But it CAN identify the moments where a
screenshot would help the reader, and structure the TODO so a human can
quickly capture them later.

## Format inside the .md (product flavor only)

Inserted immediately AFTER the paragraph mentioning the screen, in an
admonition block. The example below is illustrative — the surrounding
prose and the field labels (`Route:`, `Description:`, etc.) render in
`{lang}`. The admonition token `[!TODO:screenshot]` stays as-is —
it's a parser token, not prose.

```markdown
<prose paragraph that mentions a UI surface, in {lang}>

> [!TODO:screenshot]
> Route: `/pre-projects`
> Description: Full Kanban board view, with at least 3 columns and 5+
> cards spread across them to illustrate normal usage.
```

## Format in state.md

Each TODO is also registered in state for programmatic listing:

```markdown
## Screenshot TODOs (open: 12)

- [open] `project-management/overview.md` — `/projects` — "Kanban view"
- [open] `project-management/create-project.md` — `/projects/new` — "Wizard step 1"
```

The `[open]` / `[captured]` / `[dropped]` status tokens stay in English
(they are state contracts). The trailing description is in `{lang}`.

## Rules

1. **One screenshot, one TODO.** If a paragraph references 3 screens, write
   3 TODOs. Don't bundle.

2. **Be GENEROUS.** Product guides should have many screenshots — every UI
   surface mentioned in prose is a candidate. The rule of thumb is
   "1 screenshot every 2-4 paragraphs" in the operational sections.
   When in doubt, write the TODO. A reviewer can drop it later; a missing
   one is invisible.

   Specifically, ALWAYS write a TODO when the prose mentions:
   - a concrete route (`/path`)
   - a sidebar, panel, drawer, modal, dialog, or tab
   - a button or action with a name (in `{lang}`)
   - a list, grid, kanban column, or chart
   - an empty state, success state, or error state worth showing
   - a step inside a wizard or multi-step flow
   - a settings section reachable from a named menu item

3. **Identify the surface as precisely as you can.** A route is best, but a
   named surface inside a route is also fine. Use the `Location:` field
   (rendered in `{lang}`) for non-route surfaces:

   ```markdown
   > [!TODO:screenshot]
   > Location: project sidebar → "Partners and splits" section
   > Base route: `/project/:project`
   > Description: <what this surface shows, in {lang}>
   ```

   Only OMIT the TODO when you genuinely don't know where the surface
   lives (e.g. "somewhere in settings" with no anchor at all). In that
   case, register a pending question instead asking the user where it is.

4. **`.md` only, never `.tech.md`.** Product guides need screenshots;
   tech guides have file:line references instead.

5. **Description guides the capturer.** Don't write something as vague
   as "the dashboard screen" — write "Dashboard right after login, with
   at least 1 project registered and 3 pending tasks". The more context,
   the better the screenshot.

6. **Status field stays simple:** `open` (default) | `captured` | `dropped`.
   Captured = human attached image. Dropped = route no longer relevant.

## When the user captures (future)

The user has two options to mark a TODO as captured:

a) Edit `.livedocs/state.md` directly, change `[open]` to `[captured]`.
b) Save the image at `.livedocs/screenshots/<cap-slug>/<article-slug>__<num>.png`
   and re-invoke the skill — it scans the dir, matches by article, marks
   captured automatically.

(Option b not implemented in v1 — manual marking only.)

## Anti-pattern

DON'T write:
```markdown
> [!TODO:screenshot]
> Route: (the settings page)
> Description: (a nice screen of the product)
```

That's noise. Either you have a concrete route → write it precisely; OR
you don't → omit the TODO entirely.
