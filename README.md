# The Unofficial Guide

<!-- Replace this line with your name and which corpus you picked. -->

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Unit 1

## What This Does

<!-- Three or four sentences. Which corpus you picked, and the kinds of
     questions your system answers. Write it for someone who has never seen
     this repo.
     I run the corpus advice_threads and ask "What do you wish you'd know in first year?" - Then, the answer will look like "That nobody is watching you as closely as you think, and you don't need to worry so much about looking like you know what you're doing....". At the same time, it will contain the resources that the answer came from which one of them should be `thread_first_year_regret.txt`.-->

## Chunking Strategy

**Chunk size:** one reply per chunk (not a character count).
**Overlap:** none — replies don't share text with each other.

<!-- What about YOUR documents made you pick these numbers? Short posts and
     long sectioned guides don't want the same chunking, and "800 seemed
     reasonable" earns nothing. Point at something you noticed when you read
     the documents in Milestone 1.

     If you changed your mind partway through, say so and say why. That's worth
     more than pretending you got it right first time.

     Milestone 3. -->

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

<!-- Five chunks, pasted as text. Label each one and name the file it came from
     AND the function that produced it — the grader checks your code against
     what you claim here.

     `python app.py chunks -n 5` prints all three for you. Copy them straight
     across.

     Milestone 3. -->

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

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

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

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1.** I asked Claude to check the size of each corpus so I could pick a chunk size and overlap that actually fit my documents. It came back with per-document stats showing every `advice_threads` document was 318–794 characters — under my `CHUNK_SIZE` of 800 — which meant `fallback_split` was never actually splitting anything; each whole thread was already one chunk. It first suggested splitting each reply out into its own chunk, but I pointed out that a bare reply on its own doesn't tell the agent what question it's answering, so we need the topic attached, not just the reply text on its own. It revised the design to prefix every reply chunk with the thread's title line before I had it write `split_thread`/`split_documents` in `chunker.py`. I also pushed back when it framed the fix as "tune chunk size" — I asked directly whether Milestone 3 was actually about changing the two config numbers rather than the function, and it pointed me to the docstring in `chunker.py` itself, which says to replace the function body, not the numbers.

**2.** For Milestone 4, I asked Claude to run my five `QUESTIONS` and five `OUT_OF_SCOPE` questions through retrieval and report the best distance for each, then asked where it would put the relevance cutoff and what I'd get wrong at that number. It came back with in-corpus distances topping out at 0.3365 and out-of-scope distances bottoming out at 0.8189, and recommended a cutoff near the middle of that gap (~0.55–0.6) rather than the starter's 0.7 default — explaining that 0.7 sits closer to the out-of-scope side and would be more likely to let a superficially similar out-of-scope question slip through, while a cutoff too low risks refusing a real question phrased awkwardly. I used that reasoning to set `THRESHOLD = 0.55` in `config.py` myself, rather than just accepting whatever number it suggested first.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

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
