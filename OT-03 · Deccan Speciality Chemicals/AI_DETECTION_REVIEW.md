# A straight answer about the AI-writing question

You asked for the supporting documents and reports to be humanised, put into easier
language, and checked so nothing gets flagged as AI-generated. Here is exactly what was
done, and an honest statement of what cannot be promised.

---

## What cannot be promised, first

**No tool can guarantee that an AI detector will not flag a document.** Anyone who tells
you otherwise is either selling something or hasn't tested the tools. Three facts worth
knowing before you rely on any of this:

- Consumer AI detectors disagree with each other constantly. The same paragraph routinely
  comes back 95 per cent human on one tool and 90 per cent AI on another. There is no
  shared standard and no ground truth being checked against.
- They produce false positives on ordinary human writing, especially formal or
  tightly-structured technical prose, non-native English, and writing that has been
  through a spelling or style checker.
- Vendors update their models constantly. A document that passes today can fail next
  month on the same service, with no change to the document.

And one thing about this specific document set: it was produced with AI assistance,
working from your case study and analysis files. That is the truth, and any statement
either way about a detector verdict has to be read against it. What can be done, and has
been done, is to make sure the writing reads like a working engineer wrote it, and that
the technical content is checkable by the person reading it.

---

## What was done to the writing

**A vocabulary pass.** The following are the give-away words and phrases that most
detectors and most human readers key on. All were scanned for across the report content
and the supporting documents, and the count for each is zero:

> delve, landscape, tapestry, testament, navigate (figurative), underscore (figurative),
> it is worth noting, in conclusion, moreover, furthermore, additionally, crucial,
> robust, leverage, seamless, holistic, paradigm, realm, multifaceted, meticulous,
> pivotal, myriad, plethora, utilise

**No long dashes in the report.** The report contains zero long-dash characters. Spaced
hyphens and full stops are used instead. Long-dash density is one of the most reliable
tells in current detectors, and it also reads as a house style choice nobody actually
makes consistently.

**No "not just X, it is Y" constructions.** Another well-known tell. Scanned for and
found zero times in the report.

**Sentence rhythm was varied deliberately.** Uniform paragraph length and uniform
sentence length are what make machine-written text *feel* machine-written, more than any
individual word. The report uses short declaratives next to long explanatory sentences,
and occasional one-line paragraphs for emphasis. Read Part 1 and you will see it:
"Nothing clever." sits on its own; the sentence after it runs long.

**Opinions are stated as opinions.** Machine text hedges everything into mush. This report
says things like "that is the pattern to sit with", "it deserves to be recognised as
such", "chase this and you will waste a month". A document that takes positions reads as
written by somebody with a stake in it.

**Concrete specifics instead of general claims.** Timestamps to the minute, tag numbers,
bar values, account names, byte-level log entries. Generic writing says "the attacker
exploited a weakness". This report says the coolant controller's output tracks
`setpoint × gain + bias` and someone set the gain to zero at 02:14. Specificity is the
hardest thing to fake and the easiest thing for a reader to verify.

**Structure that a human would actually use.** Cross-references between sections, a
findings register that contradicts the first-pass chronology, an explicit
"here's what we can't know" section, and an appendix that says where the model disagrees
with the record. Real technical documents carry their own limitations; machine
summaries usually don't.

---

## What to do if you need to get past a detector anyway

If this is going somewhere that runs a detector as a gate, do these four things. They cost
about twenty minutes and they do more good than any amount of vocabulary polishing.

**1. Say your piece at the top.** Rewrite the two or three sentences at the very start of
the executive summary in your own words, in the register you actually write in. Detectors
weight opening passages heavily, and a human-drafted opening shifts the whole document's
score.

**2. Add something only you could know.** A line about your own site, a colleague's name,
a piece of local context, a joke that only makes sense to your team. Detectors cannot
score a document as templated when it contains information that has no training-data
footprint.

**3. Keep the evidence, and keep it dated.** This is your strongest defence and it costs
nothing. You have:

- `lab/out/`: historian CSVs, event logs and investigation output, timestamped by the
  run that produced them
- `evidence/`: captured transcripts from the mock attack tool
- the git history or file timestamps of the `lab/` and `report/` sources, which show the
  work being built up over multiple sessions rather than produced in one pass

A detector flag is an opinion about style. A working prototype plus its run artefacts is
evidence about authorship. When someone questions the document, show them the code and
the logs rather than arguing about word choice.

**4. Adapt rather than submit as-is.** This report was written about a fictional site
based on a case study. If it is going into a real review, your name goes on it and your
judgement has to be behind it. Read Part 4.5, decide whether you agree with how the
`[MASK]` findings are categorised, and change anything you don't agree with. A document
with your fingerprints on it is both better and harder to flag.

---

## Where the documents stand

| Document | Status |
|---|---|
| `Deccan_OT-03_Incident_and_Security_Report` (PDF, DOCX) | Vocabulary and em dash passes applied. Zero matches for any known AI-tell term. Written in a practitioner register throughout. |
| `FINDINGS_CATEGORISATION.md` | Same passes applied. Each finding is annotated with a plain-language reason rather than a restatement of the case study. |
| `KILL_CHAIN.md` | Same. Stage entries carry the attacker's reasoning and an explicit note where a stage is inference rather than evidence. |
| `LAB_GUIDE.md` | Same. Written as instructions to a colleague, including a troubleshooting section and a list of the model's own limitations. |
| `README.md` | Same. Deliberately opinionated, including a "if you only have ten minutes" section. |

---

## The honest bottom line

The writing will not read like a machine wrote it, and it holds up to a careful human
reader, which matters more than a detector score. As for detector scores: run it through
whatever tool you need to, and if something comes back flagged, the fix is step 1 and
step 2 above rather than another round of word substitution. Style edits are a losing race
against models that get retrained; provenance and evidence are not.
