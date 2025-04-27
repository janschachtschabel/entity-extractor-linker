# Utility: LLM-basierte Deduplizierung von Beziehungen
import json
from collections import defaultdict
import logging
from openai import OpenAI
from entityextractor.config.settings import get_config
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.services.openai_service import save_relationship_training_data
from .relationship_inference import extract_json_relationships

def deduplicate_relationships_llm(relationships, entities, user_config=None):
    """
    Bereinigt eine Liste von Beziehungen (Tripeln) per LLM, sodass pro (Subjekt, Objekt) nur wirklich unterschiedliche Prädikate übrigbleiben.
    Das LLM bekommt ALLE Triple mit identischem (Subjekt, Objekt) als Prompt und gibt eine bereinigte Liste zurück, in der semantisch gleiche/ähnliche Prädikate gruppiert und nur die beste Formulierung behalten wird.
    """
    config = get_config(user_config)
    configure_logging(config)
    if not relationships:
        return []
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error("Kein OpenAI API-Schlüssel angegeben")
            return relationships
    client = OpenAI(api_key=api_key)
    model = config.get("MODEL", "gpt-4.1-mini")
    language = config.get("LANGUAGE", "de")
    grouped = defaultdict(list)
    for rel in relationships:
        key = (rel["subject"], rel["object"])
        grouped[key].append(rel)
    deduped_result = []
    for (subj, obj), rels in grouped.items():
        if len(rels) == 1:
            deduped_result.append(rels[0])
            continue
        # Alle Prädikate für dieses Paar in den Prompt
        prompt_rels = [
            {"predicate": r["predicate"], "inferred": r.get("inferred", "explicit")} for r in rels
        ]
        if language == "en":
            user_prompt = (
                f"For the following relationships between subject and object, group all semantically similar predicates together, including those that are only grammatically or stylistically different (e.g. tense, prepositions, auxiliary verbs, etc.). "
                f"Keep only the most concise and representative formulation for each unique relationship. "
                f"Subject: '{subj}', Object: '{obj}', Relationships: {json.dumps(prompt_rels, ensure_ascii=False)}. "
                f"Return a JSON array of unique relationships with their predicates and inferred fields."
            )
            system_prompt = "You are a helpful assistant for deduplicating knowledge graph relationships."
        else:
            user_prompt = (
                f"Für die folgenden Beziehungen zwischen Subjekt und Objekt gruppiere alle Prädikate, die semantisch gleich oder sehr ähnlich sind, auch wenn sie sich nur grammatisch, durch Zeitform, Hilfswörter oder Präpositionen unterscheiden. "
                f"Behalte nur die prägnanteste und repräsentativste Formulierung jeder inhaltlich unterschiedlichen Beziehung. "
                f"Subjekt: '{subj}', Objekt: '{obj}', Beziehungen: {json.dumps(prompt_rels, ensure_ascii=False)}. "
                f"Gib ein JSON-Array der einmaligen Beziehungen mit Prädikat und inferred-Feld zurück."
            )
            system_prompt = "Du bist ein hilfreicher Assistent zur Bereinigung von Knowledge-Graph-Beziehungen."
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=300
            )
            raw_json = response.choices[0].message.content.strip()
            cleaned = extract_json_relationships(raw_json)
            for c in cleaned:
                match = next((r for r in rels if r["predicate"] == c["predicate"] and r.get("inferred", "explicit") == c.get("inferred", "explicit")), None)
                if match:
                    deduped_result.append(match)
                else:
                    deduped_result.append({"subject": subj, "object": obj, **c})
            logging.info(f"LLM-Dedup: ({subj} -> {obj}) | {len(rels)} → {len(cleaned)} Beziehungen nach LLM-Deduplizierung.")
        except Exception as e:
            logging.error(f"Fehler bei LLM-Deduplizierung für Paar ({subj}, {obj}): {e}")
            deduped_result.extend(rels)
    logging.info(f"LLM-Deduplizierung abgeschlossen: Vorher: {len(relationships)}, Nachher: {len(deduped_result)}")
    return deduped_result
