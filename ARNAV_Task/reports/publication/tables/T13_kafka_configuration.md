# Tested Kafka infrastructure

One ARM64 broker/controller in KRaft mode, one partition and replication factor one; localhost-only external listener. Not a high-availability deployment.

| Parameter | Value |
| --- | --- |
| version | 4.4.0 |
| image | apache/kafka:4.4.0@sha256:833b867a9585a141da455dc2b57431c65cbccb27f11c91f694444cca9f777e0f |
| architecture | arm64 |
| immutable_index_digest | sha256:833b867a9585a141da455dc2b57431c65cbccb27f11c91f694444cca9f777e0f |
| arm64_manifest_digest | sha256:77b56ddfb7104fc5814a3d0127fcff49983220c7c7ad9bfc1f0af4d439228329 |
| heap | -Xms256m -Xmx512m |
| container_memory_limit_bytes | 1610612736 |
| topic | {"brokers":[{"broker_id":1,"host":"127.0.0.1","is_fenced":false,"port":19092,"rack":null}],"connected":true,"partitions":1,"replication_factor":1,"topic":"ecosched.workload.arrivals.v1"} |

Sources: `ARNAV_Task/reports/phase4_verification.json`, `ARNAV_Task/docker-compose.yml`.
