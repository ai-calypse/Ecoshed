"""Real arrival replay monitoring. Workers always run in the external controller."""
import io
import json
import pandas as pd
import streamlit as st

from ARNAV_Task.dashboard.replay_service import get_replay_service,utc,progress,SPEEDS
from ARNAV_Task.dashboard.components.metrics import page_header
from ARNAV_Task.dashboard.components.charts import show
from ARNAV_Task.dashboard.components.replay_charts import replay_chart
from ARNAV_Task.kafka.state import ACTIVE

service=get_replay_service()
page_header('Live Workload Replay','Real Apache Kafka arrival transport · independent of the seven offline scheduling research pages.')
st.caption('Offered requests are not allocated CPU, memory utilization, active hosts, live energy or SLA measurements. '
           'At least once delivery with idempotent SQLite persistence; no distributed exactly-once or high-availability claim.')
initial=service.snapshot()
choice=st.session_state.get('live_session','follow')
monitor_active=bool(initial.get('active')) and (choice=='follow' or choice==initial['active']['replay_id'])
poll_seconds=2 if monitor_active else 15 if initial.get('active') else None


@st.fragment(run_every=poll_seconds)
def monitor():
    snap=service.snapshot();broker=service.broker();inputs=service.inputs();active=snap.get('active')
    with st.container(border=True):
        cols=st.columns([1,1,1])
        cols[0].badge('Kafka reachable' if broker['connected'] else 'Kafka unavailable',color='green' if broker['connected'] else 'red')
        cols[1].badge('Inputs verified' if inputs['available'] else 'Inputs unavailable',color='green' if inputs['available'] else 'orange')
        cols[2].badge('Controller '+active['status'] if active else 'No active replay',color='blue' if active else 'gray')
        st.caption(f"{broker['endpoint']} · {broker['topic']} · partitions: {broker.get('partitions') if broker.get('partitions') is not None else 'unavailable'} · broker checked {utc(broker['checked_at'])}")
    if not broker['connected']:
        st.warning('Kafka is unavailable. Stored sessions and all offline research pages remain accessible.')
        st.code('docker compose -f ARNAV_Task/docker-compose.yml up -d --wait\npython -m ARNAV_Task.kafka.admin --ensure-topic',language='bash')
        with st.expander('Broker connection details'):st.text(broker.get('error','Unavailable'))
    if not inputs['available']:st.warning('Validated inputs are unavailable: '+inputs.get('reason','Run Phase 3 restoration.'))
    if snap.get('error'):st.error('Replay state is unavailable: '+snap['error'])
    with st.container(border=True):
        st.subheader('Configure arrival replay')
        left,right=st.columns(2)
        sizes=inputs.get('verified_sizes') or [250,1000,4000]
        size=left.selectbox('Workload (task groups)',sizes,key='live_size',format_func=lambda n:f'{n:,}',persist_state='session')
        speed=right.selectbox('Replay speed',SPEEDS,index=2,key='live_speed',
              format_func=lambda n:'Fast verification mode' if n=='fast' else f'{n}×',persist_state='session')
        workload=next((r for r in inputs.get('workloads',[]) if r['task_groups']==size),None)
        window=inputs.get('arrival_windows',{}).get(size)
        expected=f"{workload['instances']:,} verified instances" if workload else 'Expected count unavailable'
        nominal=(window['last_observed_arrival_s']-window['logical_start_s'])/speed if window and speed!='fast' else None
        st.caption(expected+(f' · nominal duration {nominal:.1f} s, including initial trace idle time; excludes processing/verification delays.' if nominal is not None else ' · Fast mode has no nominal duration estimate.' if speed=='fast' else ' · Arrival-span estimate unavailable.'))
        buttons=st.columns([1,1,1])
        start=buttons[0].button('Start replay',type='primary',key='live_start',width='stretch',
                     disabled=bool(active) or not broker['connected'] or not inputs['available'] or size not in inputs.get('replay_verified_sizes',[]))
        stop=buttons[1].button('Stop active replay',key='live_stop',width='stretch',disabled=not bool(active) or bool(active and active['stop_requested']))
        refresh=buttons[2].button('Refresh / reconnect',key='live_refresh',width='stretch')
        try:
            if start:
                with st.spinner('Starting the external replay controller…'):result=service.action('start',size=size,speed=speed)
                st.session_state['live_session']='follow'
                st.session_state['live_message']='Replay started: '+result['replay_id']
                st.rerun()
            if stop:
                service.action('stop',sid=active['replay_id']);st.session_state['live_message']='Cooperative stop requested; confirmed deliveries will drain.';st.rerun()
            if refresh:
                service.broker(refresh=True);service.inputs(refresh=True);st.rerun()
        except Exception as exc:st.error('Replay action failed: '+str(exc))
        if st.session_state.get('live_message'):st.caption(st.session_state['live_message'])
        if active:st.caption('Active replay: '+active['replay_id']+' · stop always targets this active session, including while inspecting history.')
    page=st.number_input('Session history page',min_value=1,max_value=1000,value=1,step=1,key='live_history_page',persist_state='session')
    listing=service.snapshot(page=page);sessions=listing['sessions'];by_id={r['replay_id']:r for r in sessions}
    options=['follow']+list(by_id)
    if st.session_state.get('live_session','follow') not in options:st.session_state['live_session']='follow'
    selected=st.selectbox('Inspect replay session',options,key='live_session',persist_state='session',
         format_func=lambda sid:'Follow active / latest session' if sid=='follow' else f"{by_id[sid]['size']:,} groups · {by_id[sid]['status']} · {sid[:8]} · {utc(by_id[sid]['started_at'])}")
    sid=active['replay_id'] if selected=='follow' and active else 'latest' if selected=='follow' else selected
    snap=service.snapshot(sid);m=snap.get('metrics')
    desired=2 if active and (selected=='follow' or selected==active['replay_id']) else 15 if active else None
    if desired!=poll_seconds:st.rerun()
    st.caption(f"Last monitor refresh: {utc(snap['read_at'])} · "+('2-second fragment updates' if desired==2 else '15-second control checks; recorded session' if desired==15 else 'Recorded / idle view; refresh on demand'))
    if m is None:
        st.info('No replay session is available. Configure and start a verified workload above. No worker starts on page load.')
    else:
        live=m['status'] in ACTIVE;fresh=snap['freshness'];receipt=m.get('verification')
        verified=bool(receipt and receipt.get('passed') and receipt.get('complete') and m['status']=='complete'
                      and receipt['input_manifest_sha256']==m['manifest'] and receipt['distinct_instances']==m['distinct_count'])
        status='stopping' if live and m['stop_requested'] else m['status']
        st.subheader(('Active session · ' if live else 'Recorded session · ')+status)
        st.code(m['replay_id'],language=None)
        st.caption(f"Producer: {m['producer_status']} · Consumer: {m['consumer_status']} · Last consumer observation: {utc(fresh['last_observed'])}")
        if fresh['controller_stale']:st.warning('Controller heartbeat is stale or missing. Counts below are recorded snapshots; inspect controller logs before starting another replay.')
        if live and fresh['consumer_stale']:st.warning('Consumer observations are stale. Recent throughput and lag are unavailable as current metrics.')
        lag_current=not fresh['consumer_stale'] and (not live or broker['connected'])
        def num(value,suffix=''):
            return 'Unavailable' if value is None else f'{value:,.1f}{suffix}' if suffix else f'{value:,}'
        values=[('Expected unique',m['expected'],'Verified source instance count'),('Published (confirmed)',m['confirmed'],'Acknowledged publications, persisted by producer batches'),
                ('Accepted deliveries',m['consumed'],'Durably accepted deliveries including duplicates'),('Distinct processed',m['distinct_count'],'Unique replay/instance identities'),
                ('Duplicates',m['duplicates'],'Exact repeated deliveries; unique counts unchanged'),('Invalid messages',m['invalid'],'Fatal validation observations'),
                ('Sequence gaps',m['gaps'],'Detected ordering gaps; not an estimate of missing instances'),('Task groups',m['groups_encountered'],'Groups encountered in distinct consumed events'),
                ('Recent throughput',m['recent_10s_instances_per_s'] if live and not fresh['consumer_stale'] else None,'Distinct instances in the preceding 10 wall-clock seconds / 10'),
                ('Average throughput',m['average_instances_per_s'],'Distinct instances / recorded session elapsed seconds'),
                ('Session lag',m['session_lag'] if lag_current else None,'Recorded offsets behind this replay producer boundary'),
                ('Topic lag',m['observed_lag'] if lag_current else None,'Recorded topic-partition offset lag; can include later sessions')]
        with st.grid(4,min_column_width=205,gap='small'):
            for label,value,help_text in values:st.metric(label,num(value,' /s' if 'throughput' in label.lower() else ''),help=help_text,border=True,height='stretch')
        p=progress(m)
        st.progress(p['confirmed'] or 0,text=f"Publication: {m['confirmed']:,} / {m['expected']:,} acknowledged")
        st.progress(p['distinct_count'] or 0,text=f"Consumption: {m['distinct_count']:,} / {m['expected']:,} distinct · {100*(p['distinct_count'] or 0):.2f}% of verified-source instances")
        logical='Unavailable' if m['last_arrival'] is None else f"{m['last_arrival']:,} s"
        selected_window=inputs.get('arrival_windows',{}).get(m['size'])
        remaining=max(0,(selected_window['last_observed_arrival_s']-(m['last_arrival'] or 0))/m['speed']) if live and m['speed'] and selected_window else None
        st.caption(f"Logical trace position: {logical} · elapsed wall time: {m['elapsed_wall_s']:.1f} s · speed: "+(f"{m['speed']:g}×" if m['speed'] else 'fast')+
                   (f' · nominal remaining trace time {remaining:.1f} s, excluding processing/verification.' if remaining is not None else ' · remaining-time estimate unavailable.'))
        if verified:st.success(f"Complete event-level verification passed: {m['distinct_count']:,} unique instances. Counts alone did not determine success.")
        elif m['status']=='partial':st.warning('Bounded partial replay: only a source prefix was processed. This is not a complete workload.')
        elif m['status']=='cancelled':st.warning('Replay cancelled. Stopping cleanly does not verify a complete workload.')
        elif m['status']=='failed':st.error('Replay failed. Review persisted errors; no complete verification is claimed.')
        elif m['status']=='complete':st.info('Controller recorded completion; detailed verification receipt is unavailable for this older session. Explicitly verify it below to display integrity checks.')
        else:st.info('Replay is still in progress. Completion requires the controller’s full event-level verification.')
        c1,c2=st.columns(2)
        with c1:show(replay_chart(m,'throughput'),'live_throughput','Actual 1-second persistence buckets, newest 600 observations. Publication throughput history is not recorded; only confirmed publication totals are shown.')
        with c2:show(replay_chart(m,'lag'),'live_lag','Real offset samples, newest 600. Markers do not invent measurements between observations. Historical samples retain their original timestamps.')
        st.caption(f"Next durable offset: {m['next_offset']:,} · last observed broker end: {m['broker_end']:,}. Topic lag can include messages from later sessions; session lag stops at this replay’s producer boundary.")
        c1,c2=st.columns(2)
        with c1:show(replay_chart(m,'demand',field='cpu'),'live_cpu','Offered requested cores summed across arriving instances in each logical interval; not CPU allocation or utilization.')
        with c2:show(replay_chart(m,'demand',field='memory'),'live_memory','Offered normalized memory requests summed across arriving instances; not GB, occupancy or server utilization.')
        with st.expander('Arrival counts and source resource composition'):
            show(replay_chart(m,'demand',field='count'),'live_arrival_counts','Distinct consumed arrivals grouped by original logical trace interval.')
            population=next((r for r in inputs.get('workloads',[]) if r['task_groups']==m['size']),None)
            if population:st.dataframe(pd.DataFrame([{'Source category':k,'Instances in complete source workload':v} for k,v in population['instance_resource_skew_counts'].items()]),hide_index=True,alt='Verified whole-source resource categories, not live consumed category counts')
            st.caption('Category counts describe the complete verified source workload. Live consumed skew aggregates are not recorded, so none are inferred.')
        with st.expander('Event integrity, worker observations and errors',expanded=verified or m['status']=='failed'):
            if receipt:
                integrity=receipt.get('passed') and receipt.get('complete') and verified
                st.caption('Verification recorded '+utc(receipt['verified_at'])+' · '+('complete source check' if receipt.get('complete') else 'prefix or failed check'))
                st.dataframe(pd.DataFrame([{'Check':label,'Evidence':'PASS' if integrity else 'Prefix / failed / superseded receipt'} for label in
                    ['Original instance identities','Sequence and arrival/tie order','Original CPU and memory requests','Original task-group multiplicity','Input manifest identity']]),hide_index=True,alt='Persisted event-level verification evidence')
                st.code(receipt['persisted_source_stream_sha256'],language=None)
            else:st.info('No detailed verification receipt exists. Individual checks are not marked passed.')
            st.caption(f"Invalid observations: {m['invalid']} · detected sequence gaps: {m['gaps']} · conflicting duplicate errors: {m['conflicting_duplicates']}")
            st.caption('Missing sequences: 0, established by complete event-level verification.' if verified else
                       'Missing sequence count: unavailable until a complete event-level verification passes; gap detections alone do not certify completeness.')
            if m['workers']:st.dataframe(pd.DataFrame(m['workers']).assign(observed_at=lambda f:f['at'].map(utc)).drop(columns=['replay_id','at']),hide_index=True,alt='Actual worker heartbeat timestamps and statuses')
            if m['errors']:st.dataframe(pd.DataFrame(m['errors'])[['code','message','kafka_offset']],hide_index=True,alt='Persisted replay errors')
            if st.button('Verify selected session',key='live_verify',disabled=m['status'] not in ('complete','partial')):
                try:
                    with st.spinner('Comparing every persisted arrival with the verified source…'):service.action('verify',sid=m['replay_id'])
                    st.rerun()
                except Exception as exc:st.error(str(exc))
        exported=service.summary(m)
        downloads=st.columns(2)
        downloads[0].download_button('Download session JSON',json.dumps(exported,indent=2),f"ecosched_replay_{m['replay_id']}.json",mime='application/json',key='live_download_json')
        flat={k:v for k,v in exported.items() if not isinstance(v,(dict,list))}
        downloads[1].download_button('Download session CSV',pd.DataFrame([flat]).to_csv(index=False),f"ecosched_replay_{m['replay_id']}.csv",mime='text/csv',key='live_download_csv')
    st.subheader('Recorded session history')
    if sessions:
        history=pd.DataFrame(sessions)[['replay_id','size','speed','status','started_at','ended_at','expected','confirmed','distinct_count','duplicates','invalid','gaps']]
        history['elapsed_s']=[max(0,(r['ended_at'] or snap['read_at'])-r['started_at']) for r in sessions]
        history['average_instances_per_s']=[r['distinct_count']/max(.001,(r['ended_at'] or snap['read_at'])-r['started_at']) for r in sessions]
        history['started_at']=history.started_at.map(utc);history['ended_at']=history.ended_at.map(utc)
        st.dataframe(history.rename(columns=lambda c:c.replace('_',' ').capitalize()),hide_index=True,alt='Recorded sessions, individually identified; at most 25 per page')
        st.caption('At most 25 sessions per history page. Select a session above; statistics are never combined across replay IDs.')
    else:st.info('No recorded sessions on this history page.')

monitor()
with st.expander('Arrival transport architecture and delivery guarantees'):
    st.mermaid_chart('''flowchart LR
        A[Validated Alibaba workload] --> B[Python producer]
        B --> C[Single Kafka partition]
        C --> D[Python consumer]
        D --> E[SQLite state]
        E --> F[Streamlit monitor]
    ''',alt='Validated Alibaba arrivals flow through external producer, Kafka, consumer and SQLite into read-only Streamlit monitoring')
    st.caption('Workers continue independently of browser navigation. SQLite commits precede Kafka offset commits. Exact duplicate deliveries do not inflate distinct counts. No live scheduler runs here.')
