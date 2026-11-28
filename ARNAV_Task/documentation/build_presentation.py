"""Editable 16:9 PowerPoint; optional native macOS PowerPoint PDF export."""
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import time
import json

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.chart.data import CategoryChartData

from .evidence import Evidence, FINAL, TEAM, TITLE, POLICY_SHORT, SHORT, read, write_json, canonical_office, safe_output
from .tables import report_table
from ARNAV_Task.dashboard.constants import POLICY_COLORS
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.analysis.artifacts import CURVES, SIZES, PRIMARY

INK='#172D3A';TEAL='#167E78';MUTED='#526975';PALE='#EFF5F5';ORANGE='#A65318'


def rgb(value):return RGBColor.from_string(value.lstrip('#'))


def box(slide,x,y,w,h,fill=PALE,line=None):
    shape=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    shape.fill.solid();shape.fill.fore_color.rgb=rgb(fill)
    if line:shape.line.color.rgb=rgb(line)
    else:shape.line.fill.background()
    return shape


def text(slide,value,x,y,w,h,size=20,color=INK,bold=False):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));frame=shape.text_frame
    frame.word_wrap=True;frame.margin_left=frame.margin_right=Inches(.02);frame.margin_top=frame.margin_bottom=0
    for n,line in enumerate(str(value).split('\n')):
        p=frame.paragraphs[0] if n==0 else frame.add_paragraph();p.text=line
        p.font.name='Arial';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=rgb(color);p.space_after=Pt(12)
    return shape


def bullets(slide,lines,x=.65,y=1.6,w=12,h=4.7,size=23):
    return text(slide,'\n'.join('• '+line for line in lines),x,y,w,h,size)


def chart(slide,data,kind,x,y,w,h,*,ylabel=None,colors=None):
    obj=slide.shapes.add_chart(kind,Inches(x),Inches(y),Inches(w),Inches(h),data).chart
    obj.chart_style=10;obj.font.name='Arial';obj.font.size=Pt(14)
    obj.has_legend=True;obj.legend.position=XL_LEGEND_POSITION.BOTTOM;obj.legend.include_in_layout=False;obj.legend.font.size=Pt(13)
    obj.category_axis.tick_labels.font.size=Pt(14);obj.value_axis.tick_labels.font.size=Pt(13)
    if ylabel:
        obj.value_axis.has_title=True;obj.value_axis.axis_title.text_frame.text=ylabel
        obj.value_axis.axis_title.text_frame.paragraphs[0].font.size=Pt(14)
    if kind==XL_CHART_TYPE.LINE:obj.value_axis.minimum_scale=0
    if colors:
        for series,color in zip(obj.series,colors):
            series.format.line.color.rgb=rgb(color);series.format.line.width=Pt(2)
            series.format.fill.solid();series.format.fill.fore_color.rgb=rgb(color)
    if kind in (XL_CHART_TYPE.COLUMN_CLUSTERED,XL_CHART_TYPE.BAR_CLUSTERED):
        for series in obj.series:series.invert_if_negative=False
    return obj


def simple_table(slide,headers,rows,x,y,w,h,font=15):
    table=slide.shapes.add_table(len(rows)+1,len(headers),Inches(x),Inches(y),Inches(w),Inches(h)).table
    for i,row in enumerate([headers]+rows):
        for j,value in enumerate(row):
            cell=table.cell(i,j);cell.text=str(value);cell.fill.solid();cell.fill.fore_color.rgb=rgb('#E4EEEE' if i==0 else '#FFFFFF')
            cell.margin_left=cell.margin_right=Inches(.08)
            for p in cell.text_frame.paragraphs:
                p.font.name='Arial';p.font.size=Pt(font);p.font.bold=i==0;p.font.color.rgb=rgb(INK)
    return table


def diagram(slide,e,identifier):
    data=read(e.figure(identifier,'json'));nodes=data['nodes'];edges=data['edges']
    maxx=max(n[2] for n in nodes);miny=min(n[3] for n in nodes);maxy=max(n[3] for n in nodes)
    positions={}
    width=2.55 if maxx==3 else 3.1
    for key,label,x,y in nodes:
        px=.55+x*(12.1-width)/max(maxx,1);py=1.7+(maxy-y)*3.6/max(1,maxy-miny)
        positions[key]=(px,py);box(slide,px,py,width,.9,line='#8EA6AE')
        text(slide,label,px+.09,py+.15,width-.18,.68,16)
    for edge in edges:
        a,b=edge[:2];x1,y1=positions[a];x2,y2=positions[b]
        if a=='consumer' and b=='topic':continue
        if abs(x2-x1)>abs(y2-y1):start=(x1+width if x2>x1 else x1,y1+.45);end=(x2 if x2>x1 else x2+width,y2+.45)
        else:start=(x1+width/2,y1+.9 if y2>y1 else y1);end=(x2+width/2,y2 if y2>y1 else y2+.9)
        line=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,*[Inches(v) for v in (*start,*end)]);line.line.color.rgb=rgb(TEAL);line.line.width=Pt(1.5)
        # Explicit arrowheads in OOXML; connectors remain editable.
        from pptx.oxml.xmlchemy import OxmlElement
        endnode=OxmlElement('a:tailEnd');endnode.set('type','triangle');line._element.spPr.get_or_add_ln().append(endnode)
    if identifier=='A02':text(slide,'Persist SQLite transaction → manual Kafka offset commit\nAt least once with idempotent persistence; external controller survives reruns.',.65,6.35,12,.55,15,TEAL)


def native_export(pptx,pdf):
    """Use only this generated deck; do not close unrelated presentations."""
    if not Path('/Applications/Microsoft PowerPoint.app').exists():raise RuntimeError('Native PDF export requires Microsoft PowerPoint on macOS; editable PPTX was still generated')
    before=sha256(pptx);previous=pdf.read_bytes() if pdf.exists() else None
    pdf.unlink(missing_ok=True)  # Avoid PowerPoint's modal replace-confirmation dialog.
    subprocess.run(['open','-a','Microsoft PowerPoint',str(pptx.resolve())],check=True)
    # HFS text is required by PowerPoint's save API; POSIX-file form can silently fail.
    script='''on run argv
with timeout of 60 seconds
set deckName to item 3 of argv
set outputPath to (POSIX file (item 2 of argv)) as text
tell application "Microsoft PowerPoint"
repeat 40 times
if exists presentation (item 3 of argv) then exit repeat
delay 0.25
end repeat
set deck to presentation deckName
try
set index of document window 1 of deck to 1
end try
save deck in outputPath as save as PDF
end tell
end timeout
end run'''
    time.sleep(1)
    result=subprocess.run(['osascript','-',str(pptx.resolve()),str(pdf.resolve()),pptx.name],input=script,text=True,capture_output=True,timeout=70)
    deadline=time.monotonic()+10
    while not pdf.is_file() and time.monotonic()<deadline:time.sleep(.25)
    if not pdf.is_file():
        if previous is not None:pdf.write_bytes(previous)
        raise RuntimeError('PowerPoint PDF export failed: '+result.stderr.strip())
    import fitz
    with fitz.open(pdf) as exported:
        if len(exported)!=len(Presentation(pptx).slides):raise RuntimeError('Native PDF slide count differs')
    subprocess.run(['osascript','-e',f'tell application "Microsoft PowerPoint" to close presentation {json.dumps(pptx.name)} saving no'],capture_output=True,timeout=15)
    if sha256(pptx)!=before:raise RuntimeError('Native export unexpectedly changed the editable PPTX')
    return dict(renderer='Microsoft PowerPoint for Mac',version=subprocess.check_output(['osascript','-e','tell application "Microsoft PowerPoint" to get version'],text=True).strip(),pptx_unchanged=True)


def build(output=FINAL/'presentation',source=None,render=False):
    output=safe_output(output);e=Evidence();output.mkdir(parents=True,exist_ok=True)
    data=read(source or FINAL/'presentation/source/slides.json');deck=Presentation();deck.slide_width=Inches(13.333333);deck.slide_height=Inches(7.5)
    deck.core_properties.title=TITLE;deck.core_properties.author='; '.join(TEAM);deck.core_properties.created=deck.core_properties.modified=datetime(2000,1,1)
    notes=['# EcoSched speaker notes','',data['timing'],'','Presenter allocations below are provisional and require team agreement.',''];inventory=[]
    for i,raw in enumerate(data['slides'],1):
        item={**raw,'title':e.text(raw['title']),'bullets':[e.text(x) for x in raw['bullets']],'notes':e.text(raw['notes'])}
        slide=deck.slides.add_slide(deck.slide_layouts[6]);slide.background.fill.solid();slide.background.fill.fore_color.rgb=rgb('#FFFFFF')
        box(slide,0,0,13.333333,.065,TEAL);text(slide,'ECOSCHED  /  AMS 560 BIG DATA',.6,.24,9,.25,10,TEAL,True)
        text(slide,item['title'],.6,.72,12.05,.8,29,INK,True)
        text(slide,'Stony Brook University · '+('Recorded transport / engineering demonstration' if item['kind'] in ('kafka','demo','streaming') else 'Offline trace-driven scheduling research'),.6,7.13,11.5,.2,9,MUTED)
        text(slide,f'{i:02d}',12.1,7.09,.55,.25,11,MUTED)
        kind=item['kind']
        if kind=='title':
            text(slide,'A Trace-Driven Evaluation of CPU and Memory-Aware\nEnergy-Efficient Data Center Scheduling',.7,1.9,11.7,1.6,29,INK,True)
            text(slide,'Controlled placement. Explainable trade-offs.',.72,3.48,11.5,.5,20,TEAL)
            text(slide,' · '.join(TEAM),.72,4.2,11.5,.9,20)
            text(slide,'AMS 560 Big Data | Stony Brook University',.72,5.38,11.5,.45,20,TEAL)
        elif kind in ('architecture','kafka'):diagram(slide,e,item['figure'])
        elif kind=='dataset':
            for j,r in enumerate(e.a.manifest['workloads']):
                x=.65+j*4.15;box(slide,x,1.72,3.92,1.63)
                text(slide,f"{r['task_groups']:,} task groups",x+.18,1.95,3.55,.45,22,TEAL,True)
                text(slide,f"{r['instances']:,} instances",x+.18,2.54,3.55,.45,25,INK,True)
            bullets(slide,item['bullets'],.7,3.8,11.8,2.8,20)
        elif kind=='power':
            d=CategoryChartData();d.categories=[str(n*10) for n in range(11)]
            for curve in CURVES:d.add_series(SHORT[curve],e.a.curve_data['curves'][curve]['watts'])
            chart(slide,d,XL_CHART_TYPE.LINE,.5,1.6,7.6,4.9,ylabel='Whole-server AC power (W)',colors=['#0072B2','#E69F00','#009E73'])
            text(slide,'SPECpower target load (%)',2.5,6.5,5,.3,13,MUTED)
            bullets(slide,item['bullets'],8.4,1.85,4.2,4.8,20)
        elif kind=='primary':
            d=CategoryChartData();d.categories=[f'{s:,} groups' for s in SIZES];pairs=e.a.comparisons(primary_only=True)
            for c in CURVES:d.add_series(SHORT[c],[next(r['energy_reduction_pct'] for r in pairs if r['workload_groups']==s and r['power_curve']==c) for s in SIZES])
            obj=chart(slide,d,XL_CHART_TYPE.COLUMN_CLUSTERED,.5,1.65,8.25,4.95,ylabel='Energy reduction (%)',colors=['#0072B2','#E69F00','#009E73'])
            import math
            obj.value_axis.minimum_scale=-math.ceil(max(abs(r['energy_reduction_pct']) for r in pairs)/2)*2
            obj.value_axis.maximum_scale=2;obj.value_axis.major_unit=2;obj.value_axis.tick_labels.number_format='0'
            obj.category_axis.tick_label_position=XL_TICK_LABEL_POSITION.LOW
            bullets(slide,item['bullets'],9.0,1.9,3.65,4.8,21)
        elif kind=='tradeoff':
            source=[e.a.index[(4000,CURVES[0],p)] for p in PRIMARY]
            for j,(metric,title,unit) in enumerate([('energy_kwh','Modeled energy','kWh'),('mean_active_hosts','Mean active hosts','hosts'),('mean_wait_s','Mean initial wait','s'),('overload_host_time_fraction','Reservation pressure','fraction')]):
                x=.65+(j%2)*6.25;y=1.65+(j//2)*2.3;box(slide,x,y,5.95,2.03)
                text(slide,title,x+.18,y+.12,5.5,.35,20,INK,True);maximum=max(r[metric] for r in source)
                for n,r in enumerate(source):
                    py=y+.68+n*.57;box(slide,x+.18,py,3.3*r[metric]/maximum,.3,POLICY_COLORS[r['policy']]);text(slide,f"{r[metric]:.3f} {unit}",x+3.65,py-.03,2.1,.4,18)
            text(slide,'Teal: CPU LR-MMT   ·   Purple: CPU/memory LR-MMT   |   HPE / 4,000 groups only',.7,6.5,12,.4,15,TEAL)
        elif kind=='mechanism':
            rows=[r for r in e.a.d5_tables['pair_energy_gap'] if r['workload_groups']==4000 and r['power_curve']==CURVES[0]];r=rows[0]
            fields=['on_running_work_kwh','on_without_work_kwh','load_dependent_kwh','wakeups_kwh']
            # Native Office inverts negative per-point chart fills on some builds.
            # Editable rectangles preserve the signed linear scale and clear colors.
            labels=['Extra on-time / running','Extra on-time / empty','Load-dependent','Wake transitions']
            maximum=max(abs(r[k]) for k in fields);scale=3.7/maximum;zero=4.25
            box(slide,zero,2.05,.012,3.65,'#758A94')
            for n,(key,label) in enumerate(zip(fields,labels)):
                y=2.2+n*.85;value=r[key];length=abs(value)*scale
                text(slide,label,.65,y,3.25,.65,17)
                box(slide,zero if value>=0 else zero-length,y+.06,length,.37,ORANGE if value>=0 else TEAL)
                text(slide,f'{value:+.3f}',8.0,y+.02,.85,.5,16)
            text(slide,'0',zero-.06,5.88,.3,.3,13,MUTED)
            text(slide,'Candidate minus CPU LR-MMT (kWh)',2.5,6.22,6,.3,15,MUTED)
            bullets(slide,item['bullets'],9.05,1.8,3.65,4.8,20)
            text(slide,'HPE / 4,000 groups; selected main components. Full six-term reconciliation: R05 / T19.',.7,6.6,12,.3,13,MUTED)
        elif kind=='demo':
            path=e.root/str(item['screenshot']);slide.shapes.add_picture(str(path),Inches(.6),Inches(1.68),width=Inches(6.35))
            bullets(slide,item['bullets'],7.45,1.9,5.1,4.8,20)
            text(slide,'Actual recorded Phase 5 screenshot · switch to the browser for the live demonstration',.65,6.7,11,.3,12,TEAL)
        elif kind=='primary_table':
            headers,rows=report_table(e,'primary');simple_table(slide,headers,rows,.65,1.7,12.05,4.8,14)
            text(slide,'Baseline: CPU LR-MMT · positive reduction = savings · no averaging across power curves',.7,6.65,12,.3,13,TEAL)
        elif kind=='streaming':
            headers,rows=report_table(e,'streaming');simple_table(slide,headers,rows,.65,1.8,12.05,2.5,18)
            b=e.receipts[5]['browser_full_250_at_600x']
            text(slide,f"Separate 600× browser replay: {b['elapsed_wall_s']:.3f} s; {b['average_instances_per_s']:.2f} distinct instances/s",.7,4.85,12,.75,23,TEAL,True)
            text(slide,'Single ARM64 laptop / one KRaft broker. Transport measurements, not scheduler benchmarks.',.7,6,12,.65,19)
        elif kind=='references':
            refs=read(e.root/'ARNAV_Task/final/report/source/references.json')
            for j,r in enumerate(refs[:4]):text(slide,f"[{r['number']}] {r['citation']}",.65,1.6+j*.95,12,.9,15)
            text(slide,'[5–7] SPECpower result pages   ·   [8–11] Kafka, Streamlit, Plotly and SQLite official documentation\n[12] EcoSched repository. Full references and Git-supported contributions: final report.',.65,5.75,12,.85,16,TEAL)
        else:bullets(slide,item['bullets'],size=24 if kind=='motivation' else 23)
        note=f"Provisional presenter: {item['presenter_provisional']}\n\n{item['notes']}"
        slide.notes_slide.notes_text_frame.text=note
        notes.extend([f"## Slide {i}: {item['title']}",'',note,''])
        inventory.append(dict(slide=i,title=item['title'],kind=kind,appendix=item.get('appendix',False),figure=item.get('figure'),presenter_provisional=item['presenter_provisional']))
    path=output/'EcoSched_Final_Presentation.pptx';deck.save(path);canonical_office(path)
    (output/'speaker_notes.md').write_text('\n'.join(notes),encoding='utf-8');write_json(output/'claims.json',e.ledger())
    receipt=dict(slide_count=len(deck.slides),main_slides=data['main_slides'],slides=inventory,format='16:9',native_charts=True,
                 presentation_figures='Editable readable variants use the Phase 1 adapter and Phase 6 diagram data; actual Phase 5 screenshot embedded.',pdf_rendering=None)
    if render:receipt['pdf_rendering']=native_export(path,output/'EcoSched_Final_Presentation.pdf')
    write_json(output/'build_receipt.json',receipt);return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--source',type=Path);p.add_argument('--render',action='store_true');a=p.parse_args()
    r=build(a.output or FINAL/'presentation',a.source,a.render);print(f"Generated {r['slide_count']} editable slides; native PDF rendered: {bool(r['pdf_rendering'])}")


if __name__=='__main__':main()
