"""One external replay process, with producer/consumer threads and cooperative stop.

start runs in foreground unless --background. Signals and stop commands request
cancellation; they never kill unrelated processes. Dead controllers require an
explicit next start, which records failure of their stale session first.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid
from kafka import KafkaConsumer,TopicPartition
from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.kafka.admin import ensure_topic,client_options
from ARNAV_Task.kafka.events import config,ReplayError,replay_id
from ARNAV_Task.kafka.state import State,ACTIVE,read_metrics
from ARNAV_Task.kafka.consumer import consume
from ARNAV_Task.kafka.producer import publish
from ARNAV_Task.workload.source import WorkloadSource
from ARNAV_Task.scripts.verify_replay import verify

SPEEDS=(0,60,120,300,600)


def alive(pid):
    if not pid:return False
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False


def run(cfg,size,speed,*,sid=None,limit=None):
    sid=sid or str(uuid.uuid4());replay_id(sid)
    if speed not in SPEEDS:raise ReplayError(f'Unsupported speed; use {SPEEDS}')
    if limit is not None and limit<=0:raise ReplayError('Bounded event limit must be positive')
    runtime=Path(cfg['runtime_directory']);runtime.mkdir(parents=True,exist_ok=True)
    with (runtime/'controller.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise ReplayError('Another replay controller is active','lifecycle') from exc
        with State(cfg['database']) as state:
            for old in state.sessions():
                if old['status'] in ACTIVE:
                    if alive(old['controller_pid']):raise ReplayError('Another replay is active','lifecycle')
                    state.error(old['replay_id'],'Controller disappeared; automatic producer restart is disabled','lifecycle')
            source=WorkloadSource();expected=source.select(size)['instances'];ensure_topic(cfg)
            probe=KafkaConsumer(**client_options(cfg),enable_auto_commit=False)
            try:start=probe.end_offsets([TopicPartition(cfg['topic'],0)])[TopicPartition(cfg['topic'],0)]
            finally:probe.close()
            state.create(sid,size,source.manifest_sha256,expected,speed,cfg,start,limit=limit,pid=os.getpid())
            stop=threading.Event();watch_stop=threading.Event();ready=threading.Event();worker_errors=[]
            def watch():
                with State(cfg['database']) as watcher:
                    while not watch_stop.wait(.2):
                        watcher.heartbeat(sid,'controller')
                        if watcher.session(sid)['stop_requested']:stop.set()
            def consumer_worker():
                try:consume(cfg,sid,stop,ready=ready)
                except Exception as exc:worker_errors.append(str(exc));stop.set()
            watcher=threading.Thread(target=watch,name='ecosched-controller-monitor',daemon=True)
            consumer=threading.Thread(target=consumer_worker,name='ecosched-consumer',daemon=True)
            previous={}
            if threading.current_thread() is threading.main_thread():
                for sig in (signal.SIGINT,signal.SIGTERM):
                    previous[sig]=signal.signal(sig,lambda *_:stop.set())
            watcher.start();consumer.start()
            try:
                deadline=time.monotonic()+15
                while not ready.wait(.1):
                    if worker_errors or time.monotonic()>deadline:raise ReplayError('Consumer initialization failed: '+str(worker_errors),'consumer')
                state.update(sid,status='running');print(json.dumps({'replay_id':sid,'status':'running','consumer_ready':True}),flush=True)
                publish(cfg,sid,stop,source=source)
                if state.session(sid)['status']!='failed':state.update(sid,status='draining')
                consumer.join(timeout=cfg['completion_timeout_s'])
                if consumer.is_alive():raise ReplayError('Consumer drain timed out','consumer')
                if worker_errors:raise ReplayError('Consumer failed: '+str(worker_errors),'consumer')
                session=state.session(sid)
                if stop.is_set() or session['producer_status']=='cancelled':
                    state.update(sid,status='cancelled',ended_at=time.time());result={'replay_id':sid,'passed':False,'status':'cancelled','complete':False}
                else:
                    state.update(sid,status='verifying')
                    result=verify(state,sid,source=source,allow_partial=limit is not None)
                state.heartbeat(sid,'controller',state.session(sid)['status'])
                return result
            except Exception as exc:
                stop.set();state.update(sid,producer_status='failed');state.error(sid,str(exc),'controller')
                consumer.join(timeout=cfg['completion_timeout_s'])
                state.update(sid,ended_at=time.time());raise
            finally:
                watch_stop.set();watcher.join(timeout=2)
                for sig,handler in previous.items():signal.signal(sig,handler)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config')
    sub=parser.add_subparsers(dest='command',required=True)
    start=sub.add_parser('start');start.add_argument('--size',type=int,required=True);start.add_argument('--speed',default='120',help='60,120,300,600 or fast')
    start.add_argument('--background',action='store_true');start.add_argument('--replay-id');start.add_argument('--limit',type=int,help='Explicit partial test; never full workload completion')
    for name in ('status','stop','list'):
        p=sub.add_parser(name)
        if name!='list':p.add_argument('--replay-id',default='latest')
    args=parser.parse_args(argv)
    try:
        cfg=config(args.config)
        if args.command=='start':
            speed=0 if args.speed=='fast' else int(args.speed)
            if args.background:
                sid=args.replay_id or str(uuid.uuid4());replay_id(sid)
                runtime=Path(cfg['runtime_directory']);runtime.mkdir(parents=True,exist_ok=True)
                cmd=[sys.executable,'-m','ARNAV_Task.kafka.controller']
                if args.config:cmd+=['--config',str(Path(args.config).resolve())]
                cmd+=['start','--size',str(args.size),'--speed',args.speed,'--replay-id',sid]
                if args.limit is not None:cmd+=['--limit',str(args.limit)]
                with (runtime/f'{sid}.log').open('ab') as log:
                    child=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                # Keep the handle alive and reap it when embedded in a longer
                # lived caller (including tests); the CLI may itself exit first.
                threading.Thread(target=child.wait,name='ecosched-child-reaper',daemon=True).start()
                for _ in range(150):
                    if child.poll() is not None:raise ReplayError(f'Controller exited {child.returncode}; see {sid}.log','lifecycle')
                    with State(cfg['database']) as state:
                        try:s=state.session(sid)
                        except ReplayError:s=None
                    if s is not None:print(json.dumps({'replay_id':sid,'pid':child.pid,'status':s['status']}));return 0
                    time.sleep(.1)
                raise ReplayError('Controller startup timed out; inspect its log','lifecycle')
            result=run(cfg,args.size,speed,sid=args.replay_id,limit=args.limit);print(json.dumps(result,indent=2))
            return 0 if result.get('passed') else 1
        with State(cfg['database']) as state:
            if args.command=='list':print(json.dumps(state.sessions(),indent=2))
            elif args.command=='status':print(json.dumps(state.metrics(args.replay_id),indent=2))
            else:
                session=state.session(args.replay_id)
                if session['status'] not in ACTIVE:raise ReplayError('Selected replay is not active','lifecycle')
                state.update(session['replay_id'],stop_requested=1)
                print(json.dumps({'replay_id':session['replay_id'],'stop_requested':True}))
        return 0
    except Exception as exc:print(f'ERROR: {exc}',file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
