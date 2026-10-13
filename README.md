# Emulsion Evidence Lab

**Evidence-linked literature extraction for stimuli-responsive Pickering emulsions.**

An early research prototype for studying whether Claude can help researchers
extract material properties and reported observations from papers, while retaining
the exact source passages needed for review.

Maintainer: **Soh Jia Sheng**. Initial code and documentation were prepared with
AI assistance. The maintainer should review the code and understand the demo before
presenting it as their work. No supervisor, laboratory, institutional endorsement,
funding award or completed scientific validation is claimed.

## Research question

Can Claude improve extraction of reported emulsion properties over a simple
pattern-matching baseline, without increasing unsupported statements or reviewer
workload?

The initial focus is iron oxide–chitosan and related Pickering emulsions. This
connects colloid chemistry with research on delivery systems. The present software
extracts reported observations; it does not establish therapeutic effectiveness
or propose validated formulations.

## Current status

| Available now | Planned work |
| --- | --- |
| Runnable Python extractor and review report | Collect a corpus with permission to process its text |
| Deterministic baseline with no external dependencies | Obtain expert-reviewed reference annotations |
| Optional Claude SDK integration | Run and compare live Claude configurations |
| Literal quote, character-offset and source-hash checks | Evaluate semantic support, negation and formulation context |
| Four clearly labelled synthetic fixtures | Measure accuracy, cost and reviewer time on held-out papers |
| 23 passing offline tests | Investigate extraction of multiple conditions and table data |

**No live Claude request has been made in the initial verification. No real
publication has been processed by the demo. Synthetic fixture scores are software
smoke tests, not research results.**

## Run the offline demo

Requires Python 3.11 or later. From this repository folder:

```bash
python3 app.py extract --input data/demo_documents.jsonl --provider baseline --output outputs/demo
python3 app.py evaluate --predictions outputs/demo/results.jsonl --gold data/demo_gold.json --output outputs/demo/evaluation.json
python3 -m unittest discover -s tests -v
```

Open `outputs/demo/review.html` in a browser. Expand an evidence row to read the
supporting passage, and use the search box to filter the report. The HTML report
is local and has no external dependencies or data uploads.

A ready-generated synthetic report is included in [examples/demo/review.html](examples/demo/review.html).
On GitHub, download that file and open it locally to use the report.

## Use Claude

Claude mode sends the supplied text to the Anthropic API and consumes API credits.
The offline demo makes no API calls. Set a current API model ID explicitly:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-claude.txt
export ANTHROPIC_API_KEY="YOUR_API_KEY"
export ANTHROPIC_MODEL="YOUR_AVAILABLE_MODEL_ID"
python3 app.py extract --input data/demo_documents.jsonl --provider claude --limit 1 --output outputs/claude-pilot
```

On Windows, use `python` and the virtual environment activation command for your
shell. `.env.example` documents the variables; the application does not load
`.env` files automatically. Never commit a real key.

The model is configurable rather than hard-coded. Check the
[official model catalogue](https://platform.claude.com/docs/en/models/overview)
for an ID available to your Console organisation. The SDK is optional and installed
only for Claude mode. Record its installed version with your research results.

The integration disables automatic SDK retries and makes at most one request per
document. A malformed, truncated or invalid extraction stops the batch. If an
error occurs, earlier calls may already have consumed credits; this prototype
does not persist partial results from a failed batch.

## Extraction and review

Seven fields are extracted: stabilizer, oil phase, pH condition, droplet size,
stability observation, magnetic response and cargo release. Each populated value
must be copied from an exact supporting quote. The quote must occur in the supplied
source. Character offsets use Python Unicode indices with an exclusive end.

Every populated field is marked `needs_review`. A null is `not_extracted` and
does not prove the paper lacks that information. A source hash and, for Claude,
model, prompt hash and token usage accompany each record.

| Output | Purpose |
| --- | --- |
| `results.jsonl` | Exact machine-readable values, quotes, provenance and metadata |
| `evidence.csv` | Spreadsheet review; formula-like text is escaped for safer viewing |
| `report.md` | Compact text summary |
| `review.html` | Searchable, expandable local evidence report |
| `evaluation.json` | Comparison with supplied reference values when evaluation is run |

Literal quote validation establishes **where text came from**. It does not prove
that the quote supports the field or that a conclusion is scientifically correct.
For example, a quote saying an oil was not used can still contain that oil's name.
Expert review must check negation, context and measurement identity.

The baseline covers a small vocabulary and a few sentence patterns. It can miss
synonyms or select a negated mention. Neither method currently associates multiple
formulations with multiple conditions. Do not interpret its first-observation
output as a complete representation of a study.

## Evaluation approach

The implemented scorer reports exact field match, non-null precision/recall/F1,
field-level mismatches and a literal-quote check rate for accepted predictions.
A wrong populated value counts as both a false positive and a false negative.
True nulls are separate, so missing fields do not inflate non-null precision.
Semantic support and failed-generation rates still require separate annotation
and run accounting, described in the research plan.

## Project documents

- [Research plan](docs/RESEARCH_PLAN.md): hypothesis, corpus, comparisons and six-month milestones.
- [Application draft](docs/APPLICATION_DRAFT.md): editable, status-accurate proposal.
- [Publishing guide](docs/PUBLISH_TO_GITHUB.md): repository creation and upload instructions.
- [Data provenance](data/README.md): synthetic fixtures and a real-paper seed catalogue.
- [Validation record](docs/VALIDATION.md): what was checked and what remains untested.

## Programme context

This repository can support an application to
[Anthropic's AI for Science Programme](https://support.claude.com/en/articles/11199177-anthropic-s-ai-for-science-program).
Its official criteria include scientific merit, potential impact, technical
feasibility and team credentials. The programme supports research API usage.
Creating this repository does not establish institutional research attachment
or guarantee acceptance. Programme details were checked on 13 October 2026.

## Licence

The code and original synthetic fixtures use the MIT licence. Bibliographic
metadata and third-party article content retain their respective rights.
