"""Editable Mermaid and matching portable Matplotlib vector diagrams."""
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import json
from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ROOT
from .style import plt
from .figures import Figure


def definitions(a, p3, discrepancy_count):
    return [
        ('A01_system','Complete EcoSched research architecture',
         [('raw','Raw Alibaba\narchive',0,2),('prepare','Extraction and\npreparation',1,2),('validated','Validated workload\npackage',2,2),('sim',f"Trace-driven simulator\n{len(a.config['policies'])} approved policies",3,2),
          ('power','SPECpower\nsurrogate model',3,1),('results',f'Experiment artifacts\n{len(a.rows)} offline outcomes',2,1),('d5','D5 mechanism\nanalysis',1,1),('d6','D6 dashboard +\npublication exports',0,1)],
         [('raw','prepare'),('prepare','validated'),('validated','sim'),('sim','results'),('power','sim'),('results','d5'),('d5','d6')],
         'The offline research path uses fixed Alibaba-derived inputs, common simulation controls and separate SPECpower curves. D6 reuses frozen results and D5 evidence; it does not rerun experiments.',
         ['RAW_Alibaba/README.md','ROHAN_Task/README.md','RUSHI_Task/README.md','ARNAV_Task/README.md']),
        ('A02_kafka','Kafka arrival transport and monitoring',
         [('input','Validated Alibaba\narrival stream',0,2),('producer','Python producer\nordered arrivals',1,2),('topic','Kafka topic\n1 partition / 1 replica',2,2),('consumer','Python consumer\nvalidate + deduplicate',3,2),
          ('controller','External controller\nworkers + lifecycle',1,1),('state','SQLite WAL\nevents + aggregates',3,1),('monitor','Streamlit monitor\nread-only snapshots',2,0)],
         [('input','producer'),('producer','topic'),('topic','consumer'),('consumer','state'),('consumer','topic','Manual commit after persistence'),
          ('controller','producer','Manage'),('controller','consumer','Manage'),('state','monitor')],
         'At-least-once transport with idempotent SQLite persistence. The external controller outlives Streamlit reruns. Manual Kafka offsets are committed after persistence; no exactly-once or high-availability claim is made.',
         ['ARNAV_Task/kafka/controller.py','ARNAV_Task/kafka/consumer.py','ARNAV_Task/kafka/state.py','ARNAV_Task/docker-compose.yml']),
        ('A03_dashboard_modes','Offline research and live transport remain separate',
         [('offline','Offline simulator\ncommitted outcomes',0,2),('adapter','Artifact adapter\nnumerical validation',1,2),('research','7 research pages\nenergy + performance',2,2),
          ('kafka','Live Kafka\narrival replay',0,0),('sqlite','SQLite transport state\ncounts + demand + lag',1,0),('live','Live replay page\ncontroller + monitoring',2,0)],
         [('offline','adapter'),('adapter','research'),('kafka','sqlite'),('sqlite','live')],
         'Offline pages show previous scheduler simulation results. The live page monitors real arrival transport only: offered requests, throughput, lag and integrity. It provides no live energy, allocation, active-host or SLA metrics.',
         ['ARNAV_Task/dashboard/data_service.py','ARNAV_Task/dashboard/replay_service.py','ARNAV_Task/dashboard/app.py']),
        ('A04_validation','Layered reproducibility and validation',
         [('fingerprint','Archive + raw-member\nfingerprints',0,2),('independent','Independent raw-row\nvalidation',1,2),('prepared',f"Prepared outputs\n{len(p3['prepared_outputs'])} exact hash matches",2,2),
          ('result',f'Result reconciliation\n{len(a.rows)} outcomes / {len(a.comparisons(primary_only=True))} pairs',2,1),('exports','Reproducible exports\nsource + output hashes',1,0),('unresolved',f'Historical metadata\n{discrepancy_count} unresolved references',0,0)],
         [('fingerprint','independent'),('independent','prepared'),('prepared','result'),('result','exports'),('unresolved','exports','Disclose separately')],
         'Raw payload and prepared-output identity are verified in Phase 3. Numerical consistency is independently checked. Three historical manifest/summary/audit references remain unresolved; these layers do not establish full end-to-end lineage.',
         ['ARNAV_Task/reports/phase3_verification.json','ARNAV_Task/reports/artifact_validation.json','ARNAV_Task/reports/provenance_reconciliation.md'])]


def architecture_figures(a=None,p3=None):
    a=a or ResearchArtifacts()
    p3=p3 or json.loads((a.root/'ARNAV_Task/reports/phase3_verification.json').read_text())
    discrepancy_count=len(json.loads((a.root/'ARNAV_Task/reports/artifact_validation.json').read_text())['provenance']['discrepancies'])
    for ident,title,nodes,edges,caption,sources in definitions(a,p3,discrepancy_count):
        sources=sources+['RAW_Alibaba/prepared/manifest.json','ARNAV_Task/reports/phase3_verification.json','ARNAV_Task/reports/artifact_validation.json']
        fig,ax=plt.subplots(figsize=(12,6.1),layout='constrained')
        xmax=max(n[2] for n in nodes)
        ymin=min(n[3] for n in nodes)
        ax.set(xlim=(-.65,xmax+.65),ylim=(ymin-.5,2.85 if ident=='A02_kafka' else 2.6));ax.axis('off')
        positions={n:(x,y) for n,label,x,y in nodes};width,height=.85,.48
        for n,label,x,y in nodes:
            color='#F6EADB' if n=='unresolved' else '#E7F1F0' if n in ('validated','state','exports') else '#ECF1F6'
            ax.add_patch(FancyBboxPatch((x-width/2,y-height/2),width,height,boxstyle='round,pad=.025',linewidth=.9,edgecolor='#45616D',facecolor=color,zorder=3))
            ax.text(x,y,label,ha='center',va='center',fontsize=9,zorder=4)
        for e in edges:
            start,end=e[:2];x1,y1=positions[start];x2,y2=positions[end]
            if start=='consumer' and end=='topic':
                ax.annotate('',xy=(x2,y2+height/2+.03),xytext=(x1,y1+height/2+.03),
                            arrowprops=dict(arrowstyle='-|>',color='#45616D',lw=1,connectionstyle='arc3,rad=.55'))
                ax.text((x1+x2)/2,2.68,e[2],ha='center',fontsize=8,bbox=dict(facecolor='white',edgecolor='none',pad=2),zorder=5)
                continue
            if start=='controller' and end=='consumer':
                ax.add_patch(FancyArrowPatch((x1+width/2+.03,y1+.1),(x2,y2-height/2-.03),
                    arrowstyle='-|>',mutation_scale=12,lw=1,color='#45616D',linestyle='--'))
                ax.text(2.1,1.4,'Manage',ha='center',fontsize=7,bbox=dict(facecolor='white',edgecolor='none',pad=1),zorder=5)
                continue
            dx,dy=x2-x1,y2-y1
            # Attach to box edges instead of drawing arrows behind node labels.
            if abs(dx)>abs(dy):p1=(x1+(width/2+.03)*(1 if dx>0 else -1),y1);p2=(x2-(width/2+.03)*(1 if dx>0 else -1),y2)
            else:p1=(x1,y1+(height/2+.03)*(1 if dy>0 else -1));p2=(x2,y2-(height/2+.03)*(1 if dy>0 else -1))
            curved=len(e)>2 or (start=='results' and end=='d6')
            ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle='-|>',mutation_scale=12,lw=1,color='#45616D',connectionstyle=f'arc3,rad={.20 if curved else 0}',zorder=2))
            if len(e)>2:ax.text((x1+x2)/2+.05,(y1+y2)/2+.13,e[2],fontsize=7,ha='center',bbox=dict(facecolor='white',edgecolor='none',pad=1),zorder=5)
        fig.suptitle(title,fontsize=14)
        yield Figure(ident,'architecture',title,caption,sources,{'nodes':nodes,'edges':edges},fig,evidence='system architecture')


def mermaid(data):
    lines=['flowchart LR']
    for n,label,x,y in data['nodes']:
        lines.append(f'    {n}["{label.replace(chr(10), "<br/>")}"]')
    for edge in data['edges']:
        lines.append(f'    {edge[0]} -->'+(f'|"{edge[2]}"|' if len(edge)>2 else '')+f' {edge[1]}')
    return '\n'.join(lines)+'\n'
