import json

import pytest

from app.core.config import settings
from app.schemas.graph import GraphQuery
from app.services.neo4j_projection import (
    COUNT_PROJECTION,
    GraphProjectionError,
    Neo4jProjectionClient,
    projection_rows,
)


class FakeResult:
    def __init__(self, records=None):
        self.records = list(records or [])

    def __iter__(self):
        return iter(self.records)

    def consume(self):
        return object()

    def single(self, strict=False):
        del strict
        assert len(self.records) == 1
        return self.records[0]


class FakeTransaction:
    def __init__(self, *, counts=None, node_records=None, edge_records=None, path_record=None):
        self.counts = counts or {}
        self.node_records = list(node_records or [])
        self.edge_records = list(edge_records or [])
        self.path_record = path_record
        self.calls = []

    def run(self, cypher, **parameters):
        self.calls.append((cypher, parameters))
        if cypher == COUNT_PROJECTION:
            count = self.counts[parameters["projection"]]
            return FakeResult(
                [{"node_count": count["nodes"], "edge_count": count["edges"]}]
            )
        if "RETURN count(root) AS root_count" in cypher:
            return FakeResult([{"root_count": 1}])
        if "RETURN node.graph_id AS graph_id" in cypher:
            return FakeResult(self.node_records)
        if "RETURN edge.payload_json AS payload_json" in cypher:
            return FakeResult(self.edge_records)
        if "OPTIONAL MATCH path=shortestPath" in cypher:
            return FakeResult([self.path_record] if self.path_record else [])
        return FakeResult()


class FakeSession:
    def __init__(self, transaction):
        self.transaction = transaction
        self.write_callbacks = []
        self.read_callbacks = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute_write(self, callback, *args):
        self.write_callbacks.append(callback)
        return callback(self.transaction, *args)

    def execute_read(self, callback, *args):
        self.read_callbacks.append(callback)
        return callback(self.transaction, *args)


class FakeDriver:
    def __init__(self, session):
        self.fake_session = session
        self.requested_database = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def session(self, *, database):
        self.requested_database = database
        return self.fake_session


def graph_fixture():
    return {
        "nodes": [
            {"id": "research:1", "type": "ResearchItem", "label": "One", "degree": 1},
            {"id": "tag:agents", "type": "Concept", "label": "Agents", "degree": 1},
        ],
        "edges": [
            {
                "id": "edge:1",
                "source": "research:1",
                "target": "tag:agents",
                "type": "RESEARCHES",
            }
        ],
    }


def client_for(transaction):
    session = FakeSession(transaction)
    driver = FakeDriver(session)
    client = Neo4jProjectionClient(
        uri="neo4j://projection.invalid:7687",
        username="neo4j",
        password="integration-only-password",
        database="neo4j",
        batch_size=1,
        connection_timeout=1,
        retry_timeout=1,
        driver_factory=lambda *_args, **_kwargs: driver,
    )
    return client, session, driver


def test_projection_rows_validate_contract_and_parameter_payloads():
    rows = projection_rows("relationship", graph_fixture(), "sync-1")

    assert [row["graph_id"] for row in rows.nodes] == ["research:1", "tag:agents"]
    assert rows.edges[0]["source"] == "research:1"
    assert json.loads(rows.edges[0]["properties"]["payload_json"])["type"] == "RESEARCHES"
    assert rows.edges[0]["properties"]["sync_id"] == "sync-1"

    broken = graph_fixture()
    broken["edges"][0]["target"] = "missing"
    with pytest.raises(GraphProjectionError) as captured:
        projection_rows("relationship", broken, "sync-2")
    assert captured.value.code == "NEO4J_PROJECTION_INVALID"


def test_rebuild_batches_both_views_in_one_atomic_replacement_transaction():
    counts = {
        "relationship": {"nodes": 2, "edges": 1},
        "hierarchy": {"nodes": 1, "edges": 0},
    }
    transaction = FakeTransaction(counts=counts)
    client, session, driver = client_for(transaction)

    actual = client.rebuild(
        graph_fixture(),
        {"nodes": [{"id": "root", "type": "System", "label": "Root"}], "edges": []},
    )

    assert actual == counts
    assert driver.requested_database == "neo4j"
    assert len(session.write_callbacks) == 3  # two constraints, then one atomic replacement
    assert session.write_callbacks[-1].__name__ == "_replace_tx"
    assert len(session.read_callbacks) == 1
    row_calls = [parameters for _cypher, parameters in transaction.calls if "rows" in parameters]
    assert row_calls
    assert all(len(parameters["rows"]) <= 1 for parameters in row_calls)
    assert all("integration-only-password" not in cypher for cypher, _ in transaction.calls)


def test_neo4j_query_is_parameterized_bounded_and_contract_valid():
    marker = "marker-not-in-cypher"
    node_payload = {
        "id": "research:1",
        "type": "ResearchItem",
        "label": marker,
        "summary": "Bounded graph result",
        "degree": 0,
    }
    transaction = FakeTransaction(
        node_records=[{"graph_id": "research:1", "payload_json": json.dumps(node_payload)}]
    )
    client, _session, _driver = client_for(transaction)

    response = client.query(GraphQuery(query=marker, limit=1))

    assert response.meta.provider == "neo4j"
    assert response.meta.node_count == 1
    assert response.nodes[0].label == marker
    node_call = next(
        (cypher, parameters)
        for cypher, parameters in transaction.calls
        if "RETURN node.graph_id AS graph_id" in cypher
    )
    assert marker not in node_call[0]
    assert node_call[1]["needle"] == marker
    assert node_call[1]["fetch_limit"] == 2


def test_selected_neo4j_provider_fails_typed_without_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "graph_data_provider", "neo4j")
    monkeypatch.setattr(settings, "neo4j_uri", None)
    monkeypatch.setattr(settings, "neo4j_password", None)

    response = client.get("/api/v1/graph")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "NEO4J_NOT_CONFIGURED",
        "message": "Đã chọn Neo4j cho đồ thị nhưng chưa cấu hình kết nối.",
    }


def test_shortest_path_is_bounded_parameterized_and_validated():
    edge = graph_fixture()["edges"][0]
    transaction = FakeTransaction(
        path_record={
            "node_ids": ["research:1", "tag:agents"],
            "edge_payloads": [json.dumps(edge)],
        }
    )
    client, _session, _driver = client_for(transaction)

    path = client.shortest_path("research:1", "tag:agents")

    assert path["node_ids"] == ["research:1", "tag:agents"]
    assert path["edges"][0]["id"] == "edge:1"
    cypher, parameters = next(
        call for call in transaction.calls if "OPTIONAL MATCH path=shortestPath" in call[0]
    )
    assert "research:1" not in cypher
    assert parameters == {"source": "research:1", "target": "tag:agents"}
