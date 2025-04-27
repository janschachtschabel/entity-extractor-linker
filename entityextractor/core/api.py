"""
Main API for the Entity Extractor.

This module provides the main API functions for extracting and linking entities,
as well as generating entities for a specific topic.
"""

import logging
import time
import urllib.parse

from entityextractor.config.settings import get_config
from entityextractor.core.extractor import extract_entities
from entityextractor.core.linker import link_entities
from entityextractor.core.generator import generate_entities
from entityextractor.core.relationship_inference import infer_entity_relationships
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.utils.text_utils import chunk_text
from entityextractor.core.graph_visualization import visualize_graph

def process_entities(input_text, user_config=None):
    """
    Extract entities from input_text and link them to knowledge bases.
    
    This is the main entry point for the Entity Extractor API in extraction mode.
    
    Args:
        input_text: The input_text to extract entities from
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of entities with knowledge base links in the legacy format
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Start timing
    start_time = time.time()
    logging.info("Starting entity extraction and linking...")
    
    # Chunking großer Texte, falls aktiviert
    if config.get("TEXT_CHUNKING", False):
        text_len = len(input_text)
        size = config.get("TEXT_CHUNK_SIZE", 2000)
        overlap = config.get("TEXT_CHUNK_OVERLAP", 50)
        logging.info(f"Chunking aktiviert: Textlänge={text_len}, Chunk-Größe={size}, Überlappung={overlap}")
        chunks = chunk_text(input_text, size, overlap)
        logging.info(f"{len(chunks)} Chunks erzeugt")
        all_entities, all_relationships = [], []
        for idx, chunk in enumerate(chunks, start=1):
            logging.info(f"Bearbeite Chunk {idx}/{len(chunks)} (Länge={len(chunk)})")
            if config.get("MODE") in ("generate", "compendium"):
                ents = generate_entities(chunk, config)
            else:
                ents = extract_entities(chunk, config)
            logging.info(f"Chunk {idx}: {len(ents)} Entitäten extrahiert")
            linked = link_entities(ents, chunk, config)
            logging.info(f"Chunk {idx}: {len(linked)} Entitäten verlinkt")
            all_entities.extend(linked)
            if config.get("RELATION_EXTRACTION", False):
                rels = infer_entity_relationships(chunk, linked, config)
                logging.info(f"Chunk {idx}: {len(rels)} Beziehungen inferiert")
                all_relationships.extend(rels)
        # Entitäten deduplizieren (nach Wikipedia-URL oder Name)
        deduped_entities, seen = [], set()
        for ent in all_entities:
            key = ent.get("wikipedia_url") or ent.get("name")
            if key and key not in seen:
                seen.add(key)
                deduped_entities.append(ent)
        logging.info(f"Entitäten gesamt: {len(all_entities)}, eindeutig: {len(deduped_entities)}")
        # Beziehungen deduplizieren (explicit überrules implicit)
        rel_map = {}
        for rel in all_relationships:
            k = (rel["subject"], rel["predicate"], rel["object"])
            if k in rel_map:
                existing = rel_map[k]
                if existing.get("inferred") == "implizit" and rel.get("inferred") == "explizit":
                    rel_map[k] = rel
            else:
                rel_map[k] = rel
        deduped_relationships = list(rel_map.values())
        logging.info(f"Beziehungen gesamt: {len(all_relationships)}, eindeutig: {len(deduped_relationships)}")
        # LLM-basierte Deduplizierung nach dem Chunking
        from entityextractor.core.deduplication_utils import deduplicate_relationships_llm
        logging.info("Starte finale LLM-Deduplizierung der Beziehungen nach Chunking...")
        deduped_relationships_final = deduplicate_relationships_llm(deduped_relationships, deduped_entities, config)
        logging.info(f"Beziehungen nach LLM-Deduplizierung: {len(deduped_relationships_final)} (vorher: {len(deduped_relationships)})")
        # Fuzzy/Semantik-Deduplizierung
        from entityextractor.core.semantic_dedup_utils import filter_semantically_similar_relationships
        deduped_relationships_final2 = filter_semantically_similar_relationships(deduped_relationships_final, similarity_threshold=0.85)
        logging.info(f"Beziehungen nach semantischer Deduplizierung: {len(deduped_relationships_final2)} (vorher: {len(deduped_relationships_final)})")
        deduped_relationships = deduped_relationships_final2
        # Knowledge Graph Completion
        if config.get("ENABLE_KGC", False):
            rounds = config.get("KGC_ROUNDS", 3)
            logging.info(f"Starte Knowledge Graph Completion-Inferenz mit {rounds} Runden")
            existing_rel_map = {(r["subject"], r["predicate"], r["object"]): r for r in deduped_relationships}
            existing_rels_list = list(existing_rel_map.values())
            for round_idx in range(1, rounds + 1):
                logging.info(f"KGC-Runde {round_idx}/{rounds} beginnt mit {len(existing_rels_list)} bestehenden Beziehungen")
                # Kopiere Konfiguration und übergebe aktuelle Beziehungen
                cfg_round = config.copy()
                cfg_round["existing_relationships"] = existing_rels_list
                # Generiere neue implizite Beziehungen
                new_rels = infer_entity_relationships(input_text, deduped_entities, cfg_round)
                logging.info(f"Runde {round_idx}: {len(new_rels)} neue implizite Beziehungen generiert")
                # Ergänze nur wirklich neue Tripel
                for rel in new_rels:
                    key = (rel["subject"], rel["predicate"], rel["object"])
                    if key not in existing_rel_map:
                        existing_rel_map[key] = rel
                existing_rels_list = list(existing_rel_map.values())
            # 1. Schnelle Filterung identischer Tripel (S,P,O)
            tripel_map = {(r["subject"], r["predicate"], r["object"]): r for r in existing_rel_map.values()}
            deduped_relationships = list(tripel_map.values())
            logging.info(f"Beziehungen nach exakter Tripel-Deduplizierung (nach KGC): {len(deduped_relationships)}")
            # 2. LLM-Deduplizierung
            from entityextractor.core.deduplication_utils import deduplicate_relationships_llm
            deduped_relationships_final = deduplicate_relationships_llm(deduped_relationships, deduped_entities, config)
            logging.info(f"Beziehungen nach LLM-Deduplizierung (nach KGC): {len(deduped_relationships_final)} (vorher: {len(deduped_relationships)})")
            # 3. Fuzzy/Semantik-Deduplizierung
            from entityextractor.core.semantic_dedup_utils import filter_semantically_similar_relationships
            deduped_relationships_final2 = filter_semantically_similar_relationships(deduped_relationships_final, similarity_threshold=0.85)
            logging.info(f"Beziehungen nach semantischer Deduplizierung (nach KGC): {len(deduped_relationships_final2)} (vorher: {len(deduped_relationships_final)})")
            deduped_relationships = deduped_relationships_final2
            logging.info(f"KGC abgeschlossen: {len(deduped_relationships)} Relationen insgesamt")
        # Ergebnis zurückgeben
        result_dict = {"entities": deduped_entities, "relationships": deduped_relationships}
        if config.get("ENABLE_GRAPH_VISUALIZATION", False):
            vis_res = visualize_graph(result_dict, config)
            result_dict["knowledgegraph_visualisation"] = [{"static": vis_res.get("png"), "interactive": vis_res.get("html")}]
        # Normalize inferred flags to English
        for ent in result_dict.get("entities", []):
            inf = ent.get("details", {}).get("inferred", "").lower()
            if inf in ("explizit", "explicit"): ent["details"]["inferred"] = "explicit"
            elif inf in ("implizit", "implicit"): ent["details"]["inferred"] = "implicit"
        for rel in result_dict.get("relationships", []):
            inf = rel.get("inferred", "").lower()
            if inf in ("explizit", "explicit"): rel["inferred"] = "explicit"
            elif inf in ("implizit", "implicit"): rel["inferred"] = "implicit"
            # Normalize subject/object inferred flags
            if "subject_inferred" in rel:
                si = rel["subject_inferred"].lower()
                if si in ("explizit", "explicit"): rel["subject_inferred"] = "explicit"
                elif si in ("implizit", "implicit"): rel["subject_inferred"] = "implicit"
            if "object_inferred" in rel:
                oi = rel["object_inferred"].lower()
                if oi in ("explizit", "explicit"): rel["object_inferred"] = "explicit"
                elif oi in ("implizit", "implicit"): rel["object_inferred"] = "implicit"
        return result_dict
    
    # Prüfe, ob der MODE-Parameter gesetzt ist und ignoriere ihn im Extraktionsmodus
    if "MODE" in config and config["MODE"] in ("generate", "compendium"):
        logging.info(f"MODE={config['MODE']} erkannt: Es werden Entitäten zum Thema generiert.")
        entities = generate_entities(input_text, config)
    else:
        logging.info("MODE=extract erkannt: Es werden Entitäten aus dem Text extrahiert.")
        # Step 1: Extract entities
        entities = extract_entities(input_text, config)
    
    # Step 2: Link entities
    # Intelligente Verarbeitung: Verwende LLM-URLs direkt und nur Fallback wenn kein Extract gefunden wird
    linked_entities = link_entities(entities, input_text, config)
    
    # Create result in legacy format
    result = []
    
    for entity in linked_entities:
        # Verwende das Zitat aus der Entität, falls vorhanden, sonst den gesamten Text
        citation = entity.get("citation", input_text)
        
        # Finde die Position des Zitats im Text
        citation_start = input_text.find(citation) if citation != input_text else 0
        citation_end = citation_start + len(citation) if citation_start != -1 else len(input_text)
        
        legacy_entity = {
            "entity": entity.get("name", ""),
            "details": {
                "typ": entity.get("type", ""),
                "inferred": entity.get("inferred", "explizit"),
                "citation": citation,
                "citation_start": citation_start,
                "citation_end": citation_end
            },
            "sources": {}
        }
        
        # Add Wikipedia source if available
        if "wikipedia_url" in entity:
            # Extrahiere das Label aus der Wikipedia-URL (letzter Teil des Pfads)
            wikipedia_url = entity.get("wikipedia_url", "")
            wikipedia_label = ""
            if "/wiki/" in wikipedia_url:
                wikipedia_label = wikipedia_url.split("/wiki/")[-1].replace("_", " ")
                # URL-Decode für Sonderzeichen
                wikipedia_label = urllib.parse.unquote(wikipedia_label)
                
            legacy_entity["sources"]["wikipedia"] = {
                "url": wikipedia_url,
                "label": wikipedia_label
            }
            if "wikipedia_extract" in entity:
                legacy_entity["sources"]["wikipedia"]["extract"] = entity.get("wikipedia_extract", "")
            # Always include Wikipedia categories
            if "wikipedia_categories" in entity:
                legacy_entity["sources"]["wikipedia"]["categories"] = entity.get("wikipedia_categories", [])
            # Add additional Wikipedia details if ADDITIONAL_DETAILS enabled
            if "wikipedia_details" in entity and entity["wikipedia_details"]:
                for key, value in entity["wikipedia_details"].items():
                    legacy_entity["sources"]["wikipedia"][key] = value
        
        # Add Wikidata source if available
        if "wikidata_id" in entity:
            legacy_entity["sources"]["wikidata"] = {
                "id": entity.get("wikidata_id", "")
            }
            # Basic information
            if "wikidata_description" in entity:
                legacy_entity["sources"]["wikidata"]["description"] = entity.get("wikidata_description", "")
            if "wikidata_types" in entity:
                legacy_entity["sources"]["wikidata"]["types"] = entity.get("wikidata_types", [])
            if "wikidata_url" in entity:
                legacy_entity["sources"]["wikidata"]["url"] = entity.get("wikidata_url", "")
            if "wikidata_label" in entity:
                legacy_entity["sources"]["wikidata"]["label"] = entity.get("wikidata_label", "")
                
            # Additional information
            if "image_url" in entity:
                legacy_entity["sources"]["wikidata"]["image_url"] = entity.get("image_url", "")
            if "website" in entity:
                legacy_entity["sources"]["wikidata"]["website"] = entity.get("website", "")
            if "coordinates" in entity:
                legacy_entity["sources"]["wikidata"]["coordinates"] = entity.get("coordinates", {})
                
            # Person-specific information
            if "birth_date" in entity:
                legacy_entity["sources"]["wikidata"]["birth_date"] = entity.get("birth_date", "")
            if "death_date" in entity:
                legacy_entity["sources"]["wikidata"]["death_date"] = entity.get("death_date", "")
            if "birth_place" in entity:
                legacy_entity["sources"]["wikidata"]["birth_place"] = entity.get("birth_place", "")
            if "death_place" in entity:
                legacy_entity["sources"]["wikidata"]["death_place"] = entity.get("death_place", "")
                
            # Location-specific information
            if "population" in entity:
                legacy_entity["sources"]["wikidata"]["population"] = entity.get("population", "")
            if "area" in entity:
                legacy_entity["sources"]["wikidata"]["area"] = entity.get("area", "")
            if "country" in entity:
                legacy_entity["sources"]["wikidata"]["country"] = entity.get("country", "")
            if "region" in entity:
                legacy_entity["sources"]["wikidata"]["region"] = entity.get("region", "")
                
            # Organization-specific information
            if "founding_date" in entity:
                legacy_entity["sources"]["wikidata"]["founding_date"] = entity.get("founding_date", "")
            if "founder" in entity:
                legacy_entity["sources"]["wikidata"]["founder"] = entity.get("founder", "")
            if "parent_company" in entity:
                legacy_entity["sources"]["wikidata"]["parent_company"] = entity.get("parent_company", "")
                
            # Additional Wikidata properties
            if "aliases" in entity:
                legacy_entity["sources"]["wikidata"]["aliases"] = entity.get("aliases", [])
            if "instance_of" in entity:
                legacy_entity["sources"]["wikidata"]["instance_of"] = entity.get("instance_of", [])
            if "subclass_of" in entity:
                legacy_entity["sources"]["wikidata"]["subclass_of"] = entity.get("subclass_of", [])
            if "part_of" in entity:
                legacy_entity["sources"]["wikidata"]["part_of"] = entity.get("part_of", [])
            if "has_parts" in entity:
                legacy_entity["sources"]["wikidata"]["has_parts"] = entity.get("has_parts", [])
            if "member_of" in entity:
                legacy_entity["sources"]["wikidata"]["member_of"] = entity.get("member_of", [])
            if "gnd_id" in entity:
                legacy_entity["sources"]["wikidata"]["gnd_id"] = entity.get("gnd_id", "")
            if "isni" in entity:
                legacy_entity["sources"]["wikidata"]["isni"] = entity.get("isni", "")
            if "official_name" in entity:
                legacy_entity["sources"]["wikidata"]["official_name"] = entity.get("official_name", "")
            if "citizenship" in entity:
                legacy_entity["sources"]["wikidata"]["citizenship"] = entity.get("citizenship", [])
            if "occupations" in entity:
                legacy_entity["sources"]["wikidata"]["occupations"] = entity.get("occupations", [])
            if "citizenships" in entity:
                legacy_entity["sources"]["wikidata"]["citizenships"] = entity.get("citizenships", [])
                
            # Organization-specific information
            if "foundation_date" in entity:
                legacy_entity["sources"]["wikidata"]["foundation_date"] = entity.get("foundation_date", "")
            if "official_name" in entity:
                legacy_entity["sources"]["wikidata"]["official_name"] = entity.get("official_name", "")
            if "population" in entity:
                legacy_entity["sources"]["wikidata"]["population"] = entity.get("population", "")
        
        # Add DBpedia source if available, split base vs detail
        if "dbpedia_info" in entity and entity["dbpedia_info"]:
            dbpedia_info = entity["dbpedia_info"]
            legacy_entity["sources"]["dbpedia"] = {
                "resource_uri": dbpedia_info.get("resource_uri", ""),
                "endpoint": dbpedia_info.get("endpoint", ""),
                "language": dbpedia_info.get("language", "")
            }
            # Base DBpedia fields (always)
            if "dbpedia_title" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["title"] = dbpedia_info.get("dbpedia_title", "")
            elif "title" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["title"] = dbpedia_info.get("title", "")
            if "abstract" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["abstract"] = dbpedia_info.get("abstract", "")
            if "label" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["label"] = dbpedia_info.get("label", "")
            if "types" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["types"] = dbpedia_info.get("types", [])
            if "same_as" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["same_as"] = dbpedia_info.get("same_as", [])
            if "subject" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["subjects"] = dbpedia_info.get("subject", [])
            elif "subjects" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["subjects"] = dbpedia_info.get("subjects", [])
            if "part_of" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["part_of"] = dbpedia_info.get("part_of", [])
            if "has_parts" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["has_parts"] = dbpedia_info.get("has_parts", [])
            if "member_of" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["member_of"] = dbpedia_info.get("member_of", [])
            if "category" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["categories"] = dbpedia_info.get("category", [])
            elif "categories" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["categories"] = dbpedia_info.get("categories", [])
            # Detail-only DBpedia fields (if ADDITIONAL_DETAILS enabled)
            if config.get("ADDITIONAL_DETAILS", False):
                if "comment" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["comment"] = dbpedia_info.get("comment", "")
                if "homepage" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["homepage"] = dbpedia_info.get("homepage", "")
                if "thumbnail" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["thumbnail"] = dbpedia_info.get("thumbnail", "")
                if "depiction" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["depiction"] = dbpedia_info.get("depiction", "")
                if "lat" in dbpedia_info and "long" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["coordinates"] = {
                        "latitude": dbpedia_info.get("lat", ""),
                        "longitude": dbpedia_info.get("long", "")
                    }
                if "birth_date" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["birth_date"] = dbpedia_info.get("birth_date", "")
                if "death_date" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["death_date"] = dbpedia_info.get("death_date", "")
                if "birth_place" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["birth_place"] = dbpedia_info.get("birth_place", "")
                if "death_place" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["death_place"] = dbpedia_info.get("death_place", "")
                if "population" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["population"] = dbpedia_info.get("population", "")
                if "area" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["area"] = dbpedia_info.get("area", "")
                if "country" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["country"] = dbpedia_info.get("country", "")
                if "region" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["region"] = dbpedia_info.get("region", "")
                if "founding_date" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["founding_date"] = dbpedia_info.get("founding_date", "")
                if "founder" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["founder"] = dbpedia_info.get("founder", "")
                if "parent_company" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["parent_company"] = dbpedia_info.get("parent_company", "")
                if "current_member" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["current_member"] = dbpedia_info.get("current_member", [])
                if "former_member" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["former_member"] = dbpedia_info.get("former_member", [])
                if "dbp_part_of" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["dbp_part_of"] = dbpedia_info.get("dbp_part_of", [])
                if "dbp_member_of" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["dbp_member_of"] = dbpedia_info.get("dbp_member_of", [])
        
        result.append(legacy_entity)
    
    # Log completion
    elapsed_time = time.time() - start_time
    logging.info(f"Entity extraction and linking completed in {elapsed_time:.2f} seconds")
    
    # Step 3: Infer relationships between entities if enabled
    if config.get("RELATION_EXTRACTION", False):
        logging.info("Starting entity relationship inference...")
        relationships_start_time = time.time()
        relationships = infer_entity_relationships(input_text, linked_entities, config)
        relationships_time = time.time() - relationships_start_time
        logging.info(f"Entity relationship inference completed in {relationships_time:.2f} seconds")
        logging.info(f"Inferred {len(relationships)} relationships")
        
        # Füge die Beziehungen zwischen Entitäten hinzu
        result_dict = {"entities": result, "relationships": relationships}
        # Normalize inferred flags to English
        for ent in result_dict.get("entities", []):
            inf = ent.get("details", {}).get("inferred", "").lower()
            if inf in ("explizit", "explicit"): ent["details"]["inferred"] = "explicit"
            elif inf in ("implizit", "implicit"): ent["details"]["inferred"] = "implicit"
        for rel in result_dict.get("relationships", []):
            inf = rel.get("inferred", "").lower()
            if inf in ("explizit", "explicit"): rel["inferred"] = "explicit"
            elif inf in ("implizit", "implicit"): rel["inferred"] = "implicit"
            # Normalize subject/object inferred flags
            if "subject_inferred" in rel:
                si = rel["subject_inferred"].lower()
                if si in ("explizit", "explicit"): rel["subject_inferred"] = "explicit"
                elif si in ("implizit", "implicit"): rel["subject_inferred"] = "implicit"
            if "object_inferred" in rel:
                oi = rel["object_inferred"].lower()
                if oi in ("explizit", "explicit"): rel["object_inferred"] = "explicit"
                elif oi in ("implizit", "implicit"): rel["object_inferred"] = "implicit"
        if config.get("ENABLE_GRAPH_VISUALIZATION", False):
            vis_res = visualize_graph(result_dict, config)
            result_dict["knowledgegraph_visualisation"] = [{"static": vis_res.get("png"), "interactive": vis_res.get("html")}]
        return result_dict
    
    return result


    """
    Generate entities related to a specific topic and link them to knowledge bases.
    
    This is the main entry point for the Entity Extractor API in generation mode.
    
    Args:
        topic: The topic to generate entities for
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of entities with knowledge base links in the legacy format
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Start timing
    start_time = time.time()
    logging.info("Starting entity generation and linking...")
    
    # Step 1: Generate entities
    generation_start_time = time.time()
    logging.info(f"Starting entity generation for topic: '{topic}'...")
    entities = generate_entities(topic, config)
    generation_time = time.time() - generation_start_time
    logging.info(f"Entity generation completed in {generation_time:.2f} seconds")
    logging.info(f"Generated {len(entities)} entities")
    
    # Step 2: Link entities
    linking_start_time = time.time()
    logging.info("Starting entity linking...")
    # Intelligente Verarbeitung: Verwende LLM-URLs direkt und nur Fallback wenn kein Extract gefunden wird
    linked_entities = link_entities(entities, None, config)
    linking_time = time.time() - linking_start_time
    logging.info(f"Entity linking completed in {linking_time:.2f} seconds")
    
    # Create result in legacy format
    result = []
    
    for entity in linked_entities:
        # Verwende das Zitat aus der Entität, falls vorhanden, sonst "generiert"
        citation = entity.get("citation", "generiert")
        
        legacy_entity = {
            "entity": entity.get("name", ""),
            "details": {
                "typ": entity.get("type", ""),
                "inferred": entity.get("inferred", "explizit"),
                "citation": citation,
                "citation_start": -1,  # -1 indicates generated content
                "citation_end": -1     # -1 indicates generated content
            },
            "sources": {}
        }
        
        # Add Wikipedia source if available
        if "wikipedia_url" in entity:
            # Extrahiere das Label aus der Wikipedia-URL (letzter Teil des Pfads)
            wikipedia_url = entity.get("wikipedia_url", "")
            wikipedia_label = ""
            if "/wiki/" in wikipedia_url:
                wikipedia_label = wikipedia_url.split("/wiki/")[-1].replace("_", " ")
                # URL-Decode für Sonderzeichen
                wikipedia_label = urllib.parse.unquote(wikipedia_label)
                
            legacy_entity["sources"]["wikipedia"] = {
                "url": wikipedia_url,
                "label": wikipedia_label
            }
            if "wikipedia_extract" in entity:
                legacy_entity["sources"]["wikipedia"]["extract"] = entity.get("wikipedia_extract", "")
            # Always include Wikipedia categories
            if "wikipedia_categories" in entity:
                legacy_entity["sources"]["wikipedia"]["categories"] = entity.get("wikipedia_categories", [])
            # Add additional Wikipedia details if ADDITIONAL_DETAILS enabled
            if "wikipedia_details" in entity and entity["wikipedia_details"]:
                for key, value in entity["wikipedia_details"].items():
                    legacy_entity["sources"]["wikipedia"][key] = value
        
        # Add Wikidata source if available
        if "wikidata_id" in entity:
            legacy_entity["sources"]["wikidata"] = {
                "id": entity.get("wikidata_id", "")
            }
            # Basic information
            if "wikidata_description" in entity:
                legacy_entity["sources"]["wikidata"]["description"] = entity.get("wikidata_description", "")
            if "wikidata_types" in entity:
                legacy_entity["sources"]["wikidata"]["types"] = entity.get("wikidata_types", [])
            if "wikidata_url" in entity:
                legacy_entity["sources"]["wikidata"]["url"] = entity.get("wikidata_url", "")
            if "wikidata_label" in entity:
                legacy_entity["sources"]["wikidata"]["label"] = entity.get("wikidata_label", "")
                
            # Additional information
            if "image_url" in entity:
                legacy_entity["sources"]["wikidata"]["image_url"] = entity.get("image_url", "")
            if "website" in entity:
                legacy_entity["sources"]["wikidata"]["website"] = entity.get("website", "")
            if "coordinates" in entity:
                legacy_entity["sources"]["wikidata"]["coordinates"] = entity.get("coordinates", {})
                
            # Person-specific information
            if "birth_date" in entity:
                legacy_entity["sources"]["wikidata"]["birth_date"] = entity.get("birth_date", "")
            if "death_date" in entity:
                legacy_entity["sources"]["wikidata"]["death_date"] = entity.get("death_date", "")
            if "birth_place" in entity:
                legacy_entity["sources"]["wikidata"]["birth_place"] = entity.get("birth_place", "")
            if "death_place" in entity:
                legacy_entity["sources"]["wikidata"]["death_place"] = entity.get("death_place", "")
                
            # Location-specific information
            if "population" in entity:
                legacy_entity["sources"]["wikidata"]["population"] = entity.get("population", "")
            if "area" in entity:
                legacy_entity["sources"]["wikidata"]["area"] = entity.get("area", "")
            if "country" in entity:
                legacy_entity["sources"]["wikidata"]["country"] = entity.get("country", "")
            if "region" in entity:
                legacy_entity["sources"]["wikidata"]["region"] = entity.get("region", "")
                
            # Organization-specific information
            if "founding_date" in entity:
                legacy_entity["sources"]["wikidata"]["founding_date"] = entity.get("founding_date", "")
            if "founder" in entity:
                legacy_entity["sources"]["wikidata"]["founder"] = entity.get("founder", "")
            if "parent_company" in entity:
                legacy_entity["sources"]["wikidata"]["parent_company"] = entity.get("parent_company", "")
                
            # Additional Wikidata properties
            if "aliases" in entity:
                legacy_entity["sources"]["wikidata"]["aliases"] = entity.get("aliases", [])
            if "instance_of" in entity:
                legacy_entity["sources"]["wikidata"]["instance_of"] = entity.get("instance_of", [])
            if "subclass_of" in entity:
                legacy_entity["sources"]["wikidata"]["subclass_of"] = entity.get("subclass_of", [])
            if "part_of" in entity:
                legacy_entity["sources"]["wikidata"]["part_of"] = entity.get("part_of", [])
            if "has_parts" in entity:
                legacy_entity["sources"]["wikidata"]["has_parts"] = entity.get("has_parts", [])
            if "member_of" in entity:
                legacy_entity["sources"]["wikidata"]["member_of"] = entity.get("member_of", [])
            if "gnd_id" in entity:
                legacy_entity["sources"]["wikidata"]["gnd_id"] = entity.get("gnd_id", "")
            if "isni" in entity:
                legacy_entity["sources"]["wikidata"]["isni"] = entity.get("isni", "")
            if "official_name" in entity:
                legacy_entity["sources"]["wikidata"]["official_name"] = entity.get("official_name", "")
            if "citizenship" in entity:
                legacy_entity["sources"]["wikidata"]["citizenship"] = entity.get("citizenship", [])
            if "occupations" in entity:
                legacy_entity["sources"]["wikidata"]["occupations"] = entity.get("occupations", [])
            if "citizenships" in entity:
                legacy_entity["sources"]["wikidata"]["citizenships"] = entity.get("citizenships", [])
                
            # Organization-specific information
            if "foundation_date" in entity:
                legacy_entity["sources"]["wikidata"]["foundation_date"] = entity.get("foundation_date", "")
            if "official_name" in entity:
                legacy_entity["sources"]["wikidata"]["official_name"] = entity.get("official_name", "")
            if "population" in entity:
                legacy_entity["sources"]["wikidata"]["population"] = entity.get("population", "")
        
        # Add DBpedia source if available, split base vs detail
        if "dbpedia_info" in entity and entity["dbpedia_info"]:
            dbpedia_info = entity["dbpedia_info"]
            legacy_entity["sources"]["dbpedia"] = {
                "resource_uri": dbpedia_info.get("resource_uri", ""),
                "endpoint": dbpedia_info.get("endpoint", ""),
                "language": dbpedia_info.get("language", "")
            }
            # Base DBpedia fields (always)
            if "dbpedia_title" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["title"] = dbpedia_info.get("dbpedia_title", "")
            elif "title" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["title"] = dbpedia_info.get("title", "")
            if "abstract" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["abstract"] = dbpedia_info.get("abstract", "")
            if "label" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["label"] = dbpedia_info.get("label", "")
            if "types" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["types"] = dbpedia_info.get("types", [])
            if "same_as" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["same_as"] = dbpedia_info.get("same_as", [])
            if "subject" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["subjects"] = dbpedia_info.get("subject", [])
            elif "subjects" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["subjects"] = dbpedia_info.get("subjects", [])
            if "part_of" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["part_of"] = dbpedia_info.get("part_of", [])
            if "has_parts" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["has_parts"] = dbpedia_info.get("has_parts", [])
            if "member_of" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["member_of"] = dbpedia_info.get("member_of", [])
            if "category" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["categories"] = dbpedia_info.get("category", [])
            elif "categories" in dbpedia_info:
                legacy_entity["sources"]["dbpedia"]["categories"] = dbpedia_info.get("categories", [])
            # Detail-only DBpedia fields (if ADDITIONAL_DETAILS enabled)
            if config.get("ADDITIONAL_DETAILS", False):
                if "comment" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["comment"] = dbpedia_info.get("comment", "")
                if "homepage" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["homepage"] = dbpedia_info.get("homepage", "")
                if "thumbnail" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["thumbnail"] = dbpedia_info.get("thumbnail", "")
                if "depiction" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["depiction"] = dbpedia_info.get("depiction", "")
                if "lat" in dbpedia_info and "long" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["coordinates"] = {
                        "latitude": dbpedia_info.get("lat", ""),
                        "longitude": dbpedia_info.get("long", "")
                    }
                if "birth_date" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["birth_date"] = dbpedia_info.get("birth_date", "")
                if "death_date" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["death_date"] = dbpedia_info.get("death_date", "")
                if "birth_place" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["birth_place"] = dbpedia_info.get("birth_place", "")
                if "death_place" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["death_place"] = dbpedia_info.get("death_place", "")
                if "population" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["population"] = dbpedia_info.get("population", "")
                if "area" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["area"] = dbpedia_info.get("area", "")
                if "country" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["country"] = dbpedia_info.get("country", "")
                if "region" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["region"] = dbpedia_info.get("region", "")
                if "founding_date" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["founding_date"] = dbpedia_info.get("founding_date", "")
                if "founder" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["founder"] = dbpedia_info.get("founder", "")
                if "parent_company" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["parent_company"] = dbpedia_info.get("parent_company", "")
                if "current_member" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["current_member"] = dbpedia_info.get("current_member", [])
                if "former_member" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["former_member"] = dbpedia_info.get("former_member", [])
                if "dbp_part_of" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["dbp_part_of"] = dbpedia_info.get("dbp_part_of", [])
                if "dbp_member_of" in dbpedia_info:
                    legacy_entity["sources"]["dbpedia"]["dbp_member_of"] = dbpedia_info.get("dbp_member_of", [])
        
        result.append(legacy_entity)
    
    elapsed_time = time.time() - start_time
    logging.info(f"Entity generation and linking completed in {elapsed_time:.2f} seconds")
    
    # Step 3: Infer relationships between entities if enabled
    if config.get("RELATION_EXTRACTION", False):
        logging.info("Starting entity relationship inference...")
        relationships_start_time = time.time()
        relationships = infer_entity_relationships(topic, linked_entities, config)
        relationships_time = time.time() - relationships_start_time
        logging.info(f"Entity relationship inference completed in {relationships_time:.2f} seconds")
        logging.info(f"Inferred {len(relationships)} relationships")
        
        # Füge die Beziehungen zwischen Entitäten hinzu
        result_dict = {"entities": result, "relationships": relationships}
        # Normalize inferred flags to English
        for ent in result_dict.get("entities", []):
            inf = ent.get("details", {}).get("inferred", "").lower()
            if inf in ("explizit", "explicit"): ent["details"]["inferred"] = "explicit"
            elif inf in ("implizit", "implicit"): ent["details"]["inferred"] = "implicit"
        for rel in result_dict.get("relationships", []):
            inf = rel.get("inferred", "").lower()
            if inf in ("explizit", "explicit"): rel["inferred"] = "explicit"
            elif inf in ("implizit", "implicit"): rel["inferred"] = "implicit"
            # Normalize subject/object inferred flags
            if "subject_inferred" in rel:
                si = rel["subject_inferred"].lower()
                if si in ("explizit", "explicit"): rel["subject_inferred"] = "explicit"
                elif si in ("implizit", "implicit"): rel["subject_inferred"] = "implicit"
            if "object_inferred" in rel:
                oi = rel["object_inferred"].lower()
                if oi in ("explizit", "explicit"): rel["object_inferred"] = "explicit"
                elif oi in ("implizit", "implicit"): rel["object_inferred"] = "implicit"
        if config.get("ENABLE_GRAPH_VISUALIZATION", False):
            vis_res = visualize_graph(result_dict, config)
            result_dict["knowledgegraph_visualisation"] = [{"static": vis_res.get("png"), "interactive": vis_res.get("html")}]
        return result_dict
    
    return result
