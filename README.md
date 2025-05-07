# Entity Extractor & Linker (LLM-basiert)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/janschachtschabel/entity-extractor-linker)

Entity Extractor and Linker ist ein leistungsstarkes Tool zur Extraktion von Entitäten in Texten mit Informationen aus Wikipedia, Wikidata und DBpedia. Die Anwendung unterstützt mehrsprachige Ausgaben (Deutsch und Englisch) und bietet eine reichhaltige JSON-Struktur mit detaillierten Informationen zu jeder erkannten Entität. Zusätzlich können Beziehungen zwischen Entitäten erkannt und als explizite oder implizite Beziehungen klassifiziert werden.

## Inhaltsverzeichnis

- [Installation](#installation)
- [Funktionen](#funktionen)
- [Konfiguration](#konfiguration)
- [Anwendungsbeispiele](#anwendungsbeispiele)
- [Ausgabestruktur](#ausgabestruktur)
- [Lizenz](#lizenz)
- [NOTICE](#notice)
- [Projektstruktur](#projektstruktur)
- [Funktionsweise](#funktionsweise)
- [Tipps und Best Practices](#tipps-und-best-practices)
- [Fehlerbehebung](#fehlerbehebung)
- [Erweiterung](#erweiterung)

## Installation

```bash
# Repository klonen
git clone https://github.com/janschachtschabel/entity-extractor-linker.git
cd entity-extractor-linker

# Option 1: Entwicklungsinstallation (empfohlen)
pip install -e .

# Option 2: Produktion
pip install entity-extractor-linker
```

Setze anschließend den OpenAI API Key in der Umgebungsvariable:

```bash
export OPENAI_API_KEY="<dein_api_key>"
```

## Funktionen

- **Entitäten extrahieren**: Direkt aus Texten identifizieren (extrahieren).
- **Entitäten generieren**: Kontextbasiert neue Entitäten vorschlagen (generieren).
- **Beziehungsextraktion**: Explizite Beziehungen (Subjekt; Prädikat; Objekt) im Text erkennen.
- **Beziehungsinferenz**: Implizite logische Verbindungen ergänzen und Knowledge Graph vervollständigen.
- **Knowledge Graph Completion (KGC)**: Fehlende Relationen in mehreren Runden automatisch generieren.
- **Graph-Visualisierung**: Erzeuge statische PNG-Graphen oder interaktive HTML-Ansichten.
- **Trainingsdaten-Generierung**: Speichere Entity- und Relationship-Daten als JSONL für OpenAI Fine-Tuning.
- **LLM-Schnittstelle**: Kompatibel mit OpenAI-API, anpassbare Basis-URL und Modell.
- **Wissensquellen-Integration**: Wikipedia, Wikidata, DBpedia (SPARQL + Lookup API Fallback).
- **Caching**: Zwischenspeicherung von API-Antworten für schnellere wiederholte Zugriffe.

## Projektstruktur

```plaintext
.
├── README.md
├── README-alt.md
├── NOTICE
├── requirements.txt
├── setup.py
├── example_extract.py
├── example_extract_simple.py
├── example_generate.py
├── example_generate_simple.py
├── example_relations.py
├── example_knowledgegraph.py
├── example_chunking.py
├── example_compendium_person.py
├── lib/                      # Externe Bibliotheken
│   └── ...
├── entityextractor/          # Hauptpaket
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── extractor.py
│   │   ├── linker.py
│   │   ├── generator.py
│   │   ├── entity_inference.py
│   │   ├── relationship_inference.py
│   │   ├── graph_visualization.py
│   │   └── visualization_api.py
│   ├── prompts/             # Prompt-Definitionen
│   │   └── ...
│   ├── services/            # Externe Dienste
│   │   ├── openai_service.py
│   │   ├── wikipedia_service.py
│   │   ├── wikidata_service.py
│   │   └── dbpedia_service.py
│   ├── utils/               # Hilfsfunktionen
│   │   ├── logging_utils.py
│   │   └── text_utils.py
│   └── cache/               # Cache-Dateien (Wikipedia, Wikidata, DBpedia)
│       └── ...
└── .pytest_cache/            # Pytest Cache-Verzeichnis
```

## Funktionsweise

Der Entity Extractor verarbeitet Text in mehreren Schritten:

1. **Entitätserkennung**: Identifikation von Entitäten im Text durch LLMs.
2. **Wikipedia-Integration**: Verknüpfung erkannter Entitäten mit Wikipedia-Artikeln und Extraktion von Zusammenfassungen.
3. **Wikidata-Integration**: Abruf von Wikidata-IDs, Typen und Beschreibungen.
4. **DBpedia-Integration**: Nutzung von DBpedia für zusätzliche strukturierte Informationen.
5. **Sprachübergreifende Verarbeitung**: Automatische Übersetzung und Suche in Deutsch und Englisch.
6. **Knowledge Graph Completion (KGC)**: Iterative Vervollständigung fehlender Relationen.
7. **Graph-Visualisierung**: Ausgabe als statisches PNG und interaktives HTML.

## Konfiguration

Alle Einstellungen liegen in `entityextractor/config/settings.py` unter `DEFAULT_CONFIG`. Wichtige Optionen:

| Parameter                                            | Typ           | Standardwert                                         | Beschreibung                                                    |
|------------------------------------------------------|---------------|------------------------------------------------------|------------------------------------------------------------------|
| `LLM_BASE_URL`                                       | string        | `"https://api.openai.com/v1"`                     | Base URL für LLM API                                             |
| `MODEL`                                              | string        | `"gpt-4.1-mini"`                                  | LLM-Modell                                                       |
| `OPENAI_API_KEY`                                     | string        | `None`                                             | OpenAI-API-Key (aus Umgebung)                                    |
| `MAX_TOKENS`                                         | int           | `16000`                                            | Maximale Tokenzahl pro Anfrage                                    |
| `TEMPERATURE`                                        | float         | `0.2`                                              | Sampling-Temperatur                                              |
| `USE_WIKIPEDIA`                                      | bool          | `True`                                             | Wikipedia-Integration aktivieren                                 |
| `USE_WIKIDATA`                                       | bool          | `False`                                            | Wikidata-Integration aktivieren                                  |
| `USE_DBPEDIA`                                        | bool          | `False`                                            | DBpedia-Integration aktivieren                                   |
| `ADDITIONAL_DETAILS`                                 | bool          | `False`                                            | Zusätzliche Details aus Wissensquellen abrufen                  |
| `DBPEDIA_USE_DE`                                     | bool          | `False`                                            | Deutsche DBpedia zuerst abfragen                                 |
| `DBPEDIA_LOOKUP_API`                                 | bool          | `False`                                            | DBpedia Lookup API verwenden                                     |
| `DBPEDIA_SKIP_SPARQL`                                | bool          | `False`                                            | Nur Lookup API, kein SPARQL                                       |
| `DBPEDIA_LOOKUP_MAX_HITS`                            | int           | `5`                                                | Max. Trefferzahl für Lookup API                                  |
| `DBPEDIA_LOOKUP_CLASS`                               | string/null   | `None`                                             | Optionale Ontologie-Klasse für Lookup API                        |
| `DBPEDIA_LOOKUP_FORMAT`                              | string        | `"json"`                                         | Format: "json", "xml" oder "both"                          |
| `LANGUAGE`                                           | string        | `"en"`                                           | Verarbeitungs-Sprache ("de" oder "en")                      |
| `TEXT_CHUNKING`                                      | bool          | `False`                                            | Text-Chunking aktivieren                                         |
| `TEXT_CHUNK_SIZE`                                    | int           | `2000`                                             | Chunk-Größe in Zeichen                                           |
| `TEXT_CHUNK_OVERLAP`                                 | int           | `50`                                               | Überlappung zwischen Chunks                                      |
| `MODE`                                               | string        | `"extract"`                                       | Modus: extract, generate oder compendium                         |
| `MAX_ENTITIES`                                       | int           | `20`                                               | Max. Anzahl extrahierter Entitäten                              |
| `ALLOWED_ENTITY_TYPES`                               | string        | `"auto"`                                         | Automatische Filterung von Typen                                  |
| `ENABLE_ENTITY_INFERENCE`                            | bool          | `False`                                            | Implizite Entitäten aktivieren                                    |
| `RELATION_EXTRACTION`                                | bool          | `False`                                            | Relationsextraction aktivieren                                   |
| `ENABLE_RELATIONS_INFERENCE`                         | bool          | `False`                                            | Implizite Relation-Inferenz aktivieren                           |
| `MAX_RELATIONS`                                      | int           | `15`                                               | Max. Anzahl Relationen pro Prompt                                |
| `ENABLE_KGC`                                         | bool          | `False`                                            | Knowledge Graph Completion aktivieren                            |
| `KGC_ROUNDS`                                         | int           | `3`                                                | Anzahl Runden für KGC                                             |
| `COLLECT_TRAINING_DATA`                              | bool          | `False`                                            | Trainingsdaten sammeln                                            |
| `OPENAI_TRAINING_DATA_PATH`                          | string        | `"entity_extractor_training_openai.jsonl"`     | Pfad für Entity-Trainingsdaten                                   |
| `OPENAI_RELATIONSHIP_TRAINING_DATA_PATH`             | string        | `"entity_relationship_training_openai.jsonl"`   | Pfad für Relation-Trainingsdaten                                 |
| `TIMEOUT_THIRD_PARTY`                                | int           | `15`                                               | Timeout für externe Dienste                                      |
| `SHOW_STATUS`                                        | bool          | `True`                                             | Statusmeldungen anzeigen                                          |
| `SUPPRESS_TLS_WARNINGS`                              | bool          | `True`                                             | TLS-Warnungen unterdrücken                                        |
| `ENABLE_GRAPH_VISUALIZATION`                         | bool          | `False`                                            | PNG & HTML-Graph aktivieren                                       |
| `GRAPH_LAYOUT_METHOD`                                | string        | `"spring"`                                       | Layout: "kamada_kawai" oder "spring"                         |
| `GRAPH_LAYOUT_K`                                     | float/null    | `None`                                             | Ideale Kantenlänge (Spring)                                       |
| `GRAPH_LAYOUT_ITERATIONS`                            | int           | `50`                                               | Iterationen für Spring-Layout                                     |
| `GRAPH_PHYSICS_PREVENT_OVERLAP`                      | bool          | `True`                                             | Überlappungsprävention aktivieren                                 |
| `GRAPH_PHYSICS_PREVENT_OVERLAP_DISTANCE`             | float         | `0.1`                                              | Mindestabstand für Überlappung                                    |
| `GRAPH_PHYSICS_PREVENT_OVERLAP_ITERATIONS`           | int           | `50`                                               | Iterationen Overlap-Prevention                                   |
| `GRAPH_PNG_SCALE`                                    | float         | `0.30`                                            | Skalierungsfaktor für statisches PNG                              |
| `GRAPH_HTML_INITIAL_SCALE`                           | int           | `10`                                               | Anfangs-Zoom im interaktiven HTML-Graph                           |
| `CACHE_ENABLED`                                      | bool          | `True`                                             | Globales Caching aktivieren                                       |
| `CACHE_DIR`                                          | string        | `./cache`                                          | Verzeichnis für Cache-Dateien                                     |
| `CACHE_DBPEDIA_ENABLED`                              | bool          | `True`                                             | DBpedia SPARQL-Cache aktivieren                                   |
| `CACHE_WIKIDATA_ENABLED`                             | bool          | `True`                                             | Wikidata-API-Cache aktivieren                                      |
| `CACHE_WIKIPEDIA_ENABLED`                            | bool          | `True`                                             | Wikipedia-API-Cache aktivieren                                     |

Alle Einstellungen können via `process_entities(text, user_config)` überschrieben werden.

## Ausgabestruktur

> **Hinweis:** Die tatsächliche Ausgabe kann je nach verwendetem Modell, den Datenquellen und dem Textkontext variieren und ist nicht in allen Fällen vollständig oder korrekt.

JSON-Output:
```json
{
  "entities": [
    {
      "entity": "Albert Einstein",
      "details": { "typ": "Person", "inferred": "explicit", "citation": "...", "citation_start": 0, "citation_end": 52 },
      "sources": { "wikipedia": { "label": "...", "url": "...", "extract": "..." } }
    },
    {
      "entity": "Theory of relativity",
      "details": { "typ": "Theory", "inferred": "explicit", "citation": "...", "citation_start": 0, "citation_end": 52 },
      "sources": { "wikipedia": { "label": "...", "url": "...", "extract": "..." } }
    }
  ],
  "relationships": [
    {
      "subject": "Albert Einstein",
      "predicate": "developed",
      "object": "Theory of relativity",
      "inferred": "explicit",
      "subject_type": "Person",
      "object_type": "Theory",
      "subject_inferred": "explicit",
      "object_inferred": "explicit"
    }
  ],
  "knowledgegraph_visualisation": [
    { "static": "knowledge_graph.png", "interactive": "knowledge_graph_interactive.html" }
  ]
}
```

**Feldbeschreibung**:

- **entities**: Liste erkannter Entitäten
  - **entity**: Name
  - **details**: Metadaten (Typ, Inferenz-Status, Zitat & Position)
  - **sources**: Daten aus Wissensquellen (z. B. `wikipedia.extract`)
- **relationships**: Liste der Tripel
  - Subjekt, Prädikat, Objekt plus Typ- und Inferenz-Flags
- **knowledgegraph_visualisation**: Pfade zu generierten Graph-Dateien (PNG & HTML)

## Anwendungsbeispiele

### Einfaches Python-Beispiel
```python
from entityextractor.core.api import process_entities
import json

text = "Albert Einstein entwickelte die Relativitätstheorie."
result = process_entities(text)
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 1. Entitäten extrahieren

```bash
python example_extract.py
```

### 2. Entitäten generieren

```bash
python example_generate.py
```

### 3. Relationen erkennen und inferieren

```bash
python example_relations.py
```

### 4. Knowledge Graph generieren

```bash
python example_knowledgegraph.py
```

Mehr Details findest du in den Beispielskripten im Repository.

## Tipps und Best Practices

- **Sprachauswahl**: Setze `LANGUAGE` auf `"de"` für deutsche oder `"en"` für englische Ausgaben.
- **Modellauswahl**: Verwende `MODEL: "gpt-4o"` für höchste Genauigkeit, `"gpt-4o-mini"` für schnellere Ergebnisse.
- **Performance**: Deaktiviere `USE_DBPEDIA` oder `USE_WIKIDATA`, um API-Aufrufe zu reduzieren.
- **Chunking und KGC**: Aktiviere `TEXT_CHUNKING` und `ENABLE_KGC` für lange Texte und vollständige Graphen.
- **Logging**: Setze `SHOW_STATUS` auf `True` für detaillierte Ausgaben beim Debugging.

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| **Timeout bei externen APIs** | Erhöhe `TIMEOUT_THIRD_PARTY` auf ≥30 Sekunden |
| **Keine Verbindung zu DBpedia** | Prüfe Netzwerk oder deaktiviere DBpedia (`USE_DBPEDIA: False`) |
| **Wikidata liefert keine Ergebnisse** | Aktiviere mehrsprachige Suche (`USE_WIKIDATA: True`) und teste alternative Synonyme |
| **OpenAI API-Fehler** | Verifiziere `OPENAI_API_KEY` und Modell-Kompatibilität |
| **Keine Entitäten gefunden** | Erhöhe `MAX_ENTITIES` oder wechsle zu leistungsfähigerem Modell |

## Erweiterung

1. **Neue Datenquellen**: Erstelle ein Modul in `entityextractor/services/`, implementiere Abruf- und Verarbeitungsfunktionen, integriere es im `linker`.
2. **Prompt-Anpassung**: Passe Prompts in `entityextractor/services/openai_service.py` an.
3. **Nachverarbeitung**: Ergänze eigene Logik in `entityextractor/core/extractor.py` oder in `core/api.py`.
4. **Konfiguration**: Füge neue Optionen in `config/settings.py` `DEFAULT_CONFIG` hinzu.

## Lizenz

Dieses Projekt steht unter der Apache License 2.0. Siehe [LICENSE](LICENSE) für Details.

## NOTICE

Für Namensnennung und weitere rechtliche Hinweise siehe die [NOTICE](NOTICE) Datei.
