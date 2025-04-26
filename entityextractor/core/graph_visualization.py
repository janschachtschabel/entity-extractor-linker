import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyvis.network import Network
import logging

def visualize_graph(result, config):
    """
    Generate PNG and HTML visualization of the knowledge graph.
    Requires config["ENABLE_GRAPH_VISUALIZATION"] True and config["RELATION_EXTRACTION"] True.
    """
    if not config.get("ENABLE_GRAPH_VISUALIZATION", False):
        return
    if not config.get("RELATION_EXTRACTION", False):
        logging.warning("Graph visualization requires RELATION_EXTRACTION=True, skipping.")
        return

    # Prepare output filenames and log status
    png_filename = "knowledge_graph.png"
    html_filename = "knowledge_graph_interactive.html"
    logging.info(f"Graph visualization enabled - PNG: {png_filename}, HTML: {html_filename}")

    entities = result.get("entities", [])
    relationships = result.get("relationships", [])

    # Build MultiDiGraph
    G = nx.MultiDiGraph()
    for rel in relationships:
        inferred = rel.get("inferred", "")
        subj = rel.get("subject")
        obj = rel.get("object")
        pred = rel.get("predicate")
        style = "solid" if inferred == "explicit" else "dashed"
        if subj:
            G.add_node(subj)
        if obj:
            G.add_node(obj)
        if subj and obj and pred:
            G.add_edge(subj, obj, label=pred, style=style)

    # Determine colors by entity type
    base_colors = {
        "person": "#ffe6e6",
        "organisation": "#e6f0ff",
        "location": "#e7ffe6",
        "event": "#fff6e6",
        "concept": "#f0e6ff",
        "work": "#ffe6cc"
    }
    additional_colors = [
        "#e6ffff", "#fff2e6", "#ffe6f2", "#f2ffe6",
        "#e6e6ff", "#ffe6eb", "#e6ffe0", "#e6f5ff"
    ]
    color_iter = iter(additional_colors)

    def get_entity_type(node):
        for rel in relationships:
            if rel.get("subject") == node and rel.get("subject_type"):
                return rel.get("subject_type").lower()
            if rel.get("object") == node and rel.get("object_type"):
                return rel.get("object_type").lower()
        for ent in entities:
            name = ent.get("entity") or ent.get("name")
            if name == node and ent.get("entity_type"):
                return ent.get("entity_type").lower()
        return ""

    type_fill_colors = {}
    for node in G.nodes():
        etype = get_entity_type(node)
        if etype in base_colors:
            type_fill_colors[node] = base_colors[etype]
        else:
            try:
                type_fill_colors[node] = next(color_iter)
            except StopIteration:
                type_fill_colors[node] = "#f2f2f2"

    # -- PNG Visualization --
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(8, 6))
    node_colors = [type_fill_colors.get(n, "#f2f2f2") for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color=node_colors, edgecolors="#222")
    nx.draw_networkx_labels(G, pos, font_size=9)
    edge_styles = [d.get("style", "solid") for _, _, d in G.edges(data=True)]
    nx.draw_networkx_edges(G, pos, arrows=True, style=edge_styles)
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    plt.axis("off")
    plt.tight_layout()
    # Legende für PNG (Kanten- und Typfarben)
    legend_elements = [
        Line2D([0], [0], color="#222", lw=2.4, label="Explicit relationship →"),
        Line2D([0], [0], color="#888", lw=2.0, linestyle="dashed", label="Implicit relationship →")
    ]
    # Typ-Farben-Legende auf Basis der Knoten
    type_color_map = {}
    for node, color in type_fill_colors.items():
        typ = get_entity_type(node)
        if typ:
            type_color_map[typ] = color
    for typ, color in sorted(type_color_map.items()):
        legend_elements.append(Patch(facecolor=color, edgecolor="#444", label=typ.capitalize()))
    plt.legend(handles=legend_elements, loc="lower left", fontsize=9, frameon=True, facecolor="white", edgecolor="#aaa")
    plt.savefig(png_filename, dpi=180)
    plt.close()
    logging.info(f"Knowledge Graph PNG gespeichert: {png_filename}")
    print(f"Knowledge Graph PNG gespeichert: {png_filename}")

    # -- HTML Visualization (interactive) using same layout as PNG --
    net = Network(height="800px", width="100%", directed=True, bgcolor="#ffffff", font_color="#222")
    # Prepare scaled positions with factor 300 and enforce a minimum pixel distance of 150
    scaled_pos = {node: (pos[node][0] * 300, pos[node][1] * 300) for node in G.nodes()}
    min_pixel_dist = 150
    for _ in range(1000):
        moved = False
        nodes = list(scaled_pos.keys())
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                n1, n2 = nodes[i], nodes[j]
                x1, y1 = scaled_pos[n1]; x2, y2 = scaled_pos[n2]
                dx, dy = x1 - x2, y1 - y2
                dist = (dx*dx + dy*dy)**0.5
                if dist < min_pixel_dist:
                    if dist == 0:
                        dx, dy = 0.1, 0.1; dist = 0.1
                    shift = (min_pixel_dist - dist) / 2
                    ux, uy = dx/dist, dy/dist
                    scaled_pos[n1] = (x1 + ux*shift, y1 + uy*shift)
                    scaled_pos[n2] = (x2 - ux*shift, y2 - uy*shift)
                    moved = True
        if not moved:
            break
    # Add nodes with computed positions
    for node, (sx, sy) in scaled_pos.items():
        net.add_node(
            node,
            label=node,
            color=type_fill_colors.get(node, "#f2f2f2"),
            x=int(sx),
            y=int(sy),
            physics=False
        )
    # Add edges with smaller font size for labels
    for u, v, d in G.edges(data=True):
        net.add_edge(
            u,
            v,
            label=d.get("label", ""),
            color="#333",
            arrows="to",
            dashes=(d.get("style") == "dashed"),
            font={"size": 10}
        )
    # Erzeuge interaktive HTML inkl. Legende und Steuerung
    try:
        html_string = net.generate_html()
        # HTML-Legende erstellen
        legend_html = '<div style="padding:8px; background:#f9f9f9; border:1px solid #ddd; margin:0 auto 8px auto; border-radius:5px; font-size:12px; max-width:800px; text-align:center;">'
        legend_html += '<h4 style="margin-top:0; margin-bottom:5px;">Knowledge Graph</h4>'
        legend_html += '<div style="margin:5px 0"><b>Entity Types:</b> '
        for typ, color in sorted(type_color_map.items()):
            legend_html += f'<span style="background:{color};border:1px solid #444;padding:1px 4px;margin-right:4px;display:inline-block;font-size:11px;">{typ.capitalize()}</span>'
        legend_html += '</div>'
        legend_html += '<div style="margin:5px 0"><b>Relationships:</b> '
        legend_html += '<span style="border-bottom:1px solid #333;padding:1px 4px;margin-right:5px;display:inline-block;font-size:11px;">Explicit</span>'
        legend_html += '<span style="border-bottom:1px dashed #555;padding:1px 4px;display:inline-block;font-size:11px;">Implicit</span>'
        legend_html += '</div>'
        legend_html += '<div style="margin-top:5px;">'
        legend_html += '<button onclick="stabilize()" style="margin-right:3px;padding:2px 5px;font-size:11px;">Stabilisieren</button>'
        legend_html += '<button onclick="togglePhysics()" style="margin-right:3px;padding:2px 5px;font-size:11px;">Physik</button>'
        legend_html += '<button onclick="fitNetwork()" style="padding:2px 5px;font-size:11px;">Zoom</button>'
        legend_html += '</div></div>'
        # JavaScript-Steuerungscode
        js_code = '''
<script type="text/javascript">
function stabilize() { network.stabilize(100); }
function togglePhysics() {
    var options = network.physics.options;
    options.enabled = !options.enabled;
    network.setOptions({ physics: options });
}
function fitNetwork() { network.fit(); }
network.on("hoverNode", function(params) { /* Highlight-Logik */ });
network.on("blurNode", function(params) { /* Rücksetzen */ });
</script>
'''
        # Legende und JS in HTML einfügen
        if '<body>' in html_string:
            parts = html_string.split('<body>')
            html_string = parts[0] + '<body>\n' + legend_html + '\n' + parts[1]
        if '</body>' in html_string:
            html_string = html_string.replace('</body>', js_code + '\n</body>')
        # Speichern
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_string)
        logging.info(f"Interaktive Knowledge Graph HTML gespeichert: {html_filename}")
        print(f"Interaktive Knowledge Graph HTML gespeichert: {html_filename}")
    except Exception as e:
        logging.error(f"Fehler beim Generieren der interaktiven HTML-Visualisierung: {e}")
    return {"png": png_filename, "html": html_filename}
