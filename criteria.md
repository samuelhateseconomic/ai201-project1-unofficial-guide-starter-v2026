# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For all 5 of my 5 test questions, at least one of the top-5 chunks
`store.search` retrieves — read as raw chunk text, before generation —
contains the `expects` phrase (or the substance of it) for that question.

**Why this target:**
Every one of my 5 questions maps to a single specific reply with distinct,
on-topic vocabulary, not a vague topic several documents could plausibly
answer. When I measured distances in Milestone 4, my worst in-corpus question
(first-gen students, 0.3365) was still nowhere near my best out-of-scope
question (ibuprofen dosage, 0.8189) — a gap of over 0.48. There's no borderline
question in my set sitting close to that boundary, so I don't have a reason to
expect any single one of the five to be fragile.


---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:**
The trieved chunks that contains the answer or not should had the ability to address its sources because it need to find the physical evidence at least one in order to reasoning from it, which avoid hallucination.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:**
<!-- What did your distances look like when you set the cutoff in Milestone 4?
     Was there a clean gap, or did the two groups overlap? -->
The distance should be lower than 0.55 in other to determine it is the answer for the question. Otherwise, it should be honest about the limitation of the documents itself rather than being hallucinated and generate fake answers. 
---

## 4. Every document gets chunked, none silently dropped

Running `python app.py chunks` over the `advice_threads` corpus reports
exactly 75 chunks total, with every source document represented at least
once — zero documents producing zero chunks.

**Why this target:**
`split_documents` has two paths: split on the `--- reply N (votes) ---`
marker, or fall back to the fixed 800-character splitter for any document
that doesn't contain that marker. A document that hits neither path — say,
one with an unexpected format — wouldn't error, it would just silently
contribute zero chunks, and every reply in it would become permanently
unretrievable without the run ever showing a failure. Checking the total
against a known number (75, one per reply, counted by hand against the
corpus) is how I catch that silently, since a wrong total is the only signal
a dropped document would leave behind.


## 5. Threshold    
When I ask a question the threshold should hold a good ceiling by comparing all the test question. So I set it at 0.55

**Why this target:**
What if even the question has in the corpus but the answers are constructed in a more complex way which trick the distance system gets really high.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->
