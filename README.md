# Entity Extractor & Linker (LLM-basiert)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/janschachtschabel/entity-extractor-linker)

Entity Extractor & Linker ist ein flexibles, modulares Tool zur automatisierten Extraktion und Generierung von Named Entities in bzw. zu beliebigen Texten. Es kann erkannte Entitäten direkt mit Informationen aus Wikipedia, Wikidata und DBpedia verknüpfen – inklusive mehrsprachiger Ausgaben (Deutsch, Englisch). Die Ergebnisse liegen in einer strukturierten JSON-Ausgabe vor, die Metadaten zu Entitäten und (optional) Beziehungen enthält. Beziehungen können als explizite (aus dem Text extrahierte) oder implizite (logisch geschlussfolgerte) Triple (Subjekt–Prädikat–Objekt) generiert und in interaktiven Knowledge Graphen visualisiert werden.

## Inhaltsverzeichnis

- [Installation](#installation)
- [Funktionen](#funktionen)
- [Anwendungsbeispiele](#anwendungsbeispiele)
- [Projektstruktur](#projektstruktur)
- [Vorteile](#vorteile)
- [Pipeline-Übersicht](#pipeline-übersicht)
- [Funktionsweise](#funktionsweise)
- [Tipps und Best Practices](#tipps-und-best-practices)
- [Konfiguration](#konfiguration)
- [Ausgabestruktur](#ausgabestruktur)
- [Lizenz](#lizenz)
- [Autor](#autor)

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

## Anwendungsbeispiele

```python
import json
from entityextractor.core.api import process_entities

text = "Albert Einstein war ein theoretischer Physiker."
config = {
    "LANGUAGE": "de",
    "MODEL": "gpt-4o-mini",
    "MODE": "extract",
    "USE_WIKIPEDIA": True
}
result = process_entities(text, config)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

### Beispiel-Musteroutput

```json
{
  "entities": [
    {
      "entity": "Albert Einstein",
      "details": {
        "typ": "Person",
        "inferred": "explicit",
        "citation": "Albert Einstein entwickelte die Relativitätstheorie.",
        "citation_start": 0,
        "citation_end": 52
      },
      "sources": {
        "wikipedia": {
          "label": "Albert Einstein",
          "url": "https://en.wikipedia.org/wiki/Albert_Einstein"
        }
      }
    }
  ],
  "relationships": [
    {
      "subject": "Albert Einstein",
      "predicate": "entwickelte",
      "object": "Relativitätstheorie",
      "inferred": "explicit",
      "subject_type": "Person",
      "object_type": "Theory",
      "subject_inferred": "explicit",
      "object_inferred": "explicit"
    }
  ],
  "statistics": {
    "total_entities": 1,
    "types_distribution": { "Person": 1 },
    "linked": {
      "wikipedia": { "count": 1, "percent": 100.0 },
      "wikidata": { "count": 0, "percent": 0.0 },
      "dbpedia": { "count": 0, "percent": 0.0 }
    },
    "top_wikipedia_categories": [],
    "top_wikidata_types": [],
    "entity_connections": [
      { "entity": "Albert Einstein", "count": 1 },
      { "entity": "Relativitätstheorie", "count": 1 }
    ],
    "top_wikidata_part_of": [],
    "top_wikidata_has_parts": [],
    "top_dbpedia_part_of": [],
    "top_dbpedia_has_parts": [],
    "top_dbpedia_subjects": []
  },
  "knowledgegraph_visualisation": {
    "static": "knowledge_graph.png",
    "interactive": "knowledge_graph_interactive.html"
  }
}
```

## Projektstruktur

```plaintext
.
├── .pytest_cache/                    # pytest Cache-Verzeichnis
├── lib/                              # Externe Bibliotheken
├── entityextractor/                  # Hauptpaket
│   ├── __init__.py
│   ├── main.py
│   ├── cache/                        # Zwischengespeicherte Daten (z. B. LLM Outputs, API-Antworten)
│   │   └── ...
│   ├── config/                       # Konfigurationsdateien
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/                         # Kernfunktionalität (Extraktion, Verknüpfung, Generierung, Inferenz)
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── extract_api.py
│   │   ├── generate_api.py
│   │   ├── link_api.py
│   │   ├── relationship_api.py
│   │   ├── orchestrator.py
│   │   ├── extractor.py
│   │   ├── generator.py
│   │   ├── linker.py
│   │   ├── entity_inference.py
│   │   ├── relationship_inference.py
│   │   ├── graph_visualization.py
│   │   ├── visualization_api.py
│   │   ├── response_formatter.py
│   │   ├── deduplication_utils.py
│   │   └── semantic_dedup_utils.py
│   ├── prompts/                      # Prompt-Definitionen
│   │   ├── __init__.py
│   │   ├── extract_prompts.py
│   │   ├── entity_inference_prompts.py
│   │   ├── deduplication_prompts.py
│   │   ├── generation_prompts.py
│   │   └── relationship_prompts.py
│   ├── services/                     # Externe Dienste (OpenAI, Wikipedia, Wikidata, DBpedia)
│   │   ├── openai_service.py
│   │   ├── wikipedia_service.py
│   │   ├── wikidata_service.py
│   │   └── dbpedia_service.py
│   └── utils/                        # Hilfsfunktionen
│       ├── __init__.py
│       ├── cache_utils.py
│       ├── category_utils.py         # Filter für irrelevante Wikipedia-Kategorien
│       ├── format_converter.py
│       ├── logging_utils.py
│       ├── prompt_utils.py
│       ├── text_utils.py
│       └── wiki_url_utils.py
├── example_extract.py                # Beispiel: Entitätsextraktion
├── example_extract_simple.py         # Einfaches Beispiel: Entitätsextraktion
├── example_generate.py               # Beispiel: Entitätsgenerierung
├── example_generate_simple.py        # Einfaches Beispiel: Entitätsgenerierung
├── example_relations.py              # Beispiel: Beziehungsinferenz
├── example_knowledgegraph.py         # Beispiel: Knowledge Graph
├── example_chunking.py               # Beispiel: Text-Chunking
├── example_compendium_person.py      # Beispiel: Wissenskompendium
├── knowledge_graph.png               # Generierte Knowledge Graph (PNG)
├── knowledge_graph_interactive.html  # Generierte Knowledge Graph (HTML)
├── NOTICE                            # Lizenz- und Rechtshinweise
├── requirements.txt                  # Projektabhängigkeiten
└── setup.py                          # Paket-Setup

## Vorteile

- Verarbeitung großer Texte in einem Schritt ohne vorherige Aufbereitung
- Besseres Kontextverständnis und weniger Fehler bei der Wahl der Entitätstypen
- Keine manuelle Satz-Splittung notwendig

## Pipeline-Übersicht

1. Entitätserkennung (Extract / Generate / Compendium)
2. Entitätsverlinkung (Wikipedia, Wikidata, DBpedia mit Fallback-Strategien)
3. Relationsextraktion und -inferenz (Tripelbildung explizit/implizit)
4. Knowledge Graph Completion & Visualisierung (PNG & interaktive HTML)

## Funktionsweise

Der Entity Extractor verarbeitet Text in mehreren Schritten:

1. **Entitätserkennung**: Identifikation von Entitäten im Text durch LLMs.
2. **Wikipedia-Integration**: Verknüpfung erkannter Entitäten mit Wikipedia-Artikeln und Extraktion von Zusammenfassungen.
3. **Wikidata-Integration**: Abruf von Wikidata-IDs, Typen und Beschreibungen.
4. **DBpedia-Integration**: Nutzung von DBpedia für zusätzliche strukturierte Informationen.
5. **Sprachübergreifende Verarbeitung**: Automatische Übersetzung und Suche in Deutsch und Englisch.
6. **Knowledge Graph Completion (KGC)**: Iterative Vervollständigung fehlender Relationen.
7. **Graph-Visualisierung**: Ausgabe als statisches PNG und interaktives HTML.

## Tipps und Best Practices

- Überprüfen Sie stets die korrekte `LANGUAGE`-Einstellung (`de` oder `en`).
- Aktivieren Sie `SHOW_STATUS=True` für detailliertes Logging bei Bedarf.
- CLI-Verwendung:
  ```bash
  entityextractor --text "Albert Einstein war ein theoretischer Physiker." \
                   --file input.txt \
                   --output result.json \
                   --language de \
                   --model gpt-4o
  ```
- Trainingsdatensammlung für OpenAI Fine-Tuning:
  Setzen Sie `COLLECT_TRAINING_DATA=True`. Die Anwendung erstellt JSONL-Dateien (`entity_extractor_training_openai.jsonl`, `entity_relationship_training_openai.jsonl`), bei denen jede Zeile ein JSON-Objekt mit `prompt` (Eingabetext) und `completion` (erwartete LLM-Ausgabe) enthält - direkt nutzbar für OpenAI Fine-Tuning.

## Konfiguration

Alle Einstellungen liegen in `entityextractor/config/settings.py` unter `DEFAULT_CONFIG`. Wichtige Optionen:

| Parameter                               | Typ                  | Standardwert                                 | Beschreibung |
|-----------------------------------------|----------------------|----------------------------------------------|--------------|
| `LLM_BASE_URL`                          | string               | `"https://api.openai.com/v1"`              | Basis-URL für die LLM-API |
| `MODEL`                                 | string               | `"gpt-4.1-mini"`                           | LLM-Modell |
| `OPENAI_API_KEY`                        | string or None       | `None`                                       | OpenAI API-Schlüssel (aus Umgebungsvariable laden) |
| `MAX_TOKENS`                            | int                  | `16000`                                      | Maximale Tokenanzahl pro Anfrage |
| `TEMPERATURE`                           | float                | `0.2`                                        | Sampling-Temperatur |
| `USE_WIKIPEDIA`                         | bool                 | `True`                                       | Wikipedia-Verknüpfung aktivieren |
| `USE_WIKIDATA`                          | bool                 | `False`                                      | Wikidata-Verknüpfung aktivieren |
| `USE_DBPEDIA`                           | bool                 | `False`                                      | DBpedia-Verknüpfung aktivieren |
| `ADDITIONAL_DETAILS`                    | bool                 | `False`                                      | Zusätzliche Details aus Wissensquellen aktivieren |
| `DBPEDIA_USE_DE`                        | bool                 | `False`                                      | Deutsche DBpedia-Server zuerst abfragen |
| `DBPEDIA_LOOKUP_API`                    | bool                 | `False`                                      | Fallback via DBpedia Lookup API aktivieren |
| `DBPEDIA_SKIP_SPARQL`                   | bool                 | `False`                                      | Nur Lookup API verwenden, keine SPARQL-Abfragen |
| `DBPEDIA_LOOKUP_MAX_HITS`               | int                  | `5`                                          | Maximale Trefferzahl für Lookup API |
| `DBPEDIA_LOOKUP_CLASS`                  | string or None       | `None`                                       | Optionale Ontologie-Klasse für Lookup API |
| `DBPEDIA_LOOKUP_FORMAT`                 | string               | `"json"`                                   | Antwortformat: `"json"`, `"xml"` oder `"both"` |
| `LANGUAGE`                              | string               | `"en"`                                     | Sprache der Verarbeitung ("de" oder "en") |
| `TEXT_CHUNKING`                         | bool                 | `False`                                      | Text-Chunking aktivieren |
| `TEXT_CHUNK_SIZE`                       | int                  | `2000`                                       | Zeichen pro Chunk |
| `TEXT_CHUNK_OVERLAP`                    | int                  | `50`                                         | Überlappung zwischen Chunks |
| `MODE`                                  | string               | `"extract"`                                | Modus: "extract", "generate" oder "compendium" |
| `MAX_ENTITIES`                          | int                  | `20`                                         | Maximale Anzahl der Entitäten |
| `ALLOWED_ENTITY_TYPES`                  | string               | `"auto"`                                   | Filter für erlaubte Entitätstypen ("auto" oder kommagetrennte Liste) |
| `ENABLE_ENTITY_INFERENCE`               | bool                 | `False`                                      | Implizite Entitätserkennung aktivieren |
| `RELATION_EXTRACTION`                   | bool                 | `False`                                      | Beziehungen zwischen Entitäten extrahieren |
| `ENABLE_RELATIONS_INFERENCE`            | bool                 | `False`                                      | Implizite Beziehungen ergänzen |
| `MAX_RELATIONS`                         | int                  | `15`                                         | Maximale Anzahl der Beziehungen pro Prompt |
| `ENABLE_KGC`                            | bool                 | `False`                                      | Knowledge Graph Completion aktivieren |
| `KGC_ROUNDS`                            | int                  | `3`                                          | Anzahl der KGC-Runden |
| `COLLECT_TRAINING_DATA`                 | bool                 | `False`                                      | Trainingsdatensammlung aktivieren |
| `OPENAI_TRAINING_DATA_PATH`             | string               | `"entity_extractor_training_openai.jsonl"` | Pfad für Entitäts-Trainingdaten |
| `OPENAI_RELATIONSHIP_TRAINING_DATA_PATH`| string               | `"entity_relationship_training_openai.jsonl"` | Pfad für Beziehungs-Trainingdaten |
| `TIMEOUT_THIRD_PARTY`                   | int                  | `15`                                         | Timeout für externe Dienste (Sekunden) |
| `SHOW_STATUS`                           | bool                 | `True`                                       | Status-/Logging-Meldungen anzeigen |
| `SUPPRESS_TLS_WARNINGS`                 | bool                 | `True`                                       | TLS-Warnungen unterdrücken |
| `ENABLE_GRAPH_VISUALIZATION`            | bool                 | `False`                                      | Statische PNG- und HTML-Graphen aktivieren (setzt RELATION_EXTRACTION voraus) |
| `GRAPH_LAYOUT_METHOD`                   | string               | `"spring"`                                 | Layoutmethode für statisches PNG: "spring" oder "kamada_kawai" |
| `GRAPH_LAYOUT_K`                        | float or None        | `None`                                       | Ideale Kantenlänge im Spring-Layout |
| `GRAPH_LAYOUT_ITERATIONS`               | int                  | `50`                                         | Iterationen für Spring-Layout |
| `GRAPH_PHYSICS_PREVENT_OVERLAP`         | bool                 | `True`                                       | Überlappungsprävention im Spring-Layout aktivieren |
| `GRAPH_PHYSICS_PREVENT_OVERLAP_DISTANCE`| float                | `0.1`                                        | Mindestabstand zwischen Knoten |
| `GRAPH_PHYSICS_PREVENT_OVERLAP_ITERATIONS`| int                | `50`                                         | Iterationen der Überlappungsprävention |
| `GRAPH_PNG_SCALE`                       | float                | `0.30`                                       | Skalierungsfaktor für das statische PNG-Layout |
| `GRAPH_HTML_INITIAL_SCALE`              | int                  | `10`                                         | Anfangs-Zoom im interaktiven HTML-Graph |
| `CACHE_ENABLED`                         | bool                 | `True`                                       | Globales Caching aktivieren |
| `CACHE_DIR`                             | string               | `"./cache"`                                | Verzeichnis für Cache-Dateien |
| `CACHE_WIKIPEDIA_ENABLED`               | bool                 | `True`                                       | Cache für Wikipedia-API aktivieren |
| `CACHE_WIKIDATA_ENABLED`                | bool                 | `True`                                       | Cache für Wikidata-API aktivieren |
| `CACHE_DBPEDIA_ENABLED`                 | bool                 | `True`                                       | Cache für DBpedia SPARQL aktivieren |
| `RATE_LIMIT_MAX_CALLS`                  | int                  | `3`                                          | Maximale Anzahl an API-Aufrufen pro Zeitraum (`RATE_LIMIT_PERIOD`) |
| `RATE_LIMIT_PERIOD`                     | int                  | `1`                                          | Zeitraum (Sekunden) für das Rate-Limiter-Fenster |
| `RATE_LIMIT_BACKOFF_BASE`               | int                  | `1`                                          | Basiswert für exponentielles Backoff bei HTTP 429 |
| `RATE_LIMIT_BACKOFF_MAX`                | int                  | `60`                                         | Maximale Backoff-Dauer (Sekunden) bei HTTP 429 |
| `USER_AGENT`                            | string               | `"EntityExtractor/1.0"`                    | HTTP `User-Agent`-Header für alle API-Anfragen |
| `WIKIPEDIA_MAXLAG`                      | int                  | `5`                                          | `maxlag`-Parameter für Wikipedia-API-Anfragen |

## Ausgabestruktur

Die Ausgabe liefert eine JSON-Struktur mit folgenden Feldern:

- **entities**: Liste erkannter Entitäten mit `entity`, `details` und `sources`.
- **relationships**: Liste von Triple-Objekten. Jede Beziehung besteht aus:
  - **subject**: Quell-Entität
  - **predicate**: Beziehungsart (z.B. "veröffentlichte")
  - **object**: Ziel-Entität
  - **inferred**: "explizit" oder "implizit"
  - **subject_type**: Typ der Quell-Entität
  - **object_type**: Typ der Ziel-Entität
  - **subject_inferred**: explizit/implizit für Quell-Entität
  - **object_inferred**: explizit/implizit für Ziel-Entität
- **statistics**: Objekt mit Statistiken zu Entitäten und Relationen:
  - **total_entities**: Gesamtanzahl der erkannten Entitäten
  - **types_distribution**: Verteilung der Entitätstypen (Typ → Anzahl)
  - **linked**: Verlinkungserfolg nach Quelle (`wikipedia`, `wikidata`, `dbpedia`)
  - **top_wikipedia_categories**: Top-10 Wikipedia-Kategorien nach Häufigkeit
  - **top_wikidata_types**: Top-10 Wikidata-Typen nach Häufigkeit
  - **entity_connections**: Anzahl eindeutiger Verknüpfungen pro Entität
  - **top_wikidata_part_of**, **top_wikidata_has_parts**, **top_dbpedia_part_of**, **top_dbpedia_has_parts**, **top_dbpedia_subjects**: Weitere Top-Statistiken für Teil-Beziehungen und DBpedia-Subjects

## Lizenz

Dieses Projekt ist unter der Apache 2.0 Lizenz veröffentlicht. Details siehe [LICENSE](LICENSE).

Weitere rechtliche Hinweise findest du in der [NOTICE](NOTICE).

## Autor

**Jan Schachtschabel**
