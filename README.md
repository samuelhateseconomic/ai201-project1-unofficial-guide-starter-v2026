# The Unofficial Guide
Samuel Do - advice_threads
---

# Unit 1

## What This Does
I run the corpus advice_threads and ask "What do you wish you'd know in first year?" - Then, the answer will look like "That nobody is watching you as closely as you think, and you don't need to worry so much about looking like you know what you're doing....". At the same time, it will contain the resources that the answer came from which one of them should be `thread_first_year_regret.txt`.

## Chunking Strategy

**Chunk size:** one reply per chunk (not a character count).
**Overlap:** none — replies don't share text with each other.

I started with the default `fallback_split` (fixed 800 characters, 120
overlap). Every document in `advice_threads` is 318–794 characters, so that
setting never actually split anything — each whole thread became one chunk.
That's the bug behind the retrieval miss I noted above: a thread is not one
thought, it's 3–5 people giving different (sometimes contradictory) answers
to the question in the title. Embedding the whole thread as one chunk averages
those answers together, so a question that matches one specific reply well
gets diluted by the unrelated replies sitting in the same vector.

So I rewrote `split_documents` to split on the `--- reply N (votes) ---`
marker instead of a character count: one reply = one chunk. Each chunk is
prefixed with the thread's title line, because a reply on its own ("Talk to
the department adviser...") doesn't say what question it's answering — the
title is what makes the chunk self-contained. Vote counts are dropped from
the chunk text; they're a ranking signal for the humans in the thread, not
content I want the model treating as fact. Any document that doesn't contain
a reply marker falls back to the original fixed-size splitter, so the
function doesn't silently mishandle a document shaped differently than I
expect.

Result: 75 chunks (one per reply) instead of 23 (one per thread), averaging
175 characters, produced by `chunker.py::split_documents`.

## Sample Chunks


**Chunk 1** — source: `thread_bike_commute.txt#0` — produced by: `chunker.py::split_documents`

```
THREAD: Is a bike worth it for a 20 minute walk commute?

Yeah. Cuts an 18 minute walk to about 6. The thing nobody mentions is storage — covered bike parking exists at three buildings and is full by 9am at all three.
```

**Chunk 2** — source: `thread_first_gen.txt#1` — produced by: `chunker.py::split_documents`

```
THREAD: Anything specific for first-generation students?

The thing I'd say: the unwritten rules are the hard part, not the coursework. Ask about the unwritten rules explicitly. People are happy to explain them and nobody volunteers them.
```

**Chunk 3** — source: `thread_laptop_specs.txt#2` — produced by: `chunker.py::split_documents`

```
THREAD: How much laptop do I actually need for CS courses?

I did two years on an 8GB machine and it was fine until the last project, at which point it very much wasn't. 16 is the answer.
```

**Chunk 4** — source: `thread_parking.txt#1` — produced by: `chunker.py::split_documents`

```
THREAD: Worth getting a parking permit?

Street parking on Verrill is legal and free and unmarked, which is why half the upper years do it.
```

**Chunk 5** — source: `thread_sleep_schedule.txt#1` — produced by: `chunker.py::split_documents`

```
THREAD: Everyone says fix your sleep. Does it actually matter?

The library being open until 2am is a trap. It's a resource, not a schedule.
```

## Sample Answer

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:** What do you wish you'd known in first year?

**Answer:**

```
Based on the provided documents, people wish they had known:
* That nobody is watching you as closely as you think, and you don't need to worry so much about looking like you know whatyou're doing.
* That you can declare a course pass/fail late, up to week eight.
* That your adviser's job is partly to know exceptions to rules, so you should ask before assuming a deadline is fixed.
* That the add/drop deadline and the withdrawal deadline are different dates, and only one is on the common calendar.
* That the writing centre will read drafts for any course for free, and these appointments often go unbooked.
```

**A note on the retrieval behind this answer:** the five chunks retrieved for
this question all come from the same thread (`thread_first_year_regret.txt`),
but the distances spread from 0.2895 (closest) to 0.6364 (farthest):

```
0.2895  #3  "Honestly: that nobody is watching as closely as you think..."  (52 votes)
0.4442  #1  "That you can take a course pass/fail and declare it late..."
0.5372  #4  "That your adviser's job is partly to know the exceptions..."
0.5993  #0  "That the add/drop deadline and the withdrawal deadline are different..."
0.6364  #2  "That the writing centre will read a draft for any course..."
```

The closest match is also the most-upvoted reply, even though it shares
almost no vocabulary with the question ("Honestly: that nobody is watching..."
has no "wish," "known," or "first year" in it). It's phrased as the same kind
of reflective, in-hindsight confession the question is asking for, so the
embedding model matches on meaning rather than shared words — the other
replies are on-topic but phrased as flat factual tips, a different sentence
shape, so they land farther away despite being valid answers too. Vote counts
have no way to influence this, since I strip them out of the chunk text
before embedding — so the top-voted reply landing closest is the community's
judgment and the embedding's judgment agreeing independently.

**My relevance cutoff:**

| Question | In corpus? | Best distance |
|---|---|---|
| Anything specific for first-generation students? | Yes | 0.3365 |
| When should you actually use the pass/fail option? | Yes | 0.1859 |
| When should I start looking for a summer internship? | Yes | 0.1309 |
| What do you wish you'd known in first year? | Yes | 0.2895 |
| The best study spots that aren't the library? | Yes | 0.1890 |
| What is the capital of Mongolia? | No | 0.8990 |
| How do I change the oil in a diesel engine? | No | 0.9047 |
| Who won the 1994 World Cup? | No | 0.8982 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.8189 |
| How do I write a for loop in Rust? | No | 0.8606 |

In-corpus questions top out at 0.3365; out-of-scope questions bottom out at 0.8189 but in the question "What do you wish you'd known in first year?" there are three more answers are out of bound, which is 0.65. However, the answer itself is considered relevant even though the word itself might not. So, instead of in `config.py` currently sets `THRESHOLD = 0.7`, I would set it to `THRESHOLD = 0.55`, which sits comfortably inside that gap.

## How I Used AI

**1.** I asked Claude to check the size of each corpus so I could pick a chunk size and overlap that actually fit my documents. It came back with per-document stats showing every `advice_threads` document was 318–794 characters — under my `CHUNK_SIZE` of 800 — which meant `fallback_split` was never actually splitting anything; each whole thread was already one chunk. It first suggested splitting each reply out into its own chunk, but I pointed out that a bare reply on its own doesn't tell the agent what question it's answering, so we need the topic attached, not just the reply text on its own. It revised the design to prefix every reply chunk with the thread's title line before I had it write `split_thread`/`split_documents` in `chunker.py`. I also pushed back when it framed the fix as "tune chunk size" — I asked directly whether Milestone 3 was actually about changing the two config numbers rather than the function, and it pointed me to the docstring in `chunker.py` itself, which says to replace the function body, not the numbers.

**2.** For Milestone 4, I asked Claude to run my five `QUESTIONS` and five `OUT_OF_SCOPE` questions through retrieval and report the best distance for each, then asked where it would put the relevance cutoff and what I'd get wrong at that number. It came back with in-corpus distances topping out at 0.3365 and out-of-scope distances bottoming out at 0.8189, and recommended a cutoff near the middle of that gap (~0.55–0.6) rather than the starter's 0.7 default — explaining that 0.7 sits closer to the out-of-scope side and would be more likely to let a superficially similar out-of-scope question slip through, while a cutoff too low risks refusing a real question phrased awkwardly. I used that reasoning to set `THRESHOLD = 0.55` in `config.py` myself, rather than just accepting whatever number it suggested first.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

## Run Log — Before

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Every document gets chunked, none dropped | 75 chunks, 0 dropped | 75, 0 dropped | 75, 0 dropped | 75, 0 dropped | MET |
| 5. Threshold (0.55) holds for in-corpus questions | 5 of 5 pass the gate | 5/5 | 5/5 | 5/5 | MET |

Source data: `results/run_2026-09-26_2118.md`, produced by `run_eval.py::main` (top-k 5, cutoff 0.55, 3 runs, caching off).

### Criterion 1 — retrieved chunk contains the answer

Chunk retrieved for "When should you actually use the pass/fail option?",
source `corpora/advice_threads/documents/thread_pass_fail.txt`, chunked by
`chunker.py::split_documents` as `thread_pass_fail.txt#1`:

```
THREAD: When should you actually use the pass/fail option?

The part that isn't advertised: you can declare it as late as week eight. So take the midterm first, then decide.
```

Generated answer, run 2, produced by `generate.py::answer_from_chunks`:

```
Based on the provided documents, you should use the pass/fail option for a course outside your major that you are taking out of curiosity. You can also take the midterm first and then decide whether to use the option, as you can declare it as late as week eight (thread_pass_fail.txt, thread_first_year_regret.txt).
```

### Criterion 2 — every answer names a source

Run 1, produced by `generate.py::answer_from_chunks`:

```
You should start looking earlier than feels reasonable, as large employers close applications in October and November for the following summer. Smaller and local places hire in February and March. 

Source: thread_internship_timing.txt
```

### Criterion 3 — gate stops out-of-corpus questions

Produced by `run_eval.py::check_out_of_scope`, cutoff 0.55, from
`results/run_2026-09-26_2118.md`:

| Out-of-scope question | Best distance | Gate |
|---|---|---|
| What is the capital of Mongolia? | 0.899 | refused |
| How do I change the oil in a diesel engine? | 0.905 | refused |
| Who won the 1994 World Cup? | 0.898 | refused |
| What is the recommended dosage of ibuprofen for a headache? | 0.819 | refused |
| How do I write a for loop in Rust? | 0.861 | refused |

### Criterion 4 — every document gets chunked, none dropped

`python app.py chunks`, produced by `chunker.py::split_documents`:

```
75 chunks total. Showing 5, spread across the corpus.
```

Checked separately for zero-chunk documents, `ingest.py::load_documents` +
`chunker.py::split_documents`:

```
total docs: 23
total chunks: 75
docs with zero chunks: []
num docs represented: 23 of 23
```

### Criterion 5 — threshold holds for in-corpus questions

Best distances per question, all under the 0.55 cutoff, produced by
`gate.py::check` via `store.py::search` (identical across all 3 runs since
retrieval is deterministic):

| Question | Best distance | Gate |
|---|---|---|
| Anything specific for first-generation students? | 0.3365 | passed |
| When should you actually use the pass/fail option? | 0.1859 | passed |
| When should I start looking for a summer internship? | 0.1309 | passed |
| What do you wish you'd known in first year? | 0.2895 | passed |
| The best study spots that aren't the library? | 0.1890 | passed |

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer (target: 5 of 5) | MET | 5/5, 5/5, 5/5 — held in all three runs, not just one. Retrieval is deterministic, so I didn't rely on the generated answer (which paraphrases); I checked each `expects` string against the actual source document and confirmed it's a verbatim line in the reply the system cites, e.g. `thread_pass_fail.txt` reply 2 matches `expects` for that question word-for-word. |
| 2 | Every answer names a source (target: 5 of 5) | MET | 5/5, 5/5, 5/5 — read all 15 generated answers (5 questions × 3 runs) by hand; every one names at least one source file. Not close. |
| 3 | Gate stops out-of-corpus questions (target: 4 of 5) | MET | 5/5 refused, one deterministic pass. Comfortably clears the target — out-of-scope distances (0.819–0.905) never came near the 0.55 cutoff, so there's no run-to-run variance to worry about here. |
| 4 | Every document gets chunked, none dropped (target: exactly 75 chunks, 0 documents at 0 chunks) | MET | Ran `python app.py chunks` (75 chunks total) and a direct doc-coverage check against `ingest.py::load_documents` + `chunker.py::split_documents`: 23 of 23 documents represented, none at zero. Deterministic, so one check is the whole measurement. |
| 5 | Threshold (0.55) holds for in-corpus questions | MET | 5/5, 5/5, 5/5 passed the gate. Best distances (0.1309–0.3365) held well under 0.55 in every run — the closest in-corpus question (first-gen, 0.3365) still isn't near the cutoff, so this wasn't a close call. |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

**Missed nothing.** All five criteria cleared in every one of the three
runs (5/5, 5/5, 5/5 on the four count-based ones; 75 chunks / 0 dropped,
checked once, on the fifth). No stage — loading, chunking, embedding,
retrieval, generation — produced a failure to trace.

That's a sign at least two of my targets were set safe rather than hard,
not that the pipeline is bulletproof:

- **Criterion 3 (gate stops out-of-corpus questions)** is the loosest one.
  My `OUT_OF_SCOPE` list (capital of Mongolia, oil changes, the 1994 World
  Cup, ibuprofen dosage, a Rust for-loop) is five completely different
  worlds from `advice_threads`, so the embedding gap is huge — the closest
  any of them got was 0.819, versus my worst in-corpus question at 0.3365
  and a cutoff at 0.55. A margin of 0.27 either side of the cutoff means
  I've never actually tested the gate near its boundary. **I'd tighten
  this to 5 of 5** and swap in adversarial questions that are topically
  *adjacent* to the corpus instead — e.g. "What's the best dining hall on
  campus?" (plausible student question, no thread answers it) or "Is it
  worth living off-campus?" (same shape as my real questions, not in the
  corpus) — so the gate is judged on questions that could plausibly embed
  close to a real thread, not on trivia from an unrelated domain.

- **Criterion 1 (retrieved chunks contain the answer)** looks strong at
  5/5, but the mechanism that makes it easy is the corpus size, not
  precision: each thread only has 3–5 replies, `top_k` is 5, and most of
  my five questions retrieve chunks almost entirely from a single thread
  (`thread_first_year_regret.txt` contributes all 5 of its replies to one
  question's top-5). With a thread that short, "the answer is somewhere
  in the top 5" is close to guaranteed by the corpus shape, not something
  retrieval had to work for. **I'd tighten this to "in the top 3"** —
  closer to the actual precision the retrieval step is providing — before
  trusting 5/5 as evidence the embedding step is doing real work.

Criteria 2, 4, and 5 don't have the same slack: criterion 2 has no room to
loosen further (every answer either names a source or it doesn't), and
criterion 4's target is an exact count with zero tolerance already.

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
