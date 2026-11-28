"""Manual Kafka offset commits after atomic SQLite persistence. Restart-safe counts."""
import argparse
import json
import threading
from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from ARNAV_Task.kafka.admin import client_options
from ARNAV_Task.kafka.events import config, decode, ReplayError
from ARNAV_Task.kafka.state import State


def make_consumer(cfg,session):
    return KafkaConsumer(**client_options(cfg),group_id=session['group_id'],enable_auto_commit=False,
                         auto_offset_reset='none',max_poll_records=cfg['batch_events'],
                         session_timeout_ms=6000,heartbeat_interval_ms=1000,allow_auto_create_topics=False)


def persist_then_commit(state,sid,records,consumer,tp,cfg):
    next_offset=state.ingest(sid,records,bucket_s=cfg['logical_bucket_s'])
    # SQLite COMMIT has returned before this call. A crash here causes exact
    # duplicate deliveries on restart, which uniqueness constraints absorb.
    consumer.commit({tp:OffsetAndMetadata(next_offset,'',-1)})
    return next_offset


def consume(cfg,sid,stop,*,ready=None,interrupt=None,from_start=False,consumer=None):
    with State(cfg['database']) as state:
        session=state.session(sid);tp=TopicPartition(cfg['topic'],0)
        consumer=consumer or make_consumer(cfg,session)
        try:
            consumer.assign([tp]);committed=consumer.committed(tp)
            if committed is not None and committed>session['next_offset']:
                raise ReplayError('Broker committed offset is ahead of durable SQLite state','offset')
            position=session['start_offset'] if from_start or committed is None else committed
            consumer.seek(tp,position)
            state.update(sid,consumer_status='running');state.heartbeat(sid,'consumer')
            if ready:ready.set()
            while True:
                if interrupt and interrupt.is_set():
                    state.update(sid,consumer_status='interrupted');state.heartbeat(sid,'consumer','interrupted');return
                session=state.session(sid)
                batches=consumer.poll(timeout_ms=cfg['consumer_poll_ms'])
                arrivals=[]
                for record in batches.get(tp,[]):
                    if session['producer_status'] in ('completed','partial','cancelled') and session['end_offset'] is not None and record.offset>=session['end_offset']:break
                    try:event=decode(record.value)
                    except ReplayError as exc:
                        state.error(sid,str(exc),'invalid',record.offset);raise
                    arrivals.append((event,record.offset))
                if arrivals:persist_then_commit(state,sid,arrivals,consumer,tp,cfg)
                end=consumer.end_offsets([tp])[tp]
                state.observe_offsets(sid,end)
                session=state.session(sid)
                terminal=session['producer_status'] in ('completed','partial','cancelled','failed')
                boundary=session['end_offset'] if session['end_offset'] is not None else end
                if terminal and session['next_offset']>=boundary and consumer.position(tp)>=boundary:
                    status='completed' if session['producer_status']=='completed' else 'stopped'
                    state.update(sid,consumer_status=status);state.heartbeat(sid,'consumer',status);return
                if stop.is_set() and terminal and not arrivals:
                    # Known confirmed events are drained first. Undelivered or
                    # ambiguous failures never become a successful completion.
                    state.update(sid,consumer_status='stopped');state.heartbeat(sid,'consumer','stopped');return
        except Exception as exc:
            if state.session(sid)['status']!='failed':state.error(sid,str(exc),'consumer')
            state.update(sid,consumer_status='failed');state.heartbeat(sid,'consumer','failed');stop.set()
            raise
        finally:consumer.close(autocommit=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config');parser.add_argument('--replay-id',required=True)
    parser.add_argument('--from-start',action='store_true',help='Explicit redelivery of this session boundary for idempotence verification')
    args=parser.parse_args(argv);stop=threading.Event();interrupt=threading.Event()
    import signal
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:interrupt.set())
    try:consume(config(args.config),args.replay_id,stop,interrupt=interrupt,from_start=args.from_start);return 0
    except Exception as exc:print(str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
