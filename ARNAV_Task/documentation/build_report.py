"""Generate the editable DOCX/Markdown and vector-composed final report PDF."""
import argparse
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import fitz
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Flowable, Frame, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from matplotlib import get_data_path
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .evidence import Evidence, FINAL, TITLE, TEAM, read, write_json, canonical_office, safe_output
from .tables import report_table

SIZES={'A4':A4,'A4L':landscape(A4),'A3':A3,'A3L':landscape(A3)}


def fonts():
    directory=Path(get_data_path())/'fonts/ttf'
    for name,file in [('Body','DejaVuSerif.ttf'),('BodyBold','DejaVuSerif-Bold.ttf'),('Sans','DejaVuSans.ttf'),('SansBold','DejaVuSans-Bold.ttf'),('Mono','DejaVuSansMono.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(directory/file)))


def paragraph(text,size=10.1,leading=14,font='Body',**kw):
    return Paragraph(escape(str(text)).replace('\n','<br/>'),ParagraphStyle('block',fontName=font,fontSize=size,leading=leading,textColor=HexColor('#1d2935'),spaceAfter=7,**kw))


def table_flow(headers,rows,width,font=8.3,widths=None):
    widths=widths or [width/len(headers)]*len(headers)
    data=[[paragraph(v,font,font*1.25,'SansBold' if i==0 else 'Sans',splitLongWords=True) for v in row] for i,row in enumerate([headers]+rows)]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e9f1f2')),('VALIGN',(0,0),(-1,-1),'TOP'),
                          ('LINEBELOW',(0,0),(-1,0),.7,HexColor('#45616d')),('LINEBELOW',(0,-1),(-1,-1),.5,HexColor('#9aa9ae')),
                          ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),1)]))
    return t


class VectorFigure(Flowable):
    def __init__(self,path,width,height,placements):
        super().__init__();self.path=path;self.width=width;self.height=height;self.placements=placements
    def draw(self):
        x,y=self.canv.absolutePosition(0,0)
        self.placements.append((self.canv.getPageNumber()-1,str(self.path),(x,y,self.width,self.height)))


def bibliography(e):
    refs=read(e.root/'ARNAV_Task/final/report/source/references.json')
    return refs


def fingerprint_rows(e):
    p3=e.receipts[3];rows=[['Active compressed archive',p3['archive']['archive_sha256']],['Legacy compressed archive (different)',p3['archive']['published_legacy_archive_sha256']]]
    rows.extend([name,r['sha256']] for name,r in sorted(p3['archive']['source_files'].items()))
    rows.extend([r['file'],r['sha256']] for r in p3['prepared_outputs'])
    old=read(e.root/'ARNAV_Task/reports/artifact_validation.json')['provenance']['discrepancies']
    rows.extend([r['id']+' expected / current',' / '.join(r['expected_sha256'])+' / '+r['current_sha256']] for r in old)
    return rows


def resolve(e,source):
    result=[]
    for page in source['pages']:
        item={**page,'blocks':[]}
        for b in page['blocks']:
            item['blocks'].append({**b,**{k:e.text(v) for k,v in b.items() if k in ('text','caption') and isinstance(v,str)}})
        result.append(item)
    return result


def build(output=FINAL/'report',source=None):
    output=safe_output(output);e=Evidence();fonts();output.mkdir(parents=True,exist_ok=True)
    source=Path(source or FINAL/'report/source/report.json');pages=resolve(e,read(source));placements=[]
    raw=BytesIO();c=canvas.Canvas(raw,invariant=1,pageCompression=1);c.setTitle(TITLE);c.setAuthor('; '.join(TEAM));c.setSubject('AMS 560 Big Data, Stony Brook University')
    doc=Document();doc.core_properties.title=TITLE;doc.core_properties.author='; '.join(TEAM)
    doc.core_properties.created=datetime(2000,1,1);doc.core_properties.modified=datetime(2000,1,1)
    normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10);normal.paragraph_format.space_after=Pt(5)
    footer=doc.sections[0].footer.paragraphs[0]
    footer.add_run('EcoSched · AMS 560 | ');field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    markdown=['# '+TITLE,'','Team: '+', '.join(TEAM),''];fig_counter=0;figures=[];tables=[];page_receipts=[]
    for i,page in enumerate(pages):
        w,h=SIZES[page['size']];margin=42 if w<700 else 34
        c.setPageSize((w,h));c.setFont('Sans',8);c.setFillColor(HexColor('#5a6d77'));c.drawString(margin,h-23,'ECOSCHED  /  AMS 560 BIG DATA  /  STONY BROOK UNIVERSITY')
        c.setStrokeColor(HexColor('#b7c4ca'));c.line(margin,33,w-margin,33);c.drawString(margin,20,'Offline scheduling research · separately verified Kafka transport');c.drawRightString(w-margin,20,str(i+1))
        c.bookmarkPage(f'page{i+1}');c.addOutlineEntry(page['title'],f'page{i+1}',level=0)
        section=doc.sections[0] if i==0 else doc.add_section(WD_SECTION_START.NEW_PAGE)
        section.page_width=Inches(w/72);section.page_height=Inches(h/72)
        section.top_margin=section.bottom_margin=Inches(.55);section.left_margin=section.right_margin=Inches(margin/72)
        doc.add_heading(page['title'],level=0 if i==0 else 1);markdown+=['',f'## Page {i+1}: '+page['title'],'']
        flow=[paragraph(page['title'],18 if i else 35,23 if i else 42,'SansBold'),Spacer(1,8)]
        width=w-2*margin
        for b in page['blocks']:
            kind=b['type']
            if kind=='cover':flow.append(Spacer(1,38));continue
            if kind in ('paragraph','heading','equation','code'):
                text=b['text'];ishead=kind=='heading';mono=kind in ('equation','code')
                cover_title=i==0 and text.startswith('A Trace-Driven')
                flow.append(paragraph(text,19 if cover_title else 11.3 if ishead else 8.0 if mono else 10.1,26 if cover_title else 15 if ishead else 11 if mono else 14,'SansBold' if ishead or cover_title else 'Mono' if mono else 'Body'))
                if ishead:doc.add_heading(text,2)
                else:doc.add_paragraph(text,style='No Spacing' if mono else None)
                markdown.append(('### ' if ishead else '')+text+'\n')
            elif kind in ('figure','screenshot'):
                fig_counter+=1;height=b.get('height',260)
                if kind=='figure':
                    ident=b['id'];meta=e.figures[ident];path=e.figure(ident)
                    flow.append(VectorFigure(path,width,height,placements))
                    caption=f"Figure {fig_counter} ({ident}). {meta['caption']}";png=e.figure(ident,'png');figures.append(ident)
                else:
                    png=e.root/b['path'];image=Image(str(png));image.drawWidth=min(width,height*image.imageWidth/image.imageHeight);image.drawHeight=height
                    flow.append(image);caption=f"Figure {fig_counter}. "+b['caption'].removeprefix('Figure 14. ')
                flow.append(paragraph(caption,8.0,10.4,'Sans'))
                image_width=min(width,height*1.6)
                doc.add_picture(str(png),width=Inches(image_width/72));doc.add_paragraph(caption,style='Caption')
                markdown.extend([f'![{caption}]({png.relative_to(e.root).as_posix()})',''])
            elif kind=='table':
                headers,rows=report_table(e,b['id']);flow.extend([paragraph(b['caption'],8.2,10.5,'SansBold'),table_flow(headers,rows,width,b.get('font',8.3)),Spacer(1,5)])
                table=doc.add_table(rows=1,cols=len(headers));table.style='Light Shading Accent 1'
                for cell,value in zip(table.rows[0].cells,headers):cell.text=str(value)
                for row in rows:
                    for cell,value in zip(table.add_row().cells,row):cell.text=str(value)
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            for run in para.runs:run.font.size=Pt(min(9,b.get('font',8.3)))
                doc.add_paragraph(b['caption'],style='Caption');tables.append(b['id'])
                markdown+=[b['caption'],'| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']
                markdown.extend('| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in rows)
            elif kind=='references':
                for ref in bibliography(e):
                    text=f"[{ref['number']}] {ref['citation']} {ref['url']}"
                    flow.append(paragraph(text,9,12,'Sans',splitLongWords=True));doc.add_paragraph(text);markdown.append(text+'\n')
            elif kind=='provenance_hashes':
                rows=fingerprint_rows(e);flow.append(table_flow(['Artifact','SHA-256 identity (expected and current where unresolved)'],rows,width,7.1,[width*.28,width*.72]))
                doc.add_heading('Exact fingerprints',2)
                for label,value in rows:doc.add_paragraph(label+'\n'+value)
                markdown.extend(label+': `'+value+'`\n' for label,value in rows)
            else:raise ValueError('Unsupported report block '+kind)
        frame=Frame(margin,43,width,h-89,showBoundary=0,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        frame.addFromList(flow,c)
        if flow:raise ValueError(f"Report page {i+1} overflow: {page['title']} ({len(flow)} remaining blocks)")
        page_receipts.append(dict(page=i+1,title=page['title'],size=page['size']))
        c.showPage()
    c.save();pdf=fitz.open(stream=raw.getvalue(),filetype='pdf')
    for index,path,(x,y,width,height) in placements:
        page=pdf[index]
        with fitz.open(path) as src:page.show_pdf_page(fitz.Rect(x,page.rect.height-y-height,x+width,page.rect.height-y),src,0,keep_proportion=True,overlay=True)
    target=output/'EcoSched_Final_Report.pdf';pdf.save(target,garbage=4,deflate=True,no_new_id=True);pdf.close()
    docx_path=output/'EcoSched_Final_Report.docx';doc.save(docx_path);canonical_office(docx_path)
    (output/'EcoSched_Final_Report.md').write_text('\n'.join(markdown),encoding='utf-8')
    write_json(output/'claims.json',e.ledger());receipt=dict(pages=page_receipts,page_count=len(pages),figures=figures,tables=tables,
        pdf=str(target.name),docx=docx_path.name,vector_publication_figures=True,source=str(source.relative_to(e.root)) if source.is_relative_to(e.root) else str(source))
    write_json(output/'build_receipt.json',receipt)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--source',type=Path);args=p.parse_args()
    result=build(args.output or FINAL/'report',args.source);print(f"Generated report: {result['page_count']} pages")


if __name__=='__main__':main()
