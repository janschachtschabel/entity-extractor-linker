#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Beispiel für die Verwendung der Entity Relationship Inference-Funktionalität.
"""

import json
from entityextractor.core.api import process_entities
import logging

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
    
    # Hinweis für implizite Beziehungen
    print("Hinweis: Implizite Beziehungen sind solche, die nicht direkt im Text erwähnt werden,")
    print("sondern aus dem Kontext abgeleitet werden können. Zum Beispiel könnte eine implizite")
    print("Beziehung zwischen 'Industrielle Revolution' und 'Arbeiterbewegung' bestehen, obwohl")
    print("diese nicht direkt im Text miteinander verbunden sind.")
    
    # Konfiguration definieren
    config = {
        # === LLM Provider Parameters ===
        "LLM_BASE_URL": "https://api.openai.com/v1",  # Base URL für LLM API
        "MODEL": "gpt-4.1-mini",   # LLM-Modell
        "OPENAI_API_KEY": None,    # API-Key aus Umgebungsvariable
        "MAX_TOKENS": 16000,       # Maximale Tokenanzahl pro Anfrage
        "TEMPERATURE": 0.2,        # Sampling-Temperature

        # === Data Source Parameters ===
        "USE_WIKIPEDIA": True,     # Wikipedia-Verknüpfung aktivieren
        "USE_WIKIDATA": True,      # Wikidata-Verknüpfung aktivieren
        "USE_DBPEDIA": False,       # DBpedia-Verknüpfung aktivieren
        "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
        "DBPEDIA_LOOKUP_API": True, # DBPedia Lookup API als Backup bei Verbindungsproblemen mit den Endpunkten
        "DBPEDIA_SKIP_SPARQL": False, # Skip DBPedia SPARQL
        "DBPEDIA_LOOKUP_FORMAT": "xml", # xml, json oder both
        "ADDITIONAL_DETAILS": False,  # Abruf zusätzlicher Details aus den Wissensquellen aktivieren
        "TIMEOUT_THIRD_PARTY": 20,  # HTTP-Timeout für Drittanbieter

        # === Entity Extraction Parameters ===
        "MAX_ENTITIES": 20,        # Max. Anzahl Entitäten
        "ALLOWED_ENTITY_TYPES": "auto", # Entitätstypen automatisch filtern
        "MODE": "extract",       # Modus (extract, generate, compendium)
        "LANGUAGE": "en",        # Sprache (de, en)
        "SHOW_STATUS": True,       # Statusmeldungen anzeigen
        "ENABLE_ENTITY_INFERENCE": False, # Entity-Inferenz aktivieren

        # === Relation Parameters ===
        "RELATION_EXTRACTION": True,          # Relationsextraktion aktivieren
        "ENABLE_RELATIONS_INFERENCE": True,  # Implizite Relationen aktivieren

        # === Other Settings ===
        "SUPPRESS_TLS_WARNINGS": True, # TLS-Warnungen unterdrücken
        "COLLECT_TRAINING_DATA": False, # Trainingsdaten sammeln

        # === Text Chunking für lange Texte ===
        "TEXT_CHUNKING": False,    # Text-Chunking aktivieren
        "TEXT_CHUNK_SIZE": 2000,   # Chunk-Größe
        "TEXT_CHUNK_OVERLAP": 50,  # Chunk-Überlappung

        # === Knowledge Graph Completion ===
        "ENABLE_KGC": False,       # Knowledge Graph Completion aktivieren
        "KGC_ROUNDS": 3,           # Anzahl KGC-Runden

        # === Graph-Visualisierung ===
        "ENABLE_GRAPH_VISUALIZATION": True    # Graph-Visualisierung aktivieren
    }

    logging.info("Starte Entitäten-Extraktion, -Verknüpfung und -Inference in test_relationships.py")
    print(f"\nExtrahiere und verknüpfe Entitäten aus dem Text und inferiere Beziehungen...")
    result = process_entities(example_text, config)
    
    # Log: Start der finalen Ergebnis-Ausgabe
    logging.info("Beginne Ausgabe der finalen Ergebnisse in test_relationships.py")
    # Ausgabe formatieren
    if isinstance(result, dict) and "entities" in result and "relationships" in result:
        # Übersichtliche Kurzfassung der Entitäten
        print("\nExtrahierte Entitäten:")
        print("-" * 100)
        print(f"{'Nr':3} | {'Name':25} | {'Typ':15} | {'Inferred':10} | {'Wikipedia':25} | {'Wikidata':15} | {'DBpedia':20}")
        print("-" * 100)
        
        for i, entity in enumerate(result["entities"]):
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
                src = entity["sources"]["dbpedia"]
                # title aus dbpedia_title oder title
                dbpedia_title = src.get("dbpedia_title", "")[:20] or src.get("title", "")[:20]
                # uri aus resource_uri oder uri
                dbpedia_uri = src.get("resource_uri", "") or src.get("uri", "")
            # Anzeige: bevorzugt Titel, ansonsten URI
            dbpedia_display = dbpedia_title or dbpedia_uri
            
            # Inferred aus Details
            inferred = entity.get('details', {}).get('inferred', entity.get('inferred', ''))
            
            # Zeile ausgeben
            print(f"{i+1:3} | {name:25} | {entity_type:15} | {inferred:10} | {wiki_label:25} | {wikidata_id:15} | {dbpedia_display:20}")
        
        print("-" * 100)
        print(f"Insgesamt {len(result['entities'])} Entitäten gefunden.")
        
        # Beziehungen nach explizit und implizit trennen
        explicit_relationships = [rel for rel in result["relationships"] if rel.get("inferred", "") == "explicit"]
        implicit_relationships = [rel for rel in result["relationships"] if rel.get("inferred", "") == "implicit"]
        
        # Explizite Beziehungen ausgeben
        print("\nExplizite Beziehungen (direkt im Text erwähnt):")
        print("-" * 140)
        print(f"{'Nr':3} | {'Subjekt':25} | {'SubjTyp':12} | {'SubjInf':10} | {'Prädikat':20} | {'Objekt':25} | {'ObjTyp':12} | {'ObjInf':10}")
        print("-" * 140)
        
        if explicit_relationships:
            for i, rel in enumerate(explicit_relationships):
                subject = rel['subject'][:25]
                subject_type = rel.get('subject_type', '')[:12]
                subject_inf = rel.get('subject_inferred', '')
                predicate = rel['predicate'][:20]
                obj = rel['object'][:25]
                object_type = rel.get('object_type', '')[:12]
                object_inf = rel.get('object_inferred', '')
                
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
                subject_inf = rel.get('subject_inferred', '')
                predicate = rel['predicate'][:20]
                obj = rel['object'][:25]
                object_type = rel.get('object_type', '')[:12]
                object_inf = rel.get('object_inferred', '')
                
                print(f"{i+1:3} | {subject:25} | {subject_type:12} | {subject_inf:10} | {predicate:20} | {obj:25} | {object_type:12} | {object_inf:10}")
        else:
            print("Keine impliziten Beziehungen gefunden.")
            
        print("-" * 140)
        print(f"Insgesamt {len(implicit_relationships)} implizite Beziehungen gefunden.")
        
        # Gesamtzahl der Beziehungen
        print(f"\nGesamtzahl der Beziehungen: {len(result['relationships'])}")
        
        # Nur Wikipedia-URLs anzeigen
        print("\nWikipedia-URLs:")
        for i, entity in enumerate(result["entities"]):
            if "sources" in entity and "wikipedia" in entity["sources"] and "url" in entity["sources"]["wikipedia"]:
                name = entity.get("entity", "")
                url = entity["sources"]["wikipedia"].get("url", "")
                if url:
                    print(f"{i+1}. {name}: {url}")
    else:
        # Alte Ausgabestruktur (nur Entitäten)
        print("\nExtrahierte Entitäten:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\nHinweis: RELATION_EXTRACTION ist nicht aktiviert oder es wurden keine Beziehungen gefunden.")

    # Log final results
    logging.info("Final results have been outputted in test_relationships.py")

if __name__ == "__main__":
    main()
