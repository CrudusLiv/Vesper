---
name: concept-wiki
description: After a lecture is summarized, extract CS concepts and create or update concept pages under concepts/. Call this after the lecture-summarizer skill, or when CrudusLiv asks to update the wiki from a lecture.
---

# Concept Wiki

Maintain a living wiki of CS concepts under `Dynamous/Memory/concepts/`. Called after the lecture-summarizer to cross-reference new material into persistent concept pages.

## When to invoke

- After the lecture-summarizer saves a new lecture note (step 8 of that skill)
- When CrudusLiv says "update the wiki", "index this lecture", or "add this to the concept wiki"

## Inputs

Path to the lecture note just created (e.g. `lectures/CS201/2026-06-10_sorting-algorithms.md`). All paths are relative to `Dynamous/Memory/`.

## Procedure

### 1. Read the lecture note

Extract:
- Frontmatter: `course`, `date`, `tags`
- **Key concepts** section bullets — primary concepts to index
- Any `[[wikilinks]]` already present in the note body

Combine tags + key concept bullets into a raw concept list. Deduplicate.

### 2. Derive slugs

For each concept, produce a slug: lowercase, hyphenated, no spaces, no punctuation.
Examples: `Dynamic Programming` → `dynamic-programming`, `Big-O Notation` → `big-o-notation`

Skip concepts that are too broad (`computer-science`, `programming`) or too granular (a variable name, a single library function).

### 3. For each concept — create or update

**If `Dynamous/Memory/concepts/<slug>.md` exists:**
- Read it
- Append a bullet to **Sources**: `- [[lectures/<course>/<lecture-slug>]] — <one-line context>`
- Increment `source_count` in frontmatter
- Update `last_updated` to today
- Save

**If it doesn't exist:**
- Create it using the template below
- Track the filename for the log entry

### 4. Update `concepts/index.md`

If the file doesn't exist yet, create it with the structure below.

For each newly created concept: add it under the correct category with a one-line description and `(1 source)`.
For each updated concept: increment the source count shown.
Update the `_Last updated:` line.

Category assignment: guess from concept name and tags. When unsure, use **Other**. Don't create a new category for a single concept.

### 5. Append to `concepts/log.md`

Use the log format below.

---

## Concept page template

```markdown
---
type: concept
tags: [<1-3 relevant tags inherited from the lecture>]
courses: [<course>]
source_count: 1
last_updated: <YYYY-MM-DD>
---

# <Concept Name>

> *Stub — extracted from [[lectures/<course>/<lecture-slug>]]*

## Key Properties

## Connected Concepts

## Sources
- [[lectures/<course>/<lecture-slug>]] — <one-line context from Key concepts>
```

Leave **Key Properties** and **Connected Concepts** empty — these get filled in over time, not on first creation.

---

## index.md structure

```markdown
# Concepts Index

_Last updated: YYYY-MM-DD_

## Algorithms
- [[dynamic-programming]] — overlapping subproblems, memoization/tabulation (2 sources)
- [[sorting]] — comparison-based and linear-time sorts (1 source)

## Data Structures
- [[trees]] — hierarchical structures, traversal patterns (1 source)

## Theory
- [[big-o-notation]] — asymptotic complexity analysis (3 sources)

## Other
- [[cache-locality]] — (1 source)
```

---

## log.md format

```
## [YYYY-MM-DD] ingest | <Lecture Title>
- Course: <course>
- Source: [[lectures/<course>/<lecture-filename-no-ext>]]
- Concepts touched: [[concept-1]], [[concept-2]], [[concept-3]]
- New pages created: concept-slug.md (or "none")
- Pages updated: concept-slug.md (1→2 sources), concept-slug-2.md (2→3 sources)
```

---

## Don't

- Don't fill in Key Properties or Connected Concepts during auto-creation — stubs only
- Don't modify lecture notes — read only
- Don't touch any files outside `Dynamous/Memory/concepts/` except reading lecture notes
- Don't delete concept pages, ever
- Don't create a concept page for things too broad (`programming`, `computer-science`) or too granular (a single variable or function name)
