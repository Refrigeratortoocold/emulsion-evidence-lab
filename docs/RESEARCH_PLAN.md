# Research plan

Status: proposed pilot. Only the synthetic software demo has been run.

## Motivation and hypothesis

Studies of stimuli-responsive Pickering emulsions report different stabilizers,
oil phases, pH conditions and measurement types. Comparing papers requires careful
attention to whether a value describes a nanoparticle, an emulsion droplet or a
different quantity. An evidence-linked extraction workflow could help organise
reported observations while preserving their source context.

Hypothesis: Claude can increase useful field extraction relative to the limited
regex baseline, while source-linked review keeps unsupported claims visible.
This hypothesis has not been tested on real papers.

Primary question: on a held-out corpus, how do extraction precision, recall and
human-rated semantic support differ between methods?

Secondary question: does the assisted workflow reduce reviewer time without
reducing correctness?

## Corpus and annotation

1. Pilot on 10 legally accessible papers to refine eligibility and the schema.
2. Target 100 eligible articles with identifiable emulsion materials and at least
   one relevant reported observation. This target depends on time and permissions.
3. Reserve 20 articles for schema and prompt development, and 80 for held-out
   evaluation. Freeze the split before comparing configurations. Group related
   articles or duplicate reports to avoid leakage.
4. Record title, DOI, publication year, licence, retrieved text location and date.
   Use supplied excerpts initially; automated full-text collection is future work.
5. Seek a domain-qualified reviewer. Independently double-annotate at least 20
   held-out articles if a second reviewer agrees to participate. No reviewer has
   yet been confirmed. Report unresolved annotation disagreements.

Exclude inaccessible or unauthorised text, reviews from the main primary-study
evaluation, and documents that cannot be represented responsibly in the initial
single-observation schema. Record exclusions before observing method outputs.
Keep reviews as background references. Do not invent missing measurements.

## Methods and comparisons

- Run the current regex baseline on the same excerpts.
- Compare two available Claude model IDs, recorded exactly at run time.
- Compare three prompt configurations, including the current literal extraction
  prompt. Create and freeze the alternatives during development.
- Repeat each model/configuration twice to examine variability.
- Treat the source as data. Apply local shape and literal quotation validation.
- Have reviewers judge semantic support, including negation, units, measurement
  identity and formulation context. Literal quotation alone is insufficient.

The present code implements only one prompt. Comparison orchestration, full run
failure logs and annotation adjudication are still planned. Failed responses must
remain in the denominator rather than being silently excluded.

## Outcomes

| Measure | How it will be assessed |
| --- | --- |
| Field exact match | Normalised string comparison with reference values |
| Non-null precision/recall/F1 | Separate present values from correctly empty fields |
| Semantic support | Human judgment that the quote supports the assigned observation |
| Invalid-output rate | All attempted outputs, including schema/quote failures and refusals |
| Measurement-confusion rate | Nanoparticle versus emulsion droplet and other identity errors |
| Reviewer time | Timed, counterbalanced manual and assisted review on matched article groups |
| API use | Recorded input/output tokens and actual billed usage |

Report per-field errors and confidence intervals at the article level. Predefine
acceptable precision and semantic-support thresholds with the reviewer rather
than choosing thresholds after seeing results. If the method fails those targets,
publish the limitations rather than claim an improvement.

## Proposed six-month schedule

| Month | Planned deliverable |
| --- | --- |
| 1 | Confirm mentor/reviewer, permissions and pilot eligibility |
| 2 | Annotate development set and freeze schema, prompts and split |
| 3 | Assemble held-out annotations and run initial model comparisons |
| 4 | Complete comparisons, repetitions and error analysis |
| 5 | Run reviewer-time pilot and improve traceability tooling |
| 6 | Release permitted annotations, code and an honest evaluation report |

## API credit request assumptions

A provisional request of **US$300 in API credits over six months** is a planning
estimate, not a claim of actual expenditure or eligibility.

At 100 articles × 3 prompt configurations × 2 models × 2 repetitions, the main
comparison requires 1,200 calls. Assuming 6,000 input and 800 output tokens per
call, this is approximately 7.2 million input and 0.96 million output tokens.
A 30% allowance for development and deliberate reruns raises those totals to
9.36 million and 1.248 million. The application itself disables automatic retries.

Update the token assumptions after the pilot. Calculate the request using actual
model rates and observed usage before submitting. Reduce corpus size or request
if the pilot does not justify the proposed scope. No maximum grant amount is
being requested merely because it is available.

## Limits and next decisions

This is a literature extraction project. It makes no claim of novel emulsion
chemistry, improved treatment, clinical safety or experimental validation.
Its scientific value depends on reliable annotations and a useful comparison,
which still need to be established. A confirmed research supervisor or collaborator
would strengthen both the study and programme eligibility.

## Starting references

These are real paper leads, not work produced or processed by this project:

1. *pH-controllable stability of iron oxide@chitosan nanocomposite-stabilized
   magnetic Pickering emulsions* (2023), DOI
   [10.1016/j.eurpolymj.2023.111870](https://doi.org/10.1016/j.eurpolymj.2023.111870).
2. He and colleagues, *pH/magnetic dual responsive Pickering emulsion stabilized
   by Fe3O4@SiO2@chitosan nanoparticles* (2023), DOI
   [10.1039/d3cp03400c](https://doi.org/10.1039/d3cp03400c),
   [PubMed record](https://pubmed.ncbi.nlm.nih.gov/37724345/).
