"""
Entity Relationship Inference Module

Dieses Modul ermöglicht die Inferenz von Beziehungen zwischen Entitäten
basierend auf dem Originaltext und den extrahierten Entitäten.
"""

import json
import time
import logging
from openai import OpenAI
from entityextractor.config.settings import get_config
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.services.openai_service import save_relationship_training_data

# Standardkonfiguration
DEFAULT_CONFIG = {
    "MODEL": "gpt-4.1-mini",
    "LANGUAGE": "de",
    "SHOW_STATUS": True,
    "RELATION_EXTRACTION": False
}

def infer_entity_relationships(text, entities, user_config=None):
    """
    Inferiert Beziehungen zwischen Entitäten basierend auf dem Originaltext.
    
    Args:
        text: Der Originaltext, aus dem die Entitäten extrahiert wurden
        entities: Die extrahierten Entitäten
        user_config: Optionale Benutzerkonfiguration
        
    Returns:
        Eine Liste von Tripeln (Subjekt, Prädikat, Objekt, Inferiert)
    
    Erweiterte Logik (ab 2025):
    - Standard: Extrahiere nur explizite Beziehungen (explizit im Text genannt)
    - Falls ENABLE_RELATIONS_INFERENCE=True: Nach Extraktion der expliziten Beziehungen wird ein zweiter Prompt ausgeführt, der zusätzlich implizite Beziehungen (aus dem Kontext abgeleitet) generiert. Dabei werden die bereits gefundenen expliziten Beziehungen übergeben und dürfen nicht erneut erzeugt werden.
    - Die Ergebnisse beider Prompts werden zusammengeführt (keine Duplikate).
    """
    # Konfiguration mit Benutzerüberschreibungen abrufen
    config = get_config(user_config)
    
    # Logging konfigurieren
    configure_logging(config)
    
    # Prüfen, ob Relationship Inference aktiviert ist
    if not config.get("RELATION_EXTRACTION", False):
        logging.info("Entity Relationship Inference ist deaktiviert.")
        return []
    
    # Zeitmessung starten
    start_time = time.time()
    logging.info("Starte Entity Relationship Inference...")
    
    # OpenAI API-Schlüssel abrufen
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error("Kein OpenAI API-Schlüssel angegeben")
            return []
    
    # OpenAI-Client erstellen
    client = OpenAI(api_key=api_key)
    
    # Modell und Sprache abrufen
    model = config.get("MODEL", "gpt-4.1-mini")
    language = config.get("LANGUAGE", "de")
    
    # Entitätsnamen und Typen extrahieren
    entity_info = []
    logging.info(f"Verarbeite {len(entities)} Entitäten für Beziehungsextraktion")
    
    for i, entity in enumerate(entities):
        # Überprüfe die Struktur der Entität für Debugging
        logging.info(f"Verarbeite Entität {i+1}: {entity.keys()}")
        
        # Versuche, den Namen und Typ aus verschiedenen möglichen Strukturen zu extrahieren
        entity_name = ""
        entity_type = ""
        
        # Direkte Felder in der Entität
        if "entity" in entity:
            entity_name = entity["entity"]
        elif "name" in entity:
            entity_name = entity["name"]
            
        if "entity_type" in entity:
            entity_type = entity["entity_type"]
        elif "type" in entity:
            entity_type = entity["type"]
        elif "details" in entity and "typ" in entity["details"]:
            entity_type = entity["details"]["typ"]
        
        # Wikipedia-Label verwenden, falls vorhanden
        if "sources" in entity and "wikipedia" in entity["sources"]:
            if "label" in entity["sources"]["wikipedia"]:
                entity_name = entity["sources"]["wikipedia"]["label"]
        
        # Nur hinzufügen, wenn Name und Typ vorhanden sind
        if entity_name and entity_type:
            entity_info.append({"name": entity_name, "type": entity_type})
            logging.info(f"  - Extrahiert: {entity_name} ({entity_type})")
        else:
            logging.warning(f"  - Konnte keinen Namen oder Typ für Entität {i+1} extrahieren: {entity}")
    
    logging.info(f"Extrahierte {len(entity_info)} Entitäten für Beziehungsextraktion")
    
    # Erstelle ein Dictionary für schnellen Zugriff auf Entitätstypen
    entity_type_map = {entity['name']: entity['type'] for entity in entity_info}
    logging.info(f"Erstellt Entitätstyp-Map mit {len(entity_type_map)} Einträgen")
    
    # Mappt jeden Entitätsnamen auf seinen Inferenzstatus
    entity_inferred_map = {(e.get("entity") or e.get("name", "")): e.get("inferred", "explizit") for e in entities}
    logging.info(f"Erstellt Entität-Inferenz-Map mit {len(entity_inferred_map)} Einträgen")

    # KGC-Modus: nur neue implizite Beziehungen basierend auf bestehenden generieren
    existing_rels = config.get("existing_relationships")
    if config.get("enable_kgc", False) and existing_rels is not None:
        logging.info(f"Starte Knowledge Graph Completion-Inferenz: {len(existing_rels)} bestehende Beziehungen")
        # System- und User-Prompt für KGC
        if language == "en":
            system_prompt = (
                "You are a knowledge graph completion assistant. Only generate new implicit relationships between the provided entities; do not invent any new entities."
            )
            user_msg = f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Existing relationships:
{json.dumps(existing_rels, indent=2)}

Identify additional IMPLICIT relationships between these entities that are not in the existing list, to logically complete the graph. Use only the provided entities as subject and object; do not introduce any other entities. Set inferred="implizit".  
"""
        else:
            system_prompt = (
                "Du bist ein Knowledge-Graph-Completion-Assistent. Erzeuge nur neue implizite Beziehungen zwischen den unten aufgeführten Entitäten; erfinde keine neuen Entitäten."
            )
            user_msg = f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Bestehende Beziehungen:
{json.dumps(existing_rels, indent=2)}

Ergänze weitere IMPLIZITE Beziehungen zwischen diesen Entitäten, die noch nicht existieren, um den Graph logisch zu vervollständigen. Nutze ausschließlich die angegebenen Entitäten als Subjekt und Objekt; erfinde keine neuen Entitäten. Setze inferred="implizit".  
"""
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        raw = response.choices[0].message.content.strip()
        new_rels = extract_json_relationships(raw)
        # Nur Beziehungen, die noch nicht vorhanden sind
        existing_keys = {(r["subject"], r["predicate"], r["object"]) for r in existing_rels}
        valid_new = []
        for rel in new_rels:
            k = (rel.get("subject"), rel.get("predicate"), rel.get("object"))
            if k not in existing_keys and all(k2 in rel for k2 in ("subject","predicate","object")):
                rel["inferred"] = "implicit"
                rel["subject_type"] = entity_type_map.get(rel["subject"], "")
                rel["object_type"] = entity_type_map.get(rel["object"], "")
                valid_new.append(rel)
        return valid_new

    # Prompt-Logik für explizite und ggf. (implizite) Beziehungen
    enable_inference = config.get("ENABLE_RELATIONS_INFERENCE", False)
    
    # Modus des ersten Prompts: extract vs generate
    mode = config.get("MODE", "extract")
    
    # Primärer Prompt: Im generate- oder compendium-Modus explizit+implizit, sonst nur explizit
    if mode in ("generate", "compendium"):
        # Unified first prompt for generate and compendium (match implicit prompt style)
        if language == "en":
            system_prompt_explicit = """
            You are an advanced AI system specialized in knowledge graph extraction and enrichment. Think deeply before answering.
            
            Your task:
            Based on the provided text and entity list, extract ALL relationships (explicit and implicit) between these entities. Do NOT invent new entities.
            
            The entity list is provided and you MUST use only these entities for subject and object.
            
            Rules:
            - Predicates MUST be 1-3 words maximum. Keep them lowercase.
            
            Output Requirements:
            - Return only a JSON array of objects with keys: "subject", "predicate", "object", and "inferred" ("explicit" or "implicit").
            """
        else:
            system_prompt_explicit = """
            Du bist ein fortschrittliches KI-System zur Extraktion und Anreicherung von Wissensgraphen. Denke vor der Antwort gründlich nach.
            
            Deine Aufgabe:
            Basierend auf dem gegebenen Text und der Entitätenliste extrahiere ALLE Beziehungen (explizit und implizit) zwischen diesen Entitäten. Erfinde keine neuen Entitäten.
            
            Die Entitätenliste ist gegeben und du DARFST nur diese Entitäten als Subjekt und Objekt verwenden.
            
            Regeln:
            - Prädikate MÜSSEN maximal 1-3 Wörter lang sein. Schreibe sie in Kleinbuchstaben.
            
            Ausgabeanforderungen:
            - Gib nur ein JSON-Array mit Objekten zurück, die "subject", "predicate", "object" und "inferred" ("explicit" oder "implicit") enthalten.
            """
        # Benutzernachricht für erste Beziehungen
        if language == "en":
            user_msg_explicit = f"""
            Topic: {text}

            Entities:
            {json.dumps(entity_info, indent=2)}

            Generate logical relationship triples (subject, predicate, object) among these entities relevant to this topic. For each triple, set inferred="implicit".
            """
        else:
            user_msg_explicit = f"""
            Thema: {text}

            Entitäten:
            {json.dumps(entity_info, indent=2)}

            Generiere logische Beziehungstripel (Subjekt, Prädikat, Objekt) zwischen diesen Entitäten passend zum Thema. Setze inferred="implicit" für jedes Tripel.
            """
    else:
        # --- Schritt 1: Nur explizite Beziehungen extrahieren ---
        if language == "en":
            system_prompt_explicit = """
            You are an advanced AI system specialized in knowledge extraction and knowledge graph generation. Think deeply before answering and provide a thorough, comprehensive response.
            Your expertise includes identifying consistent entity references and meaningful relationships in text.

            Your task:
            Extract ONLY explicit (directly mentioned in the text) relationships between the provided entities. Do NOT infer or add any relationships that are not directly stated in the text.

            The entity list is provided and you MUST use only these entities for subject and object. Do NOT invent or add new entities.

            Rules:
            - Entity Consistency: Use ONLY the provided entity names consistently.
            - CRITICAL: Both subject and object MUST be from the provided entity list. DO NOT create new entities.
            - Pairwise Relationships: Create one triple for each pair of entities from the provided list that has a meaningful relationship.
            - CRITICAL INSTRUCTION: Predicates MUST be 1-3 words maximum. Never more than 3 words. Keep them extremely concise.
            - IMPORTANT: Only make the predicate (P) lower-case. Subject (S) and Object (O) should maintain their original capitalization as provided in the entity names, especially for proper nouns, names of people, places, etc.
            - Only extract relationships that are explicitly stated in the text.

            Output Requirements:
            - Return only the JSON array, with each triple as an object containing "subject", "predicate", "object", and "inferred" (always set to "explicit").
            - Make sure the JSON is valid and properly formatted.
            """
        else:
            system_prompt_explicit = """
            Du bist ein fortschrittliches KI-System, das auf Wissensextraktion und Wissensgraphgenerierung spezialisiert ist. Denke vor der Antwort gründlich nach und antworte besonders vollständig und sorgfältig.
            Deine Aufgabe:
            Extrahiere NUR explizite (direkt im Text genannte) Beziehungen zwischen den bereitgestellten Entitäten. Schließe KEINE Beziehungen ein, die nicht direkt im Text genannt werden.

            Die Entitätenliste ist gegeben und du DARFST nur diese Entitäten als Subjekt und Objekt verwenden. Erfinde oder ergänze KEINE neuen Entitäten.

            Regeln:
            - Entitätskonsistenz: Verwende NUR die bereitgestellten Entitätsnamen konsistent.
            - KRITISCH: Sowohl Subjekt als auch Objekt MÜSSEN aus der bereitgestellten Entitätsliste stammen. Erfinde KEINE neuen Entitäten.
            - Paarweise Beziehungen: Erstelle ein Tripel für jedes Paar von Entitäten aus der bereitgestellten Liste, das eine bedeutungsvolle Beziehung hat.
            - WICHTIGE ANWEISUNG: Prädikate MÜSSEN maximal 1-3 Wörter lang sein. Niemals mehr als 3 Wörter. Halte sie äußerst prägnant.
            - WICHTIG: Schreibe nur das Prädikat (P) in Kleinbuchstaben. Subjekt (S) und Objekt (O) sollten ihre ursprüngliche Groß-/Kleinschreibung beibehalten.

            Ausgabeanforderungen:
            - Gib nur das JSON-Array zurück, wobei jedes Tripel ein Objekt ist, das "subject", "predicate", "object" und "inferred" ("explicit") enthält.
            - Stelle sicher, dass das JSON gültig und korrekt formatiert ist.
            """
        # Benutzernachricht für explizite Beziehungen
        if language == "en":
            user_msg_explicit = f"""
            Text: ```{text}```

            Entities:
            {json.dumps(entity_info, indent=2)}

            Identify all EXPLICIT relationships between these entities in the text. For each relationship, set inferred="explicit".
            """
        else:
            user_msg_explicit = f"""
            Text: ```{text}```

            Entitäten:
            {json.dumps(entity_info, indent=2)}

            Identifiziere alle EXPLIZITEN Beziehungen zwischen diesen Entitäten im Text. Setze für jede Beziehung inferred="explicit".
            """
    
    # --- Prompt 1: Explizite Beziehungen ---
    try:
        logging.info(f"Rufe OpenAI API für explizite Beziehungen auf (Modell {model})...")
        response_explicit = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_explicit},
                {"role": "user", "content": user_msg_explicit}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        raw_json_explicit = response_explicit.choices[0].message.content.strip()
        logging.info(f"Erhaltene Antwort (explizit): {raw_json_explicit[:200]}...")
        elapsed_time = time.time() - start_time
        logging.info(f"Erster Prompt abgeschlossen in {elapsed_time:.2f} Sekunden")

        relationships_explicit = extract_json_relationships(raw_json_explicit)
        valid_relationships_explicit = []
        for rel in relationships_explicit:
            if all(k in rel for k in ["subject", "predicate", "object"]):
                # Im generate- oder compendium-Modus implizite/explizite Markierung beibehalten
                inferred_status = rel.get("inferred", "explicit") if mode in ("generate", "compendium") else "explicit"
                rel["inferred"] = inferred_status
                rel["subject_type"] = entity_type_map.get(rel["subject"], "")
                rel["object_type"] = entity_type_map.get(rel["object"], "")
                rel["subject_inferred"] = entity_inferred_map.get(rel["subject"], "explicit")
                rel["object_inferred"] = entity_inferred_map.get(rel["object"], "explicit")
                if rel["subject_type"] and rel["object_type"]:
                    valid_relationships_explicit.append(rel)
        logging.info(f"{len(valid_relationships_explicit)} gültige explizite Beziehungen gefunden")

        # Wenn keine Inferenz gewünscht: Nur explizite Beziehungen zurückgeben
        if not enable_inference:
            return valid_relationships_explicit

        # --- Schritt 2: Implizite Beziehungen ergänzen (Prompt 2) ---
        if language == "en":
            system_prompt_implicit = """
            You are an advanced AI system specialized in knowledge graph enrichment. Think deeply before answering.

            Your task:
            Based on the provided text, entity list, and the already extracted EXPLICIT relationships, identify and add all additional IMPLICIT (inferred, background knowledge) relationships between the entities. DO NOT repeat any relationship already present in the explicit list. Only add new, implicit relationships.

            The entity list is provided and you MUST use only these entities for subject and object. Do NOT invent or add new entities.

            Rules:
            - Predicates MUST be 1-3 words maximum. Keep them lowercase.

            Output Requirements:
            - Return only the JSON array, with each triple as an object containing "subject", "predicate", "object", and "inferred" (always set to "implicit").
            - Make sure the JSON is valid and properly formatted.
            """
        else:
            system_prompt_implicit = """
            Du bist ein KI-System zur Anreicherung von Wissensgraphen.
            Deine Aufgabe:
            Ergänze auf Basis des Textes, der Entitäten und der bereits extrahierten EXPLIZITEN Beziehungen alle weiteren IMPLIZITEN (aus dem Kontext abgeleiteten) Beziehungen zwischen den Entitäten. Gib KEINE Beziehungen zurück, die bereits in der expliziten Liste enthalten sind. Ergänze nur neue, implizite Beziehungen.

            Die Entitätenliste ist gegeben und du DARFST nur diese Entitäten als Subjekt und Objekt verwenden. Erfinde oder ergänze KEINE neuen Entitäten.

            Regeln:
            - Prädikate MÜSSEN maximal 1-3 Wörter lang sein. Schreibe sie in Kleinbuchstaben.

            Ausgabeanforderungen:
            - Gib nur das JSON-Array zurück, wobei jedes Tripel ein Objekt ist, das "subject", "predicate", "object" und "inferred" ("implicit") enthält.
            - Stelle sicher, dass das JSON gültig und korrekt formatiert ist.
            """

        # Benutzernachricht für implizite Beziehungen
        if language == "en":
            user_msg_implicit = f"""
            Text: ```{text}```

            Entities:
            {json.dumps(entity_info, indent=2)}

            Explicit relationships (do NOT repeat these):
            {json.dumps(valid_relationships_explicit, indent=2)}

            Identify all additional IMPLICIT relationships between these entities in the text. For each, set inferred="implicit".
            """
        else:
            user_msg_implicit = f"""
            Text: ```{text}```

            Entitäten:
            {json.dumps(entity_info, indent=2)}

            Explizite Beziehungen (NICHT erneut ausgeben):
            {json.dumps(valid_relationships_explicit, indent=2)}

            Ergänze alle weiteren IMPLIZITEN Beziehungen zwischen diesen Entitäten. Setze für jede Beziehung inferred="implicit".
            """

        logging.info(f"Rufe OpenAI API für implizite Beziehungen auf (Modell {model})...")
        response_implicit = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_implicit},
                {"role": "user", "content": user_msg_implicit}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        raw_json_implicit = response_implicit.choices[0].message.content.strip()
        logging.info(f"Erhaltene Antwort (implizit): {raw_json_implicit[:200]}...")

        relationships_implicit = extract_json_relationships(raw_json_implicit)
        valid_relationships_implicit = []
        for rel in relationships_implicit:
            if all(k in rel for k in ["subject", "predicate", "object"]):
                rel["inferred"] = "implicit"
                rel["subject_type"] = entity_type_map.get(rel["subject"], "")
                rel["object_type"] = entity_type_map.get(rel["object"], "")
                rel["subject_inferred"] = entity_inferred_map.get(rel["subject"], "explicit")
                rel["object_inferred"] = entity_inferred_map.get(rel["object"], "explicit")
                if rel["subject_type"] and rel["object_type"]:
                    valid_relationships_implicit.append(rel)
        logging.info(f"{len(valid_relationships_implicit)} gültige implizite Beziehungen gefunden")

        # --- Zusammenführen (explizit + implizit, keine Duplikate) ---
        def rel_key(rel):
            return (rel["subject"], rel["predicate"], rel["object"])
        all_relationships = {rel_key(rel): rel for rel in valid_relationships_explicit}
        for rel in valid_relationships_implicit:
            if rel_key(rel) not in all_relationships:
                all_relationships[rel_key(rel)] = rel
        result = list(all_relationships.values())
        logging.info(f"Gesamt: {len(result)} Beziehungen (explizit + implizit)")
        
        # Trainingsdaten für Beziehungsextraktion speichern
        if config.get("COLLECT_TRAINING_DATA", False):
            # Explizite Beziehungen
            save_relationship_training_data(system_prompt_explicit, user_msg_explicit, valid_relationships_explicit, config)
            # Implizite Beziehungen, falls aktiviert
            if config.get("ENABLE_RELATIONS_INFERENCE", False):
                save_relationship_training_data(system_prompt_implicit, user_msg_implicit, valid_relationships_implicit, config)
        return result

    except Exception as e:
        logging.error(f"Fehler beim Aufruf der OpenAI API: {e}")
        return []

def extract_json_relationships(raw_json):
    try:
        json_start = raw_json.find('[')
        json_end = raw_json.rfind(']') + 1
        if json_start >= 0 and json_end > json_start:
            json_content = raw_json[json_start:json_end]
            relationships = json.loads(json_content)
        else:
            relationships = json.loads(raw_json)
        return relationships
    except Exception as e:
        logging.error(f"Fehler beim Parsen der JSON-Antwort: {e}")
        logging.error(f"Rohantwort: {raw_json}")
        return []
