# UCSF-PDGM transfer setup checkpoint

Resolved 2026-10-08: Aspera installation verified and the first pilot MRI/mask pair downloaded and imported. See `PDGM_FIRST_IMPORT.md`. The entries below are historical setup checkpoints.

Checked 2026-10-07. The official Aspera package is now browsable; the earlier page
unavailability is no longer the immediate blocker. The package heading is
`UCSF-PDGM Version 5` (package 1065).

Navigated to the first preselected import-pilot exam:
`UCSF-PDGM-v5/UCSF-PDGM-0200_nifti`. The listing exposes both
`UCSF-PDGM-0200_T1c.nii.gz` and `UCSF-PDGM-0200_T1c_bias.nii.gz`.
The download action on the T1c file returned the IBM Aspera client setup prompt.
No completed transfer was shown. The page's package status "Completed" refers
to the source package, not a successful local download.

No Aspera installation was found in Windows uninstall entries, the `ascp` command
lookup, or the standard LocalAppData locations checked. The source page offers
Windows x64 User and System installers. The proposed action is the official
per-user client installation, followed by downloading the recorded pilot's image
and mask files into the project. No installation, license acceptance, or background
transfer occurred in this stage.

Browser-action rules require explicit approval for installing vendor software
when that specific installation was not previously authorized. Any binding license
acceptance must be handled separately when the exact agreement is displayed.

Evidence: `experiments/pdgm-transfer-check-001/status.json` and
`aspera-setup.png`. MRI files acquired: **0**. Overall estimated implementation
progress stays **80%**. Latest code regression result remains 146 passed from the
calibration stage; no code was changed or new model evaluation performed here.

Next: install/launch the client after authorization, verify one pilot transfer,
record file hashes, acquire the paired segmentation, then run the existing importer
and review real image/mask alignment. Do not treat filename discovery as modality
verification or a completed data acquisition.

## Installer acquisition update

The official per-user installer was downloaded to `C:\Users\abdel\Downloads\ibm-aspera-desktop-1.1.1-x64.exe` (30,408,408 bytes). Windows Authenticode validation passed with IBM as signer. SHA256 and status are in `experiments/aspera-installer-001/status.json`. The installer was not launched: Windows Computer Use failed to initialize with a missing-path kernel-assets error, including after reset. User installation is required to unblock UI setup; no license was accepted and no MRI transfer started. Existing installation authorization is retained; this is a tooling handoff, not a renewed permission request.
