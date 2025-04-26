"""
Entity linking core functionality.

This module provides the main functions for linking entities to knowledge bases
like Wikipedia, Wikidata, and DBpedia.
"""

import logging
import time
import re
import urllib.parse

from entityextractor.utils.text_utils import is_valid_wikipedia_url

from entityextractor.config.settings import get_config
from entityextractor.services.wikipedia_service import (
    fallback_wikipedia_url,
    get_wikipedia_extract,
    convert_to_de_wikipedia_url,
    follow_wikipedia_redirect
)
from entityextractor.services.wikidata_service import (
    get_wikidata_id_from_wikipedia_url,
    get_wikidata_details
)
from entityextractor.services.dbpedia_service import get_dbpedia_info_from_wikipedia_url
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.utils.text_utils import strip_trailing_ellipsis

def link_entities(entities, text=None, user_config=None):
    """
    Link extracted entities to Wikipedia, Wikidata, and DBpedia.
    
    Args:
        entities: List of extracted entities
        text: Original text (optional, for context)
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of entities with knowledge base links
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Link entities
    start_time = time.time()
    logging.info("Starting entity linking...")
    
    linked_entities = []
    
    for entity in entities:
        entity_name = entity.get("name", "")
        if not entity_name:
            continue
            
        linked_entity = entity.copy()
        
        # Step 1: Find Wikipedia URL
        # Zuerst prüfen, ob das LLM bereits eine URL generiert hat
        wikipedia_url = None
        llm_generated_url = entity.get("wikipedia_url", None)
        
        if llm_generated_url and is_valid_wikipedia_url(llm_generated_url):
            # Verwende die vom LLM generierte URL
            logging.info(f"Using LLM-generated Wikipedia URL for '{entity_name}': {llm_generated_url}")
            wikipedia_url = llm_generated_url
        else:
            # Wenn keine URL vorhanden oder ungültig, verwende den Fallback-Mechanismus
            if llm_generated_url:
                logging.info(f"LLM-generated URL invalid or incomplete: '{llm_generated_url}'. Using fallback.")
            wikipedia_url = fallback_wikipedia_url(entity_name, language=config.get("LANGUAGE", "de"))
        
        if wikipedia_url:
            linked_entity["wikipedia_url"] = wikipedia_url
            
            # Step 2: Follow redirects and get the correct title
            final_url, page_title = follow_wikipedia_redirect(wikipedia_url, entity_name)
            if final_url and final_url != wikipedia_url:
                linked_entity["wikipedia_url"] = final_url
                
            if page_title and page_title != entity_name:
                linked_entity["wikipedia_title"] = page_title
                
            # Step 3: Convert to German Wikipedia URL if configured
            if config.get("CONVERT_TO_DE", False) and "en.wikipedia.org" in linked_entity["wikipedia_url"]:
                de_url = convert_to_de_wikipedia_url(linked_entity["wikipedia_url"])
                if de_url:
                    linked_entity["wikipedia_url"] = de_url
            
            # Step 4: Get Wikipedia extract
            extract = get_wikipedia_extract(linked_entity["wikipedia_url"], config)
            
            # Step 4b: Fallback if no extract found with LLM URL
            if extract is None and llm_generated_url == wikipedia_url:
                logging.info(f"No extract found for LLM-generated URL. Trying fallback for '{entity_name}'...")
                fallback_url = fallback_wikipedia_url(entity_name, language=config.get("LANGUAGE", "de"))
                
                if fallback_url and fallback_url != wikipedia_url:
                    logging.info(f"Using fallback URL: {fallback_url} instead of {wikipedia_url}")
                    linked_entity["wikipedia_url"] = fallback_url
                    
                    # Try to get extract with fallback URL
                    extract = get_wikipedia_extract(fallback_url, config)
            
            if extract:
                linked_entity["wikipedia_extract"] = strip_trailing_ellipsis(extract)
            
            # Step 5: Get Wikidata ID and details
            if config.get("USE_WIKIDATA", True):
                # Pass entity name for fallback search if Wikipedia method fails
                wikidata_id = get_wikidata_id_from_wikipedia_url(linked_entity["wikipedia_url"], entity_name=entity_name, config=config)
                if wikidata_id:
                    linked_entity["wikidata_id"] = wikidata_id
                    
                    # Get detailed Wikidata information
                    wikidata_details = get_wikidata_details(
                        wikidata_id, 
                        language=config.get("LANGUAGE", "de"),
                        config=config
                    )
                    
                    if wikidata_details:
                        # Add Wikidata URL
                        linked_entity["wikidata_url"] = f"https://www.wikidata.org/wiki/{wikidata_id}"
                        
                        # Add description if available
                        if "description" in wikidata_details:
                            linked_entity["wikidata_description"] = wikidata_details["description"]
                            
                        # Add label/name if available
                        if "label" in wikidata_details:
                            linked_entity["wikidata_label"] = wikidata_details["label"]
                            
                        # Add types if available
                        if "types" in wikidata_details:
                            linked_entity["wikidata_types"] = wikidata_details["types"]
                            
                        # Add subclasses if available
                        if "subclasses" in wikidata_details:
                            linked_entity["wikidata_subclasses"] = wikidata_details["subclasses"]
                            
                        # Add image URL if available
                        if "image_url" in wikidata_details:
                            linked_entity["image_url"] = wikidata_details["image_url"]
                            
                        # Add website if available
                        if "website" in wikidata_details:
                            linked_entity["website"] = wikidata_details["website"]
                            
                        # Add coordinates if available
                        if "coordinates" in wikidata_details:
                            linked_entity["coordinates"] = wikidata_details["coordinates"]
                            
                        # Add foundation date if available
                        if "foundation_date" in wikidata_details:
                            linked_entity["foundation_date"] = wikidata_details["foundation_date"]
                            
                        # Add birth and death dates if available
                        if "birth_date" in wikidata_details:
                            linked_entity["birth_date"] = wikidata_details["birth_date"]
                            
                        if "death_date" in wikidata_details:
                            linked_entity["death_date"] = wikidata_details["death_date"]
                            
                        # Add occupations if available
                        if "occupations" in wikidata_details:
                            linked_entity["occupations"] = wikidata_details["occupations"]
            
            # Step 6: Get DBpedia information
            if config.get("USE_DBPEDIA", False):
                dbpedia_info = get_dbpedia_info_from_wikipedia_url(linked_entity["wikipedia_url"], config)
                if dbpedia_info:
                    # Store the complete DBpedia info object
                    linked_entity["dbpedia_info"] = dbpedia_info
                    
                    # Also store the title if available
                    if "dbpedia_title" in dbpedia_info:
                        linked_entity["dbpedia_title"] = dbpedia_info["dbpedia_title"]
                    elif "title" in dbpedia_info:
                        linked_entity["dbpedia_title"] = dbpedia_info["title"]
                        
                    # For backward compatibility, also store individual fields
                    if "resource_uri" in dbpedia_info:
                        linked_entity["dbpedia_uri"] = dbpedia_info["resource_uri"]
                    elif "uri" in dbpedia_info:
                        linked_entity["dbpedia_uri"] = dbpedia_info["uri"]
                        
                    # Add abstract if available
                    if "abstract" in dbpedia_info:
                        linked_entity["dbpedia_abstract"] = dbpedia_info["abstract"]
                        
                    # Add types if available
                    if "types" in dbpedia_info:
                        linked_entity["dbpedia_types"] = dbpedia_info["types"]
                        
                    # Add language information
                    if "language" in dbpedia_info:
                        linked_entity["dbpedia_language"] = dbpedia_info["language"]
        
        linked_entities.append(linked_entity)
    
    elapsed_time = time.time() - start_time
    logging.info(f"Entity linking completed in {elapsed_time:.2f} seconds")
    
    return linked_entities
