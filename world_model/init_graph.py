import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "zana_neo4j")

def init_ontology():
    print(f"Connecting to Neo4j at {URI}...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    with driver.session() as session:
        # Create Constraints
        print("Setting up constraints...")
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entidad) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Intencion) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Valor) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (es:Estado) REQUIRE es.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:AEON) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Proyecto) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (art:Artefacto) REQUIRE art.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Recurso) REQUIRE r.id IS UNIQUE",
        ]
        for c in constraints:
            session.run(c)
            
        # Initialize Core Nodes (The Foundation)
        print("Forging the Foundation...")
        session.run("""
        MERGE (v:Valor {id: 'core_principles', nombre: 'Core Principles', descripcion: 'Engineering excellence and cognitive integrity'})
        MERGE (zana:AEON {id: 'zana_core', nombre: 'ZANA', rol: 'Cognitive Architect'})
        MERGE (aria:AEON {id: 'aria_design', nombre: 'ARIA', rol: 'Elite Design Agency'})

        MERGE (v)-[:RESTRINGE]->(zana)
        MERGE (v)-[:RESTRINGE]->(aria)

        MERGE (i:Intencion {id: 'primary_goal', nombre: 'Primary Goal', descripcion: 'Sovereignty and radical scalability'})
        MERGE (p_default:Proyecto {id: 'project_alpha', nombre: 'Project Alpha', estado: 'ACTIVO'})

        MERGE (i)-[:DEFINE]->(p_default)

        MERGE (r_liq:Recurso {id: 'liquidity', nombre: 'Liquidity', unidad: 'USD'})
        MERGE (r_time:Recurso {id: 'time', nombre: 'Time', unidad: 'Hours'})

        MERGE (zana)-[:CONSUME]->(r_time)
        """)
        
        print("✅ World Model Ontology initialized.")
        
    driver.close()

if __name__ == "__main__":
    init_ontology()
