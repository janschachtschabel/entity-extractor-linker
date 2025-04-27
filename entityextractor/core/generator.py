"""
Entity generation core functionality.

This module provides functions for generating entities related to a specific topic
to create a comprehensive knowledge compendium.
"""

import logging
import time
import json

from openai import OpenAI
from entityextractor.config.settings import get_config, DEFAULT_CONFIG
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.utils.text_utils import clean_json_from_markdown
from entityextractor.services.openai_service import save_training_data as save_extraction_training_data
from entityextractor.core.entity_inference import infer_entities

def save_training_data(topic, entities, config=None):
    """
    Save training data for future fine-tuning in generation mode.
    
    Args:
        topic: The input topic
        entities: The generated entities
        config: Configuration dictionary with training data path
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    # Gemeinsame JSONL für alle Entity-Modi
    training_data_path = config.get("OPENAI_TRAINING_DATA_PATH", DEFAULT_CONFIG["OPENAI_TRAINING_DATA_PATH"])
    
    try:
        # Get system prompt based on language
        language = config.get("LANGUAGE", "de")
        system_prompt = ""
        
        if language == "en":
            system_prompt = "You are a comprehensive knowledge generator for creating educational compendia. Your task is to generate the most important entities related to a specific topic."
        else:
            system_prompt = "Du bist ein umfassender Wissensgenerator für die Erstellung von Bildungskompendien. Deine Aufgabe ist es, die wichtigsten Entitäten zu einem bestimmten Thema zu generieren."
        
        # Create a training example in OpenAI format
        example = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate the most important entities related to the topic: {topic}"},
                {"role": "assistant", "content": json.dumps({"entities": entities}, ensure_ascii=False)}
            ]
        }
        
        # Ensure each entity has an 'inferred' field
        mode = config.get("MODE", "")
        for ent in entities:
            if "inferred" not in ent:
                ent["inferred"] = "implicit" if mode in ("generate", "compendium") else "explicit"
        
        # Append to the JSONL file
        with open(training_data_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            
        logging.info(f"Saved generation training example to {training_data_path}")
    except Exception as e:
        logging.error(f"Error saving generation training data: {e}")

def generate_entities(topic, user_config=None):
    """
    Generate entities related to a specific topic.
    
    Args:
        topic: The topic to generate entities for
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of generated entities
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Start timing
    start_time = time.time()
    logging.info(f"Starting entity generation for topic: {topic}")
    
    # Get OpenAI API key
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error("No OpenAI API key provided")
            return []
    
    # Create OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Get model and max entities
    model = config.get("MODEL", "gpt-4.1-mini")
    max_entities = config.get("MAX_ENTITIES", 10)
    language = config.get("LANGUAGE", "de")
    
    # Get allowed entity types if specified
    allowed_entity_types = config.get("ALLOWED_ENTITY_TYPES", "auto")
    
    # Override prompts in generate mode: only implicit entities
    mode = config.get("MODE", "extract")
    # Compendium mode: detailed prompt focused on implicit entities
    if mode == "compendium":
        if language == "de":
            system_prompt = f"""
Du bist ein umfassender Wissensgenerator für die Erstellung von Bildungskompendien. Denke sorgfältig nach und antworte vollständig.
Generiere genau {max_entities} implizite, logische Entitäten zum Thema: {topic}.

Achte darauf, ausschließlich implizit aus dem Kontext abgeleitete Entitäten zu generieren und keine expliziten Entitäten aufzunehmen.

Gib ein JSON-Array mit {max_entities} Objekten zurück. Jedes Objekt enthält:
- entity: Exakter Titel im deutschen Wikipedia-Artikel
- entity_type: Typ der Entität
- wikipedia_url: URL des deutschen Wikipedia-Artikels
- citation: "generated"
- inferred: "implicit"

Berücksichtige bei der Auswahl impliziter Entitäten z.B.:
1. Einführung & Grundlagen
2. Fachterminologie & Konzepte
3. Systematische Struktur
4. Gesellschaftlicher Kontext
5. Historische Entwicklung
6. Akteure & Institutionen
7. Berufliche Praxis
8. Quellen & Literatur
9. Bildungsaspekte
10. Rechtlicher & ethischer Rahmen
11. Nachhaltigkeit
12. Interdisziplinarität
13. Aktuelle Entwicklungen
14. Ressourcen & Werkzeuge
15. Praxisbeispiele

Regeln:
- Generiere ausschließlich implizite Entitäten.
- Generiere genau {max_entities} Entitäten.
- Verwende deutsche Wikipedia-Titel und URLs.
- Gib nur gültiges JSON ohne Erklärung zurück.
"""
            user_msg = system_prompt
        else:
            system_prompt = f"""
You are a comprehensive knowledge generator for creating educational compendia. Think carefully and answer thoroughly.
Generate exactly {max_entities} implicit, logical entities for the topic: {topic}.

Ensure that you only generate entities that are implicitly derived from the context and exclude any explicit entities.

Return a JSON array of {max_entities} objects. Each object contains:
- entity: Exact English Wikipedia title
- entity_type: Type of the entity
- wikipedia_url: URL of the English Wikipedia article
- citation: "generated"
- inferred: "implicit"

Consider when selecting implicit entities:
1. Introduction & Fundamentals
2. Core Terminology & Concepts
3. Systematic Structure
4. Social Context
5. Historical Development
6. Actors & Institutions
7. Professional Practice
8. Sources & Literature
9. Educational Aspects
10. Legal & Ethical Framework
11. Sustainability
12. Interdisciplinarity
13. Current Developments
14. Resource Connections
15. Practical Examples

Rules:
- Generate only implicit entities.
- Generate exactly {max_entities} entities.
- Use English Wikipedia titles and URLs.
- Return only valid JSON without explanation.
"""
            user_msg = system_prompt
    elif mode == "generate":
        # Determine the prompt based on language
        if language == "en":
            system_prompt = f"Generate {max_entities} implicit, logical entities relevant to the topic: {topic}. Only output implicit entities."
            user_msg = f"Provide a JSON array of {max_entities} objects, each with fields 'entity', 'entity_type', 'wikipedia_url', 'inferred', 'citation'. Set 'inferred' to \"implicit\" and 'citation' to \"generated\" for all entities. Return only JSON."
        else:
            system_prompt = f"Generiere {max_entities} implizite, logische Entitäten zum Thema: {topic}. Ausgabe: nur implizite Entitäten."
            user_msg = f"Gib ein JSON-Array von {max_entities} Objekten mit den Feldern 'entity', 'entity_type', 'wikipedia_url', 'inferred', 'citation' zurück. Setze 'inferred' auf \"implicit\" und 'citation' auf \"generated\" für alle Entitäten. Nur JSON zurückgeben."
    else:
        logging.warning(f"MODE '{mode}' nicht unterstützt; wechsle zum 'generate'-Verhalten.")
        # Fallback auf vereinfachten Generate-Prompt
        if language == "en":
            system_prompt = f"Generate {max_entities} implicit, logical entities relevant to the topic: {topic}. Only output implicit entities."
            user_msg = f"Provide a JSON array of {max_entities} objects, each with fields 'entity', 'entity_type', 'wikipedia_url', 'inferred', 'citation'. Set 'inferred' to \"implicit\" and 'citation' to \"generated\" for all entities. Return only JSON."
        else:
            system_prompt = f"Generiere {max_entities} implizite, logische Entitäten zum Thema: {topic}. Ausgabe: nur implizite Entitäten."
            user_msg = f"Gib ein JSON-Array von {max_entities} Objekten mit den Feldern 'entity', 'entity_type', 'wikipedia_url', 'inferred', 'citation' zurück. Setze 'inferred' auf \"implicit\" und 'citation' auf \"generated\" für alle Entitäten. Nur JSON zurückgeben."
    
    try:
        # Log the model being used
        logging.info(f"Generating entities with OpenAI model {model}...")
        logging.debug(f"[GENERATION] SYSTEM PROMPT:\n{system_prompt}")
        logging.debug(f"[GENERATION] USER MSG:\n{user_msg}")
        generation_start_time = time.time()
        
        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7  # Higher temperature for more creative generation
        )
        
        # Log the HTTP response
        generation_time = time.time() - generation_start_time
        logging.info(f"HTTP Request: POST https://api.openai.com/v1/chat/completions \"HTTP/1.1 200 OK\"")
        logging.info(f"Generation API call completed in {generation_time:.2f} seconds")
        
        # Process the response
        if not response.choices or not response.choices[0].message.content:
            logging.error("Empty response from OpenAI API")
            return []
            
        raw_json = response.choices[0].message.content
        clean_json = clean_json_from_markdown(raw_json)
        
        try:
            result = json.loads(clean_json)
            # Handle both JSON array and object with 'entities' key
            if isinstance(result, dict) and isinstance(result.get("entities"), list):
                entities = result.get("entities")
            elif isinstance(result, list):
                entities = result
            else:
                logging.error("Unexpected JSON format; expected list or object with 'entities'")
                entities = []
            
            # Convert field names if necessary
            mode = config.get("MODE", "extract")
            processed_entities = []
            for entity in entities:
                processed_entity = {}
                
                # Map entity fields to expected names
                if "entity" in entity:
                    processed_entity["name"] = entity["entity"]
                elif "name" in entity:
                    processed_entity["name"] = entity["name"]
                    
                if "entity_type" in entity:
                    processed_entity["type"] = entity["entity_type"]
                elif "type" in entity:
                    processed_entity["type"] = entity["type"]
                    
                if "wikipedia_url" in entity:
                    processed_entity["wikipedia_url"] = entity["wikipedia_url"]
                    
                # Set citation based on inferred flag
                if entity.get("inferred", "implicit") == "explicit":
                    processed_entity["citation"] = topic
                else:
                    processed_entity["citation"] = "generated"
                
                # Preserve 'inferred' flag from JSON (default to implicit in generate and compendium modes)
                inferred = entity.get("inferred")
                if not inferred:
                    inferred = "implicit" if mode in ("generate", "compendium") else "explicit"
                processed_entity["inferred"] = inferred
                
                # Add to processed entities if it has at least name and type
                if "name" in processed_entity and "type" in processed_entity:
                    processed_entities.append(processed_entity)
            
            elapsed_time = time.time() - start_time
            logging.info(f"Generated {len(processed_entities)} entities in {elapsed_time:.2f} seconds")
            
            # Save training data if enabled
            if config.get("COLLECT_TRAINING_DATA", False):
                save_training_data(topic, processed_entities, config)
                
            # Ergänze implizite Entitäten via ENABLE_ENTITY_INFERENCE
            if config.get("ENABLE_ENTITY_INFERENCE", False):
                processed_entities = infer_entities(topic, processed_entities, config)
            
            # Add 'sources' field for detail enrichment
            for pe in processed_entities:
                pe["sources"] = {}
                
            return processed_entities
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON response: {e}")
            logging.error(f"Raw response: {raw_json}")
            return []
    except Exception as e:
        logging.error(f"Error generating entities: {e}")
        return []
