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
        "USE_DBPEDIA": False,       # DBpedia-Verknüpfung aktivieren
        "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
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
    print("-" * 100)
    print(f"{'Nr':3} | {'Name':25} | {'Typ':15} | {'Inferred':10} | {'Wikipedia':25} | {'Wikidata':15} | {'DBpedia':20}")
    print("-" * 100)
    
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
        wiki_label = ""
        wiki_url = ""
        if "sources" in entity and "wikipedia" in entity["sources"]:
            wiki_label = entity["sources"]["wikipedia"].get("label", "")[:25]
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
        print(f"{i+1:3} | {name:25} | {entity_type:15} | {inferred:10} | {wiki_label:25} | {wikidata_id:15} | {dbpedia_title:20}")
    
    print("-" * 100)
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
    
    # Statistiken ausgeben
    print(f"\nStatistiken:")
    print(f"Anzahl extrahierter Entitäten: {len(entities)}")
    
    # Typen zählen
    entity_types = {}
    for entity in entities:
        entity_type = entity["details"]["typ"]
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    print("\nVerteilung der Entitätstypen:")
    for entity_type, count in entity_types.items():
        print(f"  {entity_type}: {count}")
    
    # Anzahl der Entitäten mit Wikipedia-URL
    with_wikipedia = sum(1 for entity in entities if "wikipedia" in entity["sources"])
    print(f"\nEntitäten mit Wikipedia-URL: {with_wikipedia} ({with_wikipedia/len(entities)*100:.1f}% wenn > 0)" if len(entities) > 0 else "\nEntitäten mit Wikipedia-URL: 0 (0.0%)")
    
    # Anzahl der Entitäten mit Wikidata-ID
    with_wikidata = sum(1 for entity in entities if "wikidata" in entity["sources"])
    print(f"Entitäten mit Wikidata-ID: {with_wikidata} ({with_wikidata/len(entities)*100:.1f}% wenn > 0)" if len(entities) > 0 else "Entitäten mit Wikidata-ID: 0 (0.0%)")
    
    # Anzahl der Entitäten mit DBpedia-Informationen
    with_dbpedia = sum(1 for entity in entities if "dbpedia" in entity["sources"])
    print(f"Entitäten mit DBpedia-Informationen: {with_dbpedia} ({with_dbpedia/len(entities)*100:.1f}% wenn > 0)" if len(entities) > 0 else "Entitäten mit DBpedia-Informationen: 0 (0.0%)")
    
    # Analyse der sich überschneidenden Wikidata- und DBpedia-Typen
    if len(entities) > 0:
        print("\nAnalyse der Wikidata-Typen:")
        wikidata_types = {}
        for entity in entities:
            if "wikidata" in entity["sources"] and "types" in entity["sources"]["wikidata"]:
                for wtype in entity["sources"]["wikidata"]["types"]:
                    wikidata_types[wtype] = wikidata_types.get(wtype, 0) + 1
        
        # Sortiere nach Häufigkeit
        sorted_wikidata_types = sorted(wikidata_types.items(), key=lambda x: x[1], reverse=True)
        for wtype, count in sorted_wikidata_types[:10]:  # Top 10 anzeigen
            if count > 1:  # Nur Typen anzeigen, die mehr als einmal vorkommen
                print(f"  {wtype}: {count}")
        
        print("\nAnalyse der DBpedia-Typen:")
        dbpedia_types = {}
        for entity in entities:
            if "dbpedia" in entity["sources"] and "types" in entity["sources"]["dbpedia"]:
                for dtype in entity["sources"]["dbpedia"]["types"]:
                    dbpedia_types[dtype] = dbpedia_types.get(dtype, 0) + 1
        
        # Sortiere nach Häufigkeit
        sorted_dbpedia_types = sorted(dbpedia_types.items(), key=lambda x: x[1], reverse=True)
        for dtype, count in sorted_dbpedia_types[:10]:  # Top 10 anzeigen
            if count > 1:  # Nur Typen anzeigen, die mehr als einmal vorkommen
                print(f"  {dtype}: {count}")
        
        # Entitäten gruppieren nach gemeinsamen Typen
        print("\nEntitäten-Cluster nach gemeinsamen Typen:")
        
        # Wikidata-Cluster
        wikidata_clusters = {}
        for entity in entities:
            if "wikidata" in entity["sources"] and "types" in entity["sources"]["wikidata"]:
                for wtype in entity["sources"]["wikidata"]["types"]:
                    if wikidata_types.get(wtype, 0) > 1:  # Nur Typen berücksichtigen, die mehr als einmal vorkommen
                        if wtype not in wikidata_clusters:
                            wikidata_clusters[wtype] = []
                        wikidata_clusters[wtype].append(entity["entity"])
        
        # Top 5 Wikidata-Cluster anzeigen
        print("\nWikidata-Cluster (Top 5):")
        top_clusters = sorted(wikidata_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for wtype, entities_list in top_clusters:
            print(f"  {wtype} ({len(entities_list)} Entitäten): {', '.join(entities_list)}")
        
        # DBpedia-Cluster
        dbpedia_clusters = {}
        for entity in entities:
            if "dbpedia" in entity["sources"] and "types" in entity["sources"]["dbpedia"]:
                for dtype in entity["sources"]["dbpedia"]["types"]:
                    if dbpedia_types.get(dtype, 0) > 1:  # Nur Typen berücksichtigen, die mehr als einmal vorkommen
                        if dtype not in dbpedia_clusters:
                            dbpedia_clusters[dtype] = []
                        dbpedia_clusters[dtype].append(entity["entity"])
        
        # Top 5 DBpedia-Cluster anzeigen
        print("\nDBpedia-Cluster (Top 5):")
        top_clusters = sorted(dbpedia_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for dtype, entities_list in top_clusters:
            print(f"  {dtype} ({len(entities_list)} Entitäten): {', '.join(entities_list)}")

        # Analyse gemeinsamer Wikipedia-Kategorien (Top 5)
        wiki_cat_entities = {}
        for ent in entities:
            cats = ent.get("sources", {}).get("wikipedia", {}).get("categories", [])
            for cat in cats:
                wiki_cat_entities.setdefault(cat, []).append(ent.get("entity", ent.get("name", "")))
        sorted_wiki_cats = sorted(wiki_cat_entities.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        print("\nWikipedia-Kategorien mit den meisten Überschneidungen (Top 5):")
        for cat, names in sorted_wiki_cats:
            if len(names) > 1:
                print(f"  {cat} ({len(names)} Entitäten): {', '.join(names)}")
    logging.info("Final results have been outputted in test.py")

if __name__ == "__main__":
    main()
