# Entity Extractor

Entity Extractor ist ein leistungsstarkes Tool zur Erkennung, Extraktion und Anreicherung von Entitäten in Texten mit Informationen aus Wikipedia, Wikidata und DBpedia. Die Anwendung unterstützt mehrsprachige Ausgaben (Deutsch und Englisch) und bietet eine reichhaltige JSON-Struktur mit detaillierten Informationen zu jeder erkannten Entität.

## Installation

### Voraussetzungen

- Python 3.8 oder höher
- OpenAI API-Schlüssel (als Umgebungsvariable `OPENAI_API_KEY`)

### Abhängigkeiten

Installieren Sie die benötigten Pakete mit:

```bash
pip install -r requirements.txt
```

## Funktionsweise

Der Entity Extractor arbeitet in mehreren Schritten:

1. **Entitätserkennung**: Verwendet OpenAI-LLMs (wie GPT-4o-mini), um Entitäten im Text zu identifizieren, ihren Typ zu bestimmen und Zitate zu extrahieren.
2. **Wikipedia-Integration**: Verknüpft erkannte Entitäten mit passenden Wikipedia-Artikeln und extrahiert Zusammenfassungen.
3. **Wikidata-Anreicherung**: Holt Wikidata-IDs, Beschreibungen und Typen für die erkannten Entitäten.
4. **DBpedia-Integration**: Verbindet zu DBpedia, um zusätzliche strukturierte Informationen zu erhalten.
5. **Sprachübergreifende Verarbeitung**: Unterstützt sowohl deutsche als auch englische Ausgaben und kann zwischen Sprachversionen von Artikeln wechseln.

## Konfiguration

Die Anwendung ist hochgradig konfigurierbar über ein Konfigurationsobjekt:

```python
config = {
    "USE_WIKIPEDIA": True,     # Immer True, Wikipedia ist Pflicht
    "USE_WIKIDATA": True,      # Wikidata verwenden
    "USE_DBPEDIA": True,       # DBpedia verwenden
    "DBPEDIA_USE_DE": True,    # Deutsche DBpedia-Server verwenden
    "DBPEDIA_TIMEOUT": 15,     # Timeout in Sekunden für DBpedia-Anfragen
    "MODEL": "gpt-4o-mini",    # LLM-Modell für die Entitätsextraktion
    "OPENAI_API_KEY": None,    # None = Aus Umgebungsvariable laden
    "LANGUAGE": "de",          # Deutsche (de) oder Englische (en) Ausgabesprache
    "SHOW_STATUS": True,       # Status-/Logging-Meldungen anzeigen
    "SUPPRESS_TLS_WARNINGS": True  # TLS-Warnungen von urllib3 unterdrücken
}
```

## Verwendung

### Einfache Verwendung

```python
import json
from nernel import link_entities_to_wikidata

text = "Apple und Microsoft sind große Technologieunternehmen."
entities = link_entities_to_wikidata(text)
print(json.dumps(entities, ensure_ascii=False, indent=2))
```

### Erweiterte Verwendung mit Konfiguration

```python
import json
from nernel import link_entities_to_wikidata

text = "Albert Einstein war ein theoretischer Physiker."
config = {
    "LANGUAGE": "en",          # Englische Ausgabe
    "MODEL": "gpt-4o",         # Alternatives Modell verwenden
    "SHOW_STATUS": False,      # Logging-Ausgaben unterdrücken
    "DBPEDIA_TIMEOUT": 30      # Längeres Timeout für DBpedia
}
entities = link_entities_to_wikidata(text, config=config)
print(json.dumps(entities, ensure_ascii=False, indent=2))
```

## Beispiel-Output

Ein typischer JSON-Output sieht wie folgt aus:

```json
[
  {
    "entity": "Apple",
    "details": {
      "typ": "Organisation",
      "citation": "Apple und Microsoft sind große Technologieunternehmen.",
      "citation_start": 0,
      "citation_end": 54
    },
    "sources": {
      "wikipedia": {
        "url": "https://de.wikipedia.org/wiki/Apple",
        "extract": "Apple Inc. [ˈæpəlˌɪŋk] ist ein US-amerikanischer Hard- und Softwareentwickler und ein Technologieunternehmen, das Computer, Smartphones und Unterhaltungselektronik sowie Betriebssysteme und Anwendungssoftware entwickelt und vertreibt..."
      },
      "wikidata": {
        "id": "Q312",
        "description": "US-amerikanisches Technologieunternehmen mit Hauptsitz in Cupertino, Kalifornien",
        "types": [
          "wirtschaftlich selbständige Organisationseinheit",
          "gewerbliche oder kaufmännische Geschäftseinheit",
          "Unternehmen, das auf Technologie spezialisiert ist"
        ]
      },
      "dbpedia": {
        "resource_uri": "http://dbpedia.org/resource/Apple_Inc.",
        "endpoint": "http://dbpedia.org/sparql",
        "language": "en",
        "title": "Apple Inc.",
        "labels": ["Apple Inc."],
        "abstract": "Apple Inc. is an American multinational technology company...",
        "types": [
          "http://www.w3.org/2002/07/owl#Thing",
          "http://dbpedia.org/ontology/Company",
          "http://schema.org/Organization"
        ]
      }
    }
  }
]
```

## Ausgabestruktur

- **entity**: Der Name der erkannten Entität
- **details**: Grundlegende Informationen
  - **typ**: Typ/Klasse der Entität (z.B. Person, Organisation, Ort)
  - **citation**: Originaler Textausschnitt, in dem die Entität erwähnt wird
  - **citation_start**: Position im Text, wo das Zitat beginnt (Zeichenindex)
  - **citation_end**: Position im Text, wo das Zitat endet (Zeichenindex)
- **sources**: Informationen aus verschiedenen Wissensquellen
  - **wikipedia**: Wikipedia-Informationen inkl. URL und Extrakt
  - **wikidata**: Wikidata-Informationen inkl. ID, Beschreibung und Typen
  - **dbpedia**: DBpedia-Informationen inkl. Ressource-URI, Typen und Abstract

## Tipps

1. **Sprachauswahl**:
   - Für deutsche Texte mit deutschen Ausgaben setzen Sie `LANGUAGE: "de"`
   - Für englische Texte oder Ausgaben setzen Sie `LANGUAGE: "en"`

2. **Fehlerbehebung**:
   - Bei Timeout-Problemen mit DBpedia erhöhen Sie `DBPEDIA_TIMEOUT`
   - Bei Problemen mit deutschen DBpedia-Servern setzen Sie `DBPEDIA_USE_DE: False`

3. **Leistungsoptimierung**:
   - Für schnellere Antworten können Sie `USE_DBPEDIA: False` setzen
   - Für bessere Entitätserkennung verwenden Sie leistungsfähigere Modelle wie `MODEL: "gpt-4o"`

4. **Logging**:
   - Für stille Ausführung setzen Sie `SHOW_STATUS: False`
   - Um Details zur Verarbeitung zu sehen, setzen Sie `SHOW_STATUS: True`

## Hinweise

- Die Anwendung benötigt eine aktive Internetverbindung für die Kommunikation mit den APIs.
- Für die OpenAI-Integration ist ein gültiger API-Schlüssel erforderlich.
- Bei großem Textvolumen können API-Kosten entstehen.
- Die Genauigkeit der Entitätserkennung hängt vom verwendeten Modell ab.
