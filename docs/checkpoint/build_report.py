"""Build the two-page mid-term report from the frozen proposal comparison."""
from pathlib import Path
from xml.sax.saxutils import escape
import json
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output/pdf"
OUT.mkdir(parents=True, exist_ok=True)
FILE = OUT / "EcoSched_Midterm_Checkpoint.pdf"
validation = json.loads((ROOT / "BASELINE_Comparison/reports/validation.json").read_text())
assert validation["passed"] and validation["unique_runs"] == 36
assert set(validation["active_policies"]) == {"lr_mmt", "lr_mmt_memory", "first_fit", "best_fit"}
navy = colors.HexColor("#183246")
teal = colors.HexColor("#167278")
gray = colors.HexColor("#52616b")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=10,
    leading=12.8, textColor=navy, spaceAfter=6))
styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=11.5,
    leading=14, textColor=teal, spaceBefore=8, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=9,
    leading=11.5, textColor=navy, spaceAfter=0))
styles.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=8.3,
    leading=10.5, textColor=gray, spaceAfter=5))
styles.add(ParagraphStyle(name="TitleCustom", fontName="Helvetica-Bold", fontSize=21,
    leading=25, textColor=navy, spaceAfter=5))
story=[]
markdown=[]


def p(text, style="ReportBody"):
    story.append(Paragraph(text,styles[style]))
    markdown.append(text.replace("<b>","**").replace("</b>","**")+"\n")


def heading(text):
    story.append(Paragraph(text,styles["Section"]))
    markdown.append("## "+text+"\n")


def table(headers, rows, widths):
    data=[[Paragraph("<b>"+escape(t)+"</b>",styles["Cell"]) for t in headers]]
    data += [[Paragraph(t,styles["Cell"]) for t in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign="LEFT",repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e6eff1")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LINEBELOW",(0,0),(-1,0),.7,teal),
        ("LINEBELOW",(0,1),(-1,-1),.3,colors.HexColor("#d7e0e4")),
    ]))
    story.append(t)
    story.append(Spacer(1,5))
    markdown.append("| "+" | ".join(headers)+" |")
    markdown.append("|"+"---|"*len(headers))
    markdown.extend("| "+" | ".join(r).replace("<b>","**").replace("</b>","**")+" |" for r in rows)
    markdown.append("")


p("AMS 560  /  MID-TERM CHECKPOINT  /  26 OCTOBER 2026","Small")
p("EcoSched","TitleCustom")
p("CPU and memory-aware placement for energy-efficient cluster scheduling","ReportBody")
p("Team: Arnav Desai, Brave Desai, Rohan Rane, Rushi Jhala and Yaksh Gandhi","Small")
heading("1. Project objective and description")
p("EcoSched investigates whether considering both CPU and memory demand during placement can reduce modeled "
  "cluster energy without unacceptable waiting, overload or migration costs. Our primary comparison is "
  "<b>CPU-oriented LR-MMT versus LR-MMT + CPU/Memory-Aware Placement</b>. Local Regression (LR) overload "
  "detection and Minimum Migration Time (MMT) selection remain fixed; only placement changes. First Fit and "
  "Best Fit provide additional baselines.")
p("We built a trace-driven simulator using independently processed Alibaba cluster-trace-v2017 raw data. "
  "The fixed 64-host pool is tested with 250, 1,000 and 4,000 task groups (16,534, 68,457 and 378,285 instances). "
  "HPE DL360 Gen9, Huawei RH2288H V3 and QuantaGrid D51B-2U SPECpower curves are applied separately. "
  "Reported energy is a simulation estimate, not Alibaba's measured electricity consumption.")
heading("2. Timeline and expected deliverables")
table(["Period / target", "Work and expected output"],[
    ["Completed by checkpoint", "Raw-data preparation, simulator, initial scheduling policies and the 36-case proposal/baseline comparison."],
    ["Oct 27 - Nov 8", "D5: analyze resource skew, fragmentation and energy/performance tradeoffs; test placement parameters."],
    ["Nov 9 - Nov 25", "D4-D5: evaluate frozen settings on untouched Alibaba samples and complete sensitivity checks; freeze core engineering and experiments by Nov 25."],
    ["Nov 26 - Dec 12", "D6: finish Kafka replay/dashboard demo, final report and presentation; reserve time for verification and rehearsal."],
],[118,410])
heading("3. Completion status of each deliverable")
table(["Deliverable", "Status and completed work"],[
    ["D1. Workload package", "<b>Complete for the current benchmark.</b> Raw-table preparation, deterministic host/workload samples, individual observed runtimes, original instance counts and input hashes."],
    ["D2. Simulator and power", "<b>Core implementation complete.</b> Event replay, CPU/memory capacity checks, FIFO queueing, sleep/wakeup, migration pauses, SPECpower integration and unit checks."],
    ["D3. Scheduling policies", "<b>Initial implementation complete.</b> Both proposed comparison policies plus First Fit and Best Fit; shared LR/MMT controller and validated capacity constraints."],
    ["D4. Experiment matrix", "<b>Initial matrix complete: 36/36 cases.</b> Four policies x three workload sizes x three separate power curves; all offered work completed."],
    ["D5. Research analysis", "<b>Partially complete.</b> Energy/performance tables, graphs and sanity checks available. Detailed skew analysis, placement sensitivity and unseen-sample evaluation remain."],
    ["D6. Final package", "<b>Partially complete.</b> Code, configuration, reproducibility instructions and plots available. Kafka demo, final report and presentation remain."],
],[118,410])
story.append(PageBreak())
p("EcoSched | Findings and completion plan","TitleCustom")
p("MID-TERM CHECKPOINT  /  PAGE 2","Small")
heading("3. Completion status: preliminary findings")
p("The proposed memory-aware placement saves energy in <b>4 of 9</b> paired workload/curve cases; CPU-oriented "
  "LR-MMT uses less energy in the other five. The proposed variant wins all three small workloads and the "
  "medium Huawei case. On the largest workload, its energy use increases as follows:")
table(["Server curve", "CPU LR-MMT", "Proposed placement", "Energy increase"],[
    ["HPE DL360 Gen9", "34.270 kWh", "39.136 kWh", "+14.20%"],
    ["Huawei RH2288H V3", "34.017 kWh", "37.745 kWh", "+10.96%"],
    ["QuantaGrid D51B-2U", "35.333 kWh", "40.478 kWh", "+14.56%"],
],[170,110,138,110])
p("Memory-aware placement lowers mean waiting and requested-resource pressure on the largest workloads, "
  "but keeps more hosts powered. Current results therefore show an energy/performance tradeoff and do not "
  "establish consistent energy savings. All 36 active cases preserve identical offered work and report zero "
  "rejected or unfinished instances. Later scheduler extensions are outside this checkpoint's scope.")
heading("4. Plan to complete unfinished deliverables")
p("<b>D4 - Extended validation:</b> Select additional untouched Alibaba windows or samples using a recorded "
  "sampling rule. Freeze policy settings before evaluation and rerun the same four-policy matrix separately "
  "for each power curve. Preserve unfavorable outcomes and validate completion and energy accounting.")
p("<b>D5 - Analysis and refinement:</b> Break down outcomes by balanced, CPU-heavy and memory-heavy demand; "
  "measure fragmentation, active-host time and migration cost. Investigate why the current memory-balance "
  "score spreads work across extra hosts. Test placement-weight and packing refinements on development "
  "samples while keeping LR detection and MMT selection unchanged, then assess the frozen rule on untouched "
  "samples. Report energy together with waiting, migrations and overload proxies.")
p("<b>D6 - Delivery:</b> Complete one Kafka replay/dashboard demonstration of the trace and scheduling "
  "outputs. Integrate the verified tables and graphs into the final report, document assumptions and "
  "reproduction commands, and prepare and rehearse the final presentation. The demo will visualize the "
  "experiment; simulator outputs remain the evaluation evidence.")
heading("5. Difficulties and risks to completing on time")
p("<b>Data access and provenance:</b> Acquiring the raw archive and resolving earlier input ambiguity took "
  "additional effort. The active pipeline now reads the uploaded raw archive independently. Its compressed "
  "checksum differs from the published legacy archive; gzip/member integrity checks and raw-file "
  "corroboration passed. The discrepancy remains documented rather than treated as a publisher checksum match.")
p("<b>Model and evidence limits:</b> The trace is large and has incomplete observations. We retain only "
  "complete eligible groups, which introduces selection bias. Samples overlap; the nine comparisons are "
  "not independent statistical replications. Power, migration and sleep assumptions require sensitivity "
  "checks; background online load and production dependencies are not replayed.")
p("<b>Algorithm and schedule risk:</b> The proposed placement does not yet deliver consistent energy "
  "improvement. Further tuning may not reverse this result. We will prioritize a defensible explanation "
  "and fair evaluation, keep scope limited to placement, and freeze core work by Nov 25. The Kafka demo "
  "and final integration are the main remaining delivery risks; Nov 26-Dec 12 is reserved for completion, "
  "reruns and rehearsal.")
p("Evidence: docs/EcoSched_Proposal.pdf; BASELINE_Comparison/reports/REPORT.md and validation.json; "
  "RAW_Alibaba/prepared/manifest.json and data_validation.json. Status reflects the current implementation; "
  "future dates are planned targets.","Small")


def page_frame(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(teal)
    canvas.setLineWidth(.75)
    canvas.line(42,32,570,32)
    canvas.setFont("Helvetica",8)
    canvas.setFillColor(gray)
    canvas.drawString(42,20,"EcoSched | AMS 560 | Mid-term checkpoint")
    canvas.drawRightString(570,20,f"{doc.page} / 2")
    canvas.restoreState()


doc=SimpleDocTemplate(str(FILE),pagesize=letter,rightMargin=42,leftMargin=42,
    topMargin=35,bottomMargin=43,title="EcoSched Mid-term Checkpoint",author="EcoSched Team")
doc.build(story,onFirstPage=page_frame,onLaterPages=page_frame)
reader=PdfReader(FILE)
assert len(reader.pages)==2, f"Expected two pages, got {len(reader.pages)}"
assert all(len(page.extract_text())>1500 for page in reader.pages)
(HERE / "EcoSched_Midterm_Checkpoint.md").write_text("\n".join(markdown),encoding="utf-8")
print(f"Created {FILE}; verified {len(reader.pages)} pages")
for i,page in enumerate(reader.pages,1):
    print(f"Page {i}: {len(page.extract_text().split())} words")
