"""Plotly views of actual bounded replay observations; never interpolate absent data."""
from datetime import datetime,timezone
import plotly.graph_objects as go
from ARNAV_Task.dashboard.components.charts import finish


def replay_chart(metrics,kind,*,field=None):
    fig=go.Figure();sid=metrics['replay_id']
    if kind=='throughput':
        rows=metrics.get('throughput',[])
        fig.add_trace(go.Bar(x=[datetime.fromtimestamp(r['wall_second'],timezone.utc) for r in rows],
             y=[r['count'] for r in rows],marker_color='#32B5A4',name='Distinct persisted arrivals',
             hovertemplate='%{x|%H:%M:%S UTC}<br>%{y:,} instances in this 1-second bucket<extra></extra>'))
        title='Measured consumption throughput';x='Wall-clock time (UTC)';y='Distinct instances / s'
    elif kind=='lag':
        rows=metrics.get('offset_history',[])
        for key,label,color in [('session_lag','Session lag','#32B5A4'),('topic_lag','Topic lag','#82A9D0')]:
            fig.add_trace(go.Scatter(x=[datetime.fromtimestamp(r['wall_second'],timezone.utc) for r in rows],
                y=[r[key] for r in rows],mode='markers',name=label,marker=dict(size=5,color=color),
                hovertemplate='%{x|%H:%M:%S UTC}<br>%{y:,} offsets<extra>'+label+'</extra>'))
        title='Observed consumer lag';x='Wall-clock observation (UTC)';y='Offsets behind'
    else:
        rows=metrics.get('demand',[])
        fields={'cpu':('Offered CPU requests','Requested cores (sum)','#32B5A4'),
                'memory':('Offered memory requests','Normalized requests (sum)','#BA92CE'),
                'count':('Workload arrivals','Distinct arriving instances','#82A9D0')}
        if field is None or field not in fields:raise ValueError('Unsupported arrival-demand field')
        title,y,color=fields[field]
        fig.add_trace(go.Bar(x=[r['logical_bucket'] for r in rows],y=[r[field] for r in rows],marker_color=color,
              width=750,hovertemplate='Logical interval starts %{x:,} s<br>%{y:,.4g}<extra></extra>'))
        x='Logical trace time (s)'
    if not rows:fig.add_annotation(text='No recorded observations yet',x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    finish(fig,title,y=y,height=315)
    fig.update_xaxes(title=x,title_font_size=11,tickfont_size=10)
    fig.update_layout(uirevision=f'{sid}-{kind}-{field}',margin=dict(l=12,r=12,t=45,b=85),showlegend=kind=='lag')
    fig.update_yaxes(rangemode='tozero',title_font_size=11,title_standoff=8,tickfont_size=10)
    if kind=='lag':
        fig.update_layout(height=340,margin=dict(b=110),legend=dict(y=-.52,x=0))
    return fig
