# Campus Graph

A web app to model a campus as a **graph**: students, courses and teachers are nodes, and
`ENROLLED_IN`, `TEACHES`, `FRIEND_OF` are relationships. Built with Flask, Neo4j and Docker Compose.

![CI](https://github.com/adam200555/campus-graph/actions/workflows/ci.yml/badge.svg)

## Features

- Interactive graph visualisation (vis-network)
- Add / delete nodes and connect them from the UI
- REST API (JSON) with input validation
- Recommendation query: courses your friends take that you do not (friends-of-graph traversal)
- Neo4j data persisted in a Docker volume
- Unit tests (pytest, database mocked) and a GitHub Actions pipeline

## Stack

Python 3.12 · Flask · Gunicorn · Neo4j 5 · Docker Compose · GitHub Actions

## Run it

```bash
cp .env.example .env          # then edit NEO4J_PASSWORD
docker compose up -d --build
```

- App: http://localhost:5000 (click **Load sample data** the first time)
- Neo4j Browser: http://localhost:7474 (user `neo4j`, password from `.env`)

```bash
docker compose logs -f api    # follow logs
docker compose down           # stop, keep data
docker compose down -v        # stop AND delete data
```

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Database connectivity check |
| GET | `/api/graph` | All nodes and relationships |
| POST | `/api/nodes` | `{"label": "Student", "name": "Sara"}` |
| POST | `/api/relationships` | `{"type": "ENROLLED_IN", "source": id, "target": id}` |
| DELETE | `/api/nodes/<id>` | Delete a node and its relationships |
| GET | `/api/recommendations/<student_id>` | Courses taken by friends |
| POST | `/api/seed` | Load sample data (idempotent) |

## Graph model

```
(Student)-[:ENROLLED_IN]->(Course)<-[:TEACHES]-(Teacher)
(Student)-[:FRIEND_OF]->(Student)
```

## Tests

```bash
pip install -r app/requirements.txt
pytest app/tests -q
```

## Design decisions

- **Cypher injection:** labels and relationship types cannot be query parameters, so they are
  checked against a whitelist; all values use parameters.
- **Secrets:** the database password comes from `.env` (git-ignored), never from the code.
- **Startup order:** the API waits for Neo4j's healthcheck before starting.
- **Container hardening:** the API image runs as a non-root user.
- **Idempotent writes:** `MERGE` prevents duplicate nodes and relationships.
