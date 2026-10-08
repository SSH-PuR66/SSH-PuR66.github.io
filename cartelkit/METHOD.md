# Method and limitations

## Edition 02: executable model audit

The 8 October 2026 workbench is documented separately in [MODEL-AUDIT.md](MODEL-AUDIT.md). It recalculates the 2025 author code’s sentence assignment from its pinned data extract, inspects three implementation questions, checks a scale transformation of the full 2023 equations, and re-expresses the 2023 policy comparison. It does not run the complete models. The institutional ledger and its 5 October coverage below remain unchanged.


## Research question

What do selected public institutional records establish about Sinaloa and CJNG, and how much can those records tell us about the effectiveness of the response?

The sample is purposive, not exhaustive. Sources were chosen for a defined role: DEA's assessment, State's published designation notice, Treasury's sanctions announcement, two DOJ announcements with different legal statuses, two GAO oversight reports, an academic model and critique, and CIA's applicant policy. The two DOJ announcements concern different cases. The number of documents is not an independent confirmation count.

## Collection and citation

Review date: 2026-10-05. Each source has a stable identifier, publisher, direct URL, publication date where established, document type, paragraph or section locator, review date, limitations, and an independence group. Records cite source IDs; analysis cites record IDs. No private companion repository was used.

The study summarizes short passages instead of mirroring documents. Selected academic full-text sections were reviewed: the original arXiv v1 section 2.2 and Figure 4, and the critique's model-identification discussion. No independent model reproduction was performed. The original v1 was not independently collated against the final Science article, which the critique addresses. The model's publication date is unasserted rather than guessed from conflicting metadata. The comment is one author's argument, not an adjudicated refutation or established consensus.

The publication date for DEA's assessment comes from its [May 13, 2025 landing page](https://www.dea.gov/es/node/230891); the ledger links the agency-hosted report. State's designation notice gives its February 20, 2025 publication date and effective-on-publication language. Administrative or legal status is recorded as of the cited document, not as a current screening result.

## Evidence status

| Status | What the cited document supplies | Limit |
| --- | --- | --- |
| `agency_assessment` | An agency's dated assessment | Not a newly measured market share or criminal verdict |
| `official_designation` | A published designation under a named authority | Not a finding that every alleged member committed a crime |
| `administrative_action` | Treasury's sanctions announcement | Not a criminal conviction or independently measured policy effect |
| `allegation` | A DOJ account of charges | Defendants are presumed innocent; later dispositions were not checked |
| `judicial_outcome_reported` | DOJ's report of a guilty plea | Signed plea and judgment were not independently retrieved |
| `oversight_finding` | GAO's stated audit finding within its scope | Historical deficiencies and sampled findings do not imply universal current failure |
| `academic_model` | Published scenario outputs at identified full-text locations | Not observed effects, an independent reproduction, or a current capacity measurement |
| `academic_critique` | A stated criticism of the model | Not a settled refutation; peer review and subsequent response not established |
| `analysis` | This study's interpretation linked to records | Not an additional independent source |

Organization IDs apply only where the source supports that organizational scope. GAO and academic context records have an empty `org_ids` array. Public officials' or defendants' names, personal contact data, wallet addresses, operational routes, and private-person profiles are not part of this dataset.

## Original artifact audit

The original commit presented explicitly synthetic text, wallet, and radio fixtures. Its eleven listed hashes match the original Windows CRLF checkout and all eleven archived result files. Only one raw Git blob matches: Git normalized line endings in ten text files. The new artifacts enforce LF explicitly. Hash agreement establishes byte identity within that scope, not evidentiary truth. The original archive contained twenty-one members, including `demo_tape` fixtures.

The lexical priority scores had no measured precision or calibration. Wallet formatting and checksum checks did not establish attribution. Transaction heuristics did not establish common ownership without assumptions and exceptions. Date-level cross-domain co-occurrence did not establish a shared actor. Radio-tone detection did not establish identity. The public terminal presentation and distribution marking gave these fixtures more apparent authority than their provenance warranted.

The current branch removes those fixtures and replaces the public archive with the study, its generator, tests, and manifest. Git history and `legacy-audit.json` preserve the original provenance. The audit contains no private local paths or purported actor identifiers.

## Reproduction and validation

The offline Python generator accepts only a small explicit schema. It checks dates, unique IDs, citation resolution, organization references, evidence/source-type compatibility, expected publisher domains, and AI-assistance metadata. It escapes text into static HTML and generates counts directly from the ledger. The ZIP uses fixed entry timestamps and includes only the artifact allowlist.

Run the commands in `README.md`. A deterministic rebuild should leave the generated files unchanged. The regression suite also checks malformed records, claim-status inflation, injection escaping, internal citations, the package inventory, and SHA-256 consistency. Neither validation nor a hash proves that a source is true, independent, complete, unchanged on the web, or sufficient to settle a question.

## What remains unverified

- The later court dispositions and signed court records for the DOJ examples.
- Current designation and sanctions-list entries beyond the historical notices cited here.
- The causal effectiveness of sanctions or arrests; document counts are not effect estimates.
- Independent reproduction of the full academic model, adjudication of its identification assumptions, later responses, and collation with the final publisher version.
- Exhaustive coverage of Mexican organized crime, international scholarship, or subsequent policy changes.

AI assisted preparation. CIA prohibits AI use in submitted writing or portfolio samples; this AI-assisted study should not be submitted as a CIA writing/portfolio sample. The author must verify the sources and produce any application work under that institution's rules.
