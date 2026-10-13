# Research plan: Claude-assisted fluorescent-protein design

Status: proposed computational study. Software verification is complete on toy
data; biological performance remains untested.

## Biological motivation

Fluorescent proteins are useful biological reporters. Changing their sequence can
change fluorescence, but mutational effects depend on the starting sequence and
combinations of substitutions. A model that helps prioritise promising variants
could make protein-engineering experiments more selective.

The first case study uses the public GFP assay from Sarkisyan and colleagues,
represented by ProteinGym. Its experimental fluorescence measurements provide
a basis for testing rankings without first requiring a laboratory campaign.
The reference sequence is pinned to the official assay metadata and is already
included in this repository.

## Main hypothesis and endpoints

Hypothesis: Claude can prioritise high-fluorescence variants more effectively
than random ranking and a mutation-distance baseline, while respecting explicit
sequence constraints and articulating useful uncertainty.

Primary endpoint: top-k enrichment or hit rate on measured variants, with the
cutoff and k chosen before the held-out evaluation.

Secondary endpoints: Spearman correlation, nDCG, mean top-k assay score, invalid
output rate, candidate diversity, repeatability and API cost. Analyse single,
double and triple substitutions separately so mutation-count differences do not
create a misleading apparent advantage.

## Two complementary workstreams

**Retrospective prioritisation:** sample measured GFP variants, withhold their
assay scores, obtain model rankings, then compare against the hidden measurements.
Use the same eligible candidate pool for every method. This is the first feasible
scientific experiment supported by the current code.

**Prospective design:** ask Claude to propose substitutions within the same
constraints, record its hypotheses, and compare proposal validity and diversity
with matched random proposals. These candidates have no assigned measured fitness.
Any novel proposal's fluorescence requires a new measurement or another documented
source of experimental evidence. Retrospective scores cannot substitute for that.

## Dataset and controls

1. Obtain the official `GFP_AEQVI_Sarkisyan_2016.csv` assay file and record its
   release, retrieval date, licence and SHA-256 hash.
2. Verify all mutation descriptors and mutated sequences against the included
   reference. Use at most three substitutions and preserve residues 65–67 for
   the initial design scope. Report all exclusions.
3. Use a small development pool for prompt refinement. Freeze prompts, model
   IDs, candidate-selection rules, hit threshold and budget before evaluation.
4. Target an evaluation pool of 2,000 eligible variants, subject to a pilot and
   data availability. Hold development genotypes out of the evaluation pool.
   Examine related genotypes and overlapping mutation backgrounds separately.
5. Compare random ranking, fewer-substitutions ranking and two Claude model IDs.
   Add a protein-specific language-model baseline from ProteinGym when the
   necessary scores or compute are available. That adapter is not implemented yet.
6. Repeat model rankings with multiple candidate orders and batch assignments.
   The current scoring batches contain up to ten candidates, so cross-batch
   score comparability must be tested rather than assumed.
7. Measure both invalid-output rate and API cost over all attempted calls.
   The initial scorer aborts on an invalid batch; a complete run/failure logger
   must be added before the main comparison.

The current `prepare` command implements seeded sampling and label separation.
Development/evaluation split orchestration, grouped analyses, confidence
intervals and the protein-specific model adapter remain planned work.

## Interpretation limits

The assay measures fluorescence in its original experimental setting. It does
not independently establish molecular brightness, folding stability, toxicity,
expression or performance in every cell type. Interpret results as assay-specific.

The published GFP landscape may appear in a language model's training data.
Keeping labels out of the prompt prevents direct label leakage but does not
demonstrate that the model has never seen the benchmark. Report retrospective
results accordingly; do not claim de novo novelty from rediscovered substitutions.

Validation against independent experiments would require a qualified laboratory
collaborator. No collaborator, wet-lab access or supervisor is currently confirmed.
The initial project can proceed as a computational evaluation.

## Six-month milestones

| Month | Planned output |
| --- | --- |
| 1 | Corpus provenance, mentor/reviewer discussions and a small assay pilot |
| 2 | Frozen prompts, models, pools and failure-accounting procedure |
| 3 | Blinded ranking comparisons and mutation-count controls |
| 4 | Repeatability, ordering sensitivity and error analysis |
| 5 | Prospective proposal study and protein-model comparison if feasible |
| 6 | Reproducible evaluation report and release of permitted outputs |

## API use and provisional request

A provisional request of **US$300 in API credits** would support the pilot and
first comparison. The final request should use measured token usage and current
model prices rather than the programme's maximum award.

For planning, 2,000 variants divided into batches of ten gives 200 scoring calls
per configuration. Two models, two prompt configurations and three repeats would
produce 2,400 calls, plus a smaller proposal pilot. Pilot token accounting will
determine whether this full scope fits the credit request; reduce the pool or
repeat count if necessary. These calls have not been made.

## Scientific references

- [Sarkisyan et al., Nature (2016)](https://doi.org/10.1038/nature17995).
- [ProteinGym paper](https://papers.nips.cc/paper_files/paper/2023/hash/cac723e5ff29f65e3fcbb0739ae91bee-Abstract-Datasets_and_Benchmarks.html).
- [Official assay metadata](https://github.com/OATML-Markslab/ProteinGym/blob/main/reference_files/DMS_substitutions.csv).
