# AI for Science application draft

Review and adapt this proposal to the current application questions. Confirm your
academic contact, actual research attachment and Claude Console organisation ID
before submission. This file is a proposal, not a submitted or approved application.

## Project title

Claude-Assisted Protein Design: Generating and Prioritising Green Fluorescent
Protein Variants Against a Public Experimental Fitness Landscape

## Applicant and project status

My name is Soh Jia Sheng. I am a Life Sciences undergraduate at the National
University of Singapore, with an interest in computational biology and protein
engineering. I am developing an independent computational prototype to investigate
how generative AI can support fluorescent-protein design.

The repository currently contains a working constrained variant generator,
optional Claude API integration, ranking baselines, benchmark-data preparation and
evaluation code. Twenty offline tests and a synthetic end-to-end demonstration
have been completed. I have not yet run a live Claude comparison on the published
GFP assay or performed laboratory validation. Project supervision and research
collaboration are not currently confirmed.

## Research question and scientific value

Can Claude generate sequence-valid GFP design hypotheses and prioritise variants
with high measured fluorescence more effectively than simple baselines?

Fluorescent proteins provide a concrete biological design problem. The public
GFP fitness landscape reported by Sarkisyan and colleagues offers experimental
measurements with which to assess prioritisation. This makes it possible to test
whether a general-purpose language model contributes useful design reasoning,
rather than assuming that its plausible explanations reflect biological accuracy.

The study will first rank measured variants while withholding their assay scores
from Claude. It will then examine constrained, unmeasured design proposals for
validity, diversity and uncertainty. Prospective candidates will remain hypotheses
until actual fluorescence evidence becomes available.

## How Claude will be used

Claude will receive the exact assay reference sequence, permitted mutation region
and protected residues. It will propose amino acid substitutions and provide
concise, uncertainty-aware rationales. In the ranking experiment, it will score
specified variants without receiving experimental labels.

Local validation checks reference residues, mutation positions, the sequence
alphabet and mutation budget. Model IDs, prompt hashes and API token usage will
be recorded. The API makes repeated comparisons and structured outputs practical.
Specialised protein models will provide an additional comparator when the relevant
scores or computing resources are available.

## Evaluation and planned outputs

The proposed evaluation uses random ranking and mutation-distance ranking as
initial controls, with the same eligible variants across methods. The main
comparison will measure top-k enrichment, rank correlation, nDCG, invalid-output
rate, diversity, repeatability and API use. Single and combined substitutions
will be analysed separately.

I plan to start with a small pilot, freeze the comparison rules, and then target
2,000 eligible measured variants if the pilot and budget justify that scope.
Repeated model runs and shuffled candidate orders will assess sensitivity to
batching and prompt presentation. Published-benchmark contamination will be
acknowledged, and retrospective performance will not be described as proof of
novel experimental improvements.

I aim to release the code, permitted candidate outputs and a reproducible
evaluation report describing both useful results and failures.

## Credit request and timeline

I provisionally request US$300 in API credits for a six-month pilot and evaluation.
I will revise the experimental scope after measuring real token use and checking
current model pricing. The first two months will establish the dataset, prompts
and comparison procedure. The next two will run the main evaluation. The final
two will examine prospective proposals, error patterns and reproducibility.

## Details to confirm

| Item | Entry |
| --- | --- |
| Repository | https://github.com/Refrigeratortoocold/claude-protein-design |
| Academic email | Enter your actual academic email |
| Research attachment or supervisor | Unconfirmed; add only a genuine agreed arrangement |
| Claude Console organisation ID | Enter the actual organisation receiving credits |
| Completed biological results | None claimed at this stage |

Anthropic prioritises biology and life sciences, and evaluates scientific merit,
impact, feasibility and team credentials. Confirm how your actual research
attachment meets its criteria using the
[official programme page](https://support.claude.com/en/articles/11199177-anthropic-s-ai-for-science-program).
