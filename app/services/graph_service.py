import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime

from app.models.document import Document
from app.models.customer import Customer, Server, Service
from app.models.event import IncidentCase
from app.models.user import User

logger = logging.getLogger(__name__)


class GraphNodeType:
    CUSTOMER = "customer"
    SERVER = "server"
    SERVICE = "service"
    DOCUMENT = "document"
    PERSON = "person"
    INCIDENT = "incident"


class GraphRelationType:
    OWNS = "OWNS"
    DEPENDS_ON = "DEPENDS_ON"
    RUNS = "RUNS"
    ABOUT = "ABOUT"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"
    MANAGES = "MANAGES"
    RESPONSIBLE_FOR = "RESPONSIBLE_FOR"
    OCCURRED_ON = "OCCURRED_ON"
    RESOLVED_BY = "RESOLVED_BY"
    SIMILAR_TO = "SIMILAR_TO"


class GraphDBService:
    """
    Graph DB service using Apache AGE.
    
    Apache AGE extends PostgreSQL with graph capabilities.
    This service provides relationship exploration between entities.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_to_graph(self, entity_type: str, entity_id: int) -> bool:
        """Sync a relational entity to graph representation."""
        try:
            if entity_type == "customer":
                await self._sync_customer(entity_id)
            elif entity_type == "server":
                await self._sync_server(entity_id)
            elif entity_type == "document":
                await self._sync_document(entity_id)
            elif entity_type == "incident":
                await self._sync_incident(entity_id)
            
            return True
        except Exception as e:
            logger.error(f"Graph sync failed for {entity_type}:{entity_id}: {e}")
            return False

    async def _sync_customer(self, customer_id: int):
        """Sync customer to graph."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            return
        
        await self.db.execute(text("""
            SELECT * FROM cypher('msp_graph', $$
                MERGE (c:Customer {id: $id})
                SET c.name = $name, c.code = $code
            $$) AS (c agtype);
        """), {
            "id": str(customer.id),
            "name": customer.name,
            "code": customer.code
        })

    async def _sync_server(self, server_id: int):
        """Sync server to graph with customer relationship."""
        result = await self.db.execute(
            select(Server).where(Server.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            return
        
        await self.db.execute(text("""
            SELECT * FROM cypher('msp_graph', $$
                MERGE (s:Server {id: $server_id})
                SET s.hostname = $hostname, s.ip_address = $ip
                WITH s
                MERGE (c:Customer {id: $customer_id})
                MERGE (c)-[:OWNS]->(s)
            $$) AS (result agtype);
        """), {
            "server_id": str(server.id),
            "hostname": server.hostname,
            "ip": server.ip_address or "",
            "customer_id": str(server.customer_id)
        })

    async def _sync_document(self, document_id: int):
        """Sync document to graph."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            return
        
        await self.db.execute(text("""
            SELECT * FROM cypher('msp_graph', $$
                MERGE (d:Document {id: $doc_id})
                SET d.title = $title, d.document_type = $doc_type
                WITH d
                MERGE (c:Customer {id: $customer_id})
                MERGE (d)-[:ABOUT]->(c)
            $$) AS (result agtype);
        """), {
            "doc_id": str(doc.id),
            "title": doc.title,
            "doc_type": str(doc.document_type),
            "customer_id": str(doc.customer_id)
        })

    async def _sync_incident(self, incident_id: int):
        """Sync incident to graph."""
        result = await self.db.execute(
            select(IncidentCase).where(IncidentCase.id == incident_id)
        )
        incident = result.scalar_one_or_none()
        
        if not incident:
            return
        
        await self.db.execute(text("""
            SELECT * FROM cypher('msp_graph', $$
                MERGE (i:Incident {id: $incident_id})
                SET i.title = $title, i.severity = $severity
                WITH i
                MERGE (c:Customer {id: $customer_id})
                MERGE (i)-[:OCCURRED_FOR]->(c)
            $$) AS (result agtype);
        """), {
            "incident_id": str(incident.id),
            "title": incident.title,
            "severity": incident.severity,
            "customer_id": str(incident.customer_id)
        })

    async def traverse(
        self, entity_type: str, entity_id: int,
        relation_types: Optional[List[str]] = None,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Traverse graph from an entity."""
        cypher_query = self._build_traverse_query(entity_type, entity_id, relation_types, depth)
        
        try:
            result = await self.db.execute(text(cypher_query), {
                "start_id": str(entity_id)
            })
            
            rows = result.fetchall()
            return self._format_traverse_result(rows)
            
        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            return {"nodes": [], "edges": [], "error": str(e)}

    def _build_traverse_query(
        self, entity_type: str, entity_id: int,
        relation_types: Optional[List[str]], depth: int
    ) -> str:
        """Build Cypher query for graph traversal."""
        label = entity_type.capitalize()
        
        rel_pattern = ""
        if relation_types:
            rel_types = "|".join(relation_types)
            rel_pattern = f"[r:{rel_types}*1..{depth}]"
        else:
            rel_pattern = f"[r*1..{depth}]"
        
        return f"""
            SELECT * FROM cypher('msp_graph', $$
                MATCH (start:{label} {{id: $start_id}})-{rel_pattern}-(connected)
                RETURN start, relationships(path) as rels, nodes(path) as nodes
            $$) AS (start agtype, rels agtype, nodes agtype);
        """

    def _format_traverse_result(self, rows: tuple) -> Dict[str, Any]:
        """Format graph traversal result."""
        nodes = []
        edges = []
        
        for row in rows:
            if len(row) >= 3:
                nodes_data = row[2]
                rels_data = row[1]
                
                for node_data in nodes_data if isinstance(nodes_data, list) else [nodes_data]:
                    if node_data:
                        node = self._parse_agtype_node(node_data)
                        if node:
                            nodes.append(node)
                
                for rel_data in rels_data if isinstance(rels_data, list) else [rels_data]:
                    if rel_data:
                        edge = self._parse_agtype_edge(rel_data)
                        if edge:
                            edges.append(edge)
        
        return {"nodes": nodes, "edges": edges}

    def _parse_agtype_node(self, agtype_data) -> Optional[Dict]:
        """Parse AGE agtype vertex to dict."""
        try:
            import json
            if hasattr(agtype_data, '__str__'):
                data_str = str(agtype_data)
                if data_str.startswith("'"):
                    data_str = data_str[1:-1]
                return json.loads(data_str)
        except Exception:
            pass
        return None

    def _parse_agtype_edge(self, agtype_data) -> Optional[Dict]:
        """Parse AGE agtype edge to dict."""
        return self._parse_agtype_node(agtype_data)

    async def find_related_servers(
        self, server_id: int, depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Find servers related to a given server (dependency chain)."""
        result = await self.traverse(
            "server", server_id,
            relation_types=["DEPENDS_ON", "RUNS"],
            depth=depth
        )
        
        return [
            node for node in result.get("nodes", [])
            if node.get("type") == GraphNodeType.SERVER
        ]

    async def find_incident_context(
        self, incident_id: int
    ) -> Dict[str, Any]:
        """Find all context around an incident."""
        result = await self.traverse(
            "incident", incident_id,
            depth=3
        )
        
        return {
            "incident": self._get_node_by_type(result.get("nodes", []), GraphNodeType.INCIDENT),
            "related_servers": self._get_nodes_by_type(result.get("nodes", []), GraphNodeType.SERVER),
            "related_documents": self._get_nodes_by_type(result.get("nodes", []), GraphNodeType.DOCUMENT),
            "related_people": self._get_nodes_by_type(result.get("nodes", []), GraphNodeType.PERSON),
            "edges": result.get("edges", [])
        }

    def _get_node_by_type(self, nodes: List[Dict], node_type: str) -> Optional[Dict]:
        """Get first node of specific type."""
        for node in nodes:
            if node.get("type") == node_type:
                return node
        return None

    def _get_nodes_by_type(self, nodes: List[Dict], node_type: str) -> List[Dict]:
        """Get all nodes of specific type."""
        return [node for node in nodes if node.get("type") == node_type]

    async def create_dependency_edge(
        self, from_server_id: int, to_server_id: int
    ) -> bool:
        """Create DEPENDS_ON relationship between servers."""
        try:
            await self.db.execute(text("""
                SELECT * FROM cypher('msp_graph', $$
                    MATCH (s1:Server {id: $from_id})
                    MATCH (s2:Server {id: $to_id})
                    MERGE (s1)-[:DEPENDS_ON]->(s2)
                $$) AS (result agtype);
            """), {
                "from_id": str(from_server_id),
                "to_id": str(to_server_id)
            })
            return True
        except Exception as e:
            logger.error(f"Failed to create dependency edge: {e}")
            return False

    async def create_similarity_edge(
        self, incident1_id: int, incident2_id: int
    ) -> bool:
        """Create SIMILAR_TO relationship between incidents."""
        try:
            await self.db.execute(text("""
                SELECT * FROM cypher('msp_graph', $$
                    MATCH (i1:Incident {id: $id1})
                    MATCH (i2:Incident {id: $id2})
                    MERGE (i1)-[:SIMILAR_TO]->(i2)
                $$) AS (result agtype);
            """), {
                "id1": str(incident1_id),
                "id2": str(incident2_id)
            })
            return True
        except Exception as e:
            logger.error(f"Failed to create similarity edge: {e}")
            return False
