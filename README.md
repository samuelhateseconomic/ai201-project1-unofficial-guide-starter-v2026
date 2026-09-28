# The Unofficial Guide
Samuel Do - advice_threads
---
<!-- ── Stretch features ─────────────────────────────────────────────────────
     Add more tests.
     Add extra layers that can replace the gemini model if it runs over usage. 
     ───────────────────────────────────────────────────────────────────────── -->

---

## Stretch feature: model rotation

**What:** `generate.py` rotates across several Gemini models instead of
calling one. Each model in `config.MODEL_POOL` gets its own per-minute
window; a call goes to the highest-priority model with a free slot, and a
model that answers 429 or 503 is cooled down while the call moves to the
next one. The default pool is `gemini-3.5-flash-lite:15`,
`gemini-3.1-flash-lite:15`, `gemini-3.5-flash:5`, `gemini-3-flash-preview:5`
— 40 calls/minute against the free tier's 15 for any single model.
`AI201_MODEL_POOL=gemini-3.5-flash-lite:15` pins one model back, which is
what an eval should use so every answer comes from the same model.

**Why:** the 15-question eval is 45 model calls per run. At one model's
quota that's a 4-minute run that crashed with a 429 the first time; with
the pool it fits in two minutes. It's also why the unit-2 test set could
grow from 5 to 15 questions.

**Evidence** — every quota pinned to 1 so five questions are forced to
rotate, `generate.usage()` at the end:

```
  [model pool] gemini-3-flash-preview is overloaded (503); cooling it down for 30s and moving to the next model (attempt 1 of 4).
  [rate limit] all 4 models used up this minute. Waiting 30s. This is normal.
[gemini-3.5-flash-lite] How many clubs is too many?
[gemini-3.1-flash-lite] Is a bike worth it for a 20 minute walk commute?
[gemini-3.5-flash] How hard is it to change major in second year?
[gemini-3.5-flash-lite] Roommate situation isn't working. What now?
[gemini-3.1-flash-lite] Everyone says fix your sleep. Does it actually matter?
6 model calls this session [gemini-3.5-flash-lite 2, gemini-3.1-flash-lite 2, gemini-3.5-flash 1, gemini-3-flash-preview 1], 2386 tokens (1964 in, 422 out)
```

Known limit: `gemini-3-flash-preview` returned 503 both times it was
reached, so in practice the pool is 35/minute with a 30-second dead spot
when the other three are exhausted.

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
land at 0.51–0.54, inside that gap, so the gate waves them through to
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

No criterion is still MISSED after the fix. That is not the same as nothing
being left. no 


## What I'd Do Differently

Actually, criterion 1 can be "top 3" instead of "top 5" and define the check mechanically. Because top 5 is a whole thread and change it would made `run_eval.py`'s column mean something instead of failing 45/45 against pararphrased answers.

## How I Used AI

**Unit 2.**
I had Claude turn `run_eval.py`'s per-question table into the
per-criterion run log. The first thing it flagged was that every cell said
`fail` even though the answers were obviously right — `scorer.py` was
checking my `expects` string against the paraphrased answer instead of the
retrieved chunk — so instead of trusting the column it checked each
`expects` string against the corpus files directly and parsed all 45
answers for a source citation, and I used those as the verdicts.

When I asked whether to add hybrid search or a second chunking strategy as
my improvement, it measured both before answering instead of agreeing:
dense retrieval already had every answer in the top 3, BM25 was worse, and
whole-thread chunks pushed my worst real question to 0.704. Then it probed
my gate with campus questions no thread answers and found 5 of 8 got
through at 0.55. I picked the gate retune over the "impressive" options
because it was the only one with a diagnosis behind it. The scope calls —
expanding to 15 questions, revising criteria 1 and 3 in `criteria.md` —
were mine after it laid out the trade-off, and I kept the fix to one number
so the before/after would be clean.

**Stretching - AI Rotation.**
