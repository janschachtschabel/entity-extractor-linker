#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from nernel import link_entities

def main():
    # Beispieltext, wie in nernel.py verwendet
    example_text = (
        "Entity Linking (EL) ist eine Aufgabe, die benannte Entitäten im Text auf "
        "entsprechende Entitäten in einer Wissensdatenbank abbildet. Apple und Microsoft sind große Technologieunternehmen."
    )
    
    # Konfiguration definieren
    config = {
        "USE_WIKIPEDIA": True,     # Immer True, Wikipedia ist Pflicht
        "USE_WIKIDATA": True,      # Wikidata verwenden
        "USE_DBPEDIA": True,       # DBpedia verwenden
        "DBPEDIA_USE_DE": True,    # Deutsche DBpedia-Server verwenden
        "DBPEDIA_TIMEOUT": 15,     # Timeout in Sekunden für DBpedia-Anfragen
        "MODEL": "gpt-4.1-mini",    # LLM-Modell für die Entitätsextraktion
        "OPENAI_API_KEY": None,    # None = Aus Umgebungsvariable laden
        "LANGUAGE": "en",          # Englische Ausgabesprache
        "SHOW_STATUS": True,       # Status-/Logging-Meldungen anzeigen
        "SUPPRESS_TLS_WARNINGS": True,  # TLS-Warnungen von urllib3 unterdrücken
        "COLLECT_TRAINING_DATA": False,  # Trainingsdaten für Finetuning sammeln
        "TRAINING_DATA_PATH": "entity_extractor_training_data.jsonl"  # Pfad zur JSONL-Datei für Trainingsdaten
    }
    
    # Entitäten extrahieren
    print("\nExtrahiere Entitäten aus dem Text...")
    entities = link_entities(example_text, config=config)
    
    # Ausgabe formatieren
    print("\nGefundene Entitäten:")
    print(json.dumps(entities, ensure_ascii=False, indent=2))
    
    # Zugriff auf einzelne Entitäten demonstrieren
    if entities:
        print("\nZugriff auf einzelne Entitäten:")
        for i, entity in enumerate(entities):
            print(f"\nEntität {i+1}: {entity['entity']}")
            print(f"Typ: {entity['details']['typ']}")
            print(f"Zitat: {entity['details']['citation']}")
            
            # Wikidata-ID, falls vorhanden
            if "wikidata" in entity["sources"]:
                print(f"Wikidata-ID: {entity['sources']['wikidata'].get('id', 'Nicht verfügbar')}")
                
            # Wikipedia-URL, falls vorhanden
            if "wikipedia" in entity["sources"]:
                print(f"Wikipedia: {entity['sources']['wikipedia'].get('url', 'Nicht verfügbar')}")

if __name__ == "__main__":
    main()
