#!/usr/bin/env python3
"""Offline public-source ledger validation and deterministic publishing.
Checks provenance structure and status compatibility, not truth or corroboration.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
import zipfile
ROOT = Path(__file__).resolve().parent
STATUS_TYPES = {'agency_assessment':'agency_assessment', 'official_designation':'designation_notice',
    'administrative_action':'sanctions_release', 'allegation':'charging_release',
    'judicial_outcome_reported':'guilty_plea_release', 'oversight_finding':'audit_report',
    'academic_model':'author_preprint', 'academic_critique':'comment_preprint'}
SOURCE_HOSTS = {'agency_assessment':'www.dea.gov', 'designation_notice':'public-inspection.federalregister.gov',
    'sanctions_release':'home.treasury.gov', 'charging_release':'www.justice.gov',
    'guilty_plea_release':'www.justice.gov', 'audit_report':'www.gao.gov', 'author_preprint':'arxiv.org',
    'comment_preprint':'arxiv.org', 'applicant_policy':'www.cia.gov'}
ARTIFACTS = ('README.md','METHOD.md','ASSESSMENT.md','cartelkit.py','test_research.py','research.json',
    'legacy-audit.json','summary.json','index.html','dossier.html','style.css',
    'model_audit.py','model-audit.json','MODEL-AUDIT.md','audit-panel.html','audit.css','audit-math.js','audit-app.js','test_model_audit.py','audit-math.test.cjs')
def load(path=ROOT/'research.json'):
    return json.loads(Path(path).read_text(encoding='utf-8'))
def validate(data):
    errors=[]
    def fields(obj, keys, where):
        if not isinstance(obj,dict): errors.append(f'{where}: expected object'); return False
        if set(obj)!=set(keys): errors.append(f'{where}: unsupported or missing fields'); return False
        return True
    def text(value): return isinstance(value,str) and bool(value.strip()) and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',value)
    def day(value, where, nullable=False):
        if nullable and value is None: return None
        try:
            parsed=date.fromisoformat(value)
            if parsed.isoformat()!=value: raise ValueError()
            return parsed
        except (TypeError,ValueError): errors.append(f'{where}: invalid ISO date'); return None
    def refs(values): return isinstance(values,list) and all(isinstance(v,str) for v in values) and len(set(values))==len(values)
    if not fields(data,('schema_version','title','edition','scope','assessment','assistance','organizations','sources','claims','analyses','open_questions'),'ledger'): return errors
    cutoff=day(data['edition'],'edition')
    if data['schema_version']!=2: errors.append('schema version must be 2')
    for key in ('title','scope'):
        if not text(data[key]): errors.append(f'{key}: nonempty text required')
    for key in ('organizations','sources','claims','analyses','open_questions'):
        if not isinstance(data[key],list) or not data[key]: errors.append(f'{key}: nonempty array required')
    a=data['assistance']
    if not fields(a,('ai_assisted','submission_ready','description','cia_policy_source_id','cia_submission_note'),'assistance'): return errors
    if a['ai_assisted'] is not True or a['submission_ready'] is not False: errors.append('preserve AI-assisted, not-submission-ready status')
    if not all(text(a[k]) for k in ('description','cia_policy_source_id','cia_submission_note')): errors.append('assistance: text required')
    if errors: return errors
    orgs=set(); sources={}; claims=set(); analyses=set()
    for org in data['organizations']:
        if not fields(org,('id','name','aliases'),'organization'): continue
        if not text(org['id']) or not text(org['name']) or not refs(org['aliases']): errors.append('organization: invalid fields'); continue
        if org['id'] in orgs: errors.append('duplicate organization id')
        orgs.add(org['id'])
    for s in data['sources']:
        keys=('id','publisher','title','url','published_on','document_type','reviewed_on','locator','limits','independence_group')
        if not fields(s,keys,'source'): continue
        if not all(text(s[k]) for k in keys if k!='published_on'): errors.append('source: nonempty text required'); continue
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9-]{2,60}',s['id']): errors.append('source: invalid id')
        if s['id'] in sources: errors.append('duplicate source id')
        sources[s['id']]=s
        reviewed=day(s['reviewed_on'],s['id']); published=day(s['published_on'],s['id'],True)
        if cutoff and reviewed and reviewed>cutoff: errors.append('review date after edition')
        if published and reviewed and published>reviewed: errors.append('review date predates publication')
        try:
            u=urlsplit(s['url'])
            if u.scheme!='https' or u.username or u.password or u.port or re.search(r'\s',s['url']) or u.hostname!=SOURCE_HOSTS.get(s['document_type']): errors.append('source URL/issuer type mismatch')
        except (ValueError,TypeError): errors.append('invalid source URL')
    if sources.get(a['cia_policy_source_id'],{}).get('document_type')!='applicant_policy': errors.append('CIA policy source missing or mistyped')
    for c in data['claims']:
        if not fields(c,('id','org_ids','statement','status','as_of','source_ids','limits'),'claim'): continue
        if not all(text(c[k]) for k in ('id','statement','status','limits')): errors.append('claim: nonempty text required'); continue
        if not re.fullmatch(r'C\d{2,}',c['id']): errors.append('claim: invalid id')
        if c['id'] in claims: errors.append('duplicate claim id')
        claims.add(c['id']); as_of=day(c['as_of'],c['id'])
        if cutoff and as_of and as_of>cutoff: errors.append('claim date after edition')
        if c['status'] not in STATUS_TYPES: errors.append('unsupported evidence status')
        if not refs(c['org_ids']) or any(org not in orgs for org in c['org_ids']): errors.append('unknown organization')
        if not refs(c['source_ids']) or not c['source_ids']: errors.append('unique source references required'); continue
        for key in c['source_ids']:
            s=sources.get(key)
            if s is None: errors.append('unresolved source reference'); continue
            if s['document_type']!=STATUS_TYPES.get(c['status']): errors.append('evidence status/source type mismatch')
            published=day(s['published_on'],key,True)
            if published and as_of and as_of<published: errors.append('claim predates cited source')
    for note in data['analyses']:
        if not fields(note,('id','statement','status','claim_ids','limits'),'analysis'): continue
        if not all(text(note[k]) for k in ('id','statement','status','limits')): errors.append('analysis: text required'); continue
        if not re.fullmatch(r'A\d{2,}',note['id']) or note['status']!='analysis': errors.append('analysis: explicit analysis status/id required')
        if note['id'] in analyses: errors.append('duplicate analysis id')
        analyses.add(note['id'])
        if not refs(note['claim_ids']) or not note['claim_ids'] or any(k not in claims for k in note['claim_ids']): errors.append('analysis: unresolved claim references')
    assessment=data['assessment']
    if fields(assessment,('question','conclusion','competing_explanations'),'assessment'):
        if not text(assessment['question']) or not text(assessment['conclusion']): errors.append('assessment: nonempty text required')
        hypotheses=assessment['competing_explanations']
        if not isinstance(hypotheses,list) or not hypotheses: errors.append('assessment: competing hypotheses required')
        else:
            seen=set()
            for hypothesis in hypotheses:
                if not fields(hypothesis,('id','statement','claim_ids','limits'),'hypothesis'): continue
                if not all(text(hypothesis[k]) for k in ('id','statement','limits')): errors.append('hypothesis: nonempty text required'); continue
                if not re.fullmatch(r'H\d{2,}',hypothesis['id']) or hypothesis['id'] in seen: errors.append('hypothesis: invalid or duplicate id')
                seen.add(hypothesis['id'])
                if not refs(hypothesis['claim_ids']) or not hypothesis['claim_ids'] or any(k not in claims for k in hypothesis['claim_ids']): errors.append('hypothesis: unresolved claim references')
    if not all(text(question) for question in data['open_questions']): errors.append('open questions: nonempty text required')
    return errors
def summary(data):
    audit=json.loads((ROOT/'model-audit.json').read_text(encoding='utf-8'))
    return {'schema_version':2,'edition':data['edition'],'synthetic_findings_used':False,
        'workbench_edition':audit['edition'],
        'model_audit':{'upstream_commit':audit['upstream']['commit'],'source_rows':audit['sentences']['rows'],
            'aggregate_sentence_lengths':audit['sentences']['unique_lengths'],'code_findings':len(audit['code_findings']),
            'exact_equation_checks':audit['checks']['exact_rational_cases'],'full_model_executed':False},
        'sources':len(data['sources']),'claims':len(data['claims']),'analyses':len(data['analyses']),
        'claims_by_status':dict(sorted(Counter(c['status'] for c in data['claims']).items())),
        'ai_assisted':True,'submission_ready':False,
        'validation_scope':'Institutional ledger structure; pinned-input sentence calculation; full-equation identity. Not complete empirical or policy validation, or current sanctions screening.'}
def audit_panel(prefix=''):
    data=json.loads((ROOT/'model-audit.json').read_text(encoding='utf-8'))
    e=lambda value:escape(str(value),quote=True)
    rows=''.join(f'<div data-bin><label for="audit-bin-{i}">{i*10}–{(i+1)*10 if i<9 else "∞"} y</label><meter id="audit-bin-{i}" min="0" max="1" value="0" aria-label="Share of assigned sentences {i*10} years and above">0</meter><span>—</span></div>' for i in range(10))
    findings=''.join(f'<article class="ca-finding"><p class="ca-kicker">{e(item["id"])} / {e(item["status"])}</p><h4>{e(item["title"])}</h4><p>{e(item["observation"])}</p><p><strong>Why it matters:</strong> {e(item["implication"])}</p><p>{e(item["limit"])}</p><a href="{e(item["source_url"])}">Inspect the pinned code ↗</a>'+ (f' · <a href="{e(item["second_url"])}">Inspect the sum ↗</a>' if item.get('second_url') else '')+'</article>' for item in data['code_findings'])
    return (ROOT/'audit-panel.html').read_text(encoding='utf-8').replace('__PREFIX__',e(prefix)).replace('__HISTOGRAM_ROWS__',rows).replace('__CODE_FINDINGS__',findings)

def render(data):
    errors=validate(data)
    if errors: raise ValueError('; '.join(errors))
    e=lambda value:escape(str(value),quote=True)
    source_map={s['id']:s for s in data['sources']}
    citation=lambda keys:' '.join('<a href="#source-'+e(k)+'">'+e(k)+'</a>' for k in keys)
    claim_link=lambda keys:' '.join('<a href="#'+e(k)+'">'+e(k)+'</a>' for k in keys)
    rows=''.join(f'<article id="{e(c["id"])}"><p class="record">{e(c["id"])} · {e(c["status"].replace("_"," "))} · {e(c["as_of"])}</p><h3>{e(c["statement"])}</h3><p>{e(c["limits"])}</p><p class="citations">{citation(c["source_ids"])}</p></article>' for c in data['claims'])
    notes=''.join(f'<article id="{e(n["id"])}"><p class="record">{e(n["id"])} · Analysis</p><h3>{e(n["statement"])}</h3><p>{e(n["limits"])}</p><p class="citations">{claim_link(n["claim_ids"])}</p></article>' for n in data['analyses'])
    alternatives=''.join(f'<article id="{e(n["id"])}"><p class="record">{e(n["id"])} · Competing hypothesis</p><h3>{e(n["statement"])}</h3><p>{e(n["limits"])}</p><p class="citations">{claim_link(n["claim_ids"])}</p></article>' for n in data['assessment']['competing_explanations'])
    sources=''.join(f'<li id="source-{e(s["id"])}"><p class="record">{e(s["id"])} · {e(s["document_type"].replace("_"," "))}</p><h3><a href="{e(s["url"])}">{e(s["title"])}</a></h3><p>{e(s["publisher"])} · Published: {e(s["published_on"] or "date not asserted")} · Reviewed: {e(s["reviewed_on"])}</p><p><strong>Locator:</strong> {e(s["locator"])}</p><p>{e(s["limits"])}</p></li>' for s in data['sources'])
    questions=''.join(f'<li>{e(q)}</li>' for q in data['open_questions'])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CARTELKIT — Open the model. Check the claim.</title><meta name="description" content="Reproduce a sentence-weighting result from 40,297 records, inspect pinned code, and test the assumptions behind published cartel models."><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="audit.css"><script src="audit-math.js" defer></script><script src="audit-app.js" defer></script><link rel="canonical" href="https://ssh-pur66.github.io/cartelkit/"></head><body>
<a class="skip" href="#main">Skip to the research</a><header><a class="brand" href="./">CARTELKIT / PUBLIC RECORD</a><nav aria-label="Main navigation"><a href="#model-audit">Model audit</a><a href="#analysis">Assessment</a><a href="#claims">Records</a><a href="#sources">Sources</a><a href="research.json">Data</a><a href="METHOD.md">Method</a></nav></header>
<main id="main"><section class="opening"><p class="record">CARTELKIT / Research workbench · Edition 02 · 8 October 2026</p><h1>Open the model.<br>Check the claim.</h1><p class="deck">Cartel research should survive a closer look.</p><p>Trace the actual data and code behind published cartel models. Reproduce a sentence-weighting result, inspect three implementation questions, and separate an assumed population scale from a measured one.</p><div class="downloads"><a href="#model-audit">Enter the workbench ↓</a><a href="MODEL-AUDIT.md">Read the research note ↗</a><a href="cartelkit_deliverable.zip">Download the reproducible study ↓</a></div></section>
{audit_panel()}
<section id="analysis"><p class="record">02 / ASSESSMENT</p><h2>What the record supports.</h2><div class="records">{notes}</div><h2>Competing explanations.</h2><p>These hypotheses identify what the source sample cannot distinguish.</p><div class="records">{alternatives}</div></section>
<section id="claims"><p class="record">03 / ATTRIBUTED RECORDS</p><h2>Keep the status with the statement.</h2><p>Institutional context reviewed 5 October 2026. These records retain their original dates and evidentiary status; the model audit above is a separate 8 October analysis.</p><div class="records">{rows}</div></section>
<section id="sources"><p class="record">04 / CITATION LEDGER</p><h2>Open the document.</h2><p>The court examples use DOJ announcements; signed court records were not independently retrieved. The model audit reproduces the supplied sentence-weighting expectation and checks an equation identity. It does not execute either full calibrated model.</p><ol class="sources">{sources}</ol></section>
<section id="questions"><h2>Questions left open.</h2><ul>{questions}</ul></section>
<section id="assistance"><h2>Preparation and authorship.</h2><p>{e(data['assistance']['description'])}</p><p>{e(data['assistance']['cia_submission_note'])} <a href="{e(source_map[data['assistance']['cia_policy_source_id']]['url'])}">CIA applicant guidance ↗</a></p><p>The previous download contained synthetic wallet, text, and radio fixtures. This edition retires that public package; its original commit and artifact hashes are documented in the audit. Those fixtures supply no evidence for this ledger.</p></section>
</main><footer>Independent public-source study · No agency affiliation or endorsement · <a href="https://github.com/SSH-PuR66/SSH-PuR66.github.io">Source and review history ↗</a></footer></body></html>
'''
def assessment_text(data):
    if errors:=validate(data): raise ValueError('; '.join(errors))
    parts=[f"# {data['title']}",f"Public-source assessment · Reviewed {data['edition']}",
        '## Research question',data['assessment']['question'],data['scope'],
        '## Assessment',data['assessment']['conclusion'],'## Key judgments']
    references=lambda keys:' · '.join(f'[{k}](index.html#{k})' for k in keys)
    for note in data['analyses']:
        parts.extend([f"### {note['id']} — {note['statement']}",note['limits'],references(note['claim_ids'])])
    parts.append('## Competing explanations')
    parts.append('The following are hypotheses, not additional findings. The reviewed sample does not distinguish among them.')
    for note in data['assessment']['competing_explanations']:
        parts.extend([f"### {note['id']} — {note['statement']}",note['limits'],references(note['claim_ids'])])
    parts.extend(['## Evidence gaps','\n'.join('- '+q for q in data['open_questions']),
        'Signed court records, later dispositions, and current listing changes were not independently retrieved. Selected academic full-text sections were reviewed; no model was independently reproduced. This source sample is not a comprehensive intelligence assessment.',
        '## Sources and authorship','[The source ledger](research.json) provides direct links, dates, locators, document types, and limitations. [Method](METHOD.md) explains selection and validation.',
        data['assistance']['description'],data['assistance']['cia_submission_note']])
    return '\n\n'.join(parts)+'\n'

def build(data,directory=ROOT):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    (directory/'index.html').write_text(render(data),encoding='utf-8',newline='\n')
    (directory/'ASSESSMENT.md').write_text(assessment_text(data),encoding='utf-8',newline='\n')
    (directory/'summary.json').write_text(json.dumps(summary(data),indent=2)+'\n',encoding='utf-8',newline='\n')
    redirect='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=./"><title>Public-source research ledger</title></head><body><p>The synthetic dossier has been retired. <a href="./">Open the public-source study</a>.</p></body></html>\n'
    (directory/'dossier.html').write_text(redirect,encoding='utf-8',newline='\n')
def hashes(directory=ROOT):
    return ''.join(f'{hashlib.sha256((Path(directory)/name).read_bytes()).hexdigest()}  {name}\n' for name in ARTIFACTS)
def package(directory=ROOT):
    directory=Path(directory)
    (directory/'MANIFEST.sha256').write_text(hashes(directory),encoding='utf-8',newline='\n')
    with zipfile.ZipFile(directory/'cartelkit_deliverable.zip','w',compression=zipfile.ZIP_STORED) as archive:
        for name in (*ARTIFACTS,'MANIFEST.sha256'):
            info=zipfile.ZipInfo('cartelkit/'+name,date_time=(2026,10,5,0,0,0))
            info.compress_type=zipfile.ZIP_STORED; info.create_system=3; info.external_attr=0o644<<16
            archive.writestr(info,(directory/name).read_bytes())
def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=('check','build','package'))
    args=parser.parse_args(); data=load(); errors=validate(data)
    if errors: print(json.dumps({'valid':False,'errors':errors},indent=2)); return 1
    if args.command in ('build','package'): build(data)
    if args.command=='package': package()
    print(json.dumps({'valid':True,**summary(data)},indent=2)); return 0
if __name__=='__main__': sys.exit(main())
