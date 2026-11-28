"""Transactional SQLite state. Readers use snapshots; Kafka commits follow DB commits."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
from ARNAV_Task.kafka.events import ReplayError, validate, payload_digest, source_event

ACTIVE=('starting','running','draining','verifying')


class State:
    def __init__(self, path, *, readonly=False):
        self.path=Path(path);self.readonly=readonly
        if not readonly:self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(f'file:{self.path}?mode=ro' if readonly else str(self.path),
                                uri=readonly,timeout=15,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=15000')
        if not readonly:
            self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions(
              replay_id TEXT PRIMARY KEY,size INTEGER NOT NULL,manifest TEXT NOT NULL,expected INTEGER NOT NULL,
              speed REAL NOT NULL,limit_events INTEGER,topic TEXT NOT NULL,bootstrap TEXT NOT NULL,group_id TEXT NOT NULL,
              status TEXT NOT NULL,producer_status TEXT NOT NULL DEFAULT 'pending',consumer_status TEXT NOT NULL DEFAULT 'pending',
              attempted INTEGER NOT NULL DEFAULT 0,confirmed INTEGER NOT NULL DEFAULT 0,consumed INTEGER NOT NULL DEFAULT 0,
              distinct_count INTEGER NOT NULL DEFAULT 0,duplicates INTEGER NOT NULL DEFAULT 0,invalid INTEGER NOT NULL DEFAULT 0,
              gaps INTEGER NOT NULL DEFAULT 0,next_sequence INTEGER NOT NULL DEFAULT 1,last_arrival INTEGER,last_group TEXT,last_source INTEGER,
              offered_cpu REAL NOT NULL DEFAULT 0,offered_memory REAL NOT NULL DEFAULT 0,
              start_offset INTEGER NOT NULL,next_offset INTEGER NOT NULL,broker_end INTEGER NOT NULL,
              started_at REAL NOT NULL,ended_at REAL,end_offset INTEGER,producer_elapsed REAL NOT NULL DEFAULT 0,max_drift REAL NOT NULL DEFAULT 0,
              controller_pid INTEGER,stop_requested INTEGER NOT NULL DEFAULT 0);
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_session ON sessions((1))
              WHERE status IN ('starting','running','draining','verifying');
            CREATE TABLE IF NOT EXISTS events(replay_id TEXT NOT NULL,instance_id TEXT NOT NULL,sequence INTEGER NOT NULL,
              digest TEXT NOT NULL,payload TEXT NOT NULL,kafka_offset INTEGER NOT NULL,
              PRIMARY KEY(replay_id,instance_id),UNIQUE(replay_id,sequence));
            CREATE TABLE IF NOT EXISTS groups(replay_id TEXT NOT NULL,task_group_id TEXT NOT NULL,count INTEGER NOT NULL,
              PRIMARY KEY(replay_id,task_group_id));
            CREATE TABLE IF NOT EXISTS demand(replay_id TEXT NOT NULL,logical_bucket INTEGER NOT NULL,
              count INTEGER NOT NULL,cpu REAL NOT NULL,memory REAL NOT NULL,PRIMARY KEY(replay_id,logical_bucket));
            CREATE TABLE IF NOT EXISTS throughput(replay_id TEXT NOT NULL,wall_second INTEGER NOT NULL,
              count INTEGER NOT NULL,PRIMARY KEY(replay_id,wall_second));
            CREATE TABLE IF NOT EXISTS errors(id INTEGER PRIMARY KEY,replay_id TEXT NOT NULL,at REAL NOT NULL,
              code TEXT NOT NULL,message TEXT NOT NULL,kafka_offset INTEGER);
            CREATE TABLE IF NOT EXISTS heartbeats(replay_id TEXT NOT NULL,worker TEXT NOT NULL,at REAL NOT NULL,
              status TEXT NOT NULL,PRIMARY KEY(replay_id,worker));
            CREATE TABLE IF NOT EXISTS offset_samples(replay_id TEXT NOT NULL,wall_second INTEGER NOT NULL,
              next_offset INTEGER NOT NULL,broker_end INTEGER NOT NULL,session_lag INTEGER NOT NULL,topic_lag INTEGER NOT NULL,
              PRIMARY KEY(replay_id,wall_second));
            CREATE TABLE IF NOT EXISTS verifications(replay_id TEXT PRIMARY KEY,verified_at REAL NOT NULL,payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS sessions_by_start ON sessions(started_at DESC);
            CREATE INDEX IF NOT EXISTS errors_by_replay ON errors(replay_id,id);
            ''')

    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:yield;self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise

    def create(self, sid, size, manifest, expected, speed, cfg, start_offset, *, limit=None,pid=None):
        try:
            with self.transaction():
                self.db.execute('''INSERT INTO sessions(replay_id,size,manifest,expected,speed,topic,bootstrap,group_id,
                    status,start_offset,next_offset,broker_end,started_at,limit_events,controller_pid)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (sid,size,manifest,expected,speed,cfg['topic'],cfg['bootstrap_servers'],cfg['group_prefix']+'.'+sid,
                     'starting',start_offset,start_offset,start_offset,time.time(),limit,pid))
        except sqlite3.IntegrityError as exc:raise ReplayError('Another replay is active, or replay_id already exists','lifecycle') from exc

    def session(self,sid='latest'):
        if sid=='latest':row=self.db.execute('SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1').fetchone()
        else:row=self.db.execute('SELECT * FROM sessions WHERE replay_id=?',(sid,)).fetchone()
        if row is None:raise ReplayError(f'Unknown replay: {sid}','lifecycle')
        return dict(row)

    def sessions(self,*,limit=None,offset=0):
        sql='SELECT * FROM sessions ORDER BY started_at DESC'
        args=()
        if limit is not None:
            if not 1<=limit<=1000 or offset<0:raise ReplayError('Invalid session history bounds')
            sql+=' LIMIT ? OFFSET ?';args=(limit,offset)
        return [dict(r) for r in self.db.execute(sql,args)]

    def observe_offsets(self,sid,end):
        """Record a real broker observation; no changes to event persistence/commits."""
        with self.transaction():
            self.update(sid,broker_end=end);self.heartbeat(sid,'consumer')
            s=self.session(sid)
            boundary=s['end_offset'] if s['end_offset'] is not None else end
            self.db.execute('INSERT OR REPLACE INTO offset_samples VALUES(?,?,?,?,?,?)',
                (sid,int(time.time()),s['next_offset'],end,max(0,boundary-s['next_offset']),max(0,end-s['next_offset'])))

    def save_verification(self,sid,result):
        self.db.execute('INSERT OR REPLACE INTO verifications VALUES(?,?,?)',
                        (sid,time.time(),json.dumps(result,sort_keys=True,allow_nan=False)))

    def update(self,sid,**values):
        # Keys are internal column names, never external SQL fragments.
        allowed={r[1] for r in self.db.execute('PRAGMA table_info(sessions)')}-{'replay_id'}
        if not values or not set(values)<=allowed:raise ReplayError('Invalid session update')
        self.db.execute('UPDATE sessions SET '+','.join(k+'=?' for k in values)+' WHERE replay_id=?',(*values.values(),sid))

    def heartbeat(self,sid,worker,status='running'):
        self.db.execute('INSERT INTO heartbeats VALUES(?,?,?,?) ON CONFLICT(replay_id,worker) DO UPDATE SET at=excluded.at,status=excluded.status',
                        (sid,worker,time.time(),status))

    def error(self,sid,message,code='invalid',offset=None):
        with self.transaction():
            self.db.execute('INSERT INTO errors(replay_id,at,code,message,kafka_offset) VALUES(?,?,?,?,?)',(sid,time.time(),code,str(message),offset))
            self.db.execute("UPDATE sessions SET status='failed',invalid=invalid+?,gaps=gaps+? WHERE replay_id=?",
                            (int(code in ('invalid','conflict','gap','order')),int(code=='gap'),sid))

    def ingest(self,sid,records,*,bucket_s=900):
        """Validate and commit an entire poll batch before its Kafka offset commit.

        records are (decoded arrival event, broker offset). A conflicting/invalid
        batch rolls back; the diagnostic survives in its own transaction.
        """
        current_offset=None
        try:
            with self.transaction():
                s=self.session(sid);accepted=0
                for event,current_offset in records:
                    validate(event,session=s)
                    if current_offset < s['start_offset']:raise ReplayError('Offset precedes replay boundary')
                    digest=payload_digest(event)
                    old=self.db.execute('SELECT digest,sequence FROM events WHERE replay_id=? AND instance_id=?',(sid,event['instance_id'])).fetchone()
                    if old:
                        if old['digest']!=digest or old['sequence']!=event['sequence']:
                            raise ReplayError('Conflicting duplicate instance payload','conflict')
                        s['duplicates']+=1;s['consumed']+=1;s['next_offset']=max(s['next_offset'],current_offset+1)
                        continue
                    if self.db.execute('SELECT 1 FROM events WHERE replay_id=? AND sequence=?',(sid,event['sequence'])).fetchone():
                        raise ReplayError('Conflicting duplicate sequence','conflict')
                    if event['sequence']!=s['next_sequence']:raise ReplayError(f"Sequence gap: expected {s['next_sequence']}, got {event['sequence']}",'gap')
                    source=int(event['instance_id'].rsplit('_',1)[1]);order=(event['arrival_time_s'],event['task_group_id'],source)
                    if s['last_arrival'] is not None and order<(s['last_arrival'],s['last_group'],s['last_source']):
                        raise ReplayError('Original arrival/tie order violated','order')
                    payload=json.dumps(source_event(event),sort_keys=True,separators=(',',':'),allow_nan=False)
                    self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(sid,event['instance_id'],event['sequence'],digest,payload,current_offset))
                    self.db.execute('INSERT INTO groups VALUES(?,?,1) ON CONFLICT(replay_id,task_group_id) DO UPDATE SET count=count+1',(sid,event['task_group_id']))
                    self.db.execute('''INSERT INTO demand VALUES(?,?,1,?,?) ON CONFLICT(replay_id,logical_bucket)
                        DO UPDATE SET count=count+1,cpu=cpu+excluded.cpu,memory=memory+excluded.memory''',
                        (sid,event['arrival_time_s']//bucket_s*bucket_s,event['cpu_request_cores'],event['memory_request_normalized']))
                    s['distinct_count']+=1;s['consumed']+=1;s['next_sequence']+=1
                    s['last_arrival'],s['last_group'],s['last_source']=order
                    s['offered_cpu']+=event['cpu_request_cores'];s['offered_memory']+=event['memory_request_normalized']
                    s['next_offset']=max(s['next_offset'],current_offset+1);accepted+=1
                keys=('distinct_count','consumed','duplicates','next_sequence','last_arrival','last_group','last_source','offered_cpu','offered_memory','next_offset')
                self.update(sid,**{k:s[k] for k in keys})
                if accepted:
                    self.db.execute('INSERT INTO throughput VALUES(?,?,?) ON CONFLICT(replay_id,wall_second) DO UPDATE SET count=count+excluded.count',
                                    (sid,int(time.time()),accepted))
                return s['next_offset']
        except ReplayError as exc:
            self.error(sid,str(exc),exc.code,current_offset);raise

    def metrics(self,sid='latest',*,history_limit=None):
        s=self.session(sid);sid=s['replay_id'];now=time.time();elapsed=max((s['ended_at'] or now)-s['started_at'],.001)
        if history_limit is not None and not 1<=history_limit<=10000:raise ReplayError('Invalid metrics history bound')
        def history(table,order):
            try:
                if history_limit is None:return [dict(r) for r in self.db.execute(f'SELECT * FROM {table} WHERE replay_id=? ORDER BY {order}',(sid,))]
                return list(reversed([dict(r) for r in self.db.execute(f'SELECT * FROM {table} WHERE replay_id=? ORDER BY {order} DESC LIMIT ?',(sid,history_limit))]))
            except sqlite3.OperationalError:
                if table=='offset_samples':return []  # Pre-Phase-5 read-only database.
                raise
        try:
            receipt=self.db.execute('SELECT * FROM verifications WHERE replay_id=?',(sid,)).fetchone()
        except sqlite3.OperationalError:receipt=None
        recent=self.db.execute('SELECT COALESCE(SUM(count),0) FROM throughput WHERE replay_id=? AND wall_second>=?',(sid,int(now)-9)).fetchone()[0]
        return {**s,'groups_encountered':self.db.execute('SELECT COUNT(*) FROM groups WHERE replay_id=?',(sid,)).fetchone()[0],
                'elapsed_wall_s':elapsed,'average_instances_per_s':s['distinct_count']/elapsed,
                'recent_10s_instances_per_s':recent/10,'recent_window_s':10,
                'observed_lag':max(0,s['broker_end']-s['next_offset']),
                'session_lag':max(0,(s['end_offset'] if s['end_offset'] is not None else s['broker_end'])-s['next_offset']),
                'lag_scope':'observed_lag is topic-partition lag at last consumer heartbeat; session_lag stops at this replay producer boundary.',
                'progress_fraction':s['distinct_count']/s['expected'],
                'workers':[dict(r) for r in self.db.execute('SELECT * FROM heartbeats WHERE replay_id=?',(sid,))],
                'errors':history('errors','id'),
                'demand':history('demand','logical_bucket'),
                'throughput':history('throughput','wall_second'),
                'offset_history':history('offset_samples','wall_second'),
                'verification':({'verified_at':receipt['verified_at'],**json.loads(receipt['payload'])} if receipt else None),
                'conflicting_duplicates':self.db.execute("SELECT COUNT(*) FROM errors WHERE replay_id=? AND code='conflict'",(sid,)).fetchone()[0],
                'metric_scope':'Live offered arrivals only; no allocated resources, energy, SLA or host utilization.'}


def read_metrics(path,sid='latest',*,history_limit=None):
    with State(path,readonly=True) as store:
        store.db.execute('BEGIN')  # One coherent WAL read snapshot across aggregates.
        return store.metrics(sid,history_limit=history_limit)


def read_sessions(path,*,limit=None,offset=0):
    with State(path,readonly=True) as store:return store.sessions(limit=limit,offset=offset)


def read_active(path):
    with State(path,readonly=True) as store:
        row=store.db.execute("SELECT * FROM sessions WHERE status IN ('starting','running','draining','verifying') LIMIT 1").fetchone()
        return dict(row) if row else None
