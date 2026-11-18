"""Campus Graph - Flask API + web UI on top of a Neo4j graph database."""
import os

from flask import Flask, jsonify, render_template, request
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (
    os.getenv("NEO4J_USER", "neo4j"),
    os.getenv("NEO4J_PASSWORD", "password123"),
)

LABELS = {"Student", "Course", "Teacher"}
# relationship type -> (source label, target label)
RULES = {
    "ENROLLED_IN": ("Student", "Course"),
    "TEACHES": ("Teacher", "Course"),
    "FRIEND_OF": ("Student", "Student"),
}

SEED = """
MERGE (adam:Student {name:'Adam'})
MERGE (sara:Student {name:'Sara'})
MERGE (omar:Student {name:'Omar'})
MERGE (java:Course {name:'Java'})
MERGE (nosql:Course {name:'NoSQL'})
MERGE (alami:Teacher {name:'Mr Alami'})
MERGE (adam)-[:FRIEND_OF]->(omar)
MERGE (adam)-[:ENROLLED_IN]->(java)
MERGE (adam)-[:ENROLLED_IN]->(nosql)
MERGE (sara)-[:ENROLLED_IN]->(nosql)
MERGE (omar)-[:ENROLLED_IN]->(java)
MERGE (alami)-[:TEACHES]->(nosql)
"""

app = Flask(__name__)
driver = GraphDatabase.driver(URI, auth=AUTH)


def run(query, **params):
    records, _, _ = driver.execute_query(query, parameters_=params)
    return records


def bad_request(message, code=400):
    return jsonify(error=message), code


@app.errorhandler(ServiceUnavailable)
def db_down(_err):
    return bad_request("Database unavailable, try again in a few seconds", 503)


@app.errorhandler(AuthError)
def db_auth(_err):
    return bad_request("Database authentication failed", 503)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    run("RETURN 1")
    return jsonify(status="ok")


@app.get("/api/graph")
def get_graph():
    nodes = run(
        "MATCH (n) RETURN elementId(n) AS id, labels(n)[0] AS label, n.name AS name"
    )
    edges = run(
        "MATCH (a)-[r]->(b) "
        "RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS type"
    )
    return jsonify(
        nodes=[dict(r) for r in nodes],
        edges=[dict(r) for r in edges],
    )


@app.post("/api/nodes")
def create_node():
    data = request.get_json(silent=True) or {}
    label = data.get("label")
    name = (data.get("name") or "").strip()
    if label not in LABELS:
        return bad_request(f"label must be one of {sorted(LABELS)}")
    if not name or len(name) > 60:
        return bad_request("name is required (max 60 characters)")
    # labels cannot be parameterised in Cypher, so they are whitelisted above
    run(f"MERGE (n:{label} {{name: $name}})", name=name)
    return jsonify(label=label, name=name), 201


@app.post("/api/relationships")
def create_relationship():
    data = request.get_json(silent=True) or {}
    rel = data.get("type")
    if rel not in RULES:
        return bad_request(f"type must be one of {sorted(RULES)}")
    src_label, dst_label = RULES[rel]
    # --- the fix: reject a node connected to itself ---
    if data.get("source") == data.get("target"):
        return bad_request("A node cannot be connected to itself")
    # --------------------------------------------------
    records = run(
        f"MATCH (a:{src_label}) WHERE elementId(a) = $src "
        f"MATCH (b:{dst_label}) WHERE elementId(b) = $dst "
        f"MERGE (a)-[r:{rel}]->(b) RETURN type(r) AS type",
        src=data.get("source"),
        dst=data.get("target"),
    )
    if not records:
        return bad_request(f"{rel} must go from a {src_label} to a {dst_label}")
    return jsonify(type=rel), 201


@app.delete("/api/nodes/<path:node_id>")
def delete_node(node_id):
    run("MATCH (n) WHERE elementId(n) = $id DETACH DELETE n", id=node_id)
    return jsonify(deleted=node_id)


@app.get("/api/recommendations/<path:student_id>")
def recommendations(student_id):
    """Courses taken by a student's friends that the student has not taken."""
    records = run(
        "MATCH (s:Student) WHERE elementId(s) = $id "
        "MATCH (s)-[:FRIEND_OF]-(f:Student)-[:ENROLLED_IN]->(c:Course) "
        "WHERE NOT (s)-[:ENROLLED_IN]->(c) "
        "RETURN c.name AS course, collect(DISTINCT f.name) AS friends "
        "ORDER BY course",
        id=student_id,
    )
    return jsonify([dict(r) for r in records])


@app.post("/api/seed")
def seed():
    run(SEED)
    return jsonify(status="seeded")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)