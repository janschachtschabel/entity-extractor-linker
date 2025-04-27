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
import wptools

from entityextractor.config.settings import DEFAULT_CONFIG
from entityextractor.utils.text_utils import is_valid_wikipedia_url
from entityextractor.utils.wiki_url_utils import sanitize_wikipedia_url

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
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)
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
    # fallback_wikipedia_url gibt bereits eine valide URL zurück, aber wir encodieren sicherheitshalber
    # (falls Opensearch einen ungecodeten Titel liefert)
    # Die Funktion wird aber meistens intern aufgerufen, daher optional am Ende encodieren
    # (siehe get_wikipedia_extract)
    pass  # Keine Änderung direkt, Encodierung erfolgt bei Verwendung
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
    url = sanitize_wikipedia_url(url)
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
    # Für API-Parameter: Klartext-Titel verwenden
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

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
        title_plain = urllib.parse.unquote(title)
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

    # 1. Versuch: Wikipedia API für Extract (LLM-URL)
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "format": "json",
        "titles": title_plain
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
        # Kein Extract gefunden: Jetzt Fallback-URL (Opensearch) versuchen
        logging.warning(f"No Wikipedia extract found for URL {wikipedia_url}. Trying fallback URL (Opensearch)...")
        fallback_url = fallback_wikipedia_url(title, language=lang)
        if fallback_url and fallback_url != wikipedia_url:
            try:
                splitted_fb = fallback_url.split("/wiki/")
                if len(splitted_fb) < 2:
                    logging.warning("Fallback Wikipedia URL has unexpected format: %s", fallback_url)
                else:
                    fb_title = splitted_fb[1].split("#")[0]
                    fb_title_plain = urllib.parse.unquote(fb_title)
                    fb_api_url = f"https://{lang}.wikipedia.org/w/api.php"
                    fb_params = params.copy()
                    fb_params["titles"] = fb_title_plain
                    r_fb = requests.get(fb_api_url, params=fb_params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
                    r_fb.raise_for_status()
                    fb_data = r_fb.json()
                    fb_pages = fb_data.get("query", {}).get("pages", {})
                    for fb_page_id, fb_page in fb_pages.items():
                        fb_extract = fb_page.get("extract", "")
                        if fb_extract:
                            logging.info(f"Wikipedia extract for fallback URL {fallback_url} successfully loaded.")
                            return fb_extract
            except Exception as fb_error:
                logging.error(f"Error retrieving Wikipedia extract for fallback URL {fallback_url}: {fb_error}")
        # Prüfe vor BeautifulSoup auf Softredirects (canonical)
        final_url, final_title = follow_wikipedia_redirect(wikipedia_url, title)
        if final_url != wikipedia_url:
            logging.info(f"Softredirect erkannt: {wikipedia_url} -> {final_url} | Versuche Extrakt erneut.")
            # Versuche erneut den Extract für die Zielseite
            try:
                splitted_sr = final_url.split("/wiki/")
                if len(splitted_sr) < 2:
                    logging.warning("Softredirect-Ziel-URL hat unerwartetes Format: %s", final_url)
                else:
                    sr_title = splitted_sr[1].split("#")[0]
                    sr_title_plain = urllib.parse.unquote(sr_title)
                    sr_api_url = f"https://{lang}.wikipedia.org/w/api.php"
                    sr_params = params.copy()
                    sr_params["titles"] = sr_title_plain
                    r_sr = requests.get(sr_api_url, params=sr_params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
                    r_sr.raise_for_status()
                    sr_data = r_sr.json()
                    sr_pages = sr_data.get("query", {}).get("pages", {})
                    for sr_page_id, sr_page in sr_pages.items():
                        sr_extract = sr_page.get("extract", "")
                        if sr_extract:
                            logging.info(f"Wikipedia extract nach Softredirect für URL {final_url} erfolgreich geladen.")
                            return sr_extract
            except Exception as sr_error:
                logging.error(f"Fehler beim Wikipedia-Extract nach Softredirect für {final_url}: {sr_error}")
        # Erst jetzt BeautifulSoup als letzte Notlösung
        logging.warning(f"No Wikipedia extract found via API for both URL {wikipedia_url} and fallback. Trying BeautifulSoup...")
        try:
            response = requests.get(wikipedia_url, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            content = None
            main_content = soup.select_one('#mw-content-text > .mw-parser-output')
            if main_content:
                paragraphs = []
                for p in main_content.find_all('p'):
                    if p.text.strip() and not p.find_parent(class_='infobox'):
                        paragraphs.append(p.text.strip())
                if paragraphs:
                    content = ' '.join(paragraphs[:3])
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
                        content = ' '.join(section_text[:3])
            if not content:
                all_paragraphs = soup.select('#bodyContent p')
                paragraphs = [p.text.strip() for p in all_paragraphs if p.text.strip() and not p.find_parent(class_='infobox')]
                if paragraphs:
                    content = ' '.join(paragraphs[:3])
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

# Retrieve article categories via MediaWiki API
def get_wikipedia_categories(wikipedia_url, config=None):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve Wikipedia categories via MediaWiki API.
    Returns a list of category names (without 'Category:' prefix).
    """
    if config is None:
        config = DEFAULT_CONFIG
    try:
        # Parse title and language
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Invalid Wikipedia URL for categories: %s", wikipedia_url)
            return []
        title = splitted[1].split("#")[0]
        title_plain = urllib.parse.unquote(title)
        domain = wikipedia_url.split("://")[1].split("/")[0] if "://" in wikipedia_url else "de.wikipedia.org"
        lang = domain.split(".")[0]
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "categories",
            "titles": title_plain,
            "cllimit": "max",
            "format": "json"
        }
        r = requests.get(api_url, params=params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        cats = []
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            for c in page.get("categories", []):
                name = c.get("title", "")
                if name.startswith("Category:"):
                    name = name.split("Category:", 1)[1]
                cats.append(name)
        return list(dict.fromkeys(cats))
    except Exception as e:
        logging.error("Error retrieving Wikipedia categories for %s: %s", wikipedia_url, e)
        return []

def get_wikipedia_details(wikipedia_url, config=None):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve additional details from a Wikipedia page using direct API calls: infobox, see-also links, image.
    """
    if config is None:
        config = DEFAULT_CONFIG
    # parse title and language
    try:
        parts = wikipedia_url.split('/wiki/')
        if len(parts) < 2:
            logging.warning("Invalid Wikipedia URL for details: %s", wikipedia_url)
            return {}
        title = parts[1].split('#')[0]
    except Exception as e:
        logging.error("Error parsing title for details: %s", e)
        return {}
    try:
        domain = wikipedia_url.split('://')[1].split('/')[0]
        lang = domain.split('.')[0]
    except Exception as e:
        logging.error("Error parsing language for details: %s", e)
        lang = 'de'
    endpoint = f"https://{lang}.wikipedia.org/w/api.php"
    result = {}
    # 1. Infobox via parse/text
    try:
        params = {
            'action': 'parse',
            'page': title_plain,
            'prop': 'text',
            'format': 'json',
            'section': 0
        }
        r = requests.get(endpoint, params=params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        html = r.json().get('parse', {}).get('text', {}).get('*', '')
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='infobox')
        if table:
            info = {}
            for tr in table.find_all('tr'):
                th = tr.find('th')
                td = tr.find('td')
                if th and td:
                    key = th.get_text(' ', strip=True)
                    value = td.get_text(' ', strip=True)
                    info[key] = value
            if info:
                result['infobox'] = info
    except Exception as e:
        logging.error("Error parsing infobox for %s: %s", wikipedia_url, e)
    # 2. See also links via parse/links
    try:
        sec_params = {'action': 'parse', 'page': title_plain, 'prop': 'sections', 'format': 'json'}
        rsec = requests.get(endpoint, params=sec_params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        rsec.raise_for_status()
        secs = rsec.json().get('parse', {}).get('sections', [])
        idx = next((s['index'] for s in secs if s.get('line', '').lower() in ('see also', 'siehe auch')), None)
        if idx:
            link_params = {'action': 'parse', 'page': title_plain, 'prop': 'links', 'format': 'json', 'section': idx}
            rlink = requests.get(endpoint, params=link_params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
            rlink.raise_for_status()
            links = rlink.json().get('parse', {}).get('links', [])
            see = []
            for l in links:
                link_title = l.get('title') or l.get('*')
                slug = urllib.parse.quote(link_title.replace(' ', '_'))
                see.append(f"https://{lang}.wikipedia.org/wiki/{slug}")
            if see:
                result['see_also'] = see
    except Exception as e:
        logging.error("Error fetching see_also for %s: %s", wikipedia_url, e)
    # 3. Main image via pageimages
    try:
        img_params = {'action': 'query', 'prop': 'pageimages', 'piprop': 'original', 'titles': title_plain, 'format': 'json'}
        rimg = requests.get(endpoint, params=img_params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        rimg.raise_for_status()
        pages = rimg.json().get('query', {}).get('pages', {})
        page_data = next(iter(pages.values()))
        img = page_data.get('original', {}).get('source') or page_data.get('thumbnail', {}).get('source')
        if img:
            result['image'] = img
    except Exception as e:
        logging.error("Error fetching image for %s: %s", wikipedia_url, e)
    return result

def get_wikipedia_summary_and_categories_props(wikipedia_url, config=None):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve title, extract, categories and Wikidata ID/URL in a single MediaWiki API call.

    Args:
        wikipedia_url: URL of the Wikipedia article
        config: Configuration dict with TIMEOUT_THIRD_PARTY

    Returns:
        A dict with keys 'title', 'extract', 'categories', 'wikidata_id', 'wikidata_url'
    """
    if config is None:
        config = DEFAULT_CONFIG
    try:
        parts = wikipedia_url.split('/wiki/')
        if len(parts) < 2:
            logging.warning("Invalid Wikipedia URL: %s", wikipedia_url)
            return {}
        title = parts[1].split('#')[0]
    except Exception as e:
        logging.error("Error parsing title from URL: %s", e)
        return {}
    try:
        domain = wikipedia_url.split('://')[1].split('/')[0]
        lang = domain.split('.')[0]
    except Exception as e:
        logging.error("Error parsing language from URL: %s", e)
        lang = 'de'
    endpoint = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'extracts|categories|pageprops',
        'ppprop': 'wikibase_item',
        'titles': title,
        'exintro': 1,
        'explaintext': 1,
        'cllimit': 'max',
        'clshow': '!hidden'
    }
    try:
        r = requests.get(endpoint, params=params, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        pages = r.json().get('query', {}).get('pages', {})
        page = next(iter(pages.values()))
        result = {
            'title': page.get('title'),
            'extract': page.get('extract', ''),
            'categories': [c.get('title','').split('Category:',1)[-1] for c in page.get('categories', [])],
            'wikidata_id': page.get('pageprops', {}).get('wikibase_item')
        }
        wid = result['wikidata_id']
        result['wikidata_url'] = f"https://www.wikidata.org/wiki/{wid}" if wid else None
        return result
    except Exception as e:
        logging.error("Error fetching wiki summary and categories: %s", e)
        return {}
