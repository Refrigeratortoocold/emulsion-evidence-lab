# AI for Science application draft

This is a proposal to review and adapt, not a submitted application. The public
form's first page was checked; later form questions were not available in that
read. The sections below are reusable proposal text rather than a claim to mirror
every current form field.

Before submission, confirm your current academic details, actual project role,
research attachment, available reviewer, repository URL and API organisation ID.
Do not list a supervisor, laboratory or collaborator without their agreement.

## Project title

Emulsion Evidence Lab: Evaluating Claude for Evidence-Linked Extraction of
Stimuli-Responsive Pickering Emulsion Research

## Applicant background

My name is Soh Jia Sheng. I am a Life Sciences undergraduate at the National
University of Singapore. My earlier project experience includes studying iron
oxide–chitosan nanocomposite Pickering emulsions. This motivated my interest in
how researchers compare reported material properties and experimental observations
across studies.

The current project is an independent prototype. I am seeking a qualified academic
mentor or collaborator to help refine the evaluation and review annotations. I do
not currently claim a confirmed project supervisor or institutional endorsement.

## Project summary

I propose to evaluate whether Claude can improve the extraction of reported
properties from research on stimuli-responsive Pickering emulsions. The workflow
will organise stabilizer materials, oil phases, pH conditions, droplet measurements,
stability observations, magnetic responses and cargo-release observations. Each
extracted value will retain an exact supporting passage for human review.

I have prepared a Python prototype with a deterministic baseline, optional Claude
API integration, source quotation checks, provenance hashes and a local review
report. It has been verified using four explicitly synthetic fixtures and offline
tests. No live Claude performance or real-paper accuracy result is claimed yet.

## Why Claude and why API access

Scientific descriptions vary in wording and often require context to distinguish
different measurements. A simple pattern matcher is limited to predefined words
and phrases. I want to test whether Claude can extract useful observations from
more varied passages while avoiding unsupported values.

API access would support repeatable comparisons across recorded model IDs and
prompt versions. It would also allow token usage to be logged alongside results.
The study will measure Claude's value rather than assume that it outperforms the
baseline. Exact quotations will remain subject to expert interpretation.

## Proposed evaluation and contribution

I plan to begin with a small corpus pilot, then target 100 eligible papers if
permissions, annotations and reviewer availability allow. Twenty articles would
be used for development and eighty reserved for evaluation. Planned comparisons
include a regex baseline, two Claude models, three prompt configurations and two
repetitions.

The main outcomes would be extraction precision and recall, human-rated semantic
support, invalid-output rate, reviewer time and API use. I would publish the code,
evaluation procedure and any annotations permitted by source licences. The aim
is a reproducible assessment of a literature extraction workflow. The project
does not claim to discover a new drug delivery formulation.

## Credit request and schedule

I provisionally request US$300 in API credits for a six-month pilot and evaluation.
The proposed main comparison comprises approximately 1,200 calls. Assuming 6,000
input and 800 output tokens per call, the estimated main use is 7.2 million input
and 0.96 million output tokens. I will revise the request after measuring pilot
usage and checking current model pricing.

The first two months would establish reviewer participation, permissions and
reference annotations. The next two would run comparisons and analyse errors.
The final two would evaluate reviewer time and prepare a reproducible release.

## Details to complete accurately

| Item | Current state |
| --- | --- |
| Academic contact email | Enter your actual academic email; not invented here |
| Research group or supervisor | Unconfirmed; do not present student enrolment as project supervision |
| Repository URL | https://github.com/Refrigeratortoocold/emulsion-evidence-lab |
| Claude Console organisation ID | Enter the actual organisation receiving credits |
| Research credentials | Link real project evidence or a CV, if requested |
| Reference annotations and live results | Planned; not completed |

The official programme is intended for institution-attached researchers and
evaluates team credentials as well as the project. Student status and a prototype
alone do not confirm eligibility. Review the
[official programme description](https://support.claude.com/en/articles/11199177-anthropic-s-ai-for-science-program)
and the
[application form](https://docs.google.com/forms/d/e/1FAIpQLSfwDGfVg2lHJ0cc0oF_ilEnjvr_r4_paYi7VLlr5cLNXASdvA/viewform)
before submitting.
