# Validation receipt

Reviewed 2026-10-05. Public-source assessment edition 2026-10-05.

- 22 offline regression checks passed.
- Ledger: 10 primary-source records, 9 attributed records, 4 analysis judgments, 3 competing hypotheses, 2 organization identifiers.
- Claim statuses remain separate: assessment, designation, administrative action, allegation, reported judicial outcome, oversight finding, academic model, and academic critique.
- Invalid evidence promotion, dangling references, duplicate identifiers, unsupported fields, malformed dates, wrong publisher URLs, and removed assistance metadata were rejected.
- Generated HTML, assessment text, summary, manifest, and archive matched the checked-in artifacts.
- Archive: 12 allowlisted members, fixed timestamps, stable ZIP metadata, byte-identical regeneration. Stored entries avoid dependence on compression-library versions.
- No legacy fixtures, personal profiles, private companion contents, or local workstation paths occur in the public assessment or package.
- Original manifest: 11 of 11 archived result files and Windows CRLF checkout files match; only 1 of 11 normalized raw Git blobs matches. Original archive: 21 members. Original commit: `a39b96f3e7b4029d32f1b72c8059e4b1e4a44ee7`. New text artifacts enforce LF.

Run the commands in `README.md` to reproduce the checks. The package manifest covers 11 artifacts; the twelfth ZIP member is that manifest. The manifest does not recursively hash itself or the ZIP.

This receipt establishes local structural and artifact checks, not source truth, full-model replication, current sanctions screening, signed court-record retrieval, agency acceptance, or publication of the draft branch to GitHub Pages.
