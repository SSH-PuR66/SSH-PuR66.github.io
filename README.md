# CARTELKIT: open the model, check the claim

An executable research workbench for auditing published cartel models. The current edition independently recalculates sentence assignment from a pinned author dataset, traces three implementation questions to exact R source lines, and examines the scale assumptions in the full 2023 network equation.

[Open the workbench](https://ssh-pur66.github.io/cartelkit/) · [Research note](cartelkit/MODEL-AUDIT.md) · [Aggregate data and code findings](cartelkit/model-audit.json) · [Institutional context](cartelkit/ASSESSMENT.md)

The author-supplied extract contains 40,297 sentence records. Its unweighted mean is 20.085401 years; the expected mean under the published inverse-length sampling rule is 8.713438 years. Reproducing that calculation does not reproduce the full cohort model or its policy conclusions. Source inspection identifies questions about the post-release calendar index, the life-limit cap, and the sentence-multiplier domain. Their effect on published figures remains unmeasured.

The population-scale explorer is an exact conditional transformation of the full 2023 equations, checked with rational arithmetic and numerical trajectories. It is not a new headcount estimate or proof of non-identifiability with fixed absolute inputs. The 5 October institutional ledger remains available as dated context.

The previous site presented synthetic text, wallet, and radio fixtures as a terminal-style dossier. Those fixtures are retired from the current public package and provide no evidence for this assessment. [The audit](cartelkit/legacy-audit.json) records the original commit, artifact hashes, and limitations; Git history preserves the original files.

AI assisted the research, editing, and software preparation. This AI-assisted study should not be submitted as a CIA writing/portfolio sample; [CIA applicant guidance](https://www.cia.gov/careers/cia-requirements/) prohibits AI use for those submissions.

## Reproduce locally

Python 3.10+ and Node.js 22+; no third-party packages. Run from the repository root:

```sh
python cartelkit/model_audit.py --fetch
python cartelkit/model_audit.py --check
python cartelkit/cartelkit.py check
python -m unittest discover -s cartelkit -p 'test_*.py' -v
node --test cartelkit/audit-math.test.cjs
python cartelkit/cartelkit.py package
git diff --exit-code -- cartelkit/index.html cartelkit/dossier.html cartelkit/summary.json cartelkit/MANIFEST.sha256 cartelkit/cartelkit_deliverable.zip
```

The explicit `--fetch` downloads two public, immutable upstream files and rejects any hash mismatch. Other commands are offline. They verify source identity, calculations, status boundaries, the static build, and the reproducible archive. Only sentence/count aggregates enter the public package. Passing checks establish structural consistency and artifact identity; they do not establish factual corroboration, complete coverage, current sanctions status, or institutional endorsement.
