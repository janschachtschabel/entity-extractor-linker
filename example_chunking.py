#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Beispiel für langen Text (~4000 Zeichen).
MODE=generate, nur Wikipedia-Integration, MAX_ENTITIES=10.
"""

from entityextractor.core.api import process_entities
import json, logging, sys

sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)

text = """Seit den frühen 1990er Jahren verfolgt Deutschland das Ziel, seine Energieversorgung grundlegend zu transformieren. Die Energiewende hat das übergeordnete Ziel, den Ausstoß von Treibhausgasen zu reduzieren und zugleich die Versorgungssicherheit zu gewährleisten. Dabei spielen erneuerbare Energien wie Windkraft, Photovoltaik und Biomasse eine zentrale Rolle. Technische Innovationen in Speichertechnologien und intelligenten Netzen ermöglichen eine immer effizientere Integration fluktuierender Stromquellen. Forschungsinstitute wie das Fraunhofer ISE und das Deutsche Zentrum für Luft- und Raumfahrt (DLR) treiben die Entwicklung von Hochleistungsspeichern und Microgrid-Lösungen voran. Politische und wirtschaftliche Rahmenbedingungen, darunter das Erneuerbare-Energien-Gesetz (EEG), schaffen Anreize für Investitionen in saubere Technologien.
Auf gesellschaftlicher Ebene fördert die Bundesregierung über Programme wie den Klimaschutzplan 2050 die Akzeptanz von Energieeffizienzmaßnahmen und Elektromobilität. Kommunale Energieversorger und Stadtwerke investieren in Ladeinfrastruktur für Elektrofahrzeugen und entwickeln integrierte Konzepte zur Sektorkopplung. Die Kosten für erneuerbare Anlagen sind in den letzten Jahren erheblich gesunken, wodurch Investitionen für private Haushalte und Unternehmen attraktiver geworden sind. Gleichzeitig erfordert die Umstellung auf erneuerbare Energien Anpassungen im Netzbetrieb und Flexibilitätsmarkt. Digitale Plattformen zur Steuerung von Verbrauchern und Prosumer-Modellen gewinnen an Bedeutung und ermöglichen eine dynamische Bilanzierung von Einspeisung und Verbrauch. Marktmechanismen wie Redispatch 2.0 und Kapazitätsmärkte stellen sicher, dass Netzausbau und Betrieb auch bei hoher Volatilität stabil bleiben.
Im internationalen Kontext kooperiert Deutschland im Rahmen der EU-Klimapolitik und globaler Klimaabkommen wie dem Pariser Abkommen, um verbindliche Emissionssenkungen zu vereinbaren. Technologietransfer und gemeinsame Forschungsprojekte mit Partnern in Nordamerika, Asien und Afrika fördern den weltweiten Ausbau sauberer Energien. Die Rolle von grünem Wasserstoff als Energiespeicher und Transformationsmedium gewinnt zunehmend an Bedeutung, da er in der Industrie und im Schwerlastverkehr fossile Brennstoffe ersetzen kann. Pilotprojekte in Schleswig-Holstein und Bayern untersuchen die Machbarkeit von Sektorenkopplung mit Wasserstoffspeichern. Langfristig zielt die Bundesrepublik darauf ab, eine klimaneutrale Wirtschaft zu erreichen und gleichzeitig die wirtschaftliche Wettbewerbsfähigkeit zu erhalten. Die Herausforderung liegt darin, technologische, regulatorische und soziale Aspekte in Einklang zu bringen, um das Ziel einer nachhaltigen Energieversorgung zu realisieren."""

config = {
    # === LLM Provider Parameters ===
    "LLM_BASE_URL": "https://api.openai.com/v1",  # Base URL für LLM API
    "MODEL": "gpt-4.1-mini",   # LLM-Modell
    "OPENAI_API_KEY": None,    # API-Key aus Umgebungsvariable
    "MAX_TOKENS": 16000,       # Maximale Tokenanzahl pro Anfrage
    "TEMPERATURE": 0.2,        # Sampling-Temperature

    # === Data Source Parameters ===
    "USE_WIKIPEDIA": True,     # Wikipedia-Verknüpfung aktivieren
    "USE_WIKIDATA": False,     # Wikidata-Verknüpfung aktivieren
    "USE_DBPEDIA": False,      # DBpedia-Verknüpfung aktivieren
    "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
    "DBPEDIA_LOOKUP_API": True, # DBPedia Lookup API als Backup bei Verbindungsproblemen mit den Endpunkten
    "DBPEDIA_SKIP_SPARQL": False, # Skip DBPedia SPARQL
    "DBPEDIA_LOOKUP_FORMAT": "xml", # xml, json oder both
    "ADDITIONAL_DETAILS": False,  # Abruf zusätzlicher Details aus den Wissensquellen aktivieren
    "TIMEOUT_THIRD_PARTY": 20,  # HTTP-Timeout für Drittanbieter

    # === Entity Extraction Parameters ===
    "MAX_ENTITIES": 20,        # Max. Anzahl Entitäten
    "ALLOWED_ENTITY_TYPES": "auto", # Entitätstypen automatisch filtern
    "MODE": "extract",         # Modus: extrahieren
    "LANGUAGE": "de",          # Sprache
    "SHOW_STATUS": True,       # Statusmeldungen anzeigen
    "ENABLE_ENTITY_INFERENCE": False, # Entity-Inferenz aktivieren

    # === RELATION PARAMETERS ===
    "RELATION_EXTRACTION": True, # Relationsextraktion aktivieren
    "ENABLE_RELATIONS_INFERENCE": False, # Implizite Relationen aktivieren

    # === OTHER SETTINGS ===
    "SUPPRESS_TLS_WARNINGS": True, # TLS-Warnungen unterdrücken
    "COLLECT_TRAINING_DATA": False, # Trainingsdaten sammeln

    # === TEXT CHUNKING FÜR LANGE TEXTE ===
    "TEXT_CHUNKING": True,    # Text-Chunking aktivieren
    "TEXT_CHUNK_SIZE": 2000,   # Chunk-Größe
    "TEXT_CHUNK_OVERLAP": 50,  # Chunk-Überlappung

    # === KNOWLEDGE GRAPH COMPLETION ===
    "ENABLE_KGC": True,       # Knowledge Graph Completion aktivieren
    "KGC_ROUNDS": 3,           # Anzahl KGC-Runden

    # === GRAPH-VISUALISIERUNG ===
    "ENABLE_GRAPH_VISUALIZATION": True    # Graph-Visualisierung aktivieren
}

result = process_entities(text, config)
logging.info("Ergebnisse für langen Text:")

# Tabellarische Ausgabe der Entitäten und Beziehungen
if isinstance(result, dict) and "entities" in result and "relationships" in result:
    entities = result["entities"]
    relationships = result["relationships"]
else:
    entities = result
    relationships = []

# Entitäten-Tabelle
print("\nExtrahierte Entitäten:")
print("-" * 100)
print(f"{'Nr':3} | {'Name':25} | {'Typ':15} | {'Inferred':10} | {'Wikipedia':25} | {'Wikidata':15} | {'DBpedia':20}")
print("-" * 100)
for i, entity in enumerate(entities, start=1):
    name = entity.get("entity", "")[:25]
    details = entity.get("details", {})
    etype = details.get("typ", "")[:15]
    inferred = details.get("inferred", "")[:10]
    sources = entity.get("sources", {})
    wiki = sources.get("wikipedia", {}).get("url", "")[:25]
    wikidata = sources.get("wikidata", {}).get("id", "")[:15]
    dbpedia = sources.get("dbpedia", {}).get("url", "")[:20]
    print(f"{i:3} | {name:25} | {etype:15} | {inferred:10} | {wiki:25} | {wikidata:15} | {dbpedia:20}")
print("-" * 100)
print(f"Insgesamt {len(entities)} Entitäten gefunden.")

# Beziehungen-Tabelle
if relationships:
    explicit = [r for r in relationships if r.get("inferred") == "explicit"]
    implicit = [r for r in relationships if r.get("inferred") == "implicit"]

    # Map Entity-Namen auf Entity-Inferenzstatus
    entity_inf_map = {ent.get("entity", ""): ent.get("details", {}).get("inferred", "") for ent in entities}

    print("\nExplizite Beziehungen:")
    print("-" * 140)
    print(f"{'Nr':3} | {'Subjekt':25} | {'SubjTyp':12} | {'SubjInf':10} | {'Prädikat':20} | {'Objekt':25} | {'ObjTyp':12} | {'ObjInf':10}")
    print("-" * 140)
    for i, rel in enumerate(explicit, start=1):
        full_subj = rel.get("subject", "")
        subj = full_subj[:25]
        stype = rel.get("subject_type", "")[:12]
        subject_inf = entity_inf_map.get(full_subj, "")[:10]
        pred = rel.get("predicate", "")[:20]
        full_obj = rel.get("object", "")
        obj = full_obj[:25]
        otype = rel.get("object_type", "")[:12]
        object_inf = entity_inf_map.get(full_obj, "")[:10]
        print(f"{i:3} | {subj:25} | {stype:12} | {subject_inf:10} | {pred:20} | {obj:25} | {otype:12} | {object_inf:10}")
    print("-" * 140)
    print(f"Insgesamt {len(explicit)} explizite Beziehungen gefunden.")

    print("\nImplizite Beziehungen:")
    print("-" * 140)
    print(f"{'Nr':3} | {'Subjekt':25} | {'SubjTyp':12} | {'SubjInf':10} | {'Prädikat':20} | {'Objekt':25} | {'ObjTyp':12} | {'ObjInf':10}")
    print("-" * 140)
    for i, rel in enumerate(implicit, start=1):
        full_subj = rel.get("subject", "")
        subj = full_subj[:25]
        stype = rel.get("subject_type", "")[:12]
        subject_inf = entity_inf_map.get(full_subj, "")[:10]
        pred = rel.get("predicate", "")[:20]
        full_obj = rel.get("object", "")
        obj = full_obj[:25]
        otype = rel.get("object_type", "")[:12]
        object_inf = entity_inf_map.get(full_obj, "")[:10]
        print(f"{i:3} | {subj:25} | {stype:12} | {subject_inf:10} | {pred:20} | {obj:25} | {otype:12} | {object_inf:10}")
    print("-" * 140)
    print(f"Insgesamt {len(implicit)} implizite Beziehungen gefunden.")
else:
    print("Keine Beziehungen gefunden.")

# Statistiken anzeigen (aus JSON-Ergebnis)
stats = result.get("statistics", {})
print("\nStatistiken:")
# Gesamt
print(f"  Gesamtentitäten: {stats.get('total_entities', 0)}")
# Typverteilung
print("\n  Typverteilung:")
for typ, count in stats.get('types_distribution', {}).items():
    print(f"    {typ}: {count}")
# Linking-Erfolg
print("\n  Linking-Erfolg:")
for source, data in stats.get('linked', {}).items():
    print(f"    {source.capitalize()}: {data['count']} ({data['percent']:.1f}%)")
# Top Wikipedia Kategorien
print("\n  Top 10 Wikipedia-Kategorien:")
for c in stats.get('top_wikipedia_categories', []):
    print(f"    {c['category']}: {c['count']}")
# Top Wikidata Typen
print("\n  Top 10 Wikidata-Typen:")
for t in stats.get('top_wikidata_types', []):
    print(f"    {t['type']}: {t['count']}")
# Entitätsverbindungen
print("\n  Entitätsverbindungen (Top 10):")
for ec in stats.get('entity_connections', [])[:10]:
    print(f"    {ec['entity']}: {ec['count']}")
# Top Wikidata part_of
print("\n  Top 10 Wikidata 'part_of':")
for po in stats.get('top_wikidata_part_of', []):
    print(f"    {po['part_of']}: {po['count']}")
# Top Wikidata has_parts
print("\n  Top 10 Wikidata 'has_parts':")
for hp in stats.get('top_wikidata_has_parts', []):
    print(f"    {hp['has_parts']}: {hp['count']}")
# Top DBpedia part_of
print("\n  Top 10 DBpedia 'part_of':")
for po in stats.get('top_dbpedia_part_of', []):
    print(f"    {po['part_of']}: {po['count']}")
# Top DBpedia has_parts
print("\n  Top 10 DBpedia 'has_parts':")
for hp in stats.get('top_dbpedia_has_parts', []):
    print(f"    {hp['has_parts']}: {hp['count']}")
# Top 10 DBpedia-Subjects
print("\n  Top 10 DBpedia-Subjects:")
for sub in stats.get('top_dbpedia_subjects', []):
    print(f"    {sub['subject']}: {sub['count']}")
