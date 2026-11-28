"""Bounded asynchronous idempotent Kafka publication over validated source events."""
from collections import deque
import argparse
import json
import threading
import time
from kafka import KafkaProducer
from ARNAV_Task.kafka.admin import client_options
from ARNAV_Task.kafka.events import arrival, encode, config, ReplayError
from ARNAV_Task.kafka.state import State
from ARNAV_Task.workload.source import WorkloadSource


class ReplayClock:
    def __init__(self,speed,stop,*,monotonic=time.monotonic,pulse=None):
        self.speed=speed;self.stop=stop;self.monotonic=monotonic
        self.started=monotonic();self.previous=None;self.max_drift=0.0;self.pulse=pulse

    def wait(self,arrival_s):
        if arrival_s!=self.previous and self.speed:
            deadline=self.started+arrival_s/self.speed
            while not self.stop.is_set():
                remaining=deadline-self.monotonic()
                if remaining<=0:break
                if self.pulse:self.pulse()
                self.stop.wait(min(remaining,.2))
            self.max_drift=max(self.max_drift,max(0,self.monotonic()-deadline))
        self.previous=arrival_s
        return not self.stop.is_set()


def make_producer(cfg):
    return KafkaProducer(**client_options(cfg),client_id='ecosched-d6-producer',
        enable_idempotence=True,acks='all',max_in_flight_requests_per_connection=5,
        delivery_timeout_ms=cfg['delivery_timeout_ms'],max_block_ms=5000,
        linger_ms=5,batch_size=32768,allow_auto_create_topics=False)


def publish(cfg,sid,stop,*,source=None,producer=None):
    source=source or WorkloadSource();pending=deque();attempted=confirmed=0;last_offset=None
    producer=producer or make_producer(cfg)
    with State(cfg['database']) as state:
        session=state.session(sid)
        if session['producer_status']!='pending':
            producer.close(timeout=5)
            raise ReplayError('Producer restart/resend is disabled; create a new replay session','lifecycle')
        clock=ReplayClock(session['speed'],stop,pulse=lambda:state.heartbeat(sid,'producer'))
        state.update(sid,producer_status='running');state.heartbeat(sid,'producer')
        def persist():
            values={'attempted':attempted,'confirmed':confirmed,'producer_elapsed':clock.monotonic()-clock.started,'max_drift':clock.max_drift}
            if last_offset is not None:values['end_offset']=last_offset+1
            state.update(sid,**values);state.heartbeat(sid,'producer')
        def settle():
            nonlocal confirmed,last_offset
            metadata=pending.popleft().get(timeout=cfg['delivery_timeout_ms']/1000+2)
            if metadata.partition!=0:raise ReplayError('Publication reached an unexpected partition')
            confirmed+=1;last_offset=metadata.offset
        try:
            for row in source.events(session['size']):
                if stop.is_set():break
                if session['limit_events'] is not None and attempted>=session['limit_events']:break
                if not clock.wait(row['arrival_time_s']):break
                event=arrival(row,sid)
                attempted+=1
                pending.append(producer.send(cfg['topic'],key=sid.encode(),value=encode(event),partition=0))
                if len(pending)>=cfg['max_pending']:
                    while pending:settle()
                    persist()
            while pending:settle()
            producer.flush(timeout=cfg['delivery_timeout_ms']/1000+2)
            persist()
            status='cancelled' if stop.is_set() else 'completed' if confirmed==session['expected'] else 'partial'
            state.update(sid,producer_status=status,end_offset=(last_offset+1 if last_offset is not None else session['start_offset']))
            state.heartbeat(sid,'producer',status)
            return {'status':status,'attempted':attempted,'confirmed':confirmed,'elapsed_s':clock.monotonic()-clock.started,'max_drift_s':clock.max_drift}
        except Exception as exc:
            # Collect already acknowledged pending futures without treating failed
            # or ambiguous deliveries as confirmed. No application-level resends.
            while pending:
                try:settle()
                except Exception:pass
            persist();state.update(sid,producer_status='failed');state.error(sid,str(exc),'delivery');stop.set()
            state.heartbeat(sid,'producer','failed')
            raise ReplayError(f'Producer delivery failed: {exc}','delivery') from exc
        finally:producer.close(timeout=5)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config');parser.add_argument('--replay-id')
    parser.add_argument('--size',type=int,help='Create a standalone publication session; run consumer and verifier separately')
    parser.add_argument('--speed',default='fast')
    args=parser.parse_args(argv);stop=threading.Event()
    import signal
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
    try:
        cfg=config(args.config);sid=args.replay_id
        if args.size is not None:
            import os,uuid
            from kafka import KafkaConsumer,TopicPartition
            from ARNAV_Task.kafka.admin import ensure_topic
            source=WorkloadSource();expected=source.select(args.size)['instances']
            speed=0 if args.speed=='fast' else int(args.speed)
            if speed not in (0,60,120,300,600):raise ReplayError('Unsupported replay speed')
            ensure_topic(cfg);sid=sid or str(uuid.uuid4())
            from ARNAV_Task.kafka.events import replay_id
            replay_id(sid)
            probe=KafkaConsumer(**client_options(cfg),enable_auto_commit=False)
            try:offset=probe.end_offsets([TopicPartition(cfg['topic'],0)])[TopicPartition(cfg['topic'],0)]
            finally:probe.close()
            with State(cfg['database']) as state:
                state.create(sid,args.size,source.manifest_sha256,expected,speed,cfg,offset,pid=os.getpid())
                state.update(sid,status='running')
            print(json.dumps({'replay_id':sid,'standalone_producer':True}),flush=True)
        if not sid:raise ReplayError('Provide --size or a registered --replay-id')
        result=publish(cfg,sid,stop)
        with State(cfg['database']) as state:
            state.update(sid,status='cancelled' if result['status']=='cancelled' else 'draining')
        print(json.dumps(result));return 0
    except Exception as exc:print(str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
