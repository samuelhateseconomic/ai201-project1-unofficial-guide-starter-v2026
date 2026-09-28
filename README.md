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
     Add more tests.
     Add extra layers that can replace the gemini model if it runs over usage. 
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

## Run Log — Before

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 15 of 15 | 15/15 | 15/15 | 15/15 | MET |
| 2. Every answer names a source | 15 of 15 | 15/15 | 15/15 | 15/15 | MET |
| 3. Gate stops out-of-corpus questions (adjacent set, revised in unit 2) | 4 of 5 | 0/5 | 0/5 | 0/5 | **MISSED** |
| 4. Every document gets chunked, none dropped | 75 chunks, 0 dropped | 75, 0 dropped | 75, 0 dropped | 75, 0 dropped | MET |
| 5. Threshold (0.55) holds for in-corpus questions | 15 of 15 pass the gate | 15/15 | 15/15 | 15/15 | MET |

Source data, all produced by `run_eval.py::main` (top-k 5, cutoff 0.55, 3
runs, caching off):

- `results/run_2026-09-26_2118.md` — the original 5 questions, unit-1
  `OUT_OF_SCOPE` set (trivia). Gate: 5/5 refused.
- `results/run_2026-09-27_1957_before.md` — expanded to 15 questions, same
  trivia set. Gate: 5/5 refused.
- `results/run_2026-09-27_2020_before.md` — 15 questions, `OUT_OF_SCOPE`
  swapped for five topically-adjacent questions (see criterion 3's unit-2
  revision in `criteria.md`). Gate: **0/5 refused.** This is the row above.

Criterion 3 is deterministic — one pass is the whole measurement — so the
same number sits in all three run columns. Against the trivia set the gate
was 5/5; the 0/5 is what it does against questions that actually sit near
the cutoff. Diagnoses below says why the 5/5 was hollow.

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

Run 2 of a question added in unit 2, same function:

```
Whether professors answer email varies enormously. A general rule is that if the syllabus states a response window, it is honored; otherwise, you should assume a 48-hour response time (thread_professor_email.txt).
```

### Criterion 3 — gate stops out-of-corpus questions

Produced by `run_eval.py::check_out_of_scope`, cutoff 0.55, from
`results/run_2026-09-27_2020_before.md` (the revised, adjacent set):

| Out-of-scope question | Best distance | Gate |
|---|---|---|
| What's the best dining hall on campus? | 0.528 | **let through** |
| Is it worth living off-campus in second year? | 0.513 | **let through** |
| Which gym membership tier should I get? | 0.526 | **let through** |
| Where can I get my bike repaired near campus? | 0.533 | **let through** |
| How much does the shuttle to downtown cost? | 0.537 | **let through** |

What the system actually said once the gate let one through — `python app.py
ask "What's the best dining hall on campus?" --threshold 0.55`, answer
produced by `generate.py::answer_from_chunks`:

```
  (best distance 0.528, cutoff 0.55)

I don't have enough information to answer your question, as the provided documents do not mention dining halls. (Source: thread_study_spots.txt and thread_meal_plan_tier.txt)

Sources retrieved: thread_meal_plan_tier.txt, thread_study_spots.txt

1 model calls this session, 408 tokens (365 in, 43 out)
```

Same question at the unit-1 trivia set's level of difficulty, for contrast —
`results/run_2026-09-27_1957_before.md`, same function:

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
retrieval is deterministic), from `results/run_2026-09-27_1957_before.md`:

| Question | Best distance | Gate |
|---|---|---|
| Anything specific for first-generation students? | 0.3365 | passed |
| When should you actually use the pass/fail option? | 0.1859 | passed |
| When should I start looking for a summer internship? | 0.1309 | passed |
| What do you wish you'd known in first year? | 0.2895 | passed |
| The best study spots that aren't the library? | 0.1890 | passed |
| When is laundry actually free in the dorms? | 0.1505 | passed |
| Is it weird to go to office hours with no specific question? | 0.1829 | passed |
| What actually happens if you hand something in late? | 0.3481 | passed |
| Is the printing quota enough? | 0.2531 | passed |
| Do professors actually answer email? | 0.2101 | passed |
| Worth getting a parking permit? | 0.2471 | passed |
| First winter here — what do I need? | 0.3092 | passed |
| Do transfer credits actually count toward the major? | 0.1696 | passed |
| Does the edition of the textbook matter? | 0.2962 | passed |
| How do you handle a group project where someone disappears? | 0.1634 | passed |

## Verdicts
| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer (target: revised in unit 2 to 15 of 15, was 5 of 5) | MET | 15/15, 15/15, 15/15 — held in all three runs, not just one. Retrieval is deterministic, so I didn't rely on the generated answer (which paraphrases); I checked each `expects` string against the actual source document and confirmed it's a verbatim line in the reply the system cites, e.g. `thread_pass_fail.txt` reply 2 matches `expects` for that question word-for-word. Verified the same way for all 10 questions added in unit 2, not just the original 5. |
| 2 | Every answer names a source (target: 15 of 15, was 5 of 5) | MET | 15/15, 15/15, 15/15 — parsed all 45 generated answers (15 questions × 3 runs) programmatically for a `thread_` citation; zero were missing one. |
| 3 | Gate stops out-of-corpus questions (target: 4 of 5; question set revised in unit 2 to topically-adjacent ones) | **MISSED** | 0/5 refused on the one deterministic pass at 0.55. All five landed at 0.513–0.537 — under the cutoff by 0.013 to 0.037 — so the gate passed every one to the model. The model's grounding prompt then refused all five on its own, but the criterion says the *gate* stops the question and returns the fixed refusal, and it didn't; the second layer catching it is not the first layer working. Against the unit-1 trivia set the same gate was 5/5 (0.819–0.905), which is exactly why that set was swapped. |
| 4 | Every document gets chunked, none dropped (target: exactly 75 chunks, 0 documents at 0 chunks) | MET | Ran `python app.py chunks` (75 chunks total) and a direct doc-coverage check against `ingest.py::load_documents` + `chunker.py::split_documents`: 23 of 23 documents represented, none at zero. Deterministic, so one check is the whole measurement. |
| 5 | Threshold (0.55) holds for in-corpus questions (now 15 of 15) | MET | 15/15, 15/15, 15/15 passed the gate. Best distances (0.1309–0.3481) held well under 0.55 in every run — the closest in-corpus question ("late work," 0.3481) still isn't near the cutoff, so even with three times the questions this wasn't a close call. |

## Diagnoses

**One miss: criterion 3.** Criteria 1, 2, 4 and 5 cleared in every run
(15/15 ×3, 15/15 ×3, 75 chunks / 0 dropped, 15/15 ×3). Criterion 3 missed
0 of 5 against the revised question set — after clearing 5 of 5 against
the original one. Both facts are part of the diagnosis.

**Where it fails: the gate, not retrieval and not generation.**

- *Retrieval did its job.* For "What's the best dining hall on campus?" the
  nearest chunks are `thread_study_spots.txt` and `thread_meal_plan_tier.txt`
  — genuinely the closest things in the corpus, and none of them answers
  the question. There is no right chunk to find, so retrieval returning
  wrong-topic neighbours at 0.528 is correct behaviour.
- *Generation held.* When the gate let the five through, the grounding
  prompt refused every one ("I don't have enough information to answer…").
  So the observable damage is one wasted model call per question (~400
  tokens each) and refusals that are inconsistent with the fixed one the
  gate produces — two of the five even carried a source line, e.g.
  `(Source: thread_study_spots.txt and thread_meal_plan_tier.txt)`, citing
  documents for a non-answer. Not a fabrication, but not the behaviour the
  criterion specifies either.
- *The gate is the stage that misfired, and the mechanism is how the cutoff
  was chosen.* In Milestone 4 I set 0.55 by splitting the gap between my
  worst real question (0.3365) and my closest trivia question (0.8189).
  That gap was only empty because the trivia set shares nothing with a
  campus-advice corpus. A question with the *shape* of a real one — campus
  life, second person, asking for a recommendation — but about a topic no
  thread covers embeds at 0.51–0.54 against its nearest neighbour, because
  it shares genre and half its vocabulary with that neighbour ("gym
  membership *tier*" → `thread_meal_plan_tier`, "bike *repaired*" →
  `thread_bike_commute`, "shuttle to downtown" → `thread_commuting`). 0.55
  is above all of those, so the gate cannot tell them from real questions.

**The pattern across the five:** it's one problem, not five. All five sit in
a narrow band (0.513–0.537) regardless of topic, and all five have a
different-topic neighbour thread within reach. That band is where "same
genre, adjacent noun" lands for this embedding model on this corpus. The
cutoff was drawn at a *domain* boundary (campus advice vs. everything else)
when the boundary that matters is a *topic* boundary inside the domain.
There is a real gap for that — my worst in-corpus question is 0.348 and the
closest adjacent non-question is 0.513 — the cutoff just wasn't in it.

**Was the original criterion 3 target set low?** Yes, and it showed. "4 of
5" against trivia is a target that cannot be missed: the closest miss was
0.27 from the cutoff. Swapping the question set (kept at 4 of 5) is the
tightening; The Improvement below is the fix.

**Criterion 1 is the other soft target,** even though it held:

- **Criterion 1 (retrieved chunks contain the answer)** looks strong at
  15/15, but the mechanism that makes it easy is still the corpus size,
  not precision: no thread has more than 5 replies, `top_k` is 5, and most
  of my questions retrieve chunks almost entirely from a single thread
  (`thread_first_year_regret.txt` contributes all 5 of its replies to one
  question's top-5; the same is true of most of the 10 questions I added
  in unit 2). With threads this short, "the answer is somewhere in the top
  5" is close to guaranteed by the corpus shape, not something retrieval
  had to work for — tripling the question count made the target easier to
  hit consistently, not harder, because it didn't change that ceiling.
  **I'd tighten this to "in the top 3"** — closer to the actual precision
  the retrieval step is providing — before trusting 15/15 as evidence the
  embedding step is doing real work. I measured it: all 15 `expects` chunks
  are already in the top 3 (9 at #1, 4 at #2, 2 at #3), so the tightened
  target would hold today. The point isn't that it would fail; it's that
  "top 3" is the ceiling I can honestly claim, and "top 5" isn't a claim at
  all on this corpus.

Criteria 2, 4, and 5 don't have the same slack: criterion 2 has no room to
loosen further (every answer either names a source or it doesn't), and
criterion 4's target is an exact count with zero tolerance already.

## The Improvement

**What I changed:** The relevance cutoff. `THRESHOLD` in `config.py` goes
from 0.55 to 0.45. Nothing else in the pipeline moves — same chunks, same
index, same top-k, same prompt.

**Why I picked it:** My criterion 3 diagnosis found that 0.55 was set by
splitting an empty gap — between my worst real question (0.348) and trivia
that sat at 0.82+ — and that plausible campus questions no thread answers
land at 0.51–0.54, *inside* that gap, so the gate waves them through to
generation. 0.45 sits in the gap that actually exists: 0.10 above the worst
real question, 0.06 below the closest adjacent non-question.

**Why not the other levers.** Before settling on the gate I checked whether
the other two stages the assignment names were the real problem:

- *Chunking.* I indexed the unit-1 fallback (whole-thread chunks, 26 of
  them) as a side-by-side variant (`--variant wholethread`) and ran all 15
  questions plus the adjacent set against both. Whole-thread ranks every
  answer #1 (the question is literally the thread title) but pushes
  distances up hard: worst real question 0.704 (it would be *refused* at
  0.55), closest adjacent non-question 0.517. Real and non-real distances
  interleave, so no cutoff separates them. Per-reply chunking is what opens
  the 0.348–0.513 band that a cutoff can live in. It isn't the lever; it's
  the reason the lever exists.
- *Retrieval / hybrid search.* Under dense retrieval every one of the 15
  `expects` chunks is already in the top 3 (9 at #1). BM25 over the same 75
  chunks is worse (6 at #1, 7 at #3), and even keyword-heavy probes
  ("Verrill", "$30", "Morrow or Fenwick") are already rank 1 under dense.
  There's nothing for a hybrid to improve, and BM25 has no "nothing
  matches" signal (it scores "ibuprofen dosage" at 8.06 against the
  laptop-specs thread), so it would only make the gate harder to trust.

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 15 of 15 | 15/15 | 15/15 | 15/15 | MET |
| 2. Every answer names a source | 15 of 15 | 15/15 | 15/15 | 15/15 | MET |
| 3. Gate stops out-of-corpus questions (adjacent set) | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Every document gets chunked, none dropped | 75 chunks, 0 dropped | 75, 0 dropped | 75, 0 dropped | 75, 0 dropped | MET |
| 5. Threshold (now 0.45) holds for in-corpus questions | 15 of 15 pass the gate | 15/15 | 15/15 | 15/15 | MET |

Source data: `results/run_2026-09-27_2024_after.md`, produced by
`run_eval.py::main` (top-k 5, cutoff 0.45, 3 runs, caching off). Criteria 3
and 4 are deterministic, one pass each; the same number sits in all three
columns. Criterion 4 is unchanged from Before — the fix didn't touch chunking.

Gate on the adjacent set, produced by `run_eval.py::check_out_of_scope`,
cutoff 0.45:

| Out-of-scope question | Best distance | Before (0.55) | After (0.45) |
|---|---|---|---|
| What's the best dining hall on campus? | 0.528 | let through | refused |
| Is it worth living off-campus in second year? | 0.513 | let through | refused |
| Which gym membership tier should I get? | 0.526 | let through | refused |
| Where can I get my bike repaired near campus? | 0.533 | let through | refused |
| How much does the shuttle to downtown cost? | 0.537 | let through | refused |

What the system says now — `python app.py ask "What's the best dining hall
on campus?" --threshold 0.45`, refusal produced by `gate.py::check` returning
`gate.REFUSAL`, no model call:

```
  (best distance 0.528, cutoff 0.45)

I don't have enough information about that.

0 model calls this session
```

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

Yes. Criterion 3 went from 0 of 5 to 5 of 5 on the same five questions, and
nothing else moved: criteria 1, 2 and 5 are 15/15 in every run after exactly
as before, and criterion 4 was never in play. I know because the two runs
differ in one number (`THRESHOLD`) and the before/after gate tables above
are the same questions at the same distances with the decision flipped.

The real question in the tail of the corpus was the one I watched: "What
actually happens if you hand something in late?" is my closest in-corpus
question to the new cutoff (0.348 vs 0.45). It still passes and still
answers from the right thread — after run 1, `generate.py::answer_from_chunks`:

```
What happens when you hand something in late is entirely dependent on the instructor, and the syllabus is accurate (e.g., if it says 10% a day, it is 10% a day). Additionally, the universal rule is to ask before the deadline rather than after, as almost everyone will give you two days if you ask beforehand, but almost nobody will on the following Monday. (Source: thread_late_work.txt)
```

Two honest qualifications:

- *What it actually fixed is the gate's own behaviour, not a hallucination.*
  At 0.55 the grounding prompt had already refused all five let-through
  questions, so the visible gain is that refusals are now the fixed string
  from `gate.py`, consistent, with no stray "(Source: …)" line — and five
  fewer model calls per eval (the gate refuses for free). The criterion was
  still missed before and met after; it just wasn't the failure mode where
  the system confidently makes things up.
- *The margin is now thinner on the refuse side than the answer side.* 0.45
  is 0.10 above my worst real question but only 0.06 below my closest
  adjacent non-question (0.513), and that's measured on eight adjacent
  probes, not a large sample. A non-question that happens to share even
  more vocabulary with a thread could land in 0.45–0.51 and get through;
  a real question phrased very unlike its thread could land above 0.45 and
  get refused. None of my 15 did (all ≤ 0.348), but 15 is not many.

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
