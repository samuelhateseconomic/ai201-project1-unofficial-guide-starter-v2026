"""
Your test questions.

Milestone 2 asks you to write five questions your system should be able to
answer from your corpus, specific enough to have a right answer.

  ✗ "What are good dining halls?"          — no right answer
  ✓ "What do students say about wait times at Commons during lunch?"

Fill in `QUESTIONS` below. `expects` is a word or short phrase you'd expect a
correct answer to contain — you'll use it in unit 2 when you build a scorer,
and having written it now means you decided what "correct" meant before you saw
any results.

`OUT_OF_SCOPE` holds five questions your documents clearly don't cover. You
need these in Milestone 4 to find where your relevance cutoff belongs, and
again in unit 2, where `run_eval.py` runs them through the gate and writes what
happened into your run log — that's the evidence for criterion 3.

Swap them for your own if you like. Keep five of them either way: criterion 3
names a target of "4 of 5", and four of three is not a thing.
"""

QUESTIONS = [
    # {"question": "...", "expects": "..."},
    {"question": "Anything specific for first-generation students?", "expects": "The thing I'd say: the unwritten rules are the hard part, not the coursework. Ask about the unwritten rules explicitly. People are happy to explain them and nobody volunteers them."},
    {"question": "When should you actually use the pass/fail option?", "expects": "The part that isn't advertised: you can declare it as late as week eight. So take the midterm first, then decide."},
    {"question": "When should I start looking for a summer internship?", "expects": "Earlier than feels reasonable. Large employers close applications in October and November for the following summer."},
    {"question": "What do you wish you'd known in first year?", "expects": "Honestly: that nobody is watching as closely as you think. I spent a year worried about looking like I knew what I was doing."},
    {"question": "The best study spots that aren't the library?", "expects": "Ridgeway Café before 10am. Empty, quiet, good coffee, and they don't push you out."},
    {"question": "When is laundry actually free in the dorms?", "expects": "Tuesday and Wednesday mornings, every building. Sunday evening is the worst and it isn't close."},
    {"question": "Is it weird to go to office hours with no specific question?", "expects": "No, and this is the single most common thing first years get wrong. 'I'm following the lectures but I don't feel like I understand the shape of it' is a completely normal thing to say."},
    {"question": "What actually happens if you hand something in late?", "expects": "The universal rule: ask before the deadline, not after. Almost everyone will give you two days if you ask on Wednesday for a Friday deadline. Almost nobody will on the following Monday."},
    {"question": "Is the printing quota enough?", "expects": "For most people yes. $30 is about 600 pages black and white. It's the colour printing that eats it — eight times the cost per page."},
    {"question": "Do professors actually answer email?", "expects": "Varies enormously. General rule I've found: if the syllabus states a response window, it's honoured. If it doesn't, assume 48 hours and don't panic before then."},
    {"question": "Worth getting a parking permit?", "expects": "Street parking on Verrill is legal and free and unmarked, which is why half the upper years do it."},
    {"question": "First winter here — what do I need?", "expects": "Boots with actual tread. The path past the pond ices over and people go down on it every year."},
    {"question": "Do transfer credits actually count toward the major?", "expects": "Toward general requirements almost always. Toward the major it's case-by-case and the department decides, not the registrar."},
    {"question": "Does the edition of the textbook matter?", "expects": "Ask the instructor directly. Most will tell you the previous edition is fine, and they can't put that in the syllabus for procurement reasons."},
    {"question": "How do you handle a group project where someone disappears?", "expects": "Document early. Not to be difficult — because if you go to the instructor in week 10 with nothing written down, there's nothing they can do."},
]

# Questions from a different world entirely. Your gate should refuse all five.
#
# There are five of these because criterion 3 in criteria.md names a target of
# "at least 4 of 5" — you need five things to try before you can report 4 of 5.
# `run_eval.py` runs these through retrieval and the gate on every eval and
# records what happened, so criterion 3 has evidence in the run log alongside
# the others. They cost no model calls: a refusal never reaches the model.
#
# Unit 2: swapped for questions that are topically ADJACENT to the corpus —
# plausible student questions no thread actually answers — instead of trivia
# from an unrelated domain. The original five (capital of Mongolia, diesel oil
# change, 1994 World Cup, ibuprofen dosage, Rust for-loop) all landed at
# distance 0.82–0.91, so they never tested the gate near its cutoff. These
# five land at 0.51–0.54 against the per-reply index.
OUT_OF_SCOPE = [
    "What's the best dining hall on campus?",
    "Is it worth living off-campus in second year?",
    "Which gym membership tier should I get?",
    "Where can I get my bike repaired near campus?",
    "How much does the shuttle to downtown cost?",
]

# Kept for reference — the unit 1 set. Not run by run_eval.py.
OUT_OF_SCOPE_UNIT1 = [
    "What is the capital of Mongolia?",
    "How do I change the oil in a diesel engine?",
    "Who won the 1994 World Cup?",
    "What is the recommended dosage of ibuprofen for a headache?",
    "How do I write a for loop in Rust?",
]


def answered() -> list[dict]:
    """The questions you've actually filled in."""
    return [q for q in QUESTIONS if q.get("question", "").strip()]
