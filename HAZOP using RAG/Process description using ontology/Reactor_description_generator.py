"""
Reactor P&ID Description Generator v2 (Reactor_Description_Generator_v2.py)

Changes from previous version:
 - Do NOT surface ontology classes (e.g., catalyst, safety) unless they are present
   in the RDF AND referenced/connected to the reactor node.
 - Extended ontology extraction to pick up reactor internals: baffles, trays,
   agitators, packing, catalyst_bed, and related datatype/object properties.
 - Inlet/Outlet sections list ONLY equipment names (no instruments, pipings, fittings).
 - Reports internal components detected in the P&ID graph when present.

Dependencies:
    pip install rdflib neo4j
"""

import logging
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set

try:
    from rdflib import Graph
    from rdflib.namespace import RDF, RDFS, OWL
    from neo4j import GraphDatabase, basic_auth
except ImportError as e:
    print(f"Missing dependency: {e}. Install with: pip install rdflib neo4j")
    sys.exit(1)

# ---------- logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("reactor_gen_v2")

# ---------- data models ----------
@dataclass
class Connection:
    source_equipment: str
    source_type: str
    target_equipment: str
    target_type: str
    connection_type: str
    pipeline_name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    source_id: Optional[int] = None
    target_id: Optional[int] = None

@dataclass
class Reactor:
    name: str
    node_id: int
    reactor_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    inlets: List[Connection] = field(default_factory=list)
    outlets: List[Connection] = field(default_factory=list)
    instruments: List[Connection] = field(default_factory=list)
    safety_devices: List[Connection] = field(default_factory=list)
    utilities: List[Connection] = field(default_factory=list)
    control_loops: List[Dict[str, str]] = field(default_factory=list)
    internals: List[Dict[str, Any]] = field(default_factory=list)  # e.g., [{'type':'Baffle','name':'Baffle_1','props':{}}]


@dataclass
class OntologyKnowledge:
    classes: Set[str] = field(default_factory=set)
    class_comments: Dict[str, str] = field(default_factory=dict)
    datatype_props: Dict[str, str] = field(default_factory=dict)
    object_props: Dict[str, Dict[str,str]] = field(default_factory=dict)
    # specific reactor internals discovered in ontology
    internals: Set[str] = field(default_factory=set)
    internal_props: Set[str] = field(default_factory=set)


# ---------- Ontology parser (focused + defensive) ----------
class ReactorOntologyParser:
    def __init__(self, ontology_path: str):
        self.graph = Graph()
        self.path = ontology_path
        self.knowledge = OntologyKnowledge()

    def load(self) -> bool:
        try:
            self.graph.parse(self.path, format="xml")
            logger.info(f"Loaded ontology: {self.path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            return False

    def extract(self) -> OntologyKnowledge:
        # gather class names and comments
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            cls_name = str(cls).split("#")[-1]
            self.knowledge.classes.add(cls_name)
            comment = str(self.graph.value(cls, RDFS.comment) or "")
            if comment:
                self.knowledge.class_comments[cls_name] = comment

            # detect internals by keyword
            lname = cls_name.lower()
            for keyword in ("baffle", "tray", "trays", "agitator", "impeller", "packing", "catalyst_bed", "packing_bed", "sieve", "disc"):
                if keyword in lname:
                    self.knowledge.internals.add(cls_name)

        # datatype properties
        for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            prop_name = str(prop).split("#")[-1]
            rng = str(self.graph.value(prop, RDFS.range) or "")
            self.knowledge.datatype_props[prop_name] = rng
            lname = prop_name.lower()
            for keyword in ("baffle", "agitator", "tray", "impeller", "packing", "bed", "count", "type"):
                if keyword in lname:
                    self.knowledge.internal_props.add(prop_name)

        # object properties
        for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            name = str(prop).split("#")[-1]
            dom = str(self.graph.value(prop, RDFS.domain) or "")
            ran = str(self.graph.value(prop, RDFS.range) or "")
            self.knowledge.object_props[name] = {"domain": dom, "range": ran}
            lname = name.lower()
            for keyword in ("hasbaffle", "has_tray", "hasagitator", "contains", "hasinternal", "haspacking", "has_impeller"):
                if keyword in lname:
                    self.knowledge.internal_props.add(name)

        logger.info("Ontology extraction complete: classes=%d internals=%d props=%d",
                    len(self.knowledge.classes), len(self.knowledge.internals), len(self.knowledge.internal_props))
        return self.knowledge


# ---------- Neo4j connector ----------
class Neo4jConnector:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password 
        self.driver = None

    def connect(self) -> bool:
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=basic_auth(self.user, self.password))
            with self.driver.session() as s:
                s.run("RETURN 1")
            logger.info("Connected to Neo4j")
            return True
        except Exception as e:
            logger.error("Failed to connect to Neo4j: %s", e)
            return False

    def close(self):
        if self.driver:
            self.driver.close()

    def fetch_nodes_and_rels(self):
        nodes = []
        rels = []
        try:
            with self.driver.session() as s:
                q1 = "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props"
                for rec in s.run(q1):
                    nodes.append({'id': rec['id'], 'labels': rec['labels'], 'props': rec['props'] or {}})
                q2 = "MATCH (a)-[r]->(b) RETURN id(a) AS a_id, id(b) AS b_id, type(r) AS type, properties(r) AS props, labels(a) AS a_labels, labels(b) AS b_labels"
                for rec in s.run(q2):
                    rels.append({'source': rec['a_id'], 'target': rec['b_id'], 'type': rec['type'], 'props': rec['props'] or {}, 'src_labels': rec['a_labels'], 'tgt_labels': rec['b_labels']})
            logger.info("Fetched nodes=%d rels=%d", len(nodes), len(rels))
            return nodes, rels
        except Exception as e:
            logger.error("Error fetching from Neo4j: %s", e)
            return [], []


# ---------- Reactor Analyzer (heavier focus on internals + equipment endpoints) ----------
class ReactorAnalyzer:
    def __init__(self, nodes: List[Dict], rels: List[Dict], ontology: OntologyKnowledge):
        # build quick lookups
        self.nodes = {n['id']: n for n in nodes}
        self.rels = rels
        self.incoming = {}  # node_id -> list of source ids
        self.outgoing = {}  # node_id -> list of target ids
        for r in rels:
            s = r['source']
            t = r['target']
            self.outgoing.setdefault(s, []).append((t, r))
            self.incoming.setdefault(t, []).append((s, r))
        self.ontology = ontology

    def _node_name(self, nid: int) -> Optional[str]:
        p = self.nodes.get(nid, {}).get('props', {})
        return p.get('name') or p.get('id') or None

    def identify_reactors(self) -> List[Reactor]:
        reactors = []
        for nid, n in self.nodes.items():
            props = n.get('props', {}) or {}
            labels = [lbl.lower() for lbl in (n.get('labels') or [])]
            ntype = (props.get('type') or "").lower()
            if 'reactor' in ntype or 'reactor' in labels or any(tok in ntype for tok in ('cstr','pfr','packed','packed-bed','packed bed','stirred','plug-flow','plug flow')):
                r = Reactor(name=props.get('name', f"Reactor_{nid}"), node_id=nid, reactor_type=props.get('type',''), properties=props)
                reactors.append(r)
        logger.info("Identified %d reactors", len(reactors))
        return reactors

    def classify_neighbor(self, nid: int) -> str:
        """Classify neighbor node into equipment | instrument | pipe/valve/fitting | internal"""
        node = self.nodes.get(nid, {})
        props = node.get('props', {}) or {}
        labels = [l.lower() for l in (node.get('labels') or [])]  # noqa: E741
        typ = (props.get('type') or "").lower()
        name = props.get('name') or ""
        # internal detection: if label/class matches known internal names from ontology
        for ic in self.ontology.internals:
            if ic.lower() in " ".join(labels) or ic.lower() in typ or ic.lower() in name.lower():
                return "internal"
        # broad heuristics
        if any(k in typ for k in ("valve","fitting","pipe","flange","joint","elbow","tee")) or any(k in " ".join(labels) for k in ("valve","fitting","pipe")):
            return "pipe"
        if any(k in typ for k in ("sensor","transmitter","indicator","controller","alarm","instrument","therm","pressure","flow","level")) or any(k in " ".join(labels) for k in ("sensor","instrument","controller")):
            return "instrument"
        # else treat as equipment
        return "equipment"

    def detect_internals(self, reactor: Reactor):
        # look for neighbors that are internals (object property like HAS_INTERNAL or label matches)
        internals = []
        neighbors = set()
        # neighbors via outgoing and incoming
        for (t, r) in self.outgoing.get(reactor.node_id, []):
            neighbors.add(t)
        for (s, r) in self.incoming.get(reactor.node_id, []):
            neighbors.add(s)
        for nid in neighbors:
            cls = self.classify_neighbor(nid)
            if cls == "internal":
                node = self.nodes.get(nid)
                props = node.get('props', {}) or {}
                internals.append({'type': props.get('type') or ",".join(node.get('labels',[])) or "Internal",
                                  'name': props.get('name') or f"Internal_{nid}",
                                  'props': props})
        reactor.internals = internals

    def collect_stream_end_equipment(self, conn_node_id: int, direction: str='upstream', max_hops: int = 12) -> Optional[str]:
        """
        Starting at node conn_node_id (which might be a pipe, valve, joint, instrument, or equipment),
        traverse upstream (direction='upstream') or downstream to find the first node classified as 'equipment'.
        """
        visited = set()
        frontier = [conn_node_id]
        hops = 0
        while frontier and hops < max_hops:
            next_frontier = []
            for nid in frontier:
                if nid in visited: 
                    continue
                visited.add(nid)
                cls = self.classify_neighbor(nid)
                if cls == 'equipment':
                    return self._node_name(nid) or f"Equipment_{nid}"
                # expand depending on direction
                if direction == 'upstream':
                    for (s, r) in self.incoming.get(nid, []):
                        if s not in visited:
                            next_frontier.append(s)
                else:
                    for (t, r) in self.outgoing.get(nid, []):
                        if t not in visited:
                            next_frontier.append(t)
            frontier = next_frontier
            hops += 1
        return None

    def analyze_connections_for_reactor(self, reactor: Reactor):
        # examine relationships to collect inlets/outlets and instruments, utilities, safety
        for (src, rel) in self.incoming.get(reactor.node_id, []):
            # incoming relationship: src -> reactor
            src_cls = self.classify_neighbor(src)
            src_name = self._node_name(src) or f"Node_{src}"
            conn = Connection(
                source_equipment=src_name,
                source_type=self.nodes.get(src, {}).get('props', {}).get('type', ''),
                target_equipment=reactor.name,
                target_type=reactor.reactor_type,
                connection_type=rel.get('type'),
                pipeline_name=rel.get('props', {}).get('name',''),
                properties=rel.get('props', {}),
                source_id=src,
                target_id=reactor.node_id
            )
            # If src is instrument or pipe/valve, find upstream equipment for the inlet equipment name
            if src_cls == 'equipment':
                reactor.inlets.append(conn)
            else:
                # walk upstream to find equipment endpoint (the FROM equipment)
                equip = self.collect_stream_end_equipment(src, direction='upstream')
                if equip:
                    # represent inbound connection as from equipment
                    conn.source_equipment = equip
                    reactor.inlets.append(conn)
                else:
                    # fallback: do not include instruments/pipes as FROM; attempt to name by resolving neighbor
                    # Only include if upstream equipment cannot be found but src node is itself equipment-like name
                    if src_cls == 'internal':
                        reactor.internals.append({'type': self.nodes[src].get('props', {}).get('type','Internal'),'name': self._node_name(src) or f"Internal_{src}", 'props': self.nodes[src].get('props', {})})
                    else:
                        # skip adding instrument/pipe as inlet equipment
                        pass

        # outgoing relationships: reactor -> tgt
        for (tgt, rel) in self.outgoing.get(reactor.node_id, []):
            tgt_cls = self.classify_neighbor(tgt)
            tgt_name = self._node_name(tgt) or f"Node_{tgt}"
            conn = Connection(
                source_equipment=reactor.name,
                source_type=reactor.reactor_type,
                target_equipment=tgt_name,
                target_type=self.nodes.get(tgt, {}).get('props', {}).get('type',''),
                connection_type=rel.get('type'),
                pipeline_name=rel.get('props', {}).get('name',''),
                properties=rel.get('props', {}),
                source_id=reactor.node_id,
                target_id=tgt
            )
            if tgt_cls == 'equipment':
                reactor.outlets.append(conn)
            else:
                equip = self.collect_stream_end_equipment(tgt, direction='downstream')
                if equip:
                    conn.target_equipment = equip
                    reactor.outlets.append(conn)
                else:
                    if tgt_cls == 'internal':
                        reactor.internals.append({'type': self.nodes[tgt].get('props', {}).get('type','Internal'),'name': self._node_name(tgt) or f"Internal_{tgt}", 'props': self.nodes[tgt].get('props', {})})
                    else:
                        # skip listing instruments/pipes as outlet equipment
                        pass

        # identify instruments and safety/utility devices attached directly to reactor (for separate section)
        for (src, rel) in self.incoming.get(reactor.node_id, []):
            src_cls = self.classify_neighbor(src)
            if src_cls == 'instrument':
                # create instrument-style connection record but keep separate
                p = self.nodes[src].get('props', {}) or {}
                reactor.instruments.append(Connection(source_equipment=p.get('name', f"Instrument_{src}"), source_type=p.get('type','Instrument'), target_equipment=reactor.name, target_type=reactor.reactor_type, connection_type=rel.get('type'), properties=rel.get('props', {}), source_id=src, target_id=reactor.node_id))
            if src_cls == 'internal':
                # collect internal if not already
                node = self.nodes[src]
                p = node.get('props', {}) or {}
                reactor.internals.append({'type': p.get('type') or ",".join(node.get('labels',[])), 'name': p.get('name') or f"Internal_{src}", 'props': p})

        for (tgt, rel) in self.outgoing.get(reactor.node_id, []):
            tgt_cls = self.classify_neighbor(tgt)
            if tgt_cls == 'instrument':
                p = self.nodes[tgt].get('props', {}) or {}
                reactor.instruments.append(Connection(source_equipment=reactor.name, source_type=reactor.reactor_type, target_equipment=p.get('name', f"Instrument_{tgt}"), target_type=p.get('type','Instrument'), connection_type=rel.get('type'), properties=rel.get('props', {}), source_id=reactor.node_id, target_id=tgt))
            if tgt_cls == 'internal':
                node = self.nodes[tgt]
                p = node.get('props', {}) or {}
                reactor.internals.append({'type': p.get('type') or ",".join(node.get('labels',[])), 'name': p.get('name') or f"Internal_{tgt}", 'props': p})

    def detect_control_loops(self, reactor: Reactor):
        # Heuristic: find instrument nodes connected to reactor which send signals to controller nodes which control valves/actuators
        for inst_conn in reactor.instruments:
            inst_id = inst_conn.source_id if inst_conn.source_equipment != reactor.name else inst_conn.target_id
            if not inst_id:
                continue
            # find outgoing relationships from instrument
            for (t, rel) in self.outgoing.get(inst_id, []):
                rtype = rel.get('type','').lower()
                if 'send' in rtype or 'signal' in rtype or 'reports_to' in rtype:
                    # t likely controller
                    ctrl_node = self.nodes.get(t)
                    if ctrl_node:
                        ctrl_name = ctrl_node.get('props',{}).get('name') or f"Controller_{t}"
                        # find what controller controls
                        for (tt, r2) in self.outgoing.get(t, []):
                            if 'controls' in r2.get('type','').lower() or 'actu' in r2.get('type','').lower():
                                act_name = self.nodes.get(tt,{}).get('props',{}).get('name') or f"Actuator_{tt}"
                                reactor.control_loops.append({'sensor': self.nodes.get(inst_id,{}).get('props',{}).get('name', f"Sensor_{inst_id}"),
                                                              'controller': ctrl_name,
                                                              'actuator': act_name})
        # deduplicate loops
        unique = []
        seen = set()
        for l in reactor.control_loops:  # noqa: E741
            key = (l['sensor'], l['controller'], l['actuator'])
            if key not in seen:
                seen.add(key)
                unique.append(l)
        reactor.control_loops = unique

    def analyze_all(self, reactors: List[Reactor]):
        for r in reactors:
            self.detect_internals(r)  # internals from ontology-class match or labels
            self.analyze_connections_for_reactor(r)
            self.detect_control_loops(r)


# ---------- Utility: attach backtracking (same as before, defensive) ----------
def attach_backtracking(NeoClass):
    def backtrack_chemicals(self, reactor_name: str, direction: str = 'upstream') -> List[Dict[str,Any]]:
        # simple pattern: try to find Chemical nodes connected to equipment upstream/downstream
        """
        Track ALL chemicals entering and leaving the reactor.
        Returns dict with keys: {"upstream": [...], "downstream": [...]}
        """
        results = {"upstream": [], "downstream": []}
        try:
            with self.driver.session() as s:
                # --- FEED CHEMICALS (upstream) ---
                q_up = """
                MATCH (chem:Chemical)-[:INLET|:FEEDS|:SUPPLIES|:PRODUCES*1..4]->(rc:Equipment {name:$name})
                RETURN DISTINCT chem.name AS cname
                """
                res_up = s.run(q_up, name=reactor_name)
                results["upstream"] = [r["cname"] for r in res_up if r["cname"]]
    
                # --- PRODUCT CHEMICALS (downstream) ---
                q_dn = """
                MATCH (rc:Equipment {name:$name})-[:OUTLET|:DISCHARGES|:FEEDS|:PRODUCES*1..4]->(chem:Chemical)
                RETURN DISTINCT chem.name AS cname
                """
                res_dn = s.run(q_dn, name=reactor_name)
                results["downstream"] = [r["cname"] for r in res_dn if r["cname"]]
    
        except Exception as e:
            logger.error(f"Chemical backtracking failed: {e}")
    
        return results
    setattr(NeoClass, "backtrack_chemicals", backtrack_chemicals)


# ---------- Generator: create textual report obeying user's constraints ----------
class ReactorDescriptionGenerator:
    def __init__(self, neo_conn: Neo4jConnector, ontology: OntologyKnowledge):
        self.neo = neo_conn
        self.ontology = ontology

    def produce(self, output_path: str = "reactor_descriptions_v2.txt"):
        nodes, rels = self.neo.fetch_nodes_and_rels()
        if not nodes:
            logger.error("No nodes fetched.")
            return
        analyzer = ReactorAnalyzer(nodes, rels, self.ontology)
        reactors = analyzer.identify_reactors()
        if not reactors:
            logger.warning("No reactors found.")
            return
        analyzer.analyze_all(reactors)

        lines = []
        lines.append("REACTOR DESCRIPTIONS (v2)")
        lines.append("="*80)
        lines.append(f"Total Reactors: {len(reactors)}\n")
        for r in reactors:
            lines.extend(self._describe_reactor(r))
            lines.append("\n" + "-"*80 + "\n")

        text = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote reactor descriptions to {output_path}")
        print(text[:1400])  # sample output

    def _describe_reactor(self, r: Reactor) -> List[str]:
        out = []
        out.append(f"REACTOR: {r.name}")
        out.append(f"Node ID: {r.node_id}")
        out.append(f"Reactor Type: {r.reactor_type or 'Not specified'}")
        # properties (only if present)
        if r.properties:
            out.append("\nProperties:")
            for k, v in r.properties.items():
                if k.lower() in ('name','type'):
                    continue
                out.append(f"  - {k}: {v}")

        # internals: only show internals discovered in graph or matching ontology internals
        if r.internals:
            out.append("\nINTERNAL COMPONENTS (detected):")
            for idx, it in enumerate(r.internals, 1):
                typ = it.get('type','Internal')
                name = it.get('name')
                props = it.get('props', {})
                out.append(f"  {idx}. {name} ({typ})")
                # print internal-specific props if available (e.g., tray_count, agitator_type, baffle_count)
                for pk, pv in props.items():
                    if pk.lower() in ('name','type'): 
                        continue
                    # only show properties that look related to internals
                    if any(tok in pk.lower() for tok in ('tray','baffle','agitator','impeller','packing','bed','count','type')):
                        out.append(f"     - {pk}: {pv}")

        # process role (concise)
        out.append("\nPROCESS ROLE / FUNCTION:")
        tl = (r.reactor_type or "").lower()
        if any(tok in tl for tok in ('cstr','stirred','stirred tank')):
            out.append("  - Continuous stirred-tank reactor: mixing-driven, likely liquid phase; internal mixing device may exist (agitator).")
        elif any(tok in tl for tok in ('packed','packed-bed','packed bed')):
            out.append("  - Packed bed reactor: likely contains packing or catalyst bed (internal packing/catalyst bed).")
        elif any(tok in tl for tok in ('pfr','plug','plug-flow','tube')):
            out.append("  - Plug-flow / tubular reactor: axial flow behavior; internals typically minimal.")
        else:
            out.append("  - Reaction vessel / reactor: check internals section for detailed mechanical internals.")

        # INLET STREAMS: ONLY equipment names (upstream equipment)
        out.append("\nINLET STREAMS (equipment sources only):")
        if r.inlets:
            seen = set()
            for i, c in enumerate(r.inlets, 1):
                equip = c.source_equipment or self._resolve_equipment_name(c.source_id)
                if not equip: 
                    continue
                if equip in seen:
                    continue
                seen.add(equip)
                out.append(f"  {i}. FROM EQUIPMENT: {equip}")
        else:
            out.append("  - No inlet equipment identified.")

        # OUTLET STREAMS: ONLY equipment names (downstream equipment)
        out.append("\nOUTLET STREAMS (equipment sinks only):")
        if r.outlets:
            seen = set()
            for i, c in enumerate(r.outlets, 1):
                equip = c.target_equipment or self._resolve_equipment_name(c.target_id, downstream=True)
                if not equip: 
                    continue
                if equip in seen: 
                    continue
                seen.add(equip)
                out.append(f"  {i}. TO EQUIPMENT: {equip}")
        else:
            out.append("  - No outlet equipment identified.")

        # inferred feeds (try Neo4j backtracking but only list chemical names)
        chem_data = self.neo.backtrack_chemicals(r.name)

        if chem_data["upstream"]:
            out.append("\nINFERRED FEED CHEMICALS (from upstream):")
            for n in sorted(set(chem_data["upstream"])):
                out.append(f"  - {n}")
        else:
            out.append("\nINFERRED FEED CHEMICALS: none detected")
        
        if chem_data["downstream"]:
            out.append("\nINFERRED PRODUCT CHEMICALS (downstream):")
            for n in sorted(set(chem_data["downstream"])):
                out.append(f"  - {n}")
        else:
            out.append("\nINFERRED PRODUCT CHEMICALS: none detected")
        

        # Instruments & control (kept separate)
        out.append("\nINSTRUMENTATION & CONTROL (separate):")
        if r.instruments:
            seen = set()
            for c in r.instruments:
                name = c.source_equipment if c.source_equipment != r.name else c.target_equipment
                typ = c.source_type if c.source_equipment != r.name else c.target_type
                if name in seen: 
                    continue
                seen.add(name)
                out.append(f"  - {name} ({typ})")
        else:
            out.append("  - None identified")

        if r.control_loops:
            out.append("\nINFERRED CONTROL LOOPS:")
            for loop in r.control_loops:
                out.append(f"  - Sensor: {loop['sensor']} -> Controller: {loop['controller']} -> Actuator: {loop['actuator']}")

        # Utilities and safety: only mention if present and connected (but user asked not to introduce unrelated safety terms)
        if r.utilities:
            out.append("\nUTILITY CONNECTIONS (detected):")
            for u in r.utilities:
                out.append(f"  - {u.source_equipment if u.source_equipment != r.name else u.target_equipment} (props: {u.properties})")

        if r.safety_devices:
            out.append("\nSAFETY DEVICES (detected):")
            for s in r.safety_devices:
                out.append(f"  - {s.source_equipment if s.source_equipment != r.name else s.target_equipment} (type: {s.target_type if s.target_equipment!=r.name else s.source_type})")

        # Process parameter hints (only report what is present)
        out.append("\nPROCESS PARAMETERS / ENGINEERING REMARKS:")
        vol = r.properties.get('volume') or r.properties.get('Volume') or r.properties.get('capacity') or r.properties.get('Volume_m3')
        if vol:
            out.append(f"  - Vessel volume: {vol}")
        else:
            out.append("  - Vessel volume: not specified in graph properties")

        # process integration summary: list named upstream and downstream equipment
        up_equip = []
        for c in r.inlets:
            if c.source_equipment:
                up_equip.append(c.source_equipment)
        dn_equip = []
        for c in r.outlets:
            if c.target_equipment:
                dn_equip.append(c.target_equipment)
        if up_equip:
            out.append("\nPROCESS INTEGRATION (summary):")
            out.append("  - Receives feed from: " + ", ".join(sorted(set(up_equip))))
        if dn_equip:
            if not up_equip:
                out.append("\nPROCESS INTEGRATION (summary):")
            out.append("  - Supplies: " + ", ".join(sorted(set(dn_equip))))

        # Ontology-sourced internal properties: include only if present in ontology and referenced in reactor internals
        ont_ints = []
        for i in r.internals:
            # include internal only if ontology flagged similar class OR its props contain internal-related keys
            name = i.get('name')
            typ = i.get('type', '')
            if any(ic.lower() in typ.lower() for ic in self.ontology.internals) or any(pk.lower() in " ".join(i.get('props',{}).keys()).lower() for pk in self.ontology.internal_props):
                ont_ints.append(i)
        if ont_ints:
            out.append("\nONTOLOGY-REFERENCED INTERNALS:")
            for i in ont_ints:
                out.append(f"  - {i['name']} ({i['type']})")
                for pk, pv in i.get('props', {}).items():
                    if pk.lower() in ('name','type'): 
                        continue
                    if any(tok in pk.lower() for tok in ('baffle','tray','agitator','impeller','packing','bed','count','type')):
                        out.append(f"     - {pk}: {pv}")

        return out

    def _resolve_equipment_name(self, node_id: Optional[int], downstream: bool=False) -> Optional[str]:
        # wrapper to find equipment using ReactorAnalyzer's traversal heuristics
        # Minimal attempt: walk neighbors once to find node classified as equipment
        if node_id is None: 
            return None
        # use short BFS built here
        visited = set([node_id])
        frontier = [node_id]
        hops = 0
        while frontier and hops < 8:
            next_f = []
            for nid in frontier:
                n = self.neo.driver # placeholder to satisfy type checking  # noqa: F841
                # find incoming/outgoing based on downstream flag
                # We can't call ReactorAnalyzer methods here without building more object; keep simple by calling Neo4j to fetch neighbors
                try:
                    with self.neo.driver.session() as s:
                        if downstream:
                            q = "MATCH (n) WHERE id(n)=$id OPTIONAL MATCH (n)-[r]->(m) RETURN id(m) AS idm, labels(m) AS labels, properties(m) AS props LIMIT 50"
                            res = s.run(q, id=nid)
                            for rec in res:
                                mid = rec['idm']
                                if mid is None:
                                    continue
                                props = rec['props'] or {}
                                labels = [l.lower() for l in (rec['labels'] or [])]  # noqa: E741
                                typ = (props.get('type') or "").lower()
                                name = props.get('name')
                                if name and (('equipment' in labels) or ('reactor' in typ) or ('tank' in typ) or ('column' in typ) or ('heater' in typ)):
                                    return name
                                if mid not in visited:
                                    next_f.append(mid)
                                    visited.add(mid)
                        else:
                            q = "MATCH (n) WHERE id(n)=$id OPTIONAL MATCH (m)-[r]->(n) RETURN id(m) AS idm, labels(m) AS labels, properties(m) AS props LIMIT 50"
                            res = s.run(q, id=nid)
                            for rec in res:
                                mid = rec['idm']
                                if mid is None: 
                                    continue
                                props = rec['props'] or {}
                                labels = [l.lower() for l in (rec['labels'] or [])]  # noqa: E741
                                typ = (props.get('type') or "").lower()
                                name = props.get('name')
                                if name and (('equipment' in labels) or ('reactor' in typ) or ('tank' in typ) or ('column' in typ) or ('heater' in typ)):
                                    return name
                                if mid not in visited:
                                    next_f.append(mid)
                                    visited.add(mid)
                except Exception:
                    # if anything fails, bail out — this resolver is best-effort only
                    return None
            frontier = next_f
            hops += 1
        return None


# ---------- main ----------
def main():
    # CONFIG - change to match your environment
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "Ontocape@123"   # <-- update
    ONTOLOGY_PATH = "Ontology/Reactor Ontology.rdf"
    OUTPUT_PATH = "Results/reactor_descriptions.txt"

    neo = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    attach_backtracking(Neo4jConnector)  # add backtracking
    if not neo.connect():
        logger.error("Neo4j connection failed. Exiting.")
        return

    parser = ReactorOntologyParser(ONTOLOGY_PATH)
    if not parser.load():
        logger.warning("Ontology load failed; continuing without ontology-derived internals.")
        ontology = OntologyKnowledge()
    else:
        ontology = parser.extract()

    gen = ReactorDescriptionGenerator(neo, ontology)
    gen.produce(output_path=OUTPUT_PATH)
    neo.close()


if __name__ == "__main__":
    main()
