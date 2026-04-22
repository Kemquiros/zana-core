import os
import sys
import json
import redis
import numpy as np
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from neo4j import GraphDatabase
from mcp.server.fastmcp import FastMCP

# Add project root to sys.path to find world_model
sys.path.append(str(Path(__file__).parent.parent.parent))
from world_model.eml import exp_eml, log_eml

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "zana_neo4j")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")

mcp = FastMCP("zana-world")

_driver = None
_redis_client = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    return _driver


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


@mcp.tool()
def query_world_model(cypher_query: str) -> str:
    """
    Execute a read-only Cypher query against the World Model (Neo4j).
    Use this to understand the topology of John's Empire.

    Args:
        cypher_query: The Cypher query to execute. MUST be a READ query (e.g., MATCH ... RETURN).
    """
    if (
        "CREATE" in cypher_query.upper()
        or "MERGE" in cypher_query.upper()
        or "DELETE" in cypher_query.upper()
    ):
        return "❌ Error: query_world_model only supports READ queries (MATCH ... RETURN). Use add_node or add_relation for writes."

    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(cypher_query)
            records = [record.data() for record in result]
            if not records:
                return "No results found."

            # Format results nicely
            formatted = []
            for r in records:
                formatted.append(str(r))
            return "\\n".join(formatted)
    except Exception as e:
        return f"❌ Cypher Error: {str(e)}"


@mcp.tool()
def add_entity(label: str, properties: dict) -> str:
    """
    Add a new entity to the World Model.

    Args:
        label: The node label (e.g., 'AEON', 'Proyecto', 'Artefacto', 'Recurso', 'Entidad').
        properties: Dictionary of properties (must include 'id' and 'nombre').
    """
    if "id" not in properties:
        return "❌ Error: Node must have an 'id' property."

    driver = get_driver()

    # Build SET clause dynamically safely
    props_str = ", ".join([f"n.{k} = ${k}" for k in properties.keys()])

    cypher = f"MERGE (n:{label} {{id: $id}}) SET {props_str} RETURN n"

    try:
        with driver.session() as session:
            result = session.run(cypher, **properties)
            record = result.single()
            return f"✅ Entity created/updated: {record[0]}"
    except Exception as e:
        return f"❌ Error adding entity: {str(e)}"


@mcp.tool()
def add_relation(source_id: str, target_id: str, relation_type: str) -> str:
    """
    Create a directed causal relationship between two entities.

    Args:
        source_id: The ID of the source node.
        target_id: The ID of the target node.
        relation_type: The relationship type (e.g., 'ALIMENTA', 'BLOQUEA', 'RESTRINGE', 'DEFINE').
    """
    driver = get_driver()
    cypher = f"""
    MATCH (a {{id: $source_id}})
    MATCH (b {{id: $target_id}})
    MERGE (a)-[r:{relation_type}]->(b)
    RETURN type(r)
    """
    try:
        with driver.session() as session:
            result = session.run(cypher, source_id=source_id, target_id=target_id)
            if not result.peek():
                return f"❌ Error: Could not find source ('{source_id}') or target ('{target_id}')."
            return f"✅ Relation {relation_type} created between {source_id} and {target_id}."
    except Exception as e:
        return f"❌ Error adding relation: {str(e)}"


@mcp.tool()
def simulate_impact(target_id: str) -> str:
    """
    Simulate what happens if a node is modified or fails.
    Returns the downstream topology (what projects or resources will be affected).

    Args:
        target_id: The ID of the node being modified or queried.
    """
    driver = get_driver()
    # Query: Find all paths extending outwards from this node up to 3 hops
    cypher = """
    MATCH p=(n {id: $target_id})-[*1..3]->(m)
    RETURN [node in nodes(p) | {id: node.id, labels: labels(node)}] as path_nodes,
           [rel in relationships(p) | type(rel)] as path_relations
    LIMIT 10
    """
    try:
        with driver.session() as session:
            result = session.run(cypher, target_id=target_id)
            records = [record.data() for record in result]

            if not records:
                # Let's check upstream too
                return f"No downstream impact detected for {target_id}. It might be a leaf node."

            output = [f"🔮 SIMULATION RESULTS FOR {target_id}:"]
            for r in records:
                path_str = f"({target_id})"
                nodes = r["path_nodes"][1:]  # skip first (which is target_id)
                rels = r["path_relations"]
                for i in range(len(rels)):
                    path_str += (
                        f" -[{rels[i]}]-> ({nodes[i]['id']} :{nodes[i]['labels'][0]})"
                    )
                output.append(path_str)

            return "\\n".join(output)
    except Exception as e:
        return f"❌ Error simulating impact: {str(e)}"


@mcp.tool()
def get_session_state(session_id: str = "default") -> str:
    """
    Get the dynamic session state from Redis.
    Use this to understand the current active project, task, and context.

    Args:
        session_id: The ID of the session (defaults to 'default').
    """
    r = get_redis()
    try:
        state = r.get(f"session:{session_id}")
        if state:
            return state
        return json.dumps(
            {"active_project": None, "current_task": None, "hot_entities": []}
        )
    except Exception as e:
        return f"❌ Error reading session state from Redis: {str(e)}"


@mcp.tool()
def update_session_state(state_update: dict, session_id: str = "default") -> str:
    """
    Update the dynamic session state in Redis.

    Args:
        state_update: Dictionary with keys to update (e.g. {'active_project': 'VECANOVA'}).
        session_id: The ID of the session (defaults to 'default').
    """
    r = get_redis()
    key = f"session:{session_id}"
    try:
        current_state_str = r.get(key)
        if current_state_str:
            state = json.loads(current_state_str)
        else:
            state = {"active_project": None, "current_task": None, "hot_entities": []}

        state.update(state_update)
        r.set(key, json.dumps(state))
        return f"✅ Session state updated: {json.dumps(state)}"
    except Exception as e:
        return f"❌ Error updating session state in Redis: {str(e)}"


@mcp.tool()
def symbolic_regression_eml(expression_str: str, x_values: List[float]) -> str:
    """
    Perform a symbolic evaluation using the EML (Exp-Minus-Log) operator.
    Currently supports simple reconstructions like exp, log.

    Args:
        expression_str: The type of function to evaluate ('exp', 'log', 'e').
        x_values: List of input values for the function.
    """
    try:
        x = np.array(x_values)
        if expression_str == "exp":
            res = exp_eml(x)
        elif expression_str == "log":
            res = log_eml(x)
        elif expression_str == "e":
            res = np.array([exp_eml(1.0)] * len(x_values))
        else:
            return f"❌ Error: Unknown expression '{expression_str}'. Supported: 'exp', 'log', 'e'."

        return f"✅ Result of {expression_str}: {res.tolist()}"
    except Exception as e:
        return f"❌ Error in symbolic regression: {str(e)}"


@mcp.tool()
def latent_sync_world(session_id: str = "default") -> str:
    """
    Synchronizes the dynamic session state (Redis) with the World Model (Neo4j).
    Creates 'RESISTANCE' or 'RESONANCE' edges between the active project and hot entities.

    Args:
        session_id: The ID of the session to sync.
    """
    r = get_redis()
    driver = get_driver()
    try:
        state_str = r.get(f"session:{session_id}")
        if not state_str:
            return "⚠️ No active session state found in Redis to sync."

        state = json.loads(state_str)
        active_project = state.get("active_project")
        hot_entities = state.get("hot_entities", [])

        if not active_project or not hot_entities:
            return "⚠️ Session state missing active_project or hot_entities for sync."

        with driver.session() as session:
            # Cypher logic: Create resonance links between active project and hot entities
            cypher = """
            MATCH (p {id: $project_id})
            UNWIND $entities as ent_id
            MATCH (e {id: ent_id})
            MERGE (p)-[r:RESONATES_WITH {timestamp: timestamp()}]->(e)
            RETURN count(r) as links
            """
            result = session.run(
                cypher, project_id=active_project, entities=hot_entities
            )
            count = result.single()["links"]

        return f"✅ Latent Sync Complete: Created/Updated {count} resonance links in World Model."
    except Exception as e:
        return f"❌ Error during Latent Sync: {str(e)}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
