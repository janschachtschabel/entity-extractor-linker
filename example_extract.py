#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from entityextractor.core.api import process_entities
import logging

def main():
    # Beispieltext
    example_text = (
        "Apple und Microsoft sind große Technologieunternehmen. "
        "Steve Jobs gründete Apple in Kalifornien und entwickelte das iPhone. Bill Gates gründete Microsoft und "
        "entwickelte Windows. Beide Unternehmen konkurrieren im Bereich der Betriebssysteme und Computerhardware. "
        "Tim Cook ist der aktuelle CEO von Apple und Satya Nadella leitet Microsoft."
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
        "USE_WIKIDATA": True,      # Wikidata-Verknüpfung aktivieren
        "USE_DBPEDIA": True,       # DBpedia-Verknüpfung aktivieren
        "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
        "DBPEDIA_LOOKUP_API": True, # DBPedia Lookup API als Backup bei Verbindungsproblemen mit den Endpunkten
        "DBPEDIA_SKIP_SPARQL": False, # Skip DBPedia SPARQL
        "DBPEDIA_LOOKUP_FORMAT": "xml", # xml, json oder both
        "ADDITIONAL_DETAILS": False,  # Abruf zusätzlicher Details aus den Wissensquellen aktivieren
        "TIMEOUT_THIRD_PARTY": 20,  # HTTP-Timeout für Drittanbieter

        # === ENTITY EXTRACTION PARAMETERS ===
        "MAX_ENTITIES": 15,        # Max. Anzahl Entitäten
        "ALLOWED_ENTITY_TYPES": "auto", # Entitätstypen automatisch filtern
        "MODE": "extract",         # Modus (extract, generate, compendium)
        "LANGUAGE": "de",          # Sprache (de, en)
        "SHOW_STATUS": True,       # Statusmeldungen anzeigen
        "ENABLE_ENTITY_INFERENCE": False,  # Entity-Inferenz aktivieren

        # === RELATION PARAMETERS ===
        "RELATION_EXTRACTION": True,  # Relationsextraktion aktivieren
        "ENABLE_RELATIONS_INFERENCE": False,  # Implizite Relationen aktivieren

        # === OTHER SETTINGS ===
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
        "ENABLE_GRAPH_VISUALIZATION": False  # Graph-Visualisierung aktivieren
    }
    
    # Entitäten extrahieren und verknüpfen
    logging.info("Starte Entitäten-Extraktion und -Verknüpfung in test.py")
    print("\nExtrahiere und verknüpfe Entitäten aus dem Text...")
    result = process_entities(example_text, config)
    
    # Prüfen, ob das Ergebnis die neue Struktur mit Entitäten und Beziehungen hat
    if isinstance(result, dict) and "entities" in result and "relationships" in result:
        entities = result["entities"]
        relationships = result["relationships"]
    else:
        # Alte Struktur (nur Entitäten)
        entities = result
        relationships = []
    
    # Übersichtliche Kurzfassung der Entitäten
    print("\nExtrahierte Entitäten:")
    print("-" * 166)
    print(f"{'Nr':3} | {'Name':25} | {'Typ':15} | {'Inferred':10} | {'Wiki-URL':60} | {'Wikidata':15} | {'DBpedia':20}")
    print("-" * 166)
    
    for i, entity in enumerate(entities):
        # Basisinformationen
        name = entity.get("entity", "")[:25]
        entity_type = ""
        
        # Typ aus verschiedenen möglichen Quellen extrahieren
        if "entity_type" in entity:
            entity_type = entity["entity_type"]
        elif "type" in entity:
            entity_type = entity["type"]
        elif "details" in entity and "typ" in entity["details"]:
            entity_type = entity["details"]["typ"]
        
        # Wikipedia-Informationen
        wiki_url = ""
        if "sources" in entity and "wikipedia" in entity["sources"]:
            wiki_url = entity["sources"]["wikipedia"].get("url", "")
        
        # Wikidata-Informationen
        wikidata_id = ""
        wikidata_label = ""
        if "sources" in entity and "wikidata" in entity["sources"]:
            wikidata_id = entity["sources"]["wikidata"].get("id", "")
            wikidata_label = entity["sources"]["wikidata"].get("label", "")[:15]
        
        # DBpedia-Informationen
        dbpedia_title = ""
        dbpedia_uri = ""
        if "sources" in entity and "dbpedia" in entity["sources"]:
            dbpedia_title = entity["sources"]["dbpedia"].get("title", "")[:20]
            dbpedia_uri = entity["sources"]["dbpedia"].get("uri", "")
        
        # Inferred merken
        inferred = entity.get('details', {}).get('inferred', entity.get('inferred', ''))
        
        # Zeile ausgeben
        print(f"{i+1:3} | {name:25} | {entity_type:15} | {inferred:10} | {wiki_url:60} | {wikidata_id:15} | {dbpedia_title:20}")
    
    print("-" * 166)
    print(f"Insgesamt {len(entities)} Entitäten gefunden.")
    
    # Wenn Beziehungen vorhanden sind, diese in Tabellen ausgeben
    if relationships:
        # Beziehungen nach explizit und implizit trennen (nur englische Werte)
        explicit_relationships = [rel for rel in relationships if rel.get("inferred", "") == "explicit"]
        implicit_relationships = [rel for rel in relationships if rel.get("inferred", "") == "implicit"]
        
        # Explizite Beziehungen ausgeben
        print("\nExplizite Beziehungen (direkt im Text erwähnt):")
        print("-" * 140)
        print(f"{'Nr':3} | {'Subjekt':25} | {'SubjTyp':12} | {'SubjInf':10} | {'Prädikat':20} | {'Objekt':25} | {'ObjTyp':12} | {'ObjInf':10}")
        print("-" * 140)
        
        if explicit_relationships:
            for i, rel in enumerate(explicit_relationships):
                subject = rel['subject'][:25]
                subject_type = rel.get('subject_type', '')[:12]
                subject_inf = rel.get('subject_inferred', '')[:10]
                predicate = rel['predicate'][:20]
                obj = rel['object'][:25]
                object_type = rel.get('object_type', '')[:12]
                object_inf = rel.get('object_inferred', '')[:10]
                
                print(f"{i+1:3} | {subject:25} | {subject_type:12} | {subject_inf:10} | {predicate:20} | {obj:25} | {object_type:12} | {object_inf:10}")
        else:
            print("Keine expliziten Beziehungen gefunden.")
            
        print("-" * 140)
        print(f"Insgesamt {len(explicit_relationships)} explizite Beziehungen gefunden.")
        
        # Implizite Beziehungen ausgeben
        print("\nImplizite Beziehungen (aus dem Kontext abgeleitet):")
        print("-" * 140)
        print(f"{'Nr':3} | {'Subjekt':25} | {'SubjTyp':12} | {'SubjInf':10} | {'Prädikat':20} | {'Objekt':25} | {'ObjTyp':12} | {'ObjInf':10}")
        print("-" * 140)
        
        if implicit_relationships:
            for i, rel in enumerate(implicit_relationships):
                subject = rel['subject'][:25]
                subject_type = rel.get('subject_type', '')[:12]
                subject_inf = rel.get('subject_inferred', '')[:10]
                predicate = rel['predicate'][:20]
                obj = rel['object'][:25]
                object_type = rel.get('object_type', '')[:12]
                object_inf = rel.get('object_inferred', '')[:10]
                
                print(f"{i+1:3} | {subject:25} | {subject_type:12} | {subject_inf:10} | {predicate:20} | {obj:25} | {object_type:12} | {object_inf:10}")
        else:
            print("Keine impliziten Beziehungen gefunden.")
            
        print("-" * 140)
        print(f"Insgesamt {len(implicit_relationships)} implizite Beziehungen gefunden.")
        
        # Gesamtzahl der Beziehungen
        print(f"\nGesamtzahl der Beziehungen: {len(relationships)}")
    else:
        print("\nKeine Beziehungen zwischen Entitäten gefunden oder RELATION_EXTRACTION ist nicht aktiviert.")
        
    # Detaillierte URLs anzeigen
    print("\nWikipedia-URLs:")
    for i, entity in enumerate(entities):
        if "sources" in entity and "wikipedia" in entity["sources"] and "url" in entity["sources"]["wikipedia"]:
            name = entity.get("entity", "")
            url = entity["sources"]["wikipedia"].get("url", "")
            if url:
                print(f"{i+1}. {name}: {url}")
    
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

    logging.info("Final results have been outputted.")

if __name__ == "__main__":
    main()
