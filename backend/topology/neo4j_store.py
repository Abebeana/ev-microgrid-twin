"""Neo4j property graph for the island topology, the current minute, and retained samples."""

from __future__ import annotations

import os
from threading import Lock

from neo4j import GraphDatabase

from backend.topology.projection import CATALOG_KINDS

LABEL_BY_KIND = {
    "site": "Site",
    "solar": "Solar",
    "battery": "Battery",
    "bus": "Bus",
    "charger": "Charger",
    "other": "Asset",
    "telemetry_sample": "TelemetrySample",
    "alert": "Alert",
}
RELATIONS = ("HAS_ASSET", "CONNECTED_TO", "OBSERVED_IN", "HAS_SAMPLE", "RAISED", "ABOUT")
CATALOG_FIELDS = {"kind", "name", "islanded", "wallbox_id", "vendor", "model", "firmware"}
HISTORY_LIMIT = 240
DOMAIN_LABELS = ":".join(LABEL_BY_KIND.values())

DOWNSTREAM_QUERY = """
MATCH (bus:TwinNode {scope: $scope, kind: 'bus'})
MATCH (charger:TwinNode {scope: $scope, kind: 'charger'})
OPTIONAL MATCH path = shortestPath((bus)-[:CONNECTED_TO*..6]->(charger))
RETURN charger.id AS charger_id, charger.name AS name, charger.value AS power_kw,
       charger.status AS status,
       CASE WHEN path IS NULL THEN [] ELSE [node IN nodes(path) | node.id] END AS path
ORDER BY charger_id
"""

PATH_QUERY = """
MATCH (source:TwinNode {scope: $scope})
WHERE source.kind IN ['solar', 'battery']
MATCH (charger:TwinNode {scope: $scope, kind: 'charger'})
OPTIONAL MATCH path = shortestPath((source)-[:CONNECTED_TO*..8]-(charger))
RETURN source.id AS source, charger.id AS target,
       CASE WHEN path IS NULL THEN [] ELSE [node IN nodes(path) | node.id] END AS hops
ORDER BY source, target
"""

IMPACT_QUERY = """
MATCH (alert:TwinNode {scope: $scope, kind: 'alert'})
OPTIONAL MATCH (alert)-[:ABOUT]->(asset:TwinNode {scope: $scope})
WITH alert, [id IN collect(DISTINCT asset.id) WHERE id IS NOT NULL] AS about
OPTIONAL MATCH (alert)-[:ABOUT]->(:TwinNode {scope: $scope})-[:CONNECTED_TO*1..4]-(neighbor:TwinNode {scope: $scope})
WHERE neighbor.kind IN ['solar', 'battery', 'bus', 'charger'] AND NOT neighbor.id IN about
WITH alert, about, [id IN collect(DISTINCT neighbor.id) WHERE id IS NOT NULL] AS exposed
RETURN alert.id AS id, alert.rule AS rule, alert.name AS message, about, exposed
ORDER BY id
"""


class Neo4jGraphStore:
    name = "Neo4j"

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        *,
        prefix: str = "",
    ):
        self.uri = uri or os.environ.get("TWIN_NEO4J_URI", "bolt://127.0.0.1:7687")
        self.user = user or os.environ.get("TWIN_NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("TWIN_NEO4J_PASSWORD", "local_dev_change_me")
        self.database = os.environ.get("TWIN_NEO4J_DATABASE", "neo4j")
        self.prefix = prefix
        self._schema_ready = False
        self._lock = Lock()
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            connection_timeout=1.0,
            connection_acquisition_timeout=1.0,
            max_transaction_retry_time=1.0,
        )

    def _scope(self, name: str) -> str:
        return f"{self.prefix}{name}"

    def verify(self) -> None:
        self.driver.verify_connectivity()
        with self.driver.session(database=self.database) as session:
            session.run(
                "CREATE CONSTRAINT twin_node_identity IF NOT EXISTS "
                "FOR (n:TwinNode) REQUIRE (n.scope, n.id) IS UNIQUE"
            ).consume()
            session.run(
                "CREATE INDEX twin_node_kind IF NOT EXISTS "
                "FOR (n:TwinNode) ON (n.scope, n.kind)"
            ).consume()
            session.run(
                "CREATE INDEX twin_sample_time IF NOT EXISTS "
                "FOR (n:TelemetrySample) ON (n.recorded_at)"
            ).consume()
        self._schema_ready = True

    def ping(self) -> dict:
        try:
            self.driver.verify_connectivity()
        except Exception as error:
            return {
                "store": self.name,
                "connected": False,
                "detail": str(error).splitlines()[0][:240],
            }
        return {"store": self.name, "connected": True, "uri": self.uri}

    def close(self) -> None:
        self.driver.close()

    def clear(self) -> None:
        if not self.prefix:
            raise RuntimeError("Refusing to clear the production graph")
        with self.driver.session(database=self.database) as session:
            session.run(
                "MATCH (n:TwinNode) WHERE n.scope STARTS WITH $prefix DETACH DELETE n",
                prefix=self.prefix,
            ).consume()

    def commit(self, view: str, nodes: list[dict], edges: list[dict], *, record_history: bool = True) -> None:
        if not self._schema_ready:
            self.verify()
        view_scope = self._scope(view)
        catalog_scope = self._scope("catalog")
        history_scope = self._scope("history")
        with self._lock:
            with self.driver.session(database=self.database) as session:
                session.execute_write(
                    lambda tx: _write(
                        tx,
                        view_scope=view_scope,
                        catalog_scope=catalog_scope,
                        history_scope=history_scope,
                        nodes=nodes,
                        edges=edges,
                        record_history=record_history,
                    )
                )

    def read(self, view: str) -> dict:
        scope = self._scope(view)
        with self.driver.session(database=self.database) as session:
            nodes = session.execute_read(
                lambda tx: [
                    _public_node(record["id"], record["properties"])
                    for record in tx.run(
                        "MATCH (n:TwinNode {scope: $scope}) "
                        "RETURN n.id AS id, properties(n) AS properties ORDER BY id",
                        scope=scope,
                    )
                ]
            )
            edges = session.execute_read(
                lambda tx: [
                    _public_edge(record)
                    for record in tx.run(
                        "MATCH (a:TwinNode {scope: $scope})-[r]->(b:TwinNode {scope: $scope}) "
                        "RETURN a.id AS source, b.id AS target, type(r) AS relation, properties(r) AS properties "
                        "ORDER BY source, relation, target",
                        scope=scope,
                    )
                ]
            )
        return {"nodes": nodes, "edges": edges}

    def analyze(self, view: str) -> dict:
        scope = self._scope(view)
        with self.driver.session(database=self.database) as session:
            return session.execute_read(lambda tx: _analyze(tx, scope))

    def history_summary(self) -> dict:
        history = self._scope("history")
        catalog = self._scope("catalog")
        with self.driver.session(database=self.database) as session:
            return session.execute_read(lambda tx: _history(tx, history, catalog))


def _write(tx, *, view_scope, catalog_scope, history_scope, nodes, edges, record_history) -> None:
    catalog_nodes = [node for node in nodes if node["kind"] in CATALOG_KINDS]
    catalog_ids = [node["id"] for node in catalog_nodes]
    tx.run(
        "MATCH (n:TwinNode {scope: $scope}) WHERE NOT n.id IN $ids DETACH DELETE n",
        scope=catalog_scope,
        ids=catalog_ids,
    ).consume()
    for label, rows in _grouped(catalog_nodes, CATALOG_FIELDS).items():
        tx.run(
            f"UNWIND $nodes AS item "
            f"MERGE (n:TwinNode {{scope: $scope, id: item.id}}) "
            f"REMOVE n:{DOMAIN_LABELS} "
            f"SET n:{label} "
            f"SET n = item.properties "
            f"SET n.scope = $scope, n.id = item.id",
            scope=catalog_scope,
            nodes=rows,
        ).consume()
    tx.run(
        "MATCH (:TwinNode {scope: $scope})-[r]->(:TwinNode {scope: $scope}) "
        "WHERE type(r) IN ['HAS_ASSET', 'CONNECTED_TO'] DELETE r",
        scope=catalog_scope,
    ).consume()
    catalog_edges = [
        edge
        for edge in edges
        if edge["relation"] in {"HAS_ASSET", "CONNECTED_TO"}
        and edge["source"] in catalog_ids
        and edge["target"] in catalog_ids
    ]
    _create_edges(tx, catalog_scope, catalog_edges)
    tx.run("MATCH (n:TwinNode {scope: $scope}) DETACH DELETE n", scope=view_scope).consume()
    for label, rows in _grouped(nodes).items():
        tx.run(
            f"UNWIND $nodes AS item "
            f"CREATE (n:TwinNode:{label} {{scope: $scope, id: item.id}}) "
            f"SET n += item.properties",
            scope=view_scope,
            nodes=rows,
        ).consume()
    _create_edges(tx, view_scope, edges)
    if record_history:
        _record_history(tx, nodes, edges, catalog_scope, history_scope)


def _record_history(tx, nodes, edges, catalog_scope, history_scope) -> None:
    sample = next(node for node in nodes if node["kind"] == "telemetry_sample")
    recorded_at = sample["recorded_at"]
    history_id = f"sample:{recorded_at}"
    tx.run(
        "MATCH (sample:TwinNode {scope: $scope, id: $id}) "
        "OPTIONAL MATCH (sample)-[:RAISED]->(alert:TwinNode {scope: $scope}) "
        "WITH sample, collect(alert) AS alerts "
        "DETACH DELETE sample "
        "WITH alerts UNWIND alerts AS alert DETACH DELETE alert",
        scope=history_scope,
        id=history_id,
    ).consume()
    properties = _properties(sample)
    properties["recorded_at"] = recorded_at
    tx.run(
        "CREATE (sample:TwinNode:TelemetrySample {scope: $scope, id: $id}) SET sample += $properties",
        scope=history_scope,
        id=history_id,
        properties=properties,
    ).consume()
    observations = [
        {
            "source": edge["source"],
            "properties": _edge_properties(edge),
        }
        for edge in edges
        if edge["relation"] == "OBSERVED_IN" and edge["target"] == sample["id"]
    ]
    if observations:
        tx.run(
            "UNWIND $edges AS edge "
            "MATCH (asset:TwinNode {scope: $catalog, id: edge.source}) "
            "MATCH (sample:TwinNode {scope: $history, id: $sample_id}) "
            "CREATE (asset)-[relation:OBSERVED_IN]->(sample) "
            "SET relation += edge.properties",
            edges=observations,
            catalog=catalog_scope,
            history=history_scope,
            sample_id=history_id,
        ).consume()
    alerts = [node for node in nodes if node["kind"] == "alert"]
    alert_rows = []
    raised = []
    about = []
    for alert in alerts:
        history_alert = f"{alert['id']}@{recorded_at}"
        alert_rows.append({"id": history_alert, "properties": _properties(alert)})
        raised.append({"source": history_id, "target": history_alert, "properties": {"rule": alert["rule"]}})
        for subject in alert.get("about") or []:
            about.append({"source": history_alert, "target": subject, "properties": {}})
    if alert_rows:
        tx.run(
            "UNWIND $nodes AS item "
            "CREATE (alert:TwinNode:Alert {scope: $scope, id: item.id}) "
            "SET alert += item.properties",
            scope=history_scope,
            nodes=alert_rows,
        ).consume()
        tx.run(
            "UNWIND $edges AS edge "
            "MATCH (sample:TwinNode {scope: $scope, id: edge.source}) "
            "MATCH (alert:TwinNode {scope: $scope, id: edge.target}) "
            "CREATE (sample)-[relation:RAISED]->(alert) "
            "SET relation += edge.properties",
            scope=history_scope,
            edges=raised,
        ).consume()
        tx.run(
            "UNWIND $edges AS edge "
            "MATCH (alert:TwinNode {scope: $history, id: edge.source}) "
            "MATCH (asset:TwinNode {scope: $catalog, id: edge.target}) "
            "CREATE (alert)-[:ABOUT]->(asset)",
            history=history_scope,
            catalog=catalog_scope,
            edges=about,
        ).consume()
    tx.run(
        "MATCH (sample:TwinNode {scope: $scope, kind: 'telemetry_sample'}) "
        "WITH sample ORDER BY sample.recorded_at DESC SKIP $keep "
        "DETACH DELETE sample",
        scope=history_scope,
        keep=HISTORY_LIMIT,
    ).consume()
    tx.run(
        "MATCH (alert:TwinNode {scope: $scope, kind: 'alert'}) "
        "WHERE NOT (alert)<-[:RAISED]-() DETACH DELETE alert",
        scope=history_scope,
    ).consume()


def _analyze(tx, scope: str) -> dict:
    utility = tx.run(
        "MATCH (n:TwinNode {scope: $scope}) "
        "WHERE n.kind = 'grid' OR n.id STARTS WITH 'grid:' "
        "RETURN count(n) AS utility_nodes",
        scope=scope,
    ).single()
    labels = [
        {"label": record["label"], "count": record["count"]}
        for record in tx.run(
            "MATCH (n:TwinNode {scope: $scope}) "
            "UNWIND labels(n) AS label "
            "WITH label WHERE label <> 'TwinNode' "
            "RETURN label, count(*) AS count ORDER BY label",
            scope=scope,
        )
    ]
    relations = [
        {"relation": record["relation"], "count": record["count"]}
        for record in tx.run(
            "MATCH (:TwinNode {scope: $scope})-[r]->(:TwinNode {scope: $scope}) "
            "RETURN type(r) AS relation, count(*) AS count ORDER BY relation",
            scope=scope,
        )
    ]
    downstream = [_row(record) for record in tx.run(DOWNSTREAM_QUERY, scope=scope)]
    paths = [_row(record) for record in tx.run(PATH_QUERY, scope=scope)]
    alerts = [_row(record) for record in tx.run(IMPACT_QUERY, scope=scope)]
    attribution = [
        _row(record)
        for record in tx.run(
            "MATCH (n:TwinNode {scope: $scope}) "
            "WHERE n.kind IN ['solar', 'battery'] "
            "RETURN n.id AS id, n.kind AS kind, n.attribution AS attribution, "
            "n.value IS NOT NULL AS attributed ORDER BY id",
            scope=scope,
        )
    ]
    utility_nodes = utility["utility_nodes"] if utility else 0
    return {
        "engine": "Cypher",
        "utility_nodes": utility_nodes,
        "islanded": utility_nodes == 0,
        "census": {"labels": labels, "relations": relations},
        "downstream": downstream,
        "electrical_paths": paths,
        "alerts": alerts,
        "attribution": attribution,
        "queries": [
            {"name": "Chargers fed by the islanded bus", "cypher": " ".join(DOWNSTREAM_QUERY.split())},
            {"name": "Shortest electrical path", "cypher": " ".join(PATH_QUERY.split())},
            {"name": "Assets sharing the bus with an alert", "cypher": " ".join(IMPACT_QUERY.split())},
        ],
    }


def _history(tx, history: str, catalog: str) -> dict:
    samples = tx.run(
        "MATCH (sample:TwinNode {scope: $scope, kind: 'telemetry_sample'}) "
        "RETURN count(sample) AS samples",
        scope=history,
    ).single()
    alerts = tx.run(
        "MATCH (alert:TwinNode {scope: $scope, kind: 'alert'}) RETURN count(alert) AS alerts",
        scope=history,
    ).single()
    recent = [
        _row(record)
        for record in tx.run(
            "MATCH (sample:TwinNode {scope: $scope, kind: 'telemetry_sample'}) "
            "OPTIONAL MATCH (sample)-[:RAISED]->(alert:TwinNode {scope: $scope, kind: 'alert'}) "
            "WITH sample, count(alert) AS alert_count, "
            "[rule IN collect(DISTINCT alert.rule) WHERE rule IS NOT NULL] AS rules "
            "RETURN sample.recorded_at AS recorded_at, alert_count, rules "
            "ORDER BY recorded_at DESC LIMIT 8",
            scope=history,
        )
    ]
    charger_trace = [
        _row(record)
        for record in tx.run(
            "MATCH (charger:TwinNode {scope: $catalog, kind: 'charger'})"
            "-[obs:OBSERVED_IN]->(sample:TwinNode {scope: $history}) "
            "RETURN charger.id AS charger_id, charger.name AS name, "
            "sample.recorded_at AS recorded_at, obs.value AS power_kw, obs.status AS status "
            "ORDER BY recorded_at DESC, charger_id LIMIT 16",
            catalog=catalog,
            history=history,
        )
    ]
    repeated = [
        _row(record)
        for record in tx.run(
            "MATCH (sample:TwinNode {scope: $history})"
            "-[:RAISED]->(alert:TwinNode {scope: $history})"
            "-[:ABOUT]->(asset:TwinNode {scope: $catalog}) "
            "WITH alert.rule AS rule, asset, count(DISTINCT sample) AS minutes "
            "ORDER BY minutes DESC, rule LIMIT 8 "
            "OPTIONAL MATCH (asset)-[:CONNECTED_TO*1..4]-(neighbor:TwinNode {scope: $catalog}) "
            "WHERE neighbor.id <> asset.id AND neighbor.kind IN ['solar', 'battery', 'bus', 'charger'] "
            "RETURN rule, asset.id AS asset_id, asset.name AS asset_name, minutes, "
            "[id IN collect(DISTINCT neighbor.id) WHERE id IS NOT NULL] AS exposed",
            history=history,
            catalog=catalog,
        )
    ]
    return {
        "samples": samples["samples"] if samples else 0,
        "alerts": alerts["alerts"] if alerts else 0,
        "recent": recent,
        "charger_trace": charger_trace,
        "repeated_exposure": repeated,
    }


def _grouped(nodes: list[dict], fields: set[str] | None = None) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for node in nodes:
        label = LABEL_BY_KIND.get(node.get("kind"))
        if label is None:
            raise ValueError(f"Unknown graph node kind: {node.get('kind')}")
        grouped.setdefault(label, []).append(
            {"id": node["id"], "properties": _properties(node, fields)}
        )
    return grouped


def _properties(node: dict, fields: set[str] | None = None) -> dict:
    properties = {}
    for key, value in node.items():
        if key == "id" or value is None:
            continue
        if fields is not None and key not in fields:
            continue
        if isinstance(value, bool | int | float | str):
            properties[key] = value
        elif isinstance(value, list) and all(isinstance(item, bool | int | float | str) for item in value):
            properties[key] = value
        else:
            raise ValueError(f"Graph property {key} is not a Neo4j value")
    return properties


def _edge_properties(edge: dict) -> dict:
    return {
        key: value
        for key, value in edge.items()
        if key not in {"source", "target", "relation"} and isinstance(value, bool | int | float | str)
    }


def _create_edges(tx, scope: str, edges: list[dict]) -> None:
    grouped: dict[str, list[dict]] = {relation: [] for relation in RELATIONS}
    for edge in edges:
        relation = edge.get("relation")
        if relation not in grouped:
            raise ValueError(f"Unknown graph relationship: {relation}")
        grouped[relation].append(
            {
                "source": edge["source"],
                "target": edge["target"],
                "properties": _edge_properties(edge),
            }
        )
    for relation, rows in grouped.items():
        if rows:
            tx.run(
                "UNWIND $edges AS edge "
                "MATCH (a:TwinNode {scope: $scope, id: edge.source}) "
                "MATCH (b:TwinNode {scope: $scope, id: edge.target}) "
                f"CREATE (a)-[relation:{relation}]->(b) "
                "SET relation += edge.properties",
                scope=scope,
                edges=rows,
            ).consume()


def _public_node(node_id: str, properties: dict) -> dict:
    node = {"id": node_id, **properties}
    node.pop("scope", None)
    node.pop("id", None)
    node["id"] = node_id
    node.setdefault("value", None)
    node.setdefault("wallbox_id", None)
    return node


def _public_edge(record) -> dict:
    edge = {
        "source": record["source"],
        "target": record["target"],
        "relation": record["relation"],
    }
    edge.update({key: value for key, value in record["properties"].items() if value is not None})
    return edge


def _row(record) -> dict:
    return record.data()


graph_store = Neo4jGraphStore()
