#!/usr/bin/env python3
"""
example_minimal_generate.py
Minimaler Beispielskript für Entity Generator mit DEFAULT_CONFIG und MODE=generate zum Thema Organische Chemie.
"""
import sys
import json
from entityextractor.core.api import process_entities

# UTF-8-Ausgabe sicherstellen
sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    topic = "Organische Chemie"
    # Nur Mode überschreiben, restliche Einstellungen aus settings.py
    config = {"MODE": "generate"}
    result = process_entities(topic, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
