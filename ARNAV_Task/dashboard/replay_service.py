"""Thin live monitor/control integration. No ingestion loops or synthetic fallback."""
import atexit
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

import streamlit as st
from kafka import KafkaAdminClient
from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.kafka.events import config, ReplayError, replay_id
from ARNAV_Task.kafka.admin import topic_status
from ARNAV_Task.kafka.state import ACTIVE, read_active, read_metrics, read_sessions
from ARNAV_Task.workload.source import availability, discover, read_json

SPEEDS=(60,120,300,600,'fast')
STALE_SECONDS=10


def utc(value):
    try:
        return datetime.fromtimestamp(value,timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if value is not None and math.isfinite(float(value)) else 'Unavailable'
    except (TypeError,ValueError,OverflowError):return 'Unavailable'


def progress(metrics):
    expected=metrics.get('expected')
    return {key:(min(1.0,max(0,metrics[key]/expected)) if expected and metrics.get(key) is not None else None)
            for key in ('confirmed','distinct_count')}


def freshness(metrics,now=None):
    now=time.time() if now is None else now
    workers={r['worker']:r for r in metrics.get('workers',[])}
    active=metrics.get('status') in ACTIVE
    consumer=workers.get('consumer');controller=workers.get('controller')
    last=consumer['at'] if consumer else None
    return {'active':active,'last_observed':last,'age_s':max(0,now-last) if last is not None else None,
            'consumer_stale':last is None or (active and now-last>STALE_SECONDS),
            'controller_stale':active and (controller is None or now-controller['at']>STALE_SECONDS)}


class ReplayService:
    def __init__(self,cfg=None,*,runner=subprocess.run,clock=time.time):
        self.cfg=cfg or config();self.runner=runner;self.clock=clock
        self._lock=threading.RLock();self._client=None;self._broker=None;self._broker_checked=0.;self._inputs=None;self._fingerprint=None
        atexit.register(self.close)

    def close(self):
        with self._lock:
            if self._client:
                try:self._client.close()
                except Exception:pass
                self._client=None

    def broker(self,*,refresh=False):
        with self._lock:
            now=self.clock()
            if not refresh and self._broker and now-self._broker_checked<10:return dict(self._broker)
            try:
                if self._client is None:
                    self._client=KafkaAdminClient(bootstrap_servers=self.cfg['bootstrap_servers'],
                        client_id='ecosched-dashboard-monitor',bootstrap_timeout_ms=1200,request_timeout_ms=1500)
                result=topic_status(self._client,self.cfg)
            except Exception as exc:
                self.close();result={'connected':False,'topic':self.cfg['topic'],'partitions':None,'error':str(exc)}
            self._broker={**result,'endpoint':self.cfg['bootstrap_servers'],'checked_at':self.clock()}
            self._broker_checked=self._broker['checked_at']
            return dict(self._broker)

    def inputs(self,*,refresh=False):
        with self._lock:
            try:
                paths=discover();files=[paths.package/'manifest.json',paths.verification,paths.recorded_manifest,
                                       ROOT/'RAW_Alibaba/prepare.py',ROOT/'RAW_Alibaba/config.json']
                files+=list(paths.package.glob('*.csv'))
                files+=list(paths.replay_directory.glob('workload_*.json'))
                fingerprint=tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in files)
            except (OSError,ValueError):fingerprint=None
            if refresh or self._inputs is None or fingerprint!=self._fingerprint:
                status=availability();windows={}
                if status['available']:
                    for size in status['verified_sizes']:
                        path=paths.replay_directory/f'workload_{size}.json'
                        try:
                            row=read_json(path)
                            if row['input_manifest_sha256']==status['input_manifest_sha256'] and row['passed']:
                                windows[size]=row['arrival_window']
                        except (OSError,ValueError,KeyError):pass
                self._inputs={**status,'arrival_windows':windows,'checked_at':self.clock()};self._fingerprint=fingerprint
            return dict(self._inputs)

    def snapshot(self,sid='latest',*,page=1):
        if type(page) is not int or not 1<=page<=1000:raise ReplayError('Invalid history page')
        result={'read_at':self.clock(),'sessions':[],'active':None,'metrics':None,'database_available':False,'error':None}
        if not Path(self.cfg['database']).is_file():return result
        try:
            sessions=read_sessions(self.cfg['database'],limit=26,offset=(page-1)*25)
            result.update(database_available=True,sessions=sessions[:25],has_more=len(sessions)>25,
                          active=read_active(self.cfg['database']))
            if sid=='latest' and not sessions:return result
            metrics=read_metrics(self.cfg['database'],sid,history_limit=600)
            result['metrics']=metrics;result['freshness']=freshness(metrics,result['read_at'])
            return result
        except (sqlite3.Error,ReplayError,OSError) as exc:
            result['error']=str(exc);return result

    def command(self,operation,*,size=None,speed=None,sid=None):
        if operation not in ('start','stop','verify'):raise ReplayError('Unsupported dashboard action')
        command=[sys.executable,'-m','ARNAV_Task.kafka.controller']
        if operation=='start':
            if type(size) is not int or size not in (250,1000,4000) or speed not in SPEEDS or isinstance(speed,bool):raise ReplayError('Invalid workload size or speed')
            return command+['start','--size',str(size),'--speed',str(speed),'--background']
        replay_id(sid)
        if operation=='stop':return command+['stop','--replay-id',sid]
        return [sys.executable,'-m','ARNAV_Task.scripts.verify_replay','--replay-id',sid]

    def action(self,operation,**kwargs):
        command=self.command(operation,**kwargs)
        snapshot=self.snapshot()
        if snapshot.get('error'):raise ReplayError(snapshot['error'])
        if operation=='start':
            if snapshot['active']:raise ReplayError('Another replay is active; duplicate start rejected')
            inputs=self.inputs(refresh=True)
            if not inputs['available'] or kwargs['size'] not in inputs['replay_verified_sizes']:raise ReplayError('Validated replay inputs are unavailable')
            if not self.broker(refresh=True)['connected']:raise ReplayError('Kafka is unavailable; start the dedicated broker and ensure the topic')
        elif operation=='stop':
            if not snapshot['active'] or snapshot['active']['replay_id']!=kwargs['sid']:raise ReplayError('Selected replay is no longer active')
        else:
            selected=self.snapshot(kwargs['sid'])['metrics']
            if not selected or selected['status'] not in ('complete','partial'):raise ReplayError('Only completed or bounded partial sessions can be explicitly reverified')
        result=self.runner(command,cwd=ROOT,capture_output=True,text=True,timeout=120 if operation=='verify' else 25,check=False)
        if result.returncode:raise ReplayError((result.stderr or result.stdout or 'Controller action failed').strip()[-2000:])
        try:return json.loads(result.stdout)
        except ValueError as exc:raise ReplayError('Controller returned malformed JSON') from exc

    def summary(self,metrics):
        # Bounded monitoring snapshot, never full event payloads or a cross-session aggregate.
        result={k:v for k,v in metrics.items() if k not in ('demand','throughput','offset_history')}
        result['recorded_session']=metrics['status'] not in ACTIVE
        result['exported_at']=self.clock();result['metric_definitions']={
            'consumed':'Durably accepted deliveries, including exact duplicates',
            'distinct_count':'Unique (replay_id, instance_id) arrivals',
            'recent_10s_instances_per_s':'Actual distinct persistence in preceding ten wall-clock seconds / 10',
            'offered_cpu':'Sum of arriving instance requests in cores; not allocation/utilization',
            'offered_memory':'Sum of normalized arriving instance memory requests; not occupancy',
            'observed_lag':'Topic-partition offset lag at last recorded broker observation',
            'session_lag':'Lag bounded to this replay producer end offset'}
        return result


@st.cache_resource(max_entries=1)
def get_replay_service():return ReplayService()
