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

base_text = """Die Energiewende in Deutschland hat in den letzten Jahren erhebliche Fortschritte gemacht. Städte wie Berlin und München setzen verstärkt auf Solarenergie, Windkraft und Biomasse. Unternehmen wie Siemens, RWE und E.ON investieren in neue Technologien. Internationale Abkommen wie das Pariser Klimaabkommen von 2015 sowie der Kyoto-Protokoll-Rahmen spielen eine entscheidende Rolle. Der Intergovernmental Panel on Climate Change (IPCC) veröffentlicht regelmäßig Berichte über die Erderwärmung. Bundesministerien und Forschungseinrichtungen wie das Fraunhofer-Institut und das Deutsche Zentrum für Luft- und Raumfahrt (DLR) arbeiten an innovativen Lösungen. Das Bundesministerium für Wirtschaft und Energie (BMWi) fördert darüber hinaus Forschungsprojekte zur Dekarbonisierung. """

text = base_text * 7  # ergibt ca. 5400 Zeichen

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
    name = entity.get("name", entity.get("entity", ""))[:25]
    etype = entity.get("type", entity.get("entity_type", ""))[:15]
    inferred = entity.get("inferred", "")[:10]
    wiki = entity.get("wikipedia_url", "")[:25]
    wikidata = entity.get("wikidata_id", "")[:15]
    dbpedia = entity.get("dbpedia_uri", "")[:20]
    print(f"{i:3} | {name:25} | {etype:15} | {inferred:10} | {wiki:25} | {wikidata:15} | {dbpedia:20}")
print("-" * 100)
print(f"Insgesamt {len(entities)} Entitäten gefunden.")

# Beziehungen-Tabelle
if relationships:
    explicit = [r for r in relationships if r.get("inferred") == "explicit"]
    implicit = [r for r in relationships if r.get("inferred") == "implicit"]

    # Map Entity-Namen auf Entity-Inferenzstatus
    entity_inf_map = {ent.get("name", ent.get("entity", "")): ent.get("inferred", "") for ent in entities}

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
