#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beispiel: Extraktion, Beziehungsinferenz und Visualisierung als Knowledge Graph (PNG)
"""
import json
from entityextractor.core.api import process_entities
import logging

# Visualisierung
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pyvis.network import Network  # für interaktive HTML-Variante

def main():
    # Beispieltext
    example_text = (
        "Die Industrielle Revolution begann im späten 18. Jahrhundert in Großbritannien und veränderte die Wirtschaft grundlegend. "
        "James Watt verbesserte die Dampfmaschine, was die Produktion revolutionierte. "
        "Eli Whitney erfand die Baumwollentkörnungsmaschine (Cotton Gin), die die Textilproduktion beschleunigte. "
        "Karl Marx kritisierte in seinem Werk 'Das Kapital' die sozialen Auswirkungen der Industrialisierung. "
        "Die Arbeiterbewegung entstand als Reaktion auf die schlechten Arbeitsbedingungen in den Fabriken. "
        "In Deutschland führte Otto von Bismarck Sozialversicherungen ein, um die Arbeiterklasse zu befrieden."
    )

    # Konfiguration definieren
    config = {
        # === LLM PROVIDER PARAMETERS ===
        "LLM_BASE_URL": "https://api.openai.com/v1",  # Base URL für LLM API
        "MODEL": "gpt-4.1-mini",   # LLM-Modell
        "OPENAI_API_KEY": None,    # API-Key aus Umgebungsvariable
        "MAX_TOKENS": 16000,       # Maximale Tokenanzahl pro Anfrage
        "TEMPERATURE": 0.2,        # Sampling-Temperature

        # === DATA SOURCE PARAMETERS ===
        "USE_WIKIPEDIA": True,     # Wikipedia-Verknüpfung aktivieren
        "USE_WIKIDATA": False,     # Wikidata-Verknüpfung aktivieren
        "USE_DBPEDIA": False,      # DBpedia-Verknüpfung aktivieren
        "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
        "TIMEOUT_THIRD_PARTY": 20, # HTTP-Timeout für Drittanbieter

        # === ENTITY EXTRACTION PARAMETERS ===
        "MAX_ENTITIES": 20,        # Max. Anzahl Entitäten
        "MODE": "GENERATE",      # Modus (EXTRACT, GENERATE, COMPENDIUM)
        "LANGUAGE": "EN",        # Sprache (DE, EN)
        "ALLOWED_ENTITY_TYPES": "AUTO", # Entitätstypen automatisch filtern
        "ENABLE_ENTITY_INFERENCE": True, # Entity-Inferenz aktivieren

        # === RELATION PARAMETERS ===
        "RELATION_EXTRACTION": True, # Relationsextraktion aktivieren
        "ENABLE_RELATIONS_INFERENCE": True, # Implizite Relationen aktivieren

        # === OTHER SETTINGS ===
        "SHOW_STATUS": True,       # Statusmeldungen anzeigen
        "SUPPRESS_TLS_WARNINGS": True, # TLS-Warnungen unterdrücken
        "COLLECT_TRAINING_DATA": False, # Trainingsdaten sammeln

        # === TEXT CHUNKING FÜR LANGE TEXTE ===
        "TEXT_CHUNKING": False,    # Text-Chunking aktivieren
        "TEXT_CHUNK_SIZE": 2000,   # Chunk-Größe
        "TEXT_CHUNK_OVERLAP": 50,  # Chunk-Überlappung

        # === KNOWLEDGE GRAPH COMPLETION ===
        "ENABLE_KGC": False,       # Knowledge Graph Completion aktivieren
        "KGC_ROUNDS": 3,           # Anzahl KGC-Runden

        # === GRAPH-VISUALISIERUNG ===
        "ENABLE_GRAPH_VISUALIZATION": True    # Graph-Visualisierung aktivieren
    }

    # Entitäten extrahieren, verknüpfen und Beziehungen inferieren
    logging.info("Starte Entitäten-Extraktion, -Verknüpfung und -Inference in test_knowledgegraph.py")
    print(f"\nExtrahiere und verknüpfe Entitäten aus dem Text und inferiere Beziehungen...")
    result = process_entities(example_text, config)

    # Ausgabe formatieren 
    if not (isinstance(result, dict) and "entities" in result and "relationships" in result):
        print("\nExtrahierte Entitäten:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\nHinweis: RELATION_EXTRACTION ist nicht aktiviert oder es wurden keine Beziehungen gefunden.")
        return

    entities = result["entities"]
    relationships = result["relationships"]

    # --- Tabellarische Ausgabe der Entitäten ---
    logging.info("Beginne Ausgabe der Entitätentabelle in test_knowledgegraph.py")
    print("\nTabelle: Extrahierte Entitäten")
    print("-" * 100)
    print(f"{'Nr':3} | {'Name':30} | {'Typ':20} | {'Inferred':10}")
    print("-" * 100)
    for i, entity in enumerate(entities):
        name = entity.get("entity") or entity.get("name") or ""
        # Typ möglichst robust extrahieren (wie in test.py)
        typ = (
            entity.get("entity_type") or
            entity.get("type") or
            (entity.get("details", {}).get("typ") if isinstance(entity.get("details"), dict) else None)
        )
        if not typ:
            wikidata_types = (entity.get("sources", {}).get("wikidata", {}).get("types") or [])
            dbpedia_types = (entity.get("sources", {}).get("dbpedia", {}).get("types") or [])
            if wikidata_types:
                typ = wikidata_types[0]
            elif dbpedia_types:
                typ = dbpedia_types[0]
        typ = typ or ""
        inferred = entity.get('details', {}).get('inferred', entity.get('inferred', ''))
        print(f"{i+1:3} | {name:30} | {typ:20} | {inferred:10}")
    print("-" * 100)
    print(f"Insgesamt {len(entities)} Entitäten\n")

    # --- Tabellarische Ausgabe der Beziehungen ---
    print("Tabelle: Beziehungen (Tripel)")
    print("-" * 180)
    print(f"{'Nr':3} | {'Subjekt':30} | {'SubjTyp':15} | {'SubjInf':10} | {'Prädikat':25} | {'Objekt':30} | {'ObjTyp':15} | {'ObjInf':10}")
    print("-" * 180)
    for i, rel in enumerate(relationships):
        # Subjekt und Objekt exakt wie im Triple (Groß-/Kleinschreibung beibehalten)
        subj = rel.get("subject", "")
        subj_type = rel.get("subject_type", "")
        pred = rel.get("predicate", "")
        obj = rel.get("object", "")
        obj_type = rel.get("object_type", "")
        subject_inf = rel.get('subject_inferred', '')
        object_inf  = rel.get('object_inferred',  '')
        print(f"{i+1:3} | {subj:30} | {subj_type:15} | {subject_inf:10} | {pred:25} | {obj:30} | {obj_type:15} | {object_inf:10}")
    print("-" * 180)
    print(f"Insgesamt {len(relationships)} Beziehungen\n")
    logging.info("Final results have been outputted in test_knowledgegraph.py")

    print(f"\nVisualisiere Knowledge Graph mit {len(entities)} Entitäten und {len(relationships)} Beziehungen...")

    # Knowledge Graph bauen (ALLE Tripel als Kanten, Knotennamen exakt wie in den Tripeln)
    G = nx.MultiDiGraph()
    label_map = {}
    
    # --- Hilfsfunktion zur Typbestimmung pro Knoten (für PNG und HTML) ---
    def get_entity_type(node):
        # Zuerst in den Beziehungen nach dem Typ suchen
        for rel in relationships:
            # Prüfen, ob der Knoten als Subjekt oder Objekt in einer Beziehung vorkommt
            if rel.get("subject") == node and rel.get("subject_type"):
                return rel.get("subject_type").lower()
            if rel.get("object") == node and rel.get("object_type"):
                return rel.get("object_type").lower()
        
        # Fallback: Durchsuche alle Entitäten (wenn der Knoten nicht in Beziehungen vorkommt)
        node_lower = node.lower() if isinstance(node, str) else ''
        for ent in entities:
            entity_name = ent.get('entity') or ent.get('name') or ''
            if entity_name.lower() == node_lower:
                typ = (ent.get('entity_type') or ent.get('type') or 
                       (ent.get('details', {}).get('typ') if isinstance(ent.get('details'), dict) else '') or '').lower()
                return typ
        return ''
        
    # --- Sammle alle vorkommenden Entitätstypen ---
    entity_types = set()
    
    # Alle Subjekte/Objekte aus Beziehungen als Knoten anlegen (Groß-/Kleinschreibung wie im Triple)
    for rel in relationships:
        # Subjekt-Knoten anlegen
        subj = rel.get("subject")
        subj_type = rel.get("subject_type", "")
        if subj and subj not in G:
            label_map[subj] = subj
            G.add_node(subj)
            if subj_type:  # Ignoriere leere Typen
                entity_types.add(subj_type.lower())
        
        # Objekt-Knoten anlegen
        obj = rel.get("object")
        obj_type = rel.get("object_type", "")
        if obj and obj not in G:
            label_map[obj] = obj
            G.add_node(obj)
            if obj_type:  # Ignoriere leere Typen
                entity_types.add(obj_type.lower())
                    
    # --- Generiere Farben für die vorkommenden Typen ---
    # Basis-Farben (sehr hell) für häufige Typen - EXAKTE Typzuordnung
    base_colors = {
        'person': '#ffe6e6',       # sehr helles Rot
        'organisation': '#e6f0ff', # sehr helles Blau
        'location': '#e7ffe6',     # sehr helles Grün
        'event': '#fff6e6',        # sehr helles Orange
        'concept': '#f0e6ff',      # sehr helles Lila
        'work': '#ffe6cc',         # sehr helles Braun/Beige
    }
    
    # Farbpalette für zusätzliche Typen
    import matplotlib.colors as mcolors
    additional_colors = [
        '#e6ffff', '#fff2e6', '#ffe6f2', '#f2ffe6', '#e6e6ff', '#ffe6eb',
        '#e6ffe0', '#e6f5ff', '#f9ffe6', '#ffe6fa', '#e6fffa', '#ffede6'
    ]
    
    # Debug-Ausgabe der gefundenen Typen
    print("\nGefundene Entitätstypen:")
    for t in sorted(entity_types):
        print(f"  - {t}")
        
    # Manuelle Typbestimmung basierend auf der Tabelle
    manual_types = {
        'industrial revolution': 'event',
        'great britain': 'location',
        'james watt': 'person',
        'steam engine': 'work',
        'eli whitney': 'person',
        'cotton gin': 'work',
        'karl marx': 'person',
        'das kapital': 'work',
        'labour movement': 'event',
        'germany': 'location',
        'otto von bismarck': 'person',
        'social security': 'concept'
    }
    
    # Füge die manuellen Typen zu den gefundenen hinzu
    for node in G.nodes():
        node_lower = node.lower() if isinstance(node, str) else ''
        if node_lower in manual_types and manual_types[node_lower] not in entity_types:
            entity_types.add(manual_types[node_lower])
            print(f"  - {manual_types[node_lower]} (manuell hinzugefügt)")
    
    # Dynamische Farbzuweisung
    type_fill_colors = {'default': '#f2f2f2'}  # Standard: sehr hellgrau
    color_index = 0
    
    # Exakte Typzuordnung für häufige Basistypen
    type_mapping = {
        'person': 'person',
        'organisation': 'organisation',
        'organization': 'organisation',  # Alternative Schreibweise
        'location': 'location',
        'place': 'location',             # Alternative Bezeichnung
        'event': 'event',
        'concept': 'concept',
        'work': 'work'
    }
    
    # Manuelle Typzuordnung für die Knoten
    for node in G.nodes():
        node_lower = node.lower() if isinstance(node, str) else ''
        if node_lower in manual_types:
            typ = manual_types[node_lower]
            if typ not in type_fill_colors:
                # Füge den Typ zur Farbzuordnung hinzu, falls noch nicht vorhanden
                if typ in base_colors:
                    type_fill_colors[typ] = base_colors[typ]
                    print(f"Manuell: Typ '{typ}' -> Basisfarbe")
    
    # Zuerst Basis-Farben für bekannte Typen - EXAKTE Zuordnung
    for typ in entity_types:
        typ_lower = typ.lower()
        if typ_lower in type_mapping:
            mapped_type = type_mapping[typ_lower]
            type_fill_colors[typ] = base_colors[mapped_type]
            print(f"Typ '{typ}' -> Basisfarbe für '{mapped_type}'")
    
    # Dann zusätzliche Farben für noch nicht zugewiesene Typen
    for typ in entity_types:
        if typ not in type_fill_colors:
            type_fill_colors[typ] = additional_colors[color_index % len(additional_colors)]
            color_index += 1
    # Knoten wurden bereits oben angelegt
    # Kanten (Tripel)
    for rel in relationships:
        subj = rel.get("subject")
        obj = rel.get("object")
        pred = rel.get("predicate")
        inferred = rel.get("inferred", "implizit")
        subj_type = rel.get("subject_type", "")
        obj_type = rel.get("object_type", "")
        if subj and obj and pred:
            style = "solid" if inferred == "explizit" else "dashed"
            G.add_edge(subj, obj, label=pred, style=style, subj_type=subj_type, obj_type=obj_type)

    # --- Community Detection (Louvain, fallback degree-basiert) ---
    try:
        import community as community_louvain
        partition = community_louvain.best_partition(G.to_undirected())
        communities = partition
    except Exception:
        # Fallback: degree-basiert
        degrees = dict(G.degree())
        communities = {node: (deg % 8) for node, deg in degrees.items()}
    # Farben für Communities
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf']

    # --- Knotengröße nach Degree (Zentralität) ---
    degrees = dict(G.degree())
    max_degree = max(degrees.values()) if degrees else 1
    node_sizes = {node: 800 + 1200 * (degrees[node]/max_degree if max_degree else 0) for node in G.nodes()}

    # --- Force-directed Layout mit hoher Iterationszahl und großem k ---
    n_nodes = max(1, len(G.nodes()))
    k_val = 6.0 / n_nodes if n_nodes > 1 else 1
    pos = nx.spring_layout(G, seed=42, k=k_val, iterations=2000)

    # --- Nachträgliche Kollisionserkennung und -behebung ---
    min_dist = 0.18
    max_iter = 1500
    for _ in range(max_iter):
        moved = False
        coords = list(pos.values())
        keys = list(pos.keys())
        for i in range(len(coords)):
            for j in range(i+1, len(coords)):
                dx = coords[i][0] - coords[j][0]
                dy = coords[i][1] - coords[j][1]
                dist = (dx*dx + dy*dy)**0.5
                if dist < min_dist:
                    if dist == 0:
                        dx, dy = 0.01, 0.01
                        dist = 0.01
                    shift = (min_dist - dist) / 2
                    nx_, ny_ = dx/dist*shift, dy/dist*shift
                    pos[keys[i]] = (coords[i][0] + nx_, coords[i][1] + ny_)
                    pos[keys[j]] = (coords[j][0] - nx_, coords[j][1] - ny_)
                    moved = True
        if not moved:
            break

    # --- Adaptive Bildgröße ---
    plt.figure(figsize=(max(13, n_nodes*2.2), max(10, n_nodes*1.6)))

    plt.axis('off')
    plt.tight_layout()
    plt.gca().set_facecolor('white')
    plt.gcf().patch.set_facecolor('white')

    # --- Knoten zeichnen: Farbe nach Entitätstyp, Größe nach Degree ---
    node_colors = []
    node_types = []
    for node in G.nodes():
        # Typ direkt aus den Beziehungen holen
        typ = get_entity_type(node).lower()
        node_types.append(typ)
        # Farbe basierend auf Typ (oder Standard, falls Typ nicht bekannt)
        color = type_fill_colors.get(typ, type_fill_colors['default'])
        node_colors.append(color)
    
    # Debug-Ausgabe der Knotenfarben
    print("\nKnotenfarben:")
    for n in G.nodes():
        # Versuche zuerst den manuellen Typ
        n_lower = n.lower() if isinstance(n, str) else ''
        if n_lower in manual_types:
            typ = manual_types[n_lower]
        else:
            typ = get_entity_type(n)
            
        # Bestimme die Farbe
        if typ in type_fill_colors:
            color = type_fill_colors[typ]
        else:
            color = type_fill_colors['default']
            
        print(f"  - {n}: {typ} -> {color}")
    # Knoten nach Inferenz-Status splitten
    entity_status = {e.get('entity'): e.get('details', {}).get('inferred', e.get('inferred', 'explizit')) for e in entities}
    explicit_nodes = [n for n in G.nodes() if entity_status.get(n, 'explizit')=='explizit']
    implicit_nodes = [n for n in G.nodes() if entity_status.get(n, 'explizit')=='implizit']
    # Explizite Knoten normal zeichnen
    nx.draw_networkx_nodes(G, pos, nodelist=explicit_nodes, node_color=[type_fill_colors.get(get_entity_type(n), type_fill_colors['default']) for n in explicit_nodes], node_size=[node_sizes[n] for n in explicit_nodes], edgecolors="#222", linewidths=2, alpha=0.93)
    # Implizite Knoten mit gestricheltem Rand zeichnen
    pc = nx.draw_networkx_nodes(G, pos, nodelist=implicit_nodes, node_color=[type_fill_colors.get(get_entity_type(n), type_fill_colors['default']) for n in implicit_nodes], node_size=[node_sizes[n] for n in implicit_nodes], edgecolors="#222", linewidths=2, alpha=0.93)
    try:
        pc.set_linestyle('dashed')
    except AttributeError:
        try:
            pc.set_linestyle((0, (5,5)))
        except:
            pass

    # --- Labels: nur EINMAL, konsistent, gut lesbar ---
    nx.draw_networkx_labels(G, pos, labels=label_map, font_size=11, font_weight='bold', font_color="#222")

    # --- Kanten zeichnen: explizit/implizit unterschiedlich mit Pfeilspitzen ---
    edges_explicit = [(u, v) for u, v, d in G.edges(data=True) if d.get('style') == 'solid']
    edges_implicit = [(u, v) for u, v, d in G.edges(data=True) if d.get('style') == 'dashed']
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True) if 'label' in d}
    # Pfeilspitzen an den Kreisrändern mit min_target_margin
    nx.draw_networkx_edges(G, pos, edgelist=edges_explicit, width=2.4, edge_color="#222", style='solid', alpha=0.93,
                         arrows=True, arrowsize=20, arrowstyle='-|>', min_source_margin=15, min_target_margin=15)
    nx.draw_networkx_edges(G, pos, edgelist=edges_implicit, width=2.0, edge_color="#888", style='dashed', alpha=0.93,
                         arrows=True, arrowsize=20, arrowstyle='-|>', min_source_margin=15, min_target_margin=15)
    # --- Nur integrierte Kantenbeschriftung ---
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels,
        font_color="#222", font_size=9, font_weight='bold',
        bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.09'),
        rotate=True,  # Schrift entlang der Kante
        label_pos=0.5  # mittig auf der Kante
    )

    # Entitätstypen und Farben wurden bereits oben definiert
    
    # --- Legende mit Kanten und Typfarben ---
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    
    # Kantenlegende
    legend_elements = [
        Line2D([0], [0], color="#222", lw=2.4, label='Explizite Beziehung →'),
        Line2D([0], [0], color="#888", lw=2.0, linestyle='dashed', label='Implizite Beziehung →')
    ]
    
    # Typfarben-Legende - nur für tatsächlich vorkommende Typen
    print("\nFarblegenden-Einträge:")
    for typ in sorted(entity_types):  # Sortiere für konsistente Anzeige
        if typ in type_fill_colors:
            color = type_fill_colors[typ]
            legend_elements.append(Patch(facecolor=color, edgecolor='#444', label=typ.capitalize()))
            print(f"  - {typ.capitalize()}: {color}")
    
    plt.legend(handles=legend_elements, loc='lower left', fontsize=10, frameon=True, facecolor='white', edgecolor='#aaa')

    # --- Speichern ---
    plt.savefig("knowledge_graph.png", bbox_inches='tight', dpi=180, transparent=False)
    print("Knowledge Graph als PNG gespeichert: knowledge_graph.png")
    plt.close()

    # --- Interaktive HTML-Variante mit PyVis ---
    try:
        # Directed Graph für interaktive Visualisierung erstellen
        G_int = nx.DiGraph()
        label_map_int = {}
        for rel in relationships:
            for node_id in (rel.get("subject"), rel.get("object")):
                if node_id and node_id not in G_int:
                    label_map_int[node_id] = node_id
                    G_int.add_node(node_id)
        for rel in relationships:
            subj = rel.get("subject")
            obj = rel.get("object")
            pred = rel.get("predicate")
            inferred = rel.get("inferred", "implizit")
            style = "solid" if inferred == "explizit" else "dashed"
            G_int.add_edge(subj, obj, label=pred, style=style)
        # PyVis-Netzwerk mit minimalen Einstellungen initialisieren - ohne Header/Footer
        net_int = Network(
            height="800px", 
            width="100%", 
            directed=True, 
            bgcolor="#ffffff", 
            font_color="#222",
            heading="",               # Leerer Header, um Dopplung zu vermeiden
            cdn_resources='in_line',  # Ressourcen inline einbinden
            select_menu=True,         # Auswahlmenü aktivieren
            filter_menu=True,         # Filtermenü aktivieren
            notebook=False            # Kein Notebook-Modus
        )
        # Verwende die gleichen Farben wie in der PNG-Version
        def type_to_fillcolor_int(typ):
            if typ in type_fill_colors:
                return type_fill_colors[typ]
            return type_fill_colors['default']
        degrees_int = dict(G_int.degree())
        max_deg_int = max(degrees_int.values()) if degrees_int else 1
        for node in G_int.nodes():
                # Verwende die gleiche Typzuordnung wie in der PNG-Version
            node_lower = node.lower() if isinstance(node, str) else ''
            if node_lower in manual_types:
                typ = manual_types[node_lower]
                # Knotendetails mit Typ direkt aus den Beziehungen
                typ = get_entity_type(node)
                node_details = f"{node}\nTyp: {typ}"
                node_title = node_details.replace('\n', '<br>')
                color = type_to_fillcolor_int(typ)
            else:
                node_title = node
                color = type_to_fillcolor_int(get_entity_type(node))
                
            # Größe basierend auf Degree (Verbindungen)
            size = 15 + 10 * (degrees_int[node] / max_deg_int)
            # Füge Knoten hinzu - einfache Version ohne Gruppen
            inferred = next((e.get('inferred') for e in entities if e.get('entity')==node), 'explizit')
            shape_props = {'borderDashes': True} if inferred=='implizit' else {}
            net_int.add_node(node, label=label_map_int[node], color=color, title=node_title, size=size, shapeProperties=shape_props)
        
        # Einfache Legende als HTML-Block - mittig ausgerichtet
        legend_html = '<div style="padding:8px; background:#f9f9f9; border:1px solid #ddd; margin:0 auto 8px auto; border-radius:5px; font-size:12px; max-width:800px; text-align:center;">' 
        legend_html += '<h4 style="margin-top:0; margin-bottom:5px;">Knowledge Graph</h4>'
        
        # Entitätstypen
        legend_html += '<div style="margin:5px 0"><b>Entitaetstypen:</b> '
        
        # Sortierte Typen für konsistente Anzeige
        for typ in sorted(entity_types):  # Sortiere für konsistente Anzeige
            if typ in type_fill_colors:
                color = type_fill_colors[typ]
                legend_html += f'<span style="background:{color};border:1px solid #444;padding:1px 4px;margin-right:4px;display:inline-block;font-size:11px;">{typ.capitalize()}</span>'
        
        legend_html += '</div>'
        
        # Beziehungstypen - kompakter
        legend_html += '<div style="margin:5px 0"><b>Beziehungen:</b> '
        legend_html += '<span style="border-bottom:1px solid #333;padding:1px 4px;margin-right:5px;display:inline-block;font-size:11px;">Explizit</span>'
        legend_html += '<span style="border-bottom:1px dashed #555;padding:1px 4px;display:inline-block;font-size:11px;">Implizit</span>'
        legend_html += '</div>'
        
        # Steuerelemente - kompakter
        legend_html += '<div style="margin-top:5px;">'
        legend_html += '<button onclick="stabilize()" style="margin-right:3px;padding:2px 5px;font-size:11px;">Stabilisieren</button>'
        legend_html += '<button onclick="togglePhysics()" style="margin-right:3px;padding:2px 5px;font-size:11px;">Physik</button>'
        legend_html += '<button onclick="fitNetwork()" style="padding:2px 5px;font-size:11px;">Zoom</button>'
        legend_html += '</div>'
        
        # Kein zusatzlicher Hinweis, um Platz zu sparen
        
        legend_html += '</div>'
        
        # JavaScript für die Steuerelemente
        js_code = '''
        <script type="text/javascript">
        function stabilize() {
            network.stabilize(100);
        }
        
        function togglePhysics() {
            var options = network.physics.options;
            options.enabled = !options.enabled;
            network.setOptions({ physics: options });
        }
        
        function fitNetwork() {
            network.fit();
        }
        
        // Hover-Effekt nach dem Laden des Netzwerks
        network.on("hoverNode", function(params) {
            var nodeId = params.node;
            var connectedNodes = network.getConnectedNodes(nodeId);
            var allNodes = network.body.nodes;
            var allEdges = network.body.edges;
            
            // Setze alle Knoten und Kanten auf halbe Transparenz
            for (var i in allNodes) {
                if (Object.prototype.hasOwnProperty.call(allNodes, i)) {
                    allNodes[i].setOptions({opacity: 0.3});
                }
            }
            
            for (var i in allEdges) {
                if (Object.prototype.hasOwnProperty.call(allEdges, i)) {
                    allEdges[i].setOptions({opacity: 0.2});
                }
            }
            
            // Hervorheben des ausgewählten Knotens und seiner Verbindungen
            allNodes[nodeId].setOptions({opacity: 1.0});
            for (var i = 0; i < connectedNodes.length; i++) {
                allNodes[connectedNodes[i]].setOptions({opacity: 0.9});
                var edgeId = network.getConnectedEdges(connectedNodes[i]);
                for (var j = 0; j < edgeId.length; j++) {
                    if (network.getConnectedNodes(edgeId[j]).includes(nodeId)) {
                        allEdges[edgeId[j]].setOptions({opacity: 1.0, width: 3});
                    }
                }
            }
        });
        
        // Zurücksetzen beim Verlassen des Knotens
        network.on("blurNode", function(params) {
            var allNodes = network.body.nodes;
            var allEdges = network.body.edges;
            
            for (var i in allNodes) {
                if (Object.prototype.hasOwnProperty.call(allNodes, i)) {
                    allNodes[i].setOptions({opacity: 1.0});
                }
            }
            
            for (var i in allEdges) {
                if (Object.prototype.hasOwnProperty.call(allEdges, i)) {
                    allEdges[i].setOptions({opacity: 1.0, width: 2.0});
                }
            }
        });
        </script>
        '''
        
        # Setze heading und footer auf leer, um Dopplung zu vermeiden
        # Wir fügen die Legende und das JavaScript später manuell ein
        net_int.heading = ""
        net_int.footer = ""
        
        # Füge Kanten hinzu
        for u, v, d in G_int.edges(data=True):
            # Einfache Kanten
            edge_label = d.get('label', '')
            is_implicit = d.get('style') == 'dashed'
            
            net_int.add_edge(u, v, 
                              label=edge_label, 
                              title=edge_label,
                              arrows='to', 
                              width=2.0,
                              dashes=(is_implicit),
                              color='#777' if is_implicit else '#333')  # 50% kleinere Schrift für Kantenbeschriftungen
        
        # Verbesserte Optionen mit Clustering
        net_int.set_options('''
        {
          "edges": {
            "smooth": false,
            "font": {"size": 9}
          },
          "nodes": {
            "font": {"size": 11}
          },
          "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 150,
              "springConstant": 0.08
            },
            "stabilization": {
              "enabled": true,
              "iterations": 200
            }
          }
        }
        ''')
        
        # Speichere den Graphen mit benutzerdefiniertem HTML
        try:
            # Generiere HTML-Code
            html_string = net_int.generate_html()
            
            # Füge die Legende nur einmal ein - am Anfang des Dokuments nach dem <body> Tag
            if '<body>' in html_string:
                # Erstelle einen vollständigen HTML-String mit der Legende nur an einer Stelle
                html_parts = html_string.split('<body>')
                if len(html_parts) > 1:
                    html_string = html_parts[0] + '<body>\n<div style="text-align:center;">\n' + legend_html + '\n</div>\n' + html_parts[1]
            
            # Füge das JavaScript vor dem schließenden </body> Tag ein
            if '</body>' in html_string:
                html_string = html_string.replace('</body>', js_code + '\n</body>')
            
            # Speichere mit expliziter UTF-8-Kodierung
            with open("knowledge_graph_interactive.html", "w", encoding="utf-8") as f:
                f.write(html_string)
            print("HTML erfolgreich mit UTF-8-Kodierung gespeichert")
        except Exception as e:
            # Fallback: Versuche, problematische Zeichen zu ersetzen
            try:
                html_string = net_int.generate_html()
                # Ersetze alle nicht-ASCII-Zeichen durch ihre HTML-Entities
                html_string = html_string.encode('ascii', 'xmlcharrefreplace').decode('ascii')
                
                # Füge die Legende nur einmal ein - am Anfang des Dokuments nach dem <body> Tag
                if '<body>' in html_string:
                    # Erstelle einen vollständigen HTML-String mit der Legende nur an einer Stelle
                    html_parts = html_string.split('<body>')
                    if len(html_parts) > 1:
                        html_string = html_parts[0] + '<body>\n<div style="text-align:center;">\n' + legend_html + '\n</div>\n' + html_parts[1]
                
                # Füge das JavaScript vor dem schließenden </body> Tag ein
                if '</body>' in html_string:
                    html_string = html_string.replace('</body>', js_code + '\n</body>')
                
                with open("knowledge_graph_interactive.html", "w", encoding="ascii") as f:
                    f.write(html_string)
                print("HTML mit ASCII-Kodierung und XML-Entities gespeichert")
            except Exception as e2:
                print(f"Fehler beim Speichern der HTML-Datei: {e2}")
                raise e
        
        # Keine nachträgliche Bearbeitung der HTML-Datei notwendig, da wir den Header direkt setzen
            
        print("Interaktive Knowledge Graph HTML gespeichert: knowledge_graph_interactive.html")
    except ImportError:
        print("PyVis nicht installiert – interaktiver HTML-Export übersprungen.")
    except Exception as e:
        print(f"Interaktiver HTML-Export fehlgeschlagen: {e}")

if __name__ == "__main__":
    main()
