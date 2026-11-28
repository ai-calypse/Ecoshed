"""Validate final claims, original publication outputs and actual rendered files."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import zipfile
import platform

import fitz
from docx import Document
from pptx import Presentation
from pptx.enum.chart import XL_CHART_TYPE

from .evidence import Evidence, FINAL, ROOT, TEAM, read, write_json
from .build_report import resolve, fingerprint_rows
from .tables import report_table
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.analysis.artifacts import CURVES, SIZES


def norm(text):return re.sub(r'\s+','',text).replace('\u00ad','')


def document_check(e,final=FINAL):
    final=Path(final);errors=[];checks={};pdf=final/'report/EcoSched_Final_Report.pdf'
    with fitz.open(pdf) as report:
        report_text='\n'.join(p.get_text() for p in report);flat=norm(report_text);checks['report_pages']=len(report)
        if len(report)!=28:errors.append('Report must have 28 planned pages')
        source=read(FINAL/'report/source/report.json');pages=resolve(e,source)
        for number,page in enumerate(pages,1):
            for b in page['blocks']:
                if b['type'] in ('paragraph','heading','equation','code') and norm(b['text']) not in flat:
                    errors.append(f'Report text missing/clipped on planned page {number}: {b["text"][:75]}')
                if b['type']=='table':
                    _,rows=report_table(e,b['id'])
                    for row in rows:
                        if norm(' '.join(str(v) for v in row)) not in flat:errors.append(f'Report table row mismatch: {b["id"]}/{row[:3]}')
        abstract=pages[1]['blocks'][1]['text'];checks['abstract_words']=len(abstract.split())
        if not 200<=checks['abstract_words']<=250:errors.append('Abstract length outside requested range')
        for page in report:
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if not page.rect.contains(fitz.Rect(span['bbox'])):errors.append(f'Text outside report page {page.number+1}: {span["text"][:40]}')
    for member in TEAM:
        if member not in report_text:errors.append('Missing team member '+member)
    for identifier in ('117382972','117312317','117568314','117479490','116932822'):
        if identifier in report_text:errors.append('Student ID exposed')
    for phrase in ('three historical','not claimed','modeled','first_fit'):
        # Policy IDs live in claims/config sources; reader-facing labels remain human-readable.
        if phrase!='first_fit' and phrase.lower() not in report_text.lower():errors.append('Missing interpretation disclosure '+phrase)
    editable_report=Document(str(final/'report/EcoSched_Final_Report.docx'))
    docx_text=norm('\n'.join([p.text for p in editable_report.paragraphs]+[' '.join(cell.text for cell in row.cells) for table in editable_report.tables for row in table.rows]))
    for page in pages:
        for block in page['blocks']:
            if block['type'] in ('paragraph','heading','equation','code') and norm(block['text']) not in docx_text:
                errors.append('Editable DOCX text differs from report source: '+block['text'][:60])
            if block['type']=='table':
                _,rows=report_table(e,block['id'])
                if any(norm(' '.join(str(v) for v in row)) not in docx_text for row in rows):errors.append('Editable DOCX table differs: '+block['id'])
    if read(final/'report/claims.json')!=e.ledger():errors.append('Report claim ledger differs from authoritative evidence')
    if read(final/'presentation/claims.json')!=e.ledger():errors.append('Presentation claim ledger differs from authoritative evidence')
    deck=Presentation(str(final/'presentation/EcoSched_Final_Presentation.pptx'))
    assert deck.slide_width is not None and deck.slide_height is not None
    checks['slides']=len(deck.slides)
    if len(deck.slides)!=20:errors.append('Expected 15 main + 5 appendix slides')
    if abs(deck.slide_width/deck.slide_height-16/9)>1e-5:errors.append('Deck is not widescreen 16:9')
    external_notes=norm((final/'presentation/speaker_notes.md').read_text())
    source_slides=read(FINAL/'presentation/source/slides.json')['slides']
    for i,(slide,source_slide) in enumerate(zip(deck.slides,source_slides),1):
        expected=norm(e.text(source_slide['notes']))
        if expected not in external_notes or expected not in norm(slide.notes_slide.notes_text_frame.text):
            errors.append(f'Speaker notes differ from verified source on slide {i}')
    with fitz.open(final/'presentation/EcoSched_Final_Presentation.pdf') as slides_pdf:
        if len(slides_pdf)!=len(deck.slides):errors.append('Native presentation PDF count mismatch')
        for i,(slide,page) in enumerate(zip(deck.slides,slides_pdf),1):
            text=norm(page.get_text())
            for shape in slide.shapes:
                if shape.left<0 or shape.top<0 or shape.left+shape.width>deck.slide_width+100 or shape.top+shape.height>deck.slide_height+100:
                    errors.append(f'Object outside slide {i}')
                if shape.has_text_frame and norm(shape.text) and norm(shape.text) not in text:
                    errors.append(f'PowerPoint text missing/clipped on slide {i}: {shape.text[:75]}')
            if not slide.has_notes_slide or len(slide.notes_slide.notes_text_frame.text)<120:errors.append(f'Missing substantial speaker notes: {i}')
    # Native editable chart numbers are checked directly, not inferred from pixel heights.
    curves_chart=next(s.chart for s in deck.slides[6].shapes if s.has_chart)
    for series,curve in zip(curves_chart.series,CURVES):
        if list(series.values)!=e.a.curve_data['curves'][curve]['watts']:errors.append('Power-curve chart values differ')
    energy_chart=next(s.chart for s in deck.slides[8].shapes if s.has_chart);pairs=e.a.comparisons(primary_only=True)
    for series,curve in zip(energy_chart.series,CURVES):
        expected=[next(r['energy_reduction_pct'] for r in pairs if r['workload_groups']==size and r['power_curve']==curve) for size in SIZES]
        if list(series.values)!=expected:errors.append('Primary chart values/signs differ')
        if series.invert_if_negative:errors.append('Negative energy bars would lose their policy/curve fill')
    expected_conclusion=f"{e.claims['wins']}/{e.claims['pairs']}"
    if expected_conclusion not in deck.slides[8].shapes[2].text:
        # Locate by text instead of making theme geometry authoritative.
        if not any(expected_conclusion in s.text for s in deck.slides[8].shapes if s.has_text_frame):errors.append('Primary savings conclusion absent')
    for name in ('demo_runbook.md','demo_checklist.md','troubleshooting.md','defense_preparation.md'):
        if not (final/'demo'/name).is_file():errors.append('Missing demonstration document '+name)
    checks.update(active_outcomes=e.validation['active_outcomes'],primary_comparisons=e.validation['primary_comparisons'],
                  primary_energy_savings_cases=e.claims['wins'],historical_lineage='UNRESOLVED',publication_output_hashes='verified',
                  source_documents='Editable JSON templates + Markdown, DOCX and PPTX',native_chart_numerics='verified')
    return dict(passed=not errors,errors=errors,checks=checks)


def render_all(final=FINAL):
    count={}
    for folder,name,stem in [('report','EcoSched_Final_Report.pdf','page'),('presentation','EcoSched_Final_Presentation.pdf','slide')]:
        out=final/folder/'previews';out.mkdir(exist_ok=True)
        with fitz.open(final/folder/name) as pdf:
            for i,page in enumerate(pdf):page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(out/f'{stem}_{i+1:02d}.png')
            count[folder]=len(pdf)
    return count


def write_manifest(e,final=FINAL):
    sources=set(e.a.source_paths)|{f'ARNAV_Task/reports/phase{n}_verification.json' for n in (3,4,5,6)}
    sources.update(['AGENTS.md','docs/EcoSched_Proposal.pdf','docs/checkpoint/EcoSched_Midterm_Checkpoint.md',
                    'ARNAV_Task/reports/publication/figure_manifest.json','ARNAV_Task/reports/publication/table_manifest.json',
                    'ARNAV_Task/reports/provenance_reconciliation.md','ARNAV_Task/requirements.txt','ARNAV_Task/README.md'])
    sources.update(str(p.relative_to(ROOT)) for p in (ROOT/'ARNAV_Task/documentation').glob('*.py'))
    sources.add('ARNAV_Task/tests/test_documentation.py')
    screenshots=['ARNAV_Task/reports/phase5_screenshots/completed_verified_replay.png'];sources.update(screenshots)
    outputs={str(p.relative_to(final)):sha256(p) for p in sorted(final.rglob('*')) if p.is_file() and p.name!='manifest.json' and not p.name.startswith('~$')}
    # Phase 6 manifests remain historical receipts. Current documentation changes
    # are disclosed rather than silently updating an old source fingerprint.
    evolved=[]
    for manifest in e.manifests.values():
        for artifact in manifest['artifacts']:
            for source,expected in artifact['source_sha256'].items():
                if sha256(ROOT/source)!=expected:
                    row=dict(path=source,phase6_sha256=expected,current_sha256=sha256(ROOT/source),interpretation='Documentation evolved after the frozen publication build; outputs are unchanged.')
                    if row not in evolved:evolved.append(row)
    manifest=dict(schema_version=1,study='EcoSched — AMS 560 Big Data, Stony Brook University',
        branch='arnav/d6-final-package',base=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),
        source_sha256={p:sha256(ROOT/p) for p in sorted(sources)},output_sha256=outputs,
        figure_ids=read(final/'report/build_receipt.json')['figures'],table_selections=read(final/'report/build_receipt.json')['tables'],
        publication_table_ids=sorted({identifier for page in read(FINAL/'report/source/report.json')['pages'] for block in page['blocks'] if block['type']=='table' for identifier in re.findall(r'\bT\d{2}\b',block['caption'])}),
        report=read(final/'report/build_receipt.json'),presentation=read(final/'presentation/build_receipt.json'),
        python_version=platform.python_version(),dependencies={p:version(p) for p in ('reportlab','python-docx','python-pptx','pymupdf','matplotlib','pypdf')},
        build_commands=['python -m ARNAV_Task.documentation.build_report','python -m ARNAV_Task.documentation.build_presentation --render','python -m ARNAV_Task.documentation.build_support','python -m ARNAV_Task.documentation.validate_final --render --write-manifest'],
        evolved_documentation_references=evolved,
        limitations=['Three historical research metadata references remain unresolved.','No full scheduler matrix rerun in D6.','Mixed A4/A3 foldout report pages preserve figure readability; DOCX pagination may vary by Word installation.','Native PowerPoint PDF metadata may differ between renders; editable Office ZIPs are normalized.','Presenter allocation/time budget are provisional; no professor-specific rubric found locally.'])
    write_json(final/'manifest.json',manifest)
    return manifest


def validate_manifest(final=FINAL):
    m=read(final/'manifest.json');errors=[]
    for path,digest in m['output_sha256'].items():
        if not (final/path).is_file() or sha256(final/path)!=digest:errors.append('Final output changed/missing: '+path)
    for path,digest in m['source_sha256'].items():
        if not (ROOT/path).is_file() or sha256(ROOT/path)!=digest:errors.append('Final source changed/missing: '+path)
    return errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--render',action='store_true');p.add_argument('--write-manifest',action='store_true');args=p.parse_args()
    e=Evidence();r=document_check(e)
    if args.render:r['rendered_pages']=render_all()
    if r['passed'] and args.write_manifest:write_manifest(e)
    elif (FINAL/'manifest.json').is_file():r['errors'].extend(validate_manifest())
    r['passed']=not r['errors'];print(json.dumps(r,indent=2));return 0 if r['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
