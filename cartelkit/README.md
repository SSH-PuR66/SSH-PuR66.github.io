# CARTELKIT: model audit and institutional context

Workbench edition: 2026-10-08. Institutional ledger: 2026-10-05. Two organizations, ten sources, nine attributed records, and four research judgments. Oversight and academic records provide institutional or methodological context; they are not attributed to a cartel.

## Read the files

- `MODEL-AUDIT.md`: findings, proof, primary-source links and reproduction commands.
- `model-audit.json`: source hashes, 804 sentence/count aggregates, numerical receipt and code findings.
- `model_audit.py`: independent, hash-pinned aggregate extraction and equation checks.
- `audit-math.js`, `audit-app.js`, `audit.css`, `audit-panel.html`: the browser workbench.
- `test_model_audit.py`, `audit-math.test.cjs`: calculation and boundary tests.


- `ASSESSMENT.md`: the research question, judgments, competing explanations, and gaps.
- `research.json`: the source ledger, dated records, analysis links, and open questions.
- `METHOD.md`: source selection, classification, limitations, and reproduction.
- `index.html`: the static study generated from the ledger.
- `summary.json`: generated counts and validation scope.
- `legacy-audit.json`: original synthetic package hashes and quality audit.
- `MANIFEST.sha256`: SHA-256 of each current package artifact.
- `cartelkit_deliverable.zip`: the public study, with fixed ZIP timestamps.
- `dossier.html`: compatibility redirect to the current study.

## Verify and build

Python 3.10+ and Node.js 22+, no third-party packages. From this directory:

```sh
python model_audit.py --fetch
python model_audit.py --check
python cartelkit.py check
python -m unittest discover -p 'test_*.py' -v
node --test audit-math.test.cjs
python cartelkit.py package
```

`check` validates the ledger without writing files. `build` generates HTML and counts. `package` builds the study, hashes the artifacts, and replaces the ZIP. The explicit audit `--fetch` retrieves the fixed author CSV and R revision to ignored local storage; the package excludes those raw files. All other commands are offline. See the research note for the precise calculation and model boundaries.

Checks enforce explicit evidence status, resolvable citations, dated sources, organization IDs, a limited public schema, and publisher domains. Host matching identifies the expected publisher; it does not verify the document's contents. Manual review of the cited source is still required.

## Authorship

AI assisted the research, editing, and software preparation. The author must independently verify and explain the work. This AI-assisted study should not be submitted as a CIA writing/portfolio sample; [CIA applicant guidance](https://www.cia.gov/careers/cia-requirements/) prohibits AI use for those submissions. The study makes no claim of government affiliation, acceptance, or endorsement.
