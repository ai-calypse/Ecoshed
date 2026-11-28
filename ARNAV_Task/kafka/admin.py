"""Explicit one-partition topic administration; never deletes topics."""
import argparse
import json
from kafka import KafkaAdminClient, KafkaConsumer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
from ARNAV_Task.kafka.events import config, ReplayError


def ensure_topic(cfg, *, create=True):
    admin=None
    try:
        admin=KafkaAdminClient(bootstrap_servers=cfg['bootstrap_servers'],client_id='ecosched-d6-admin',
                               request_timeout_ms=cfg['request_timeout_ms'],bootstrap_timeout_ms=5000)
        if create:
            try:
                admin.create_topics([NewTopic(cfg['topic'],num_partitions=1,replication_factor=1,
                    topic_configs={'retention.ms':'86400000','retention.bytes':'1073741824','min.insync.replicas':'1'})])
            except TopicAlreadyExistsError:pass
        return topic_status(admin,cfg)
    except Exception as exc:
        raise ReplayError(f'Kafka administration failed at {cfg["bootstrap_servers"]}: {exc}','broker') from exc
    finally:
        if admin:admin.close()


def topic_status(admin,cfg):
    """Read metadata through an existing client; never creates/deletes a topic."""
    description=admin.describe_topics([cfg['topic']])[0]
    if description.get('error_code',0):raise ReplayError(f'Topic metadata error: {description}')
    partitions=description['partitions']
    if len(partitions)!=1 or len(partitions[0]['replica_nodes'])!=1:
        raise ReplayError('Replay topic must have exactly one partition and replication factor one')
    return {'connected':True,'topic':cfg['topic'],'partitions':len(partitions),
            'replication_factor':1,'brokers':admin.describe_cluster()['brokers']}


def client_options(cfg):
    return dict(bootstrap_servers=cfg['bootstrap_servers'],request_timeout_ms=cfg['request_timeout_ms'],
                bootstrap_timeout_ms=5000)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config');parser.add_argument('--ensure-topic',action='store_true');parser.add_argument('--status',action='store_true')
    args=parser.parse_args(argv)
    try:print(json.dumps(ensure_topic(config(args.config),create=args.ensure_topic),indent=2));return 0
    except ReplayError as exc:print(str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
