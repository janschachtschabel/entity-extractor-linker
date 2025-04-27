"""
DBpedia service module for the Entity Extractor.

This module provides functions for interacting with the DBpedia API
and extracting information from DBpedia resources.
"""

import logging
import requests
import urllib.parse
from SPARQLWrapper import SPARQLWrapper, JSON

from entityextractor.config.settings import DEFAULT_CONFIG
from entityextractor.services.wikipedia_service import get_wikipedia_title_in_language

def get_dbpedia_info_from_wikipedia_url(wikipedia_url, config=None):
    """
    Retrieve information about an entity from DBpedia based on its Wikipedia URL.
    
    Args:
        wikipedia_url: URL of the Wikipedia article
        config: Configuration dictionary with timeout and language settings
        
    Returns:
        A dictionary with DBpedia information or an empty dictionary if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    if not config.get("USE_DBPEDIA", False):
        logging.info("DBpedia integration is disabled in configuration.")
        return {}
        
    try:
        # Extract the title and language from the Wikipedia URL
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            source_lang = domain.split('.')[0]
        else:
            source_lang = "de"
            
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia URL has unexpected format for DBpedia: %s", wikipedia_url)
            return {}
            
        title = splitted[1].split("#")[0]
        title = urllib.parse.unquote(title).replace("_", " ")
        
        # Determine target language based on configuration
        target_lang = "de" if config.get("DBPEDIA_USE_DE", False) else "en"
        
        # If source and target languages differ, translate the title
        if source_lang != target_lang:
            translated_title = get_wikipedia_title_in_language(
                title, 
                from_lang=source_lang, 
                to_lang=target_lang,
                config=config
            )
            
            if translated_title:
                title = translated_title
                logging.info(f"Translated title for DBpedia: {source_lang}:{title} -> {target_lang}:{translated_title}")
            else:
                logging.warning(f"Could not translate title for DBpedia: {source_lang}:{title} -> {target_lang}")
                # If translation fails and we want German, try English as fallback
                if target_lang == "de":
                    target_lang = "en"
                    logging.info(f"Falling back to English DBpedia for {title}")
        
        # Construct DBpedia resource URI based on language
        if target_lang == "de":
            resource_uri = f"http://de.dbpedia.org/resource/{title.replace(' ', '_')}"
        else:  # target_lang == "en" or other
            resource_uri = f"http://dbpedia.org/resource/{title.replace(' ', '_')}"
        
        # Query DBpedia for information about the resource
        result = query_dbpedia_resource(resource_uri, target_lang, config)
        
        # Add metadata to the result
        result["dbpedia_language"] = target_lang
        result["dbpedia_title"] = title
        
        return result
    except Exception as e:
        logging.error(f"Error retrieving DBpedia info for {wikipedia_url}: {e}")
        return {}

def get_dbpedia_details(wikipedia_url, config=None):
    """
    Retrieve additional DBpedia details for an entity based on its Wikipedia URL.
    Wrapper for get_dbpedia_info_from_wikipedia_url.
    """
    if config is None:
        config = DEFAULT_CONFIG
    return get_dbpedia_info_from_wikipedia_url(wikipedia_url, config)

def query_dbpedia_resource(resource_uri, lang="en", config=None):
    """
    Query DBpedia for information about a resource using SPARQL.
    
    Args:
        resource_uri: The DBpedia resource URI
        lang: Language for the DBpedia endpoint ("de" or "en")
        config: Configuration dictionary with timeout settings
        
    Returns:
        A dictionary with DBpedia information or an empty dictionary if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    timeout = config.get("TIMEOUT_THIRD_PARTY", 15)
    dbpedia_timeout = config.get("DBPEDIA_TIMEOUT", timeout)
    
    # Define endpoints based on language
    if lang == "de":
        endpoints = [
            # German DBpedia endpoint
            "http://de.dbpedia.org/sparql",
            # Fallback to main DBpedia endpoint
            "http://dbpedia.org/sparql",
            "https://dbpedia.org/sparql"
        ]
    else:  # lang == "en" or other
        endpoints = [
            # Main DBpedia endpoint (for English)
            "http://dbpedia.org/sparql",
            "https://dbpedia.org/sparql",
            # Public DBpedia endpoint as fallback
            "https://dbpedia-live.openlinksw.com/sparql"
        ]
    
    # Construct the SPARQL query with property paths for types, part-whole and membership
    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbp: <http://dbpedia.org/property/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>

    SELECT ?abstract ?label ?type ?comment ?sameAs ?homepage ?thumbnail ?depiction
           ?lat ?long ?subject ?category ?birthDate ?deathDate ?birthPlace ?deathPlace
           ?populationTotal ?areaTotal ?country ?region ?foundingDate ?founder ?parentCompany
           ?part_of ?has_part ?member_of ?current_member ?former_member ?dbp_part_of ?dbp_member_of WHERE {{
       # Basic information
       OPTIONAL {{ <{resource_uri}> dbo:abstract ?abstract . FILTER(LANG(?abstract) = "{lang}") }}
       OPTIONAL {{ <{resource_uri}> rdfs:label ?label . FILTER(LANG(?label) = "{lang}") }}
       # Inherited and direct types via subclass path
       OPTIONAL {{ <{resource_uri}> rdf:type/rdfs:subClassOf* ?type . }}
       OPTIONAL {{ <{resource_uri}> rdfs:comment ?comment . FILTER(LANG(?comment) = "{lang}") }}
       OPTIONAL {{ <{resource_uri}> owl:sameAs ?sameAs . }}
       # Web presence
       OPTIONAL {{ <{resource_uri}> foaf:homepage ?homepage . }}
       OPTIONAL {{ <{resource_uri}> dbo:thumbnail ?thumbnail . }}
       OPTIONAL {{ <{resource_uri}> foaf:depiction ?depiction . }}
       # Geo information
       OPTIONAL {{ <{resource_uri}> geo:lat ?lat . }}
       OPTIONAL {{ <{resource_uri}> geo:long ?long . }}
       # Categories and subjects
       OPTIONAL {{ <{resource_uri}> dcterms:subject ?subject . }}
       OPTIONAL {{ <{resource_uri}> dbo:category ?category . }}
       # Additional entity info
       OPTIONAL {{ <{resource_uri}> dbo:birthDate ?birthDate . }}
       OPTIONAL {{ <{resource_uri}> dbo:deathDate ?deathDate . }}
       OPTIONAL {{ <{resource_uri}> dbo:birthPlace ?birthPlace . }}
       OPTIONAL {{ <{resource_uri}> dbo:deathPlace ?deathPlace . }}
       OPTIONAL {{ <{resource_uri}> dbo:populationTotal ?populationTotal . }}
       OPTIONAL {{ <{resource_uri}> dbo:areaTotal ?areaTotal . }}
       OPTIONAL {{ <{resource_uri}> dbo:country ?country . }}
       OPTIONAL {{ <{resource_uri}> dbo:region ?region . }}
       OPTIONAL {{ <{resource_uri}> dbo:foundingDate ?foundingDate . }}
       OPTIONAL {{ <{resource_uri}> dbo:founder ?founder . }}
       OPTIONAL {{ <{resource_uri}> dbo:parentCompany ?parentCompany . }}
       # Part-whole relations (direct and inverse)
       OPTIONAL {{ <{resource_uri}> dbo:isPartOf ?part_of . }}
       OPTIONAL {{ <{resource_uri}> ^dbo:hasPart ?part_of . }}
       OPTIONAL {{ <{resource_uri}> dbo:hasPart ?has_part . }}
       OPTIONAL {{ <{resource_uri}> ^dbo:isPartOf ?has_part . }}
       # Membership generic (direct and inverse)
       OPTIONAL {{ <{resource_uri}> ?p_mem ?member_of . ?p_mem rdfs:subPropertyOf* dul:hasMember . }}
       OPTIONAL {{ <{resource_uri}> dbo:currentMember ?current_member . }}
       OPTIONAL {{ <{resource_uri}> dbo:formerMember ?former_member . }}
       # Wiki-infobox raw
       OPTIONAL {{ <{resource_uri}> dbp:partof ?dbp_part_of . }}
       OPTIONAL {{ <{resource_uri}> dbp:memberOf ?dbp_member_of . }}
    }} LIMIT 200
    """
    
    # Try each endpoint until one works
    for endpoint in endpoints:
        try:
            # Set up the SPARQL wrapper
            sparql = SPARQLWrapper(endpoint)
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            sparql.setTimeout(dbpedia_timeout)
            
            # Execute the query
            logging.info(f"Querying DBpedia endpoint {endpoint} for resource: {resource_uri}")
            results = sparql.query().convert()
            
            # Process the results
            bindings = results.get("results", {}).get("bindings", [])
            if not bindings:
                logging.warning(f"No DBpedia data found for {resource_uri} at {endpoint}")
                continue  # Try next endpoint
                
            # Extract information from the results
            result = {
                "resource_uri": resource_uri,
                "endpoint": endpoint,
                "language": lang
            }
            
            # Extract labels
            labels = [b.get("label", {}).get("value") for b in bindings if "label" in b]
            if labels:
                result["labels"] = list(dict.fromkeys(labels))  # Deduplizieren
            
            # Extract abstract
            abstracts = [b.get("abstract", {}).get("value") for b in bindings if "abstract" in b]
            if abstracts:
                result["abstract"] = abstracts[0]
                
            # Extract types
            types = [b.get("type", {}).get("value") for b in bindings if "type" in b]
            if types:
                # Filter out basic RDF types
                filtered_types = [t for t in types if t]
                if filtered_types:
                    result["types"] = list(dict.fromkeys(filtered_types))  # Deduplizieren
                    
            # Extract comment
            comments = [b.get("comment", {}).get("value") for b in bindings if "comment" in b]
            if comments:
                result["comment"] = comments[0]
                
            # Extract sameAs links
            same_as = [b.get("sameAs", {}).get("value") for b in bindings if "sameAs" in b]
            if same_as:
                result["sameAs"] = list(dict.fromkeys(same_as))  # Deduplizieren
                
            # Extract web presence information
            homepages = [b.get("homepage", {}).get("value") for b in bindings if "homepage" in b]
            if homepages:
                result["homepage"] = homepages[0]
                
            thumbnails = [b.get("thumbnail", {}).get("value") for b in bindings if "thumbnail" in b]
            if thumbnails:
                result["thumbnail"] = thumbnails[0]
                
            depictions = [b.get("depiction", {}).get("value") for b in bindings if "depiction" in b]
            if depictions:
                result["depiction"] = depictions[0]
                
            # Extract geo information
            lats = [b.get("lat", {}).get("value") for b in bindings if "lat" in b]
            longs = [b.get("long", {}).get("value") for b in bindings if "long" in b]
            if lats and longs:
                result["coordinates"] = {
                    "latitude": lats[0],
                    "longitude": longs[0]
                }
                
            # Extract categories and subjects
            subjects = [b.get("subject", {}).get("value") for b in bindings if "subject" in b]
            if subjects:
                result["subjects"] = list(dict.fromkeys(subjects))  # Deduplizieren
                
            categories = [b.get("category", {}).get("value") for b in bindings if "category" in b]
            if categories:
                result["categories"] = list(dict.fromkeys(categories))  # Deduplizieren
                
            # Extract person-specific information
            birth_dates = [b.get("birthDate", {}).get("value") for b in bindings if "birthDate" in b]
            if birth_dates:
                result["birth_date"] = birth_dates[0]
                
            death_dates = [b.get("deathDate", {}).get("value") for b in bindings if "deathDate" in b]
            if death_dates:
                result["death_date"] = death_dates[0]
                
            birth_places = [b.get("birthPlace", {}).get("value") for b in bindings if "birthPlace" in b]
            if birth_places:
                result["birth_place"] = birth_places[0]
                
            death_places = [b.get("deathPlace", {}).get("value") for b in bindings if "deathPlace" in b]
            if death_places:
                result["death_place"] = death_places[0]
                
            # Extract location-specific information
            populations = [b.get("populationTotal", {}).get("value") for b in bindings if "populationTotal" in b]
            if populations:
                result["population"] = populations[0]
                
            areas = [b.get("areaTotal", {}).get("value") for b in bindings if "areaTotal" in b]
            if areas:
                result["area"] = areas[0]
                
            countries = [b.get("country", {}).get("value") for b in bindings if "country" in b]
            if countries:
                result["country"] = countries[0]
                
            regions = [b.get("region", {}).get("value") for b in bindings if "region" in b]
            if regions:
                result["region"] = regions[0]
                
            # Extract organization-specific information
            founding_dates = [b.get("foundingDate", {}).get("value") for b in bindings if "foundingDate" in b]
            if founding_dates:
                result["founding_date"] = founding_dates[0]
                
            founders = [b.get("founder", {}).get("value") for b in bindings if "founder" in b]
            if founders:
                result["founder"] = founders[0]
                
            parent_companies = [b.get("parentCompany", {}).get("value") for b in bindings if "parentCompany" in b]
            if parent_companies:
                result["parent_company"] = parent_companies[0]
                
            # Extract generic part-whole and membership bindings
            vals = lambda k: [b.get(k, {}).get("value") for b in bindings if k in b]
            part_of_vals = vals("part_of")
            has_part_vals = vals("has_part")
            member_of_vals = vals("member_of")
            current_vals = vals("current_member")
            former_vals = vals("former_member")
            dbp_part_vals = vals("dbp_part_of")
            dbp_member_vals = vals("dbp_member_of")
            if part_of_vals: result["part_of"] = list(dict.fromkeys(part_of_vals))
            if has_part_vals: result["has_parts"] = list(dict.fromkeys(has_part_vals))
            if member_of_vals: result["member_of"] = list(dict.fromkeys(member_of_vals))
            if current_vals: result["current_member"] = list(dict.fromkeys(current_vals))
            if former_vals: result["former_member"] = list(dict.fromkeys(former_vals))
            if dbp_part_vals: result["dbp_part_of"] = list(dict.fromkeys(dbp_part_vals))
            if dbp_member_vals: result["dbp_member_of"] = list(dict.fromkeys(dbp_member_vals))
            
            # Ensure type and relation keys are always present (even if empty)
            for key in ("types", "part_of", "has_parts", "member_of", "current_member", "former_member", "dbp_part_of", "dbp_member_of"):
                result.setdefault(key, [])
             
            logging.info(f"Successfully retrieved DBpedia data for {resource_uri} from {endpoint}")
            return result
            
        except Exception as e:
            logging.warning(f"Error querying DBpedia endpoint {endpoint} for {resource_uri}: {e}")
            # Continue to the next endpoint
    
    # If we get here, all endpoints failed
    logging.error(f"All DBpedia endpoints failed for {resource_uri}")
    return {}
