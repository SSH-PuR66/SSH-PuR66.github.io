# CARTELKIT: what the model assumes, and what its code computes

Reviewed 8 October 2026. Independent analysis of version-pinned public research. No claim of a new cartel headcount, first discovery, or full model replication.

## Finding 1: the supplied sentence assignment is reproducible

The [2025 preprint](https://arxiv.org/html/2512.17973v1), section 4.4 and Supplementary B, explains why longer sentences are overrepresented in a prison-stock survey. The linked [author repository](https://github.com/rafaelprietocuriel/IncarcerationAndRehabilitation/tree/224e9cc9382672cd6e48b3de830afbe9706b3d0a) supplies an ENPOL extract and R implementation.

We retrieved both files at commit `224e9cc9382672cd6e48b3de830afbe9706b3d0a`, verified their SHA-256 identities, read the supplied sentence column, and computed expectations directly. No stochastic sampling is necessary for this calculation.

| Quantity | Independently calculated |
| --- | ---: |
| Included rows | 40,297 |
| Unweighted extract mean | 20.085401 years |
| Expected mean under the code's inverse-length assignment | 8.713438 years |
| Minimum supplied length | about 1 month |
| Maximum supplied length | 89.583333 years |

For sentence lengths s with counts n, assignment probability is proportional to n/s. The expected assigned length is therefore sum(n) / sum(n/s), the harmonic mean of the supplied row values. This agrees with the paper's approximately 8.7-year result at the level of its input sampling rule. It does not reproduce its cohort population, recidivism simulation, crimes-averted measure, or policy effects.

The public aggregate retains only sentence lengths and counts. It excludes the CSV's person identifiers, states and offence columns. The author-prepared extract was not independently reconstructed from original INEGI microdata. Equal row weights and inverse sentence-length weights are not the survey's population expansion weights. The correction requires assumptions about admissions, time served, censoring and population composition; it is not a direct observation of cartel sentences.

### The lifetime cap is a separate calculation

The paper uses age 69 as a fixed life limit. At selected incarceration age a and sentence multiplier alpha, this audit compares E[alpha s] with E[min(alpha s, 69-a)]. Assignment probabilities remain proportional to 1/s, matching the upstream code's order: sample first, then multiply. The selected age is a sensitivity slice, not the paper's full age distribution. Changing age cannot change the assigned-sentence expectation; it changes the cap.

The difference is the expected number of assigned years beyond the assumed life limit. It is not a new estimate of actual time served or a recalculated crime reduction.

## Finding 2: three implementation questions deserve a bounded rerun

All line references identify the exact linked revision, rather than moving main.

1. **The post-release calendar lookup does not advance.** In [`Recidiv`, lines 303–328](https://github.com/rafaelprietocuriel/IncarcerationAndRehabilitation/blob/224e9cc9382672cd6e48b3de830afbe9706b3d0a/Cartel%20Recruitment%20-%20Age%20cohort.R#L303), counter starts at zero and its increment is commented out; `AlphaRecidiv` repeats this at lines 355–380. The individual keeps the same population-based hazard lookup throughout the loop. This could be a deliberate approximation, but the rationale is not established here. The code does not advance that calendar index as the simulated person ages.
2. **The age-limit classification and incarceration-years sum differ.** [`AlphaRecidiv`, lines 347–353](https://github.com/rafaelprietocuriel/IncarcerationAndRehabilitation/blob/224e9cc9382672cd6e48b3de830afbe9706b3d0a/Cartel%20Recruitment%20-%20Age%20cohort.R#L347) marks release beyond 69 as death in prison. Yet [lines 558–567](https://github.com/rafaelprietocuriel/IncarcerationAndRehabilitation/blob/224e9cc9382672cd6e48b3de830afbe9706b3d0a/Cartel%20Recruitment%20-%20Age%20cohort.R#L558) sum full assigned sentences into the incarceration-saved quantity. Section 4.5 expressly defines its incarceration metric as the sum of assigned sentence lengths, so the code follows that stated definition. The question is whether this uncapped metric is compatible with the separately defined finite-lifetime cartel potential: it can include years beyond the model's life limit. The fixed-age explorer measures this arithmetic distinction only.
3. **The sampled multiplier range is broader than the methods description.** Section 4.5 describes alpha >= 1 for longer sentences, whereas [line 559](https://github.com/rafaelprietocuriel/IncarcerationAndRehabilitation/blob/224e9cc9382672cd6e48b3de830afbe9706b3d0a/Cartel%20Recruitment%20-%20Age%20cohort.R#L559) samples 2 times a uniform draw, spanning 0 to 2. Part of that domain shortens sentences. Fixed alpha=1 and alpha=2 comparisons would make the intended experiment easier to reproduce.

These are source-inspection findings. We did not execute the full R analysis, establish which version generated each published figure, or measure how alternative implementations change the paper's conclusions. They are research questions for a controlled rerun, not an accusation or an empirical refutation.

## Finding 3: the full 2023 network equation has a scale transformation

This concerns the [2023 v1 network model](https://arxiv.org/html/2307.06302v1), not the distinct aggregate 2025 cohort model. Equation 1 is

    dC_i/dt = rho C_i - eta C_i / sum(C_j)
              - theta C_i sum_{j != i}(S_ij C_j) - omega C_i².

For k > 0, define

    C'_i(t) = k C_i(t), C'_i(0) = k C_i(0)
    rho' = rho, eta' = k eta, theta' = theta/k, omega' = omega/k, S' = S.

Substitution gives, term by term:

    rho' C'_i = k rho C_i
    eta' C'_i / sum(C'_j) = k eta C_i / sum(C_j)
    theta' C'_i sum(S'_ij C'_j) = k theta C_i sum(S_ij C_j)
    omega' (C'_i)² = k omega C_i².

Thus the transformed derivative is k times the original derivative for positive total population. The conflict total in equation 3, incapacitation total eta, recruitment and saturation totals all scale by k. No saturation term was dropped, unlike the reduced accounting argument reviewed in [Rojas §3](https://arxiv.org/html/2310.05975v1).

### What follows for the fitted target

The authors' targets include assumed fractions f of casualties T and g of incapacitations I. If f'=kf and g'=kg, the targets scale with the model outputs. Consequently the unnormalised squared-error objective is E'=k²E, not unchanged. Relative residuals are unchanged. If optimizer domains are transformed too, minimizers correspond within the transformed domains; we did not recover or rerun those optimizer domains.

This is a **conditional structural equivariance**, not proof of non-identifiability after f, g and absolute initial conditions are fixed. An independently measured absolute population, a fixed attribution fraction, fixed absolute parameters, or unscaled optimizer bounds can break this correspondence. Fractions must remain within [0,1]. The UI's k in [0.5,2] keeps the paper's f=0.10 and g=0.05 admissible.

The deterministic initial vector transforms exactly. Multiplying a Poisson draw by k does not produce a Poisson draw with mean multiplied by k; the authors' stochastic initialization requires a separate treatment. Integer rounding, extinction thresholds and priors can also matter. Our equation checks use strictly positive dimensionless states and no stochastic initialization or extinction event.

Twenty exact rational cases span 1, 2, 3 and 5 nodes, asymmetric nonnegative interactions and five scales. Four 208-step RK4 trajectories compare the two parameterizations, yielding maximum relative discrepancy below 2e-15 on the recorded run. These are arithmetic fixtures validating the implementation of the identity. They are not observed cartel data or an empirical calibration.

The practical question is which evidence anchors f, g, the starting population and the loss rates. The scale transformation makes that dependency inspectable. The wider literature has not been exhaustively searched, so this work makes no priority claim.

## Finding 4: a starting-year increase is not an intervention effect

The 2023 v1 preprint's §2.2 and Figure 4 report approximately +40% casualties under unchanged policy and +8% under doubled incapacitation by 2027, relative to 2022. Taking 2022=100 gives 140 and 108. The latter is approximately 22.9% below the unchanged 2027 counterfactual: (108/140 - 1) × 100.

Switching the reference year changes the question. It does not alter either published scenario. These rounded outputs neither validate the original model nor establish the effectiveness or feasibility of a real intervention. The final Science article and its full supplement were not collated against this version.

## Reproduce

Python 3.10+ and Node.js, no third-party packages. From the repository root:

```sh
python cartelkit/model_audit.py --fetch
python cartelkit/model_audit.py --check
python -m unittest discover -s cartelkit -p 'test_*.py' -v
node --test cartelkit/audit-math.test.cjs
python cartelkit/cartelkit.py package
```

Only `--fetch` makes network requests. It downloads two exact public upstream files to ignored local working storage and rejects bytes whose hash differs. To reproduce offline, supply `--input-dir` containing those exact files. `--check` compares the recalculated public output. The static package contains aggregate data, source hashes, this analysis, independent code and tests; it contains neither the original personal-level extract nor the upstream R program.

Research, derivation, code and editing were prepared with AI assistance. Source authors retain credit for their models and data preparation. This audit preserves the earlier project's contribution record and does not certify an applicant writing sample or agency acceptance.
