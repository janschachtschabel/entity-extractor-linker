# Entity Extractor & Linker (LLM-basiert)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/janschachtschabel/entity-extractor-linker)

Entity Extractor & Linker ist ein flexibles, modulares Tool zur automatisierten Extraktion und Generierung von Named Entities in bzw. zu beliebigen Texten. Es kann erkannte Entitäten direkt mit Informationen aus Wikipedia, Wikidata und DBpedia verknüpfen – inklusive mehrsprachiger Ausgaben (Deutsch, Englisch). Die Ergebnisse liegen in einer strukturierten JSON-Ausgabe vor, die Metadaten zu Entitäten und (optional) Beziehungen enthält. Beziehungen können als explizite (aus dem Text extrahierte) oder implizite (logisch geschlussfolgerte) Triple (Subjekt–Prädikat–Objekt) generiert und in interaktiven Knowledge Graphen visualisiert werden.

## Inhaltsverzeichnis

- [Installation](#installation)
- [Funktionen](#funktionen)
- [Anwendungsbeispiele](#anwendungsbeispiele)
- [Projektstruktur](#projektstruktur)
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
- **Entitäteninferenz**: Implizite logische Knoten ergänzen und Knowledge Graph vervollständigen.
- **Beziehungsinferenz**: Implizite logische Verbindungen ergänzen und Knowledge Graph vervollständigen.
- **Knowledge Graph Completion (KGC)**: Fehlende Relationen in mehreren Runden automatisch generieren.
- **Graph-Visualisierung**: Erzeuge statische PNG-Graphen oder interaktive HTML-Ansichten.
- **Kompendium-Generierung**: Erstellung eines kompendialen (zusammenfassenden) Textes mit Referenzen (optional mit Optimierungen für Bildung).
 **Trainingsdaten-Generierung**: Speichere Entity- und Relationship-Daten als JSONL für OpenAI Fine-Tuning.
- **LLM-Schnittstelle**: Kompatibel mit OpenAI-API, anpassbare Basis-URL und Modell.
- **Wissensquellen-Integration**: Wikipedia, Wikidata, DBpedia (SPARQL + Lookup API Fallback).
- **Caching**: Zwischenspeicherung von API-Antworten für schnellere wiederholte Zugriffe.
- **Ratelimiter**: Fängt Fehler mit Ratelimits der Wissensquellen ab.
- **Statistiken**: Vorberechnete Statistiken u.a. zu gehäuft auftretenen Kategorien.

## Anwendungsbeispiele

```python
import json
from entityextractor.core.api import process_entities

text = "Albert Einstein war ein theoretischer Physiker."
config = {
    "LANGUAGE": "en",
    "MODEL": "gpt-4.1-mini",
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
  },
  "compendium": {
    "text": "Albert Einstein war ein theoretischer Physiker, der die Relativitätstheorie entwickelte.",
    "references": [
      "https://en.wikipedia.org/wiki/Albert_Einstein",
      "https://de.wikipedia.org/wiki/Relativitätstheorie"
    ]
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
                   --model gpt-4o \
                   --enable-compendium True \
                   --compendium-length 8000
  ```
- Trainingsdatensammlung für OpenAI Fine-Tuning:
  Setzen Sie `COLLECT_TRAINING_DATA=True`. Die Anwendung erstellt JSONL-Dateien (`entity_extractor_training_openai.jsonl`, `entity_relationship_training_openai.jsonl`), bei denen jede Zeile ein JSON-Objekt mit `prompt` (Eingabetext) und `completion` (erwartete LLM-Ausgabe) enthält - direkt nutzbar für OpenAI Fine-Tuning.

## Konfiguration

Alle Einstellungen liegen in `entityextractor/config/settings.py` unter `DEFAULT_CONFIG`. Wichtige Optionen:

| Parameter                               | Typ                | Standardwert                                 | Beschreibung                                                                                          |
|-----------------------------------------|--------------------|----------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `LLM_BASE_URL`                          | string             | `"https://api.openai.com/v1"`              | Base-URL für die LLM-API                                                                               |
| `MODEL`                                 | string             | `"gpt-4.1-mini"`                            | LLM-Modell (empfohlen: `gpt-4.1-mini`, `gpt-4o-mini`)                                                 |
| `OPENAI_API_KEY`                        | string / None      | `None`                                       | API-Key setzen oder aus Umgebungsvariable                                                              |
| `MAX_TOKENS`                            | integer            | `16000`                                      | Maximale Tokenanzahl pro Anfrage                                                                       |
| `TEMPERATURE`                           | float              | `0.2`                                        | Sampling-Temperatur                                                                                   |
| `LANGUAGE`                              | string             | `"en"`                                      | Sprache der Verarbeitung (`de` oder `en`)                                                              |
| `TEXT_CHUNKING`                         | boolean            | `False`                                      | Text-Chunking aktivieren (`False` = ein LLM-Durchgang)                                                 |
| `TEXT_CHUNK_SIZE`                       | integer            | `1000`                                       | Chunk-Größe in Zeichen                                                                                |
| `TEXT_CHUNK_OVERLAP`                    | integer            | `50`                                         | Überlappung zwischen Chunks in Zeichen                                                                 |
| `MODE`                                  | string             | `"extract"`                                | Modus: `extract` oder `generate`                                                                       |
| `MAX_ENTITIES`                          | integer            | `15`                                         | Maximale Anzahl extrahierter Entitäten                                                                 |
| `ALLOWED_ENTITY_TYPES`                  | string             | `"auto"`                                    | Automatische Filterung erlaubter Entitätstypen                                                         |
| `ENABLE_ENTITY_INFERENCE`               | boolean            | `False`                                      | Implizite Entitätserkennung aktivieren                                                                 |
| `RELATION_EXTRACTION`                   | boolean            | `True`                                       | Relationsextraktion aktivieren                                                                         |
| `ENABLE_RELATIONS_INFERENCE`            | boolean            | `False`                                      | Implizite Relationen aktivieren                                                                         |
| `MAX_RELATIONS`                         | integer            | `15`                                         | Maximale Anzahl Beziehungen pro Prompt                                                                 |
| `USE_WIKIPEDIA`                         | boolean            | `True`                                       | Wikipedia-Verknüpfung aktivieren (immer `True`)                                                        |
| `USE_WIKIDATA`                          | boolean            | `False`                                      | Wikidata-Verknüpfung aktivieren                                                                         |
| `USE_DBPEDIA`                           | boolean            | `False`                                      | DBpedia-Verknüpfung aktivieren                                                                          |
| `DBPEDIA_USE_DE`                        | boolean            | `False`                                      | Deutsche DBpedia nutzen (Standard: False = englische DBpedia)                                           |
| `ADDITIONAL_DETAILS`                    | boolean            | `False`                                      | Zusätzliche Details aus allen Wissensquellen abrufen (mehr Infos, aber langsamer)                    |
| `DBPEDIA_LOOKUP_API`                    | boolean            | `True`                                       | Fallback via DBpedia Lookup API aktivieren                                                              |
| `DBPEDIA_SKIP_SPARQL`                   | boolean            | `False`                                      | SPARQL-Abfragen überspringen und nur Lookup-API verwenden                                              |
| `DBPEDIA_LOOKUP_MAX_HITS`               | integer            | `5`                                          | Maximale Trefferzahl für Lookup-API                                                                     |
| `DBPEDIA_LOOKUP_CLASS`                  | string / None      | `None`                                       | Optionale DBpedia-Ontology-Klasse für Lookup-API (derzeit ungenutzt)                                   |
| `DBPEDIA_LOOKUP_FORMAT`                 | string             | `"xml"`                                     | Response-Format: `"json"`, `"xml"` (empfohlen) oder `"beide"`                                      |
| `ENABLE_COMPENDIUM`                     | boolean            | `False`                                      | Kompendium-Generierung aktivieren                                                                       |
| `COMPENDIUM_LENGTH`                     | integer            | `8000`                                       | Anzahl der Zeichen für das Kompendium (ca. 4 A4-Seiten)                                                 |
| `COMPENDIUM_EDUCATIONAL_MODE`           | boolean            | `False`                                      | Bildungsmodus für Kompendium aktivieren                                                                 |
| `ENABLE_GRAPH_VISUALIZATION`            | boolean            | `False`                                      | Statische PNG- und interaktive HTML-Ansicht aktivieren (erfordert `RELATION_EXTRACTION=True`)         |
| `ENABLE_KGC`                            | boolean            | `False`                                      | Knowledge-Graph-Completion aktivieren (Vervollständigung mit impliziten Relationen)                   |
| `KGC_ROUNDS`                            | integer            | `3`                                          | Anzahl der KGC-Runden                                                                                   |
| `GRAPH_LAYOUT_METHOD`                   | string             | `"spring"`                                  | Layout: `"kamada_kawai"` (ohne K-/Iter-Param) oder `"spring"` (Fruchterman-Reingold)               |
| `GRAPH_LAYOUT_K`                        | integer / None     | `None`                                       | (Spring-Layout) Ideale Kantenlänge (None=Standard)                                                      |
| `GRAPH_LAYOUT_ITERATIONS`               | integer            | `50`                                         | (Spring-Layout) Anzahl der Iterationen                                                                  |
| `GRAPH_PHYSICS_PREVENT_OVERLAP`         | boolean            | `True`                                       | (Spring-Layout) Überlappungsprävention aktivieren                                                       |
| `GRAPH_PHYSICS_PREVENT_OVERLAP_DISTANCE`| float              | `0.1`                                        | (Spring-Layout) Mindestabstand zwischen Knoten                                                          |
| `GRAPH_PHYSICS_PREVENT_OVERLAP_ITERATIONS`| integer          | `50`                                         | (Spring-Layout) Iterationen zur Überlappungsprävention                                                  |
| `GRAPH_PNG_SCALE`                       | float              | `0.30`                                       | Skalierungsfaktor für statisches PNG-Layout (Standard `0.33`)                                           |
| `GRAPH_HTML_INITIAL_SCALE`              | integer            | `10`                                         | Anfangs-Zoom (network.moveTo scale): >1 rauszoomen, <1 reinzoomen                                         |
| `COLLECT_TRAINING_DATA`                 | boolean            | `False`                                      | Trainingsdaten für Fine-Tuning sammeln                                                                  |
| `OPENAI_TRAINING_DATA_PATH`             | string             | `"entity_extractor_training_openai.jsonl"` | Pfad für Entitäts-Trainingsdaten                                                                         |
| `OPENAI_RELATIONSHIP_TRAINING_DATA_PATH`| string             | `"entity_relationship_training_openai.jsonl"`| Pfad für Beziehungs-Trainingsdaten                                                                       |
| `TIMEOUT_THIRD_PARTY`                   | integer            | `15`                                         | Timeout für externe Dienste (Wikipedia, Wikidata, DBpedia)                                              |
| `RATE_LIMIT_MAX_CALLS`                  | integer            | `3`                                          | Maximale Anzahl Aufrufe pro Zeitraum                                                                    |
| `RATE_LIMIT_PERIOD`                     | integer            | `1`                                          | Zeitraum für das Rate-Limiter-Fenster (Sekunden)                                                         |
| `RATE_LIMIT_BACKOFF_BASE`               | integer            | `1`                                          | Basiswert für exponentielles Backoff bei HTTP 429                                                       |
| `RATE_LIMIT_BACKOFF_MAX`                | integer            | `60`                                         | Maximale Backoff-Dauer (Sekunden) bei HTTP 429                                                           |
| `USER_AGENT`                            | string             | `"EntityExtractor/1.0"`                    | HTTP User-Agent-Header für alle API-Anfragen                                                            |
| `WIKIPEDIA_MAXLAG`                      | integer            | `5`                                          | Maxlag-Parameter für Wikipedia-API-Anfragen                                                              |
| `CACHE_ENABLED`                         | boolean            | `True`                                       | Caching global aktivieren oder deaktivieren                                                              |
| `CACHE_DIR`                             | string             | `os.path.join(..., "cache")`               | Verzeichnis für Cache-Dateien innerhalb des Pakets (bei Bedarf erstellen)                                |
| `CACHE_DBPEDIA_ENABLED`                 | boolean            | `True`                                       | Caching für DBpedia-SPARQL-Abfragen aktivieren                                                           |
| `CACHE_WIKIDATA_ENABLED`                | boolean            | `True`                                       | Caching für Wikidata-API aktivieren                                                                      |
| `CACHE_WIKIPEDIA_ENABLED`               | boolean            | `True`                                       | Caching für Wikipedia-API-Anfragen aktivieren                                                            |
| `SHOW_STATUS`                           | boolean            | `True`                                       | Statusmeldungen anzeigen                                                                                |
| `SUPPRESS_TLS_WARNINGS`                 | boolean            | `True`                                       | TLS-Warnungen unterdrücken                                                                              |

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
- **compendium**: Objekt mit `text` (kompendialer Text) und `references` (Liste der verwendeten Quellen-URLs)

## Lizenz

Dieses Projekt ist unter der Apache 2.0 Lizenz veröffentlicht. Details siehe [LICENSE](LICENSE).

Weitere rechtliche Hinweise findest du in der [NOTICE](NOTICE).

## Autor

**Jan Schachtschabel**
