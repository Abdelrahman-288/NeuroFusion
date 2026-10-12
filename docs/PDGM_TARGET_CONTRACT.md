# UCSF candidate target contract and compatibility review

2026-10-08. Candidate configuration: configs/ucsf_target_contract.json.
Evidence and native-mask inventory: experiments/pdgm-target-contract-001.

The [official BraTS 2021 source](https://www.med.upenn.edu/cbica/brats2021/)
explicitly identifies 1 as necrotic core, 2 as edematous/invaded tissue and 4 as
enhancing tumor. Its region definitions imply ET={4}, TC={1,4}, WT={1,2,4}.
These are the candidate unions implemented for annotation QA.

The [TCIA UCSF collection](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/)
links its annotation process to BraTS 2021 and describes enhancing,
non-enhancing/necrotic and surrounding FLAIR-abnormality compartments. The
previously archived official page was used; the live page again returned HTTP
500 during this review. Applying the BraTS numeric mapping to UCSF version 5 is
an inference from these sources, not explicit version-specific confirmation.
The candidate contract deliberately retains version_specific_mapping_confirmed=false.

## Compatibility finding

Our current compact 2D U-Net (experiments/tumor-seg-001/last.pt) was trained on
binary BRISC foreground masks. The available training contract does not establish
which UCSF compartment or union that foreground represents. Do not relabel its
single probability map as three distinct region predictions or automatically
score it against WT/TC/ET as if those were its trained targets. A future model or
evaluation protocol must define a defensible matching target first.

## Implemented checks

candidate_regions validates finite 3D masks with exactly permitted numeric IDs,
then constructs nested Boolean unions without changing source files. Twenty
original-resolution pilot masks were inventoried with source checksum verification.
Numeric voxel counts are candidate annotation summaries, not certified tumor volumes.
Absent regions are retained as empty arrays, not interpreted as a healthy diagnosis.

require_evaluation_contract rejects missing version confirmation, target equivalence
or protocol readiness. It is a helper for a future evaluation runner, not a claim
that every existing inference endpoint now uses it. The actual candidate contract
was tested and rejected as expected. No inference, scoring or promotion occurred.

Next: obtain explicit UCSF version-specific mapping confirmation, review anatomical
alignment, establish patient/source independence and select a compatible task/model
before freezing an evaluation protocol. Pilot development use remains documented;
it is not an untouched test cohort. Overall scope estimate stays approximately 83%.

Target-contract validation: full regression **164 tests passed**, including nine new union, invalid-label, empty-region and evaluation-gate checks.
