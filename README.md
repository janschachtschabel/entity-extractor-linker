# Entity Extractor and Linker (LLM based)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/janschachtschabel/entity-extractor-linker)

Entity Extractor and Linker ist ein leistungsstarkes Tool zur Erkennung, Extraktion und Anreicherung von Entitäten in Texten mit Informationen aus Wikipedia, Wikidata und DBpedia. Die Anwendung unterstützt mehrsprachige Ausgaben (Deutsch und Englisch) und bietet eine reichhaltige JSON-Struktur mit detaillierten Informationen zu jeder erkannten Entität. Zusätzlich können Beziehungen zwischen Entitäten erkannt und als explizite oder implizite Beziehungen klassifiziert werden.

## Inhaltsverzeichnis

- [Funktionen](#funktionen)
- [Modulare Struktur](#modulare-struktur)
- [Installation](#installation)
- [Verwendung](#verwendung)
- [Konfiguration](#konfiguration)
- [Ausgabestruktur](#ausgabestruktur)
- [Tipps und Best Practices](#tipps)
- [Fehlerbehebung](#fehlerbehebung)
- [Erweiterung](#erweiterung)
- [Lizenz](#lizenz)
- [Autor](#autor)

## Funktionen

- **KI-basierte Entitätserkennung** mit OpenAI-Modellen (GPT-4o-mini, GPT-4o, etc.)
- **Automatische Verknüpfung** mit Wikipedia-Artikeln und Extraktion von Zusammenfassungen
- **Wikidata-Integration** für strukturierte Daten wie Typen, Beschreibungen, Bilder und mehr
- **DBpedia-Unterstützung** für zusätzliche semantische Informationen
- **Triple-basierte Beziehungserkennung** zwischen Entitäten mit Subjekt-, Prädikat-, Objekt-Tripeln, Inferenz-Status (explizit/implizit) und Entitätstypen
- **Entity-Inferenz** zur Ergänzung impliziter Entitäten aus dem Kontext
- **Text-Chunking** zur Aufteilung langer Texte in überlappende Chunks für die Verarbeitung
- **Knowledge Graph Completion (KGC)** als iterativer Schritt zur Vervollständigung von Knowledge Graphs
- **Sammlung von Trainingsdaten** für das Finetuning bei OpenAI zur Verbesserung der Entitätserkennung mit korrigierten URLs
- **Mehrsprachige Unterstützung** für Deutsch und Englisch mit automatischer Übersetzung
- **Robuste Fehlerbehandlung** mit Fallback-Mechanismen für verschiedene Datenquellen
- **Modulare Architektur** für einfache Erweiterbarkeit und Wartung
- **Kommandozeilenschnittstelle** für schnelle Verarbeitung von Texten und Dateien
- **Umfangreiche Konfigurationsoptionen** für maximale Flexibilität

## Modulare Struktur

```
entityextractor/
├── __init__.py           # Paket-Initialisierung
├── main.py               # Haupteinstiegspunkt und CLI
├── config/               # Konfigurationsmodule
│   ├── __init__.py
│   └── settings.py       # Standardkonfiguration
├── core/                 # Kernfunktionalität
│   ├── __init__.py
│   ├── api.py            # Hauptschnittstelle
│   ├── extractor.py      # Entitätsextraktion
│   ├── linker.py         # Entitätsverknüpfung
│   ├── generator.py      # Entitätsgenerierung
│   ├── entity_inference.py # Entity-Inferenz für implizite Entitäten
│   └── relationship_inference.py # Beziehungserkennung und -inferenz
└── services/             # Externe Dienste
│   ├── __init__.py
│   ├── openai_service.py # OpenAI-Integration
│   ├── wikipedia_service.py # Wikipedia-Integration
│   ├── wikidata_service.py  # Wikidata-Integration
│   └── dbpedia_service.py   # DBpedia-Integration
└── utils/                # Hilfsfunktionen
    ├── __init__.py
    ├── logging_utils.py  # Logging-Funktionen
    └── text_utils.py     # Textverarbeitung
```

## Installation

### Voraussetzungen

- Python 3.8 oder höher
- OpenAI API-Schlüssel (als Umgebungsvariable `OPENAI_API_KEY`)

### Abhängigkeiten

Installieren Sie die benötigten Pakete mit:

```bash
pip install -r requirements.txt
```

### Installation als Paket

Sie können das Paket auch direkt installieren:

```bash
pip install -e .
```

Dies ermöglicht die Verwendung des `entityextractor`-Befehls in der Kommandozeile.

## Funktionsweise

Der Entity Extractor arbeitet in mehreren Schritten:

1. **Entitätserkennung**: Verwendet OpenAI-LLMs (wie GPT-4.1-mini), um Entitäten im Text zu identifizieren, ihren Typ zu bestimmen und Zitate zu extrahieren.
2. **Wikipedia-Integration**: Verknüpft erkannte Entitäten mit passenden Wikipedia-Artikeln und extrahiert Zusammenfassungen.
3. **Wikidata-Integration**: Holt Wikidata-IDs, Beschreibungen und Typen für die erkannten Entitäten.
4. **DBpedia-Integration**: Verbindet zu DBpedia, um zusätzliche strukturierte Informationen zu erhalten.
5. **Sprachübergreifende Verarbeitung**: Unterstützt sowohl deutsche als auch englische Ausgaben und kann zwischen Sprachversionen von Artikeln wechseln.
6. **Trainingsdatensammlung**: Kann optional korrigierte Entitätsdaten im JSONL-Format für OpenAI-Finetuning sammeln.

## Konfiguration

Die Anwendung ist hochgradig konfigurierbar über ein Konfigurationsobjekt. Alle Einstellungen haben sinnvolle Standardwerte, sodass nur die Werte angegeben werden müssen, die vom Standard abweichen sollen.

### Verfügbare Konfigurationsoptionen

| Parameter | Typ | Standardwert | Beschreibung |
|-----------|-----|--------------|-------------|
| `LANGUAGE` | string | `"de"` | Ausgabesprache ("de" oder "en") |
| `MODEL` | string | `"gpt-4.1-mini"` | OpenAI-Modell für die Entitätsextraktion |
| `MAX_ENTITIES` | int | `10` | Maximale Anzahl der zu extrahierenden/generierenden Entitäten |
| `USE_WIKIPEDIA` | bool | `True` | Wikipedia-Integration aktivieren |
| `USE_WIKIDATA` | bool | `True` | Wikidata-Integration aktivieren |
| `USE_DBPEDIA` | bool | `True` | DBpedia-Integration aktivieren |
| `ADDITIONAL_DETAILS` | bool | `False` | Abruf zusätzlicher Details aus den Wissensquellen aktivieren |
| `DBPEDIA_USE_DE` | bool | `True` | Deutsche DBpedia-Server verwenden |
| `TIMEOUT_THIRD_PARTY` | int | `20` | Timeout für externe API-Anfragen in Sekunden |
| `OPENAI_API_KEY` | string | `None` | OpenAI API-Schlüssel (None = aus Umgebungsvariable laden) |
| `SHOW_STATUS` | bool | `False` | Status-/Logging-Meldungen anzeigen |
| `SUPPRESS_TLS_WARNINGS` | bool | `True` | TLS-Warnungen von urllib3 unterdrücken |
| `COLLECT_TRAINING_DATA` | bool | `False` | Sammelt Trainingsdaten für Finetuning |
| `TRAINING_DATA_PATH` | string | `"entity_extractor_training_data.jsonl"` | Pfad zur JSONL-Datei für Trainingsdaten |
| `ALLOWED_ENTITY_TYPES` | string | `"auto"` | Zulässige Entitätstypen: "auto" für alle oder kommagetrennte Liste (z.B. "Person,Organization,Location") |
| `RELATION_EXTRACTION` | bool | `False` | Beziehungen zwischen Entitäten extrahieren |
| `ENABLE_RELATIONS_INFERENCE` | bool | `False` | Ergänzt nach expliziten Beziehungen auch implizite Beziehungen durch einen zweiten Prompt (siehe unten, betrifft Beziehungen, nicht Entitäten) |
| `MODE` | string | `"extract"` | Modus: "extract" (Entitäten aus Text extrahieren), "generate" (Entitäten zu einem Thema generieren) oder "compendium" (Erzeugt Entitäten wie im Generate-Modus, bringt jedoch gezielt Aspekte und Schwerpunkte für ein Bildungs­kompendium ein). |
| `TEXT_CHUNKING` | bool | `False` | Wenn True, wird langer Text in überlappende Chunks geteilt und stückweise verarbeitet. |
| `TEXT_CHUNK_SIZE` | int | `2000` | Maximale Zeichenlänge eines Text-Abschnitts (Chunk) beim Chunking. |
| `TEXT_CHUNK_OVERLAP` | int | `50` | Anzahl sich überlappender Zeichen zwischen aufeinanderfolgenden Chunks. |
| `ENABLE_KGC` | bool | `False` | Aktiviert nach der Extraktion einen Knowledge Graph Completion-Schritt zur Vervollständigung impliziter Beziehungen. |
| `KGC_ROUNDS` | int | `3` | Anzahl der Iterationen für die Knowledge Graph Completion (Wert zwischen 1 und 100). |
| `ENABLE_GRAPH_VISUALIZATION` | bool | `False` | Aktiviert die Ausgabe des Knowledge Graph als PNG und HTML (erfordert RELATION_EXTRACTION=True). |

### Beispiel-Konfiguration

```python
config = {
    "LANGUAGE": "en",          # Englische Ausgabe
    "MODEL": "gpt-4o",         # Leistungsfähigeres Modell verwenden
    "MAX_ENTITIES": 5,         # Maximal 5 Entitäten extrahieren
    "TIMEOUT_THIRD_PARTY": 30, # Längeres Timeout für externe APIs
    "USE_DBPEDIA": True        # DBpedia-Integration aktivieren
}
```

## Verwendung

### Einfache Verwendung

```python
import json
from entityextractor.core.api import process_entities

text = "Apple und Microsoft sind große Technologieunternehmen."
result = process_entities(text)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

### Erweiterte Verwendung mit Konfiguration

```python
import json
from entityextractor.core.api import process_entities

# --- Extraktionsmodus: Entitäten aus Text extrahieren ---
text = "Albert Einstein war ein theoretischer Physiker."
config_extract = {
    "LANGUAGE": "de",              # Ausgabesprache ("de" oder "en")
    "MODEL": "gpt-4.1-mini",       # OpenAI-Modell
    "MODE": "extract",             # Extraktionsmodus
    "USE_WIKIPEDIA": True,          # Wikipedia-Integration
    "USE_WIKIDATA": True,           # Wikidata-Integration
    "USE_DBPEDIA": False,           # DBpedia-Integration
    "SHOW_STATUS": True             # Logging-Ausgaben anzeigen
}
result = process_entities(text, config_extract)
print(json.dumps(result, ensure_ascii=False, indent=2))

# --- Generierungsmodus: Entitäten zu einem Thema generieren (inkl. Beziehungen) ---
topic = "Klassische Mechanik und ihre Anwendungen in der Physik"
config_generate = {
    "LANGUAGE": "en",
    "MODEL": "gpt-4.1-mini",
    "MODE": "generate",
    "MAX_ENTITIES": 10,
    "USE_WIKIPEDIA": True,
    "USE_WIKIDATA": True,
    "USE_DBPEDIA": True,
    "ALLOWED_ENTITY_TYPES": "Concept,Theory,Law,Formula",
    "RELATION_EXTRACTION": True,   # Beziehungen zwischen Entitäten generieren
    "SHOW_STATUS": True
}
result = process_entities(topic, config_generate)
print(json.dumps(result, ensure_ascii=False, indent=2))

# --- Extraktionsmodus mit Chunking und KGC ---
text = "Apple und Microsoft sind große Technologieunternehmen."
config_chunking = {
    "LANGUAGE": "de",
    "MODEL": "gpt-4o-mini",
    "MODE": "extract",
    "MAX_ENTITIES": 5,
    "USE_WIKIPEDIA": True,
    "USE_WIKIDATA": True,
    "USE_DBPEDIA": False,
    "TEXT_CHUNKING": True,
    "TEXT_CHUNK_SIZE": 2000,
    "TEXT_CHUNK_OVERLAP": 50,
    "ENABLE_KGC": True,
    "KGC_ROUNDS": 3
}
result = process_entities(text, config_chunking)
print(json.dumps(result, ensure_ascii=False, indent=2))

# --- Rückgabe-Struktur ---
# Das Ergebnis ist ein dict mit mindestens "entities" (Liste) und ggf. "relationships" (Liste von Tripeln)
# Beispiel:
# {
#   "entities": [...],
#   "relationships": [...],
#   "config": {...},
#   ...
# }

# --- Hinweise ---
# - Für reine Extraktion: MODE="extract" (Standard)
# - Für Generierung zu einem Thema: MODE="generate" (Topic als String übergeben)
# - RELATION_EXTRACTION (bzw. INFER_RELATIONSHIPS) aktiviert die Beziehungserkennung
# - ALLOWED_ENTITY_TYPES: Kommagetrennte Liste oder "auto" für alle Typen
# - OPENAI_API_KEY: None = aus Umgebungsvariable laden
# - DBpedia/Wikidata/Wikipedia lassen sich einzeln per USE_DBPEDIA, USE_WIKIDATA, USE_WIKIPEDIA steuern
```

### Verwendung über die Kommandozeile

Wenn Sie das Paket installiert haben, können Sie es auch über die Kommandozeile verwenden:

```bash
# Extrahiere Entitäten aus einem Text
entityextractor --text "Albert Einstein war ein theoretischer Physiker." --language de

# Extrahiere Entitäten aus einer Datei und speichere das Ergebnis
entityextractor --file input.txt --output result.json --language en --model gpt-4o
```

## Beispiel-Output

Ein typischer JSON-Output sieht wie folgt aus:

```json
[
  {
    "entity": "Johann Amos Comenius",
    "details": {
      "typ": "Person",
      "inferred": "explizit",
      "citation": "Johann Amos Comenius veröffentlichte 1632 sein Werk 'Didactica Magna', das als Grundlage der modernen Pädagogik gilt.",
      "citation_start": 0,
      "citation_end": 117
    },
    "sources": {
      "wikipedia": {
        "url": "https://de.wikipedia.org/wiki/Johann_Amos_Comenius",
        "label": "Johann Amos Comenius",
        "extract": "Johann Amos Comenius (deutsch auch Komenius, lateinisch Iohannes Amos Comenius, tschechisch Jan Amos Komenský, früherer Familienname Segeš; * 28. März 1592 in Nivnice, Mähren; † 15. November 1670 in Amsterdam) war ein mährischer Philosoph, Pädagoge und evangelischer Theologe. Comenius war Bischof der Böhmischen Brüder."
      }
    }
  },
  {
    "entity": "Didactica Magna",
    "details": {
      "typ": "Werk",
      "inferred": "explizit",
      "citation": "Johann Amos Comenius veröffentlichte 1632 sein Werk 'Didactica Magna', das als Grundlage der modernen Pädagogik gilt.",
      "citation_start": 0,
      "citation_end": 117
    },
    "sources": {
      "wikipedia": {
        "url": "https://de.wikipedia.org/wiki/Didactica_magna",
        "label": "Didactica magna",
        "extract": "Die Didactica Magna oder Große Didaktik wurde von Johann Amos Comenius zwischen 1627 und 1638 in lateinischer Sprache verfasst und im Jahr 1657 erstmals veröffentlicht."
      }
    }
  },
  {
    "entity": "1632",
    "details": {
      "typ": "Zeitraum",
      "inferred": "explizit",
      "citation": "Johann Amos Comenius veröffentlichte 1632 sein Werk 'Didactica Magna', das als Grundlage der modernen Pädagogik gilt.",
      "citation_start": 0,
      "citation_end": 117
    },
    "sources": {
      "wikipedia": {
        "url": "https://de.wikipedia.org/wiki/1632",
        "label": "1632",
        "extract": "Portal Geschichte | Portal Biografien | Aktuelle Ereignisse | Jahreskalender | Tagesartikel..."  
      }
    }
  },
  {
    "entity": "Pädagogik",
    "details": {
      "typ": "Wissenschaft",
      "inferred": "explizit",
      "citation": "Johann Amos Comenius veröffentlichte 1632 sein Werk 'Didactica Magna', das als Grundlage der modernen Pädagogik gilt.",
      "citation_start": 0,
      "citation_end": 117
    },
    "sources": {
      "wikipedia": {
        "url": "https://de.wikipedia.org/wiki/P%C3%A4dagogik",
        "label": "Pädagogik",
        "extract": "Pädagogik (Wortbildung aus altgriechisch…) sind Bezeichnungen für eine wissenschaftliche Disziplin..."
      }
    }
  }
]
```

## Ausgabestruktur

Die Ausgabe ist ein JSON-Objekt mit folgender Struktur, abhängig davon, ob die Beziehungserkennung aktiviert ist oder nicht.

### Basisstruktur

**Wenn `RELATION_EXTRACTION` deaktiviert ist:**

```json
[
  {
    "entity": "Entität",
    "details": { ... },
    "sources": { ... }
  },
  ...
]
```

**Wenn `RELATION_EXTRACTION` aktiviert ist:**

```json
{
  "entities": [ ... ],
  "relationships": [ ... ],
  "knowledgegraph_visualisation": [ ... ]
}
```

### Entitäten-Struktur

Jede Entität in der `entities`-Liste enthält folgende Eigenschaften:

- **entity**: Der Name der erkannten Entität
- **details**: Detailinformationen zur Entität
  - **typ**: Typ/Klasse der Entität (z.B. Person, Organisation, Ort)
  - **inferred**: Gibt an, ob die Entität explizit im Text erwähnt wird ("explizit") oder aus dem Kontext abgeleitet wurde ("implizit")
  - **citation**: Textstelle, die die Entität im Originaltext erwähnt
  - **citation_start**: Startposition der Textstelle
  - **citation_end**: Endposition der Textstelle
- **sources**: Informationen aus verschiedenen Quellen
  - **wikipedia**: Informationen aus Wikipedia
    - **url**: URL des entsprechenden Wikipedia-Artikels
    - **label**: Titel des Wikipedia-Artikels
    - **extract**: Auszug aus dem Wikipedia-Artikel

### Beziehungs-Struktur

Wenn `RELATION_EXTRACTION` aktiviert ist, enthält die Ausgabe eine Liste von Beziehungen zwischen den erkannten Entitäten:

```json
"relationships": [
  {
    "subject": "Johann Amos Comenius",
    "predicate": "veröffentlichte",
    "object": "Didactica Magna",
    "inferred": "explizit",
    "subject_type": "Person",
    "object_type": "Werk",
    "subject_inferred": "explizit",
    "object_inferred": "explizit"
  },
  {
    "subject": "Didactica Magna",
    "predicate": "veröffentlicht in",
    "object": "1632",
    "inferred": "explizit",
    "subject_type": "Werk",
    "object_type": "Zeitraum",
    "subject_inferred": "explizit",
    "object_inferred": "explizit"
  },
  {
    "subject": "Didactica Magna",
    "predicate": "ist grundlage von",
    "object": "Pädagogik",
    "inferred": "explizit",
    "subject_type": "Werk",
    "object_type": "Wissenschaft",
    "subject_inferred": "explizit",
    "object_inferred": "explizit"
  }
]
```

Jede Beziehung besteht aus:
- **subject**: Die Quell-Entität der Beziehung
- **predicate**: Die Art der Beziehung (z.B. "veröffentlichte", "ist Teil von")
- **object**: Die Ziel-Entität der Beziehung
- **inferred**: Gibt an, ob die Beziehung explizit im Text erwähnt wird ("explizit") oder aus dem Kontext abgeleitet wurde ("implizit")
- **subject_type**: Der Typ der Quell-Entität
- **object_type**: Der Typ der Ziel-Entität
- **subject_inferred**: Gibt an, ob die Quell-Entität explizit im Text erwähnt wird ("explizit") oder aus dem Kontext abgeleitet wurde ("implizit")
- **object_inferred**: Gibt an, ob die Ziel-Entität explizit im Text erwähnt wird ("explizit") oder aus dem Kontext abgeleitet wurde ("implizit")

## Tipps

### Optimale Spracheinstellungen

- **Für deutschsprachige Texte**:
  ```python
  config = {"LANGUAGE": "de"}
  ```
  Dies liefert deutsche Beschreibungen und bevorzugt deutsche Wikipedia-Artikel.

- **Für englischsprachige Texte**:
  ```python
  config = {"LANGUAGE": "en"}
  ```
  Dies liefert englische Beschreibungen und bevorzugt englische Wikipedia-Artikel.

### Modellauswahl nach Anwendungsfall

- **Für schnelle Verarbeitung mit guter Qualität**:
  ```python
  config = {"MODEL": "gpt-4o-mini"}
  ```

- **Für höchste Genauigkeit bei der Entitätserkennung**:
  ```python
  config = {"MODEL": "gpt-4o"}
  ```

### Performance-Optimierung

- **Schnellere Verarbeitung** (ohne DBpedia):
  ```python
  config = {"USE_DBPEDIA": False, "USE_WIKIDATA": True}
  ```

- **Nur grundlegende Informationen** (minimale API-Aufrufe):
  ```python
  config = {"USE_WIKIDATA": False, "USE_DBPEDIA": False}
  ```

- **Maximale Informationstiefe** (alle Quellen):
  ```python
  config = {"USE_WIKIPEDIA": True, "USE_WIKIDATA": True, "USE_DBPEDIA": True}
  ```

### Logging und Debugging

- **Ausführliches Logging für Debugging**:
  ```python
  config = {"SHOW_STATUS": True}
  ```

- **Stille Ausführung für Produktionsumgebungen**:
  ```python
  config = {"SHOW_STATUS": False}
  ```

### Trainingsdatensammlung

Die Anwendung bietet die Möglichkeit, Trainingsdaten für das Finetuning bei OpenAI zu sammeln. Dies ist besonders nützlich, um die Entitätserkennung mit korrigierten URLs und Metadaten zu verbessern.

```python
config = {
    "COLLECT_TRAINING_DATA": True,  # Aktiviert die Sammlung von Trainingsdaten
    "TRAINING_DATA_PATH": "meine_trainingsdaten.jsonl"  # Pfad zur JSONL-Datei für Trainingsdaten
}
```

Wenn aktiviert, speichert die Anwendung für jede Extraktion folgende Informationen:
- Den Originaltext
- Die erkannten Entitäten mit ihren Typen
- Die korrekten Wikipedia-, Wikidata- und DBpedia-Links

Diese Daten werden im JSONL-Format gespeichert und können direkt für das Finetuning eigener OpenAI-Modelle verwendet werden. Durch das Training mit diesen Daten kann die Genauigkeit der Entitätserkennung und -verknüpfung erheblich verbessert werden, insbesondere für domänenspezifische Anwendungen.

## Fehlerbehebung

### Häufige Probleme und Lösungen

| Problem | Lösung |
|---------|--------|
| **Timeout bei externen APIs** | Erhöhen Sie den Wert von `TIMEOUT_THIRD_PARTY` auf 30 oder mehr Sekunden |
| **Keine Verbindung zu DBpedia** | Prüfen Sie Ihre Internetverbindung oder deaktivieren Sie DBpedia mit `USE_DBPEDIA: False` |
| **Probleme mit deutschen DBpedia-Servern** | Verwenden Sie englische Server mit `DBPEDIA_USE_DE: False` |
| **OpenAI API-Fehler** | Prüfen Sie, ob Ihr API-Schlüssel gültig ist und als Umgebungsvariable gesetzt wurde |
| **Keine Entitäten gefunden** | Verwenden Sie ein leistungsfähigeres Modell wie `MODEL: "gpt-4o"` |
| **Falsche Entitäten erkannt** | Prüfen Sie die Spracheinstellung und verwenden Sie ein besseres Modell |

### Logging für Debugging

Für detaillierte Fehleranalyse aktivieren Sie das Logging:

```python
config = {"SHOW_STATUS": True}
```

## Erweiterung

### Eigene Datenquellen hinzufügen

1. Erstellen Sie ein neues Service-Modul in `entityextractor/services/`
2. Implementieren Sie die Funktionen zum Abrufen und Verarbeiten der Daten
3. Integrieren Sie den Service in `entityextractor/core/linker.py`
4. Fügen Sie Konfigurationsoptionen in `entityextractor/config/settings.py` hinzu

### Anpassung der Entitätsextraktion

Sie können die Entitätsextraktion anpassen, indem Sie:

1. Den Prompt in `entityextractor/services/openai_service.py` ändern
2. Eigene Nachverarbeitungslogik in `entityextractor/core/extractor.py` implementieren
3. Zusätzliche Metadaten in der Ausgabe in `entityextractor/core/api.py` hinzufügen

## Lizenz

Dieses Projekt ist unter der Apache 2.0 Lizenz veröffentlicht. Details siehe [LICENSE](LICENSE).

Weitere rechtliche Hinweise findest du in der [NOTICE](NOTICE)-Datei.

## Autor

**Jan Schachtschabel**
