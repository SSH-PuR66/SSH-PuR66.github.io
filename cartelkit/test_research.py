"""Offline regression checks for provenance, status boundaries, and publication."""
from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urlsplit
import zipfile

import cartelkit as study


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids=[]
        self.hrefs=[]
        self.scripts=[]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs: self.ids.append(attrs['id'])
        if 'href' in attrs: self.hrefs.append(attrs['href'])
        if tag=='script': self.scripts.append(attrs)


class ResearchChecks(unittest.TestCase):
    def setUp(self):
        self.data=deepcopy(study.load())

    def rejected(self, fragment):
        errors=study.validate(self.data)
        self.assertTrue(errors)
        self.assertTrue(any(fragment in error for error in errors),errors)

    def test_public_ledger_validates(self):
        self.assertEqual(study.validate(self.data),[])

    def test_allegation_cannot_be_promoted_to_reported_outcome(self):
        next(c for c in self.data['claims'] if c['id']=='C04')['status']='judicial_outcome_reported'
        self.rejected('status/source type')

    def test_critique_cannot_be_promoted_to_oversight_finding(self):
        next(c for c in self.data['claims'] if c['id']=='C09')['status']='oversight_finding'
        self.rejected('status/source type')

    def test_unresolved_source_and_analysis_references(self):
        self.data['claims'][0]['source_ids']=['NONEXISTENT']
        self.data['analyses'][0]['claim_ids']=['C999']
        errors=study.validate(self.data)
        self.assertIn('unresolved source reference',errors)
        self.assertIn('analysis: unresolved claim references',errors)

    def test_duplicate_identifiers_and_citations_rejected(self):
        self.data['sources'].append(deepcopy(self.data['sources'][0]))
        self.data['claims'][0]['source_ids']*=2
        errors=study.validate(self.data)
        self.assertIn('duplicate source id',errors)
        self.assertIn('unique source references required',errors)

    def test_unknown_organization_rejected(self):
        self.data['claims'][0]['org_ids']=['unknown']
        self.rejected('unknown organization')

    def test_private_dossier_fields_rejected(self):
        self.data['claims'][0]['contact']='unsupported private field'
        self.rejected('unsupported or missing fields')

    def test_bad_reference_type_rejected_without_exception(self):
        self.data['claims'][0]['source_ids']=[{}]
        self.data['claims'][0]['org_ids']=None
        errors=study.validate(self.data)
        self.assertIn('unique source references required',errors)
        self.assertIn('unknown organization',errors)

    def test_future_and_invalid_dates_rejected(self):
        self.data['sources'][0]['reviewed_on']='2026-10-06'
        self.data['claims'][0]['as_of']='2025-02-30'
        errors=study.validate(self.data)
        self.assertIn('review date after edition',errors)
        self.assertTrue(any('invalid ISO date' in error for error in errors))

    def test_claim_cannot_predate_cited_document(self):
        self.data['claims'][0]['as_of']='2020-01-01'
        self.rejected('claim predates cited source')

    def test_publisher_url_boundary(self):
        for url in ('http://www.dea.gov/report','https://www.dea.gov.evil.example/report',
                    'https://name:password@www.dea.gov/report','https://www.dea.gov:443/report',
                    'javascript:alert(1)'):
            with self.subTest(url=url):
                self.data['sources'][0]['url']=url
                self.rejected('URL/issuer type mismatch')

    def test_assistance_is_retained_and_not_submission_ready(self):
        self.data['assistance']['ai_assisted']=False
        self.data['assistance']['submission_ready']=True
        self.rejected('AI-assisted, not-submission-ready')

    def test_hypotheses_require_dated_record_references(self):
        self.data['assessment']['competing_explanations'][0]['claim_ids']=['C999']
        self.rejected('hypothesis: unresolved claim references')

    def test_invalid_assessment_shape_rejected(self):
        self.data['assessment']['competing_explanations']=None
        self.rejected('competing hypotheses required')

    def test_text_escaped_into_html(self):
        self.data['claims'][0]['statement']='<script>bad()</script> & "quoted"'
        html=study.render(self.data)
        self.assertIn('&lt;script&gt;bad()&lt;/script&gt; &amp; &quot;quoted&quot;',html)
        self.assertEqual([item.get('src') for item in Links(html).scripts],['audit-math.js','audit-app.js'])

    def test_rendered_internal_links_and_local_assets_resolve(self):
        parsed=Links(study.render(self.data))
        self.assertEqual(len(parsed.ids),len(set(parsed.ids)))
        for href in parsed.hrefs:
            if href.startswith('#'): self.assertIn(href[1:],parsed.ids)
            elif not urlsplit(href).scheme:
                self.assertTrue((study.ROOT/href).exists(),href)

    def test_context_records_do_not_imply_cartel_attribution(self):
        for claim in self.data['claims']:
            if claim['status'] in ('oversight_finding','academic_model','academic_critique'):
                self.assertEqual(claim['org_ids'],[],claim['id'])

    def test_summary_counts_derived_from_current_ledger(self):
        output=study.summary(self.data)
        self.assertEqual(sum(output['claims_by_status'].values()),len(self.data['claims']))
        self.assertEqual(output['sources'],len(self.data['sources']))
        self.assertFalse(output['synthetic_findings_used'])

    def test_generated_artifacts_match_checked_in_files(self):
        self.assertEqual((study.ROOT/'index.html').read_text(encoding='utf-8'),study.render(self.data))
        self.assertEqual((study.ROOT/'ASSESSMENT.md').read_text(encoding='utf-8'),study.assessment_text(self.data))
        self.assertEqual(json.loads((study.ROOT/'summary.json').read_text()),study.summary(self.data))
        self.assertEqual((study.ROOT/'MANIFEST.sha256').read_text(),study.hashes())

    def test_package_is_reproducible_and_allowlisted(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)
            for name in study.ARTIFACTS: shutil.copyfile(study.ROOT/name,path/name)
            study.build(self.data,path)
            study.package(path)
            original=(path/'cartelkit_deliverable.zip').read_bytes()
            study.package(path)
            self.assertEqual(original,(path/'cartelkit_deliverable.zip').read_bytes())
            self.assertEqual(original,(study.ROOT/'cartelkit_deliverable.zip').read_bytes())
            with zipfile.ZipFile(path/'cartelkit_deliverable.zip') as archive:
                expected=['cartelkit/'+name for name in (*study.ARTIFACTS,'MANIFEST.sha256')]
                self.assertEqual(archive.namelist(),expected)
                for info in archive.infolist():
                    self.assertEqual(info.date_time,(2026,10,5,0,0,0))
                    self.assertEqual(info.create_system,3)
                for name in study.ARTIFACTS:
                    self.assertEqual(archive.read('cartelkit/'+name),(path/name).read_bytes())

    def test_legacy_manifest_is_bounded_and_hash_shaped(self):
        audit=json.loads((study.ROOT/'legacy-audit.json').read_text())
        self.assertTrue(audit['synthetic'])
        self.assertFalse(audit['evidence_for_current_assessment'])
        self.assertEqual(audit['manifest_files_checked'],len(audit['manifest']))
        self.assertEqual(audit['manifest_matches'],len(audit['manifest']))
        for entry in audit['manifest']:
            self.assertNotIn('/',entry['path'])
            self.assertRegex(entry['sha256'],r'^[0-9a-f]{64}$')

    def test_public_artifacts_exclude_workstation_paths(self):
        for name in ('research.json','index.html','summary.json','legacy-audit.json','ASSESSMENT.md'):
            content=(study.ROOT/name).read_text(encoding='utf-8')
            self.assertNotRegex(content,r'(?i)[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]')
            self.assertNotIn('cartelkit-ops',content)


if __name__=='__main__': unittest.main()
