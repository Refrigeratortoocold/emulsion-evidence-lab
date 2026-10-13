# Data provenance

## Real reference sequence

`reference.json` contains the exact reference for
`GFP_AEQVI_Sarkisyan_2016`, retrieved from the official ProteinGym
`reference_files/DMS_substitutions.csv` on 13 October 2026.

- Source: https://github.com/OATML-Markslab/ProteinGym/blob/main/reference_files/DMS_substitutions.csv
- Source blob SHA: `8d1ea9a19c0404b511cd24378b25c2a5f86f10e9`
- Organism: Aequorea victoria.
- Sequence length: 238 amino acids.
- Exact assay reference: use this background for mutation numbering and validation.
- Upstream licence: MIT; the original notice is retained in `PROTEINGYM_LICENSE.txt`.

The permitted mutation region and the protected positions define this project's
initial design constraints. The protected motif is `SYG` at positions 65–67.

## Synthetic software fixture

`synthetic_assay.csv` contains nine invented mutation/score examples built from
the real reference sequence. Their `DMS_score` values are made up solely for
software verification. They are not values measured by Sarkisyan and colleagues,
ProteinGym, the maintainer or a laboratory.

Eight examples meet the project's design constraints. One changes a protected
position so the pipeline can verify exclusion accounting. Generated example
reports explicitly label these assay scores as synthetic.

## Actual experimental measurements

The full published assay is not bundled. Obtain it from the official ProteinGym
resources, record its release and provenance, and supply it locally to `prepare`
and `evaluate`. Label published data explicitly with `--data-kind published`.

Required columns: `mutant`, `mutated_sequence`, `DMS_score`. Larger DMS scores
represent higher assay fitness in the ProteinGym convention. Keep the original
measurement interpretation and licence with the imported dataset. `prepare`
withholds measured scores from the candidate input; `evaluate` loads them later.

Store downloaded or restricted data in `private_data/`, which is excluded from git.
