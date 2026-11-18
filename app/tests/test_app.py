"""Unit tests: the Neo4j driver is mocked, so no database is needed."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as campus  # noqa: E402


def client():
    campus.app.config["TESTING"] = True
    return campus.app.test_client()


def test_create_node_rejects_unknown_label():
    res = client().post("/api/nodes", json={"label": "Hacker", "name": "x"})
    assert res.status_code == 400


def test_create_node_rejects_empty_name():
    res = client().post("/api/nodes", json={"label": "Student", "name": "   "})
    assert res.status_code == 400


def test_create_node_ok():
    with patch.object(campus, "run", return_value=[]) as run:
        res = client().post("/api/nodes", json={"label": "Student", "name": "Yassine"})
    assert res.status_code == 201
    assert res.get_json() == {"label": "Student", "name": "Yassine"}
    run.assert_called_once()


def test_relationship_rejects_unknown_type():
    res = client().post("/api/relationships", json={"type": "HACKS"})
    assert res.status_code == 400


def test_relationship_wrong_node_types_returns_400():
    with patch.object(campus, "run", return_value=[]):
        res = client().post(
            "/api/relationships",
            json={"type": "ENROLLED_IN", "source": "a", "target": "b"},
        )
    assert res.status_code == 400


def test_cypher_injection_in_label_is_blocked():
    res = client().post(
        "/api/nodes", json={"label": "Student) DETACH DELETE (n", "name": "x"}
    )
    assert res.status_code == 400
def test_relationship_to_itself_is_rejected():
    res = client().post(
        "/api/relationships",
        json={"type": "FRIEND_OF", "source": "x", "target": "x"},
    )
    assert res.status_code == 400