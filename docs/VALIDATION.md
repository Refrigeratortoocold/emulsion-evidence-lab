# Initial validation

Checked on 13 October 2026 using Python 3.12.14.

The initial offline verification passed 23 tests covering the complete extraction
and evaluation workflow, missing information, decimal and Unicode handling,
particle-versus-droplet distinctions, fabricated quotes, source hashes,
character-offset tampering, evaluation denominators, HTML escaping and input
provenance. Mocked Claude tests checked configured model use, token metadata,
disabled retries and rejection of a truncated response.

The command-line demo and evaluation were also run. The four fixtures contain
28 field slots. The regex baseline matched their manually specified expected
values. This deliberately small synthetic example is not a scientific benchmark.

The CI workflow is prepared for Python 3.11 and 3.12 and will run on GitHub after
the project files are uploaded. Check the repository's Actions page for the actual
run status. No live API request was made; no credit was spent in validation.
Real Claude compatibility and accuracy require an actual permitted pilot run
with an API key.

The generated HTML report was checked for its synthetic-data label and escaped
content. Quote presence is explicitly insufficient to establish semantic support.
Full scientific annotation, source licensing decisions and institutional research
attachment remain outside the completed software verification.
