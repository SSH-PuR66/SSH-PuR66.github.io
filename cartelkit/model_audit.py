"""Reproduce a bounded model audit from a hash-pinned author data file.

No upstream R is executed. Public output contains sentence/count aggregates only.
The default build is offline; --fetch explicitly downloads two fixed public files.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
COMMIT = '224e9cc9382672cd6e48b3de830afbe9706b3d0a'
REPOSITORY = 'https://github.com/rafaelprietocuriel/IncarcerationAndRehabilitation'
INPUTS = {
    'ENPOL sentences.csv': 'f55f40dd90df2d2ce04e66cf483d62ffdbdcdb8ecb86dc7d7c902dac6b7544f3',
    'Cartel Recruitment - Age cohort.R': 'a12bcda76ba92115ee5446d2acb9525dfaa7db9edecb8596cfc81e5e9a0a161e',
}

def verify_bytes(name, payload):
    if name not in INPUTS or hashlib.sha256(payload).hexdigest() != INPUTS[name]:
        raise ValueError('Input identity differs from the reviewed upstream revision')
    return payload

def read_distribution(payload):
    verify_bytes('ENPOL sentences.csv', payload)
    counts = Counter()
    for row in csv.DictReader(io.StringIO(payload.decode('utf-8-sig'))):
        value = float(row['SENTENCE'])
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Sentence must be finite and positive')
        counts[value] += 1
    return [[value, count] for value, count in sorted(counts.items())]

def sentence_stats(distribution, age=40, multiplier=1, inverse=True):
    if not 15 <= age <= 69 or not 0.5 <= multiplier <= 3:
        raise ValueError('Age or multiplier outside the documented sensitivity range')
    denominator = math.fsum(n / s if inverse else n for s, n in distribution)
    expected = math.fsum((n / s if inverse else n) * s * multiplier for s, n in distribution) / denominator
    remaining = 69 - age
    capped = math.fsum((n / s if inverse else n) * min(s * multiplier, remaining)
                       for s, n in distribution) / denominator
    beyond = math.fsum(n / s if inverse else n for s, n in distribution
                       if s * multiplier > remaining) / denominator
    return {'assigned_years': expected, 'capped_years': capped,
            'years_beyond_age_69': expected - capped, 'probability_beyond_age_69': beyond}

def rhs(c, params, network):
    """2023 paper Eq.1, for positive states; no extinction rule inferred."""
    rho, eta, theta, omega = params
    total = sum(c)
    if total <= 0 or any(x <= 0 for x in c):
        raise ValueError('This audit evaluates strictly positive states only')
    return [rho*x - eta*x/total - theta*x*sum(c[j]*network[i][j] for j in range(len(c)) if j != i)
            - omega*x*x for i, x in enumerate(c)]

def casualties(c, params, network):
    return params[2]*sum(c[i]*c[j]*network[i][j] for i in range(len(c)) for j in range(len(c)) if i != j)

def transformed(c, params, factor):
    rho, eta, theta, omega = params
    return [factor*x for x in c], [rho, factor*eta, theta/factor, omega/factor]

def rk4(c, params, network, dt):
    k1 = rhs(c, params, network)
    k2 = rhs([x+dt*k/2 for x,k in zip(c,k1)],params,network)
    k3 = rhs([x+dt*k/2 for x,k in zip(c,k2)],params,network)
    k4 = rhs([x+dt*k for x,k in zip(c,k3)],params,network)
    return [x+dt*(a+2*b+2*d+e)/6 for x,a,b,d,e in zip(c,k1,k2,k3,k4)]

def check_symmetry():
    # Dimensionless arithmetic fixtures, not observed cartel networks or a calibration.
    exact_cases = 0
    for size in (1, 2, 3, 5):
        network = [[Fraction(0) if i == j else Fraction((i+2)*(j+1),7) for j in range(size)] for i in range(size)]
        c = [Fraction(i+2) for i in range(size)]
        p = [Fraction(3,100),Fraction(1,50),Fraction(1,1000),Fraction(1,500)]
        for factor in (Fraction(1,2),Fraction(3,4),Fraction(1),Fraction(5,4),Fraction(2)):
            scaled, q = transformed(c,p,factor)
            assert rhs(scaled,q,network) == [factor*x for x in rhs(c,p,network)]
            assert casualties(scaled,q,network) == factor*casualties(c,p,network)
            exact_cases += 1
    network = [[0.,.3,.8],[.7,0.,.4],[.2,.9,0.]]
    c0 = [20.,12.,6.]
    p = [.03,.05,.0004,.0003]
    max_error = 0.
    for factor in (.5,.75,1.25,2.):
        base = c0[:]
        scaled,q = transformed(base,p,factor)
        for _ in range(208):
            base = rk4(base,p,network,.25)
            scaled = rk4(scaled,q,network,.25)
            max_error = max(max_error, *(abs(y-factor*x)/max(1,abs(factor*x)) for x,y in zip(base,scaled)))
    return {'exact_rational_cases':exact_cases,'trajectory_cases':4,'steps_per_trajectory':208,
            'step_size':0.25,'max_relative_trajectory_error':max_error,
            'scope':'Algebra and numerical implementation checks on dimensionless fixtures; no empirical network fit.'}

def source_url(name, lines=''):
    return f'{REPOSITORY}/blob/{COMMIT}/{quote(name)}' + (f'#L{lines}' if lines else '')

def reproduce(directory):
    directory = Path(directory)
    raw = {name:verify_bytes(name,(directory/name).read_bytes()) for name in INPUTS}
    distribution = read_distribution(raw['ENPOL sentences.csv'])
    code = raw['Cartel Recruitment - Age cohort.R'].decode('utf-8')
    # Fail closed if the code observations no longer match the exact reviewed input.
    assert code.count('#counter <- counter + 1') == 2
    assert 'IncapS <- sum(RecidAnalysis$SENTENCE*365)' in code
    assert 'Alpha = 2*runif(1)' in code
    n = sum(count for _,count in distribution)
    return {
      'schema_version':1,'edition':'2026-10-08','title':'CARTELKIT / Model audit',
      'upstream':{'repository':REPOSITORY,'commit':COMMIT,'files':[
        {'name':name,'sha256':INPUTS[name],'bytes':len(raw[name]),'url':source_url(name)} for name in INPUTS]},
      'papers':[
        {'id':'network-2023-v1','url':'https://arxiv.org/html/2307.06302v1','locators':'Equations 1–3; §2.2; Appendix A.3, S1–S5','reviewed_on':'2026-10-08'},
        {'id':'critique-2023-v1','url':'https://arxiv.org/html/2310.05975v1','locators':'§§2–3','reviewed_on':'2026-10-08'},
        {'id':'cohort-2025-v1','url':'https://arxiv.org/html/2512.17973v1','locators':'§§4.4–4.7; Supplementary B, sentence sampling','reviewed_on':'2026-10-08'}],
      'sentences':{'rows':n,'unique_lengths':len(distribution),
        'survey_mean_years':sentence_stats(distribution,inverse=False)['assigned_years'],
        'inverse_weighted_mean_years':sentence_stats(distribution)['assigned_years'],
        'minimum_years':min(s for s,_ in distribution),'maximum_years':max(s for s,_ in distribution),
        'distribution':distribution,
        'meaning':'Author-supplied ENPOL extract; no independent reconstruction from original INEGI microdata or survey-weighted population estimate.',
        'privacy':'Only sentence lengths and frequency counts are retained; person IDs, locations and offence columns are excluded.'},
      'checks':check_symmetry(),
      'baseline':{'year':2027,'reference_year':2022,'reference_index':100,'unchanged_index':140,'double_incapacitation_index':108,
        'relative_change_percent':(108/140-1)*100,
        'meaning':'Approximate published 2023-v1 scenario values, re-expressed arithmetically; not a new simulation or observed effect.'},
      'code_findings':[
        {'id':'M01','title':'Post-release calendar index stays fixed','status':'verified source inspection',
         'source_url':source_url('Cartel Recruitment - Age cohort.R','303-L328'),
         'observation':'Both release functions initialize counter at zero; the only increment is commented out. Each person therefore reuses the same calendar index inside the weekly loop.',
         'implication':'The supplied loop does not advance the population-dependent hazard lookup over that person’s post-release weeks.',
         'limit':'No full R rerun or published-effect change is established. An intentionally frozen-hazard approximation remains possible; its rationale is not established by this inspection.'},
        {'id':'M02','title':'Assigned years exceed some remaining lifetimes','status':'verified source inspection and bounded calculation',
         'source_url':source_url('Cartel Recruitment - Age cohort.R','347-L353'),
         'second_url':source_url('Cartel Recruitment - Age cohort.R','558-L567'),
         'observation':'Release classification uses age 69, while the displayed incarceration-saved calculation sums complete assigned sentences without that cap.',
         'implication':'Section 4.5 defines the metric as summed sentence lengths, so the code follows that definition. The question is compatibility with finite-lifetime potential: assigned sentence-years and years available before age 69 differ. The explorer quantifies that difference at a chosen age.',
         'limit':'A single chosen age is a sensitivity slice, not the paper’s age distribution, an estimate of real time served, or a corrected policy-effect result.'},
        {'id':'M03','title':'The sampled policy domain differs from the methods domain','status':'verified source comparison',
         'source_url':source_url('Cartel Recruitment - Age cohort.R','558-L566'),
         'observation':'The methods describe sentence multipliers alpha ≥ 1; the supplied analysis samples 2 × runif(1), spanning 0 to 2. Values below 1 shorten sentences.',
         'implication':'A reproducible comparison should specify the intended policy domain and include fixed alpha=1 and alpha=2 baselines.',
         'limit':'This checks the supplied sampling domain, not the origin of every plotted point or the direction of a recomputed policy effect.'}],
      'scope':{'full_R_model_executed':False,'original_INEGI_microdata_rebuilt':False,'new_cartel_population_estimate':False,
        'structural_result':'Full 2023 ODE is equivariant when population, initial state, eta, f and g scale by k, while theta and omega divide by k and rho/network stay fixed. Absolute outputs scale; raw least-squares loss scales by k². This is not equal absolute-data fit with fixed f/g/initial state.',
        'novelty':'An independent explanatory audit; no claim of first discovery or a complete literature review.'}
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=ROOT.parent/'dist/model-audit-inputs')
    parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--check',action='store_true',help='Compare the derived JSON without writing')
    args=parser.parse_args()
    if args.fetch:
        args.input_dir.mkdir(parents=True,exist_ok=True)
        for name in INPUTS:
            url=f'https://raw.githubusercontent.com/rafaelprietocuriel/IncarcerationAndRehabilitation/{COMMIT}/{quote(name)}'
            with urlopen(url,timeout=30) as response: payload=response.read(8*1024*1024+1)
            verify_bytes(name,payload)
            (args.input_dir/name).write_bytes(payload)
    output=json.dumps(reproduce(args.input_dir),indent=2,ensure_ascii=False)+'\n'
    target=ROOT/'model-audit.json'
    if args.check:
        if target.read_text(encoding='utf-8') != output: raise SystemExit('Audit output differs; review required')
    else: target.write_text(output,encoding='utf-8',newline='\n')
    data=json.loads(output)
    print(json.dumps({'rows':data['sentences']['rows'],'survey_mean':data['sentences']['survey_mean_years'],
       'weighted_mean':data['sentences']['inverse_weighted_mean_years'],'checks':data['checks']},indent=2))

if __name__=='__main__': main()
