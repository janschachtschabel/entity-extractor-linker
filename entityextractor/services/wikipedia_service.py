"""
Wikipedia service module for the Entity Extractor.

This module provides functions for interacting with the Wikipedia API
and extracting information from Wikipedia pages.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse

from entityextractor.config.settings import DEFAULT_CONFIG
from entityextractor.utils.text_utils import is_valid_wikipedia_url

def get_wikipedia_title_in_language(title, from_lang="de", to_lang="en", config=None):
    """
    Convert a Wikipedia title from one language to another using interlanguage links.
    
    Args:
        title: The Wikipedia article title
        from_lang: Source language of the title
        to_lang: Target language for the title
        config: Configuration dictionary with timeout settings
        
    Returns:
        The corresponding title in the target language or None if no translation is found
    """
    if from_lang == to_lang:
        return title
        
    if config is None:
        config = DEFAULT_CONFIG
        
    api_url = f"https://{from_lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "langlinks",
        "titles": title,
        "lllang": to_lang,
        "format": "json"
    }
    
    try:
        logging.info(f"Searching translation from {from_lang}:{title} to {to_lang}")
        r = requests.get(api_url, params=params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        
        pages = data.get("query", {}).get("pages", {})
        target_title = None
        
        for page_id, page in pages.items():
            langlinks = page.get("langlinks", [])
            if langlinks:
                # Take the first entry - this should be the target language version
                target_title = langlinks[0].get("*")
                break
                
        if target_title:
            logging.info(f"Translation found: {from_lang}:{title} -> {to_lang}:{target_title}")
            return target_title
        else:
            logging.info(f"No translation found from {from_lang}:{title} to {to_lang}")
            return None
            
    except Exception as e:
        logging.error(f"Error retrieving translation for {title}: {e}")
        return None

def convert_to_de_wikipedia_url(wikipedia_url):
    """
    Convert a Wikipedia URL (e.g., from en.wikipedia.org) to the German Wikipedia URL if available.
    
    Args:
        wikipedia_url: The original Wikipedia URL
        
    Returns:
        Tuple of (German Wikipedia URL or original URL, updated entity name or None)
    """
    # If the URL is already German, don't change it
    if "de.wikipedia.org" in wikipedia_url:
        return wikipedia_url, None

    try:
        # Extract the title from the original URL
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia URL has unexpected format: %s", wikipedia_url)
            return wikipedia_url, None
        original_title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Error extracting title from URL %s: %s", wikipedia_url, e)
        return wikipedia_url, None
        
    try:
        # Determine the source language from the domain
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            from_lang = domain.split('.')[0]
        else:
            from_lang = "en"
            
        # Get the German title using interlanguage links
        de_title = get_wikipedia_title_in_language(original_title, from_lang=from_lang, to_lang="de")
        
        if de_title:
            # Create the German Wikipedia URL
            de_title_encoded = urllib.parse.quote(de_title.replace(" ", "_"))
            de_url = f"https://de.wikipedia.org/wiki/{de_title_encoded}"
            logging.info("Conversion: '%s' converted to '%s'", wikipedia_url, de_url)
            return de_url, de_title  # de_title as optional updated entity name
        else:
            logging.info("No German version found for URL: %s", wikipedia_url)
            return wikipedia_url, None
    except Exception as e:
        logging.error("Error querying German langlinks for %s: %s", wikipedia_url, e)
        return wikipedia_url, None

def fallback_wikipedia_url(query, langs=None, language="de"):
    """
    Search for a Wikipedia article for an entity and return a valid URL.
    
    Args:
        query: The search term (entity name)
        langs: Optional list of languages to try in sequence
               (overridden if language="en" is set)
        language: Language configuration ("de" or "en")
        
    Returns:
        A valid Wikipedia URL or None if none was found
    """
    # If no languages are specified, choose based on language parameter
    if not langs:
        if language == "en":
            langs = ["en", "de"]
        else:
            langs = ["de", "en"]
    
    # Try each language in sequence
    for lang in langs:
        try:
            # URL-encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Use the opensearch API to find matching articles
            api_url = f"https://{lang}.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json"
            }
            
            logging.info(f"Fallback ({lang}): Searching Wikipedia URL for '{query}'...")
            
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 3 and data[3] and len(data[3]) > 0:
                url = data[3][0]
                if is_valid_wikipedia_url(url):
                    logging.info(f"Fallback ({lang}) successful: Found URL '{url}' for '{query}'.")
                    return url
        except Exception as e:
            logging.error(f"Error searching Wikipedia for {query} in {lang}: {e}")
            
    logging.warning(f"Fallback failed: No Wikipedia URL found for '{query}'.")
    return None

def follow_wikipedia_redirect(url, entity_name):
    """
    Follow Wikipedia redirects and extract the actual page title.
    
    1. Directly check the provided URL for redirects via HTTP request.
    2. Extract the real Wikipedia title from <title> of the target page.
    3. Return final URL and title.
    
    Args:
        url: Initial Wikipedia URL
        entity_name: Original entity name
        
    Returns:
        Tuple of (final URL, page title)
    """
    if not url:
        logging.warning(f"No URL provided for '{entity_name}'")
        return None, None
        
    try:
        # Follow redirects and get the final URL
        response = requests.get(url, allow_redirects=True)
        final_url = response.url
        html = response.text
        
        # Check for soft redirect via canonical link
        canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        if canonical_match:
            canonical_url = canonical_match.group(1)
            if canonical_url != final_url:
                logging.info(f"Wikipedia-Soft-Redirect (canonical) detected: {final_url} -> {canonical_url}")
                # Extract title from canonical URL
                title_match = re.search(r'/wiki/([^#]+)', canonical_url)
                if title_match:
                    canonical_title = urllib.parse.unquote(title_match.group(1)).replace('_', ' ')
                    logging.info(f"Entity corrected: '{entity_name}' -> '{canonical_title}'")
                    return canonical_url, canonical_title
                return canonical_url, entity_name
        
        # Extract page title from HTML
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            page_title = title_match.group(1)
            # Remove " - Wikipedia" oder " – Wikipedia" suffix (berücksichtigt sowohl Bindestrich als auch Gedankenstrich)
            page_title = re.sub(r'[\s]*[–-][\s]*Wikipedia.*$', '', page_title)
            
            if page_title.lower() != entity_name.lower():
                logging.info(f"Wikipedia-Title-Correction: '{entity_name}' -> '{page_title}'")
            else:
                logging.info(f"Wikipedia-Opensearch: '{entity_name}' -> {final_url} | Official title: '{page_title}'")
            return final_url, page_title
        else:
            logging.info(f"Wikipedia-Opensearch: '{entity_name}' -> {final_url} | Official title: '{page_title}'")
            return final_url, page_title
    except Exception as e:
        logging.warning(f"Wikipedia-Redirect/Title-Check failed: {e}")
        splitted = url.split("/wiki/")
        title = splitted[1].split("#")[0].replace('_', ' ') if len(splitted) >= 2 else entity_name
        return url, title

def get_wikipedia_extract(wikipedia_url, config=None):
    """
    Retrieve the extract (summary) of a Wikipedia article.
    
    Args:
        wikipedia_url: URL of the Wikipedia article
        config: Configuration dictionary with timeout settings
        
    Returns:
        The article extract or None if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    try:
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia URL has unexpected format (Extract): %s", wikipedia_url)
            return None
        title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Error extracting title for extract: %s", e)
        return None

    try:
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            lang = domain.split('.')[0]
        else:
            domain = "de.wikipedia.org"
            lang = "de"
    except Exception as e:
        logging.error("Error determining language for extract: %s", e)
        lang = "de"

    # 1. Attempt: Wikipedia API for extract
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "format": "json",
        "titles": title
    }
    try:
        r = requests.get(api_url, params=params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            extract_text = page.get("extract", "")
            if extract_text:
                logging.info(f"Wikipedia extract for URL {wikipedia_url} successfully loaded.")
                return extract_text
        
        # No extract found - fallback to HTML parsing
        logging.warning(f"No Wikipedia extract found for URL {wikipedia_url}.")
        logging.warning(f"Note: This Wikipedia page may not have a dedicated Wikidata entry/extract (possibly a redirect/collection page). Trying fallback extract with BeautifulSoup.")
        
        # 2. Attempt: Direct HTML parsing with BeautifulSoup
        try:
            response = requests.get(wikipedia_url, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Different strategies for extracting content
            content = None
            
            # Strategy 1: Main content via div#mw-content-text > div.mw-parser-output
            main_content = soup.select_one('#mw-content-text > .mw-parser-output')
            if main_content:
                # Find the first paragraph that is not empty and not in an infobox
                paragraphs = []
                for p in main_content.find_all('p'):
                    # Skip empty paragraphs or those in infoboxes
                    if p.text.strip() and not p.find_parent(class_='infobox'):
                        paragraphs.append(p.text.strip())
                
                if paragraphs:
                    content = ' '.join(paragraphs[:3])  # Take the first 3 paragraphs
            
            # Strategy 2: If strategy 1 fails, try with the first section
            if not content:
                first_heading = soup.select_one('.mw-headline')
                if first_heading and first_heading.parent:
                    section = first_heading.parent.find_next_sibling()
                    section_text = []
                    while section and section.name != 'h2' and section.name != 'h3':
                        if section.name == 'p' and section.text.strip():
                            section_text.append(section.text.strip())
                        section = section.find_next_sibling()
                    
                    if section_text:
                        content = ' '.join(section_text[:3])  # Take the first 3 paragraphs
            
            # Strategy 3: Search for all paragraphs in the main area
            if not content:
                all_paragraphs = soup.select('#bodyContent p')
                paragraphs = [p.text.strip() for p in all_paragraphs if p.text.strip() and not p.find_parent(class_='infobox')]
                if paragraphs:
                    content = ' '.join(paragraphs[:3])  # Take the first 3 paragraphs
            
            if content:
                logging.info(f"BeautifulSoup: Extract successfully extracted for {wikipedia_url}.")
                return content
            else:
                logging.warning(f"BeautifulSoup: No paragraphs found in content for {wikipedia_url}.")
                return None
                
        except Exception as bs_error:
            logging.error(f"Error in BeautifulSoup fallback for {wikipedia_url}: {bs_error}")
            return None
            
    except Exception as e:
        logging.error("Error retrieving Wikipedia extract for %s: %s", wikipedia_url, e)
        return None
