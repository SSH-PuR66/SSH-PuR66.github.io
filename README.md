# Cartels and the institutional record

A dated, organization-level public-source assessment of Sinaloa and CJNG. The ledger separates agency assessments, official designations, sanctions, allegations, reported court outcomes, and academic work. Research judgments are labeled as analysis and link back to the records they use.

[Read the study](https://ssh-pur66.github.io/cartelkit/) · [Assessment](cartelkit/ASSESSMENT.md) · [Citation ledger](cartelkit/research.json) · [Method](cartelkit/METHOD.md)

The previous site presented synthetic text, wallet, and radio fixtures as a terminal-style dossier. Those fixtures are retired from the current public package and provide no evidence for this assessment. [The audit](cartelkit/legacy-audit.json) records the original commit, artifact hashes, and limitations; Git history preserves the original files.

AI assisted the research, editing, and software preparation. This AI-assisted study should not be submitted as a CIA writing/portfolio sample; [CIA applicant guidance](https://www.cia.gov/careers/cia-requirements/) prohibits AI use for those submissions.

## Reproduce locally

Python 3.10 or later; standard library only. Run from the repository root:

```sh
python cartelkit/cartelkit.py check
python -m unittest discover -s cartelkit -p 'test_*.py' -v
python cartelkit/cartelkit.py package
git diff --exit-code -- cartelkit/index.html cartelkit/dossier.html cartelkit/summary.json cartelkit/MANIFEST.sha256 cartelkit/cartelkit_deliverable.zip
```

These commands validate references and evidence types, rebuild the static study, and reproduce the archive. They make no network requests. Passing checks establish structural consistency and artifact identity; they do not establish factual corroboration, complete coverage, current sanctions status, or institutional endorsement.
