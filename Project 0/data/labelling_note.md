# Labelling Note — data/items.jsonl

## Where the data came from
- **Schema & seed data**: hand-written for this project (`data/schema.sql`, `data/seed.sql`), an online-bookstore domain with 5 tables (`authors`, `books`, `customers`, `orders`, `order_items`) chosen to support filters, joins across 2–3 tables, GROUP BY / HAVING, ORDER BY / LIMIT, and aggregates.
- **Questions**: hand-written against the seeded data, not pulled from a public dataset. Each question was written to require a specific SQL feature (see `category` field per item) so the 50-item set covers a spread of difficulty, not just simple `WHERE` filters.
- **Reference SQL + expected result**: for each question, the reference SQL was written first, then executed against `data/bookstore.db` to confirm it runs and returns a sensible, non-trivial result (not empty, not the whole table). `score.py` re-executes the reference SQL at scoring time rather than storing a hardcoded expected result, so the "expected answer" can never drift from the live seed data.

## How correctness was verified
Two people independently:
1. Read the natural-language question and wrote down what they believe the correct SQL logic is (without looking at the stored reference SQL).
2. Ran their own version against `data/bookstore.db` and compared the result to the stored reference SQL's result.
3. Any mismatch is a sign the question is ambiguous (e.g. "top books" without specifying by what metric) and was rewritten.

Only items where both reviewers agree are included in the final `items.jsonl`.

## Dev / test split
- `data/items.jsonl` currently has 10 starter items (`q001`–`q010`), covering: filter+order, aggregate, group_by, join+having, join+aggregate, join+group_by+limit, join+distinct, join+order+limit.
- Target: 50+ items total. Plan is roughly 40 test items (frozen, used only for final scoring) + 10 dev items (used while iterating on the prompt, never included in the reported accuracy number).
- TODO before freeze: expand to 50+, tag each item with `split: "dev"` or `split: "test"`, and re-run the two-person check on the full set.

## Known limitations
- The seed data is small (20 books, 15 orders) by design — just enough that a wrong query returns a visibly different result from the correct one, not a realistic production volume.
- Questions assume a single correct SQL *result*, not a single correct SQL *string* — `score.py` compares executed result sets, so differently-written-but-equivalent queries both score as correct.
