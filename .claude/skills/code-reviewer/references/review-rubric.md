# Code Review Rubric (degree-level CS assignments)

> Loaded on demand by the code-reviewer skill. Reference card, not exhaustive.

## Correctness checklist

- [ ] Function does what its name claims.
- [ ] Return type matches signature / docstring.
- [ ] No off-by-one in loops, ranges, slicing, indexing.
- [ ] No unhandled `None` / null returns.
- [ ] No silent exception swallowing (`except: pass`, `catch (Exception) {}`).
- [ ] No mutable default arguments in Python (`def f(x=[])`).
- [ ] Floating-point compares use a tolerance, not `==`.
- [ ] Loops actually terminate. Recursion has a base case.
- [ ] Resources are closed (`with` blocks, `try/finally`, RAII).
- [ ] No use-after-free / dangling pointers (C/C++).

## Edge cases checklist

- Empty input (empty string, empty list, empty file).
- Single-element input.
- Maximum-size input — memory? time? stack depth?
- Negative numbers, zero, very large numbers, `NaN`, `inf`.
- Unicode and combining characters in strings.
- Concurrent calls if state is shared.
- File not found / permission denied / disk full.
- Network call timeout / 5xx / DNS failure.
- Off-by-one at array bounds.

## Algorithmic complexity

- Identify nested loops over the same data → flag if quadratic where linear is possible.
- Hash lookups (`O(1)`) vs list scans (`O(n)`).
- Sort-then-scan vs hash dedupe.
- Recursive calls without memoization on overlapping subproblems.
- Repeated string concatenation in a loop (Python: use `"".join(parts)`; Java: `StringBuilder`).

## Style (light touch — degree-level)

- Function names: verbs (`compute_total`). Variable names: nouns (`total_price`).
- If the function doesn't fit on one screen, consider splitting.
- Comments explain **why**, not **what**. Code already shows what.
- Magic numbers → named constants.
- Single responsibility: one function, one job.
- Consistent indentation, consistent quote style, consistent naming convention within a file.

## Tone for written feedback

- **Direct.** "This is wrong because X" beats "you might want to consider X".
- **Cite filename:line** for every finding — CrudusLiv jumps straight there.
- **Three levels:**
  - **bug** — definitely wrong, will fail on some input.
  - **smell** — probably fine, worth a second look.
  - **nit** — style or readability, optional.
- **If the code is good, say so.** Empty findings sections are fine — better than padding with non-issues.

## What NOT to flag

- Choices that are different from how you'd do it but still correct.
- Style nits the user is consistent on (their convention, not a violation).
- Performance concerns that don't matter at coursework input sizes (don't suggest a hash map for a list of 5 items).
- Anything outside the diff. Reviewing untouched code is scope creep.
