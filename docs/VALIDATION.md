# Software validation

Checked on 13 October 2026 using Python 3.12.14.

Twenty offline tests passed. They cover reference-sequence identity, canonical
substitution parsing, protected residues, mutation budgets, reproducibility,
measured-label separation, exclusion accounting, tie-aware correlation,
normalised ranking metrics, assay-hash consistency, malformed Claude scores,
HTML escaping and complete command-line demo execution.

Mocked Claude calls verified that measured labels are absent from the model
payload, automatic retries are disabled, and model/token metadata is recorded.
No real Claude request was made in this verification.

The public ProteinGym reference sequence and its source blob were retrieved and
checked. The full experimental assay was not downloaded or evaluated. The demo
uses invented fluorescence scores solely to exercise the software pipeline.

The GitHub Actions workflow runs the tests and demo on Python 3.11 and 3.12.
Check the repository's Actions page for the result of each published commit.
Scientific validation still requires the actual assay comparison described in
the research plan.
