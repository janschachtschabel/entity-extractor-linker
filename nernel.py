#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import logging
import urllib.parse
import requests
import io
import sys
from openai import OpenAI
import urllib3

# Setze UTF-8-Kodierung für Konsole, um Unicode-Probleme zu vermeiden
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

##############################################################################
# Standardkonfiguration für die Entity-Extraktion
##############################################################################
DEFAULT_CONFIG = {
    "USE_WIKIPEDIA": True,    # Immer True, Wikipedia ist Pflicht
    "USE_WIKIDATA": True,     # Standard: aktiviert
    "USE_DBPEDIA": False,     # Standard: deaktiviert
    "DBPEDIA_USE_DE": False,  # Standard: Englische DBpedia verwenden
    "DBPEDIA_TIMEOUT": 15,    # Timeout in Sekunden für DBpedia-Anfragen
    "MODEL": "gpt-4o-mini",   # Standard LLM-Modell für Entitätsextraktion
    "OPENAI_API_KEY": None,   # Standard: None = Aus Umgebungsvariable lesen
    "LANGUAGE": "de",         # Sprache: "de" für Deutsch, "en" für Englisch
    "SHOW_STATUS": True,      # Status-/Logging-Meldungen anzeigen (True) oder ausblenden (False)
    "SUPPRESS_TLS_WARNINGS": True  # TLS-Warnungen von urllib3 unterdrücken
}

# Logging-Konfiguration basierend auf der SHOW_STATUS-Einstellung
def configure_logging(config=None):
    if config is None:
        config = DEFAULT_CONFIG
        
    # Standard-Logging-Konfiguration
    logging_level = logging.INFO if config.get("SHOW_STATUS", True) else logging.ERROR
    
    # Handler zurücksetzen, um Doppelungen zu vermeiden
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Neue Konfiguration setzen
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # TLS-Warnungen unterdrücken, wenn in Konfiguration aktiviert
    if config.get("SUPPRESS_TLS_WARNINGS", True):
        # Option 1: Warnungen ins Logging-System umleiten
        logging.captureWarnings(True)
        
        # Option 2: Alle urllib3-Warnungen vollständig deaktivieren
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialisiere Logging mit Standardkonfiguration
configure_logging()

##############################################################################
# Client-Initialisierung und Konfiguration
##############################################################################
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    logging.error("Kein API-Key vorhanden. Bitte Umgebungsvariable OPENAI_API_KEY setzen.")
    raise ValueError("Kein API-Key vorhanden.")

client = OpenAI(api_key=api_key)

##############################################################################
# Hilfsfunktion: Entfernt Markdown-Codeblock-Markierungen aus LLM-Antworten
##############################################################################
def clean_json_response(raw_text):
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        # Entferne erste und letzte Zeile, falls sie mit ``` beginnen
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()
    return raw_text

##############################################################################
# Hilfsfunktion: Validiert, ob eine Wikipedia-URL dem erwarteten Muster entspricht.
##############################################################################
def is_valid_wikipedia_url(url):
    pattern = re.compile(r"^https?://[a-z]{2}\.wikipedia\.org/wiki/[\w\-%]+")
    return bool(pattern.match(url))

##############################################################################
# Neue Funktion: Konvertiert einen Wikipedia-Link (z.B. aus en.wikipedia.org)
# in den deutschen Wikipedia-Link, sofern vorhanden. Dabei werden die intersprachlichen
# Verknüpfungen (langlinks) genutzt.
##############################################################################
def convert_to_de_wikipedia_url(wikipedia_url):
    # Wenn die URL bereits deutsch ist, nichts ändern.
    if "de.wikipedia.org" in wikipedia_url:
        return wikipedia_url, None

    try:
        # Extrahiere den Titel aus der Original-URL
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia-URL hat unerwartetes Format: %s", wikipedia_url)
            return wikipedia_url, None
        original_title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Fehler beim Extrahieren des Titels aus URL %s: %s", wikipedia_url, e)
        return wikipedia_url, None

    # Query an den englischen Wikipedia-Endpunkt, um deutsche Langlinks abzurufen.
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "langlinks",
        "lllang": "de",
        "format": "json",
        "titles": original_title
    }
    try:
        logging.info("HTTP Request: POST https://api.openai.com/v1/chat/completions")
        r = requests.get(api_url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        de_title = None
        for page_id, page in pages.items():
            langlinks = page.get("langlinks", [])
            if langlinks:
                # Nehme den ersten Eintrag – das sollte die deutsche Version sein.
                de_title = langlinks[0].get("*")
                break
        if de_title:
            # URL-kodierung des Titels
            de_title_encoded = urllib.parse.quote(de_title.replace(" ", "_"))
            de_url = f"https://de.wikipedia.org/wiki/{de_title_encoded}"
            logging.info("Konvertierung: '%s' wird umgewandelt zu '%s'", wikipedia_url, de_url)
            return de_url, de_title  # de_title als optionaler aktualisierter Entitätsname
        else:
            logging.info("Keine deutsche Version gefunden für URL: %s", wikipedia_url)
            return wikipedia_url, None
    except Exception as e:
        logging.error("Fehler bei der Abfrage der deutschen Langlinks für %s: %s", wikipedia_url, e)
        return wikipedia_url, None

##############################################################################
# Hilfsfunktion: Konvertiert einen Wikipedia-Titel in den entsprechenden Titel in einer anderen Sprache
##############################################################################
def get_wikipedia_title_in_language(title, from_lang="de", to_lang="en", timeout=15):
    """
    Konvertiert einen Wikipedia-Titel von einer Sprache in eine andere,
    indem die intersprachlichen Verknüpfungen (langlinks) genutzt werden.
    
    Args:
        title: Der Titel des Wikipedia-Artikels
        from_lang: Die Quellsprache des Titels
        to_lang: Die Zielsprache für den Titel
        timeout: Timeout in Sekunden
        
    Returns:
        Der entsprechende Titel in der Zielsprache oder None, wenn keine Übersetzung gefunden wird
    """
    if from_lang == to_lang:
        return title
        
    # Query an den Wikipedia-Endpunkt der Quellsprache, um Langlinks abzurufen
    api_url = f"https://{from_lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "langlinks",
        "lllang": to_lang,
        "format": "json",
        "titles": title
    }
    
    try:
        logging.info(f"Suche Übersetzung von {from_lang}:{title} nach {to_lang}")
        r = requests.get(api_url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        
        pages = data.get("query", {}).get("pages", {})
        target_title = None
        
        for page_id, page in pages.items():
            langlinks = page.get("langlinks", [])
            if langlinks:
                # Nehme den ersten Eintrag – das sollte die Zielsprachen-Version sein
                target_title = langlinks[0].get("*")
                break
                
        if target_title:
            logging.info(f"Übersetzung gefunden: {from_lang}:{title} -> {to_lang}:{target_title}")
            return target_title
        else:
            logging.info(f"Keine Übersetzung von {from_lang}:{title} nach {to_lang} gefunden")
            return None
            
    except Exception as e:
        logging.error(f"Fehler beim Abrufen der Übersetzung für {title}: {e}")
        return None

##############################################################################
# Fallback-Funktion: Ermittle eine gültige Wikipedia-URL über die opensearch API.
# Je nach Konfiguration wird zuerst in der deutschen oder englischen Wikipedia gesucht.
##############################################################################
def fallback_wikipedia_url(query, langs=None, language="de"):
    """
    Sucht nach einem Wikipedia-Artikel für eine Entität und liefert eine gültige URL zurück.
    
    Args:
        query: Der Suchbegriff (Entitätsname)
        langs: Optional Liste von Sprachen, die nacheinander probiert werden sollen
               (wird überschrieben, wenn language="en" gesetzt ist)
        language: Sprachkonfiguration ("de" oder "en")
        
    Returns:
        Eine gültige Wikipedia-URL oder None, wenn keine gefunden wurde
    """
    # Wenn keine Sprachen angegeben sind, wähle basierend auf language-Parameter
    if langs is None:
        if language == "de":
            langs = ["de", "en"]  # Deutsch zuerst, dann Englisch als Fallback
        else:  # language == "en"
            langs = ["en"]  # Nur Englisch, kein Fallback
    
    # Wichtig: Diese Bedingung entfernen, da sie die vorherige Logik überschreiben würde
    # Wenn language="en" gesetzt ist, erzwinge Englisch zuerst, unabhängig von langs
    # if language == "en" and langs and langs[0] != "en":
    #     langs = ["en"] + [lang for lang in langs if lang != "en"]
    
    for lang in langs:
        # Logge, in welcher Sprache gesucht wird
        logging.info(f"Fallback ({lang}): Suche Wikipedia-URL für '{query}'...")
        
        # URL für die Wikipedia-API-Suche erstellen
        search_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "opensearch",
            "search": query,
            "limit": 1,
            "namespace": 0,
            "format": "json"
        }
        
        try:
            response = requests.get(search_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 3 and data[3] and len(data[3]) > 0:
                    url = data[3][0]
                    if is_valid_wikipedia_url(url):
                        logging.info(f"Fallback ({lang}) erfolgreich: Für '{query}' wurde URL '{url}' ermittelt.")
                        return url
        except Exception as e:
            logging.error(f"Fehler bei der Wikipedia-Suche für {query} in {lang}: {e}")
            
    logging.warning(f"Fallback fehlgeschlagen: Keine Wikipedia-URL für '{query}' gefunden.")
    return None

##############################################################################
# Funktion 1: LLM-Aufruf, um Entitäten & Wikipedia-URLs zu extrahieren
##############################################################################
def extract_entities_with_openai(text, client, model="gpt-4o-mini", language="de"):
    # Optimierter Prompt basierend auf der gewählten Sprache
    if language == "de":
        system_msg = (
            "Du bist ein hilfreiches KI-System für die Erkennung und Verlinkung von Entitäten. "
            "Deine Aufgabe ist es, aus einem gegebenen Text die wichtigsten Entitäten zu identifizieren "
            "und sie mit ihren Wikipedia-Seiten zu verknüpfen. "
            "Wenn möglich, bevorzuge die deutsche Wikipedia (de.wikipedia.org). "
            "Falls ein Begriff keinen deutschen Wikipedia-Eintrag hat, verwende die englische Wikipedia (en.wikipedia.org). "
            "Beachte, dass nicht alle genannten Konzepte eigene Wikipedia-Artikel haben. "
            "Verknüpfe nur Entitäten, bei denen du dir sicher bist, dass sie einen eigenen Wikipedia-Artikel besitzen. "
            "Gib für jede Entität auch deren Typ (z.B. Person, Organisation, Ort, Konzept) und ein Zitat aus dem Text an."
        )
        
        user_msg = (
            "Identifiziere die Hauptentitäten im folgenden Text und gib mir die Wikipedia-URLs, Entitätstypen und Zitate dazu. "
            "Formatiere deine Antwort im JSON-Format mit einem Array von Objekten. "
            "Jedes Objekt sollte die Felder 'entity', 'entity_type', 'wikipedia_url' und 'citation' enthalten.\n\n"
            f"Text: {text}"
        )
    else:  # language == "en"
        system_msg = (
            "You are a helpful AI system for recognizing and linking entities. "
            "Your task is to identify the most important entities from a given text "
            "and link them to their Wikipedia pages. "
            "Always prefer the English Wikipedia (en.wikipedia.org). "
            "Note that not all mentioned concepts have their own Wikipedia articles. "
            "Only link entities that you are confident have their own Wikipedia article. "
            "For each entity, also provide its type (e.g., person, organization, location, concept) and a citation from the text."
        )
        
        user_msg = (
            "Identify the main entities in the following text and provide their Wikipedia URLs, entity types, and citations. "
            "Format your response in JSON format with an array of objects. "
            "Each object should contain the fields 'entity', 'entity_type', 'wikipedia_url', and 'citation'.\n\n"
            f"Text: {text}"
        )

    try:
        logging.info("HTTP Request: POST https://api.openai.com/v1/chat/completions")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0,
            max_tokens=1000
        )
        logging.info("HTTP Request: POST https://api.openai.com/v1/chat/completions \"HTTP/1.1 200 OK\"")
        
        # Extrahiere die Antwort
        content = response.choices[0].message.content
        
        # Versuche, JSON zu extrahieren
        content = clean_json_response(content)
        
        # Parse JSON
        entities = json.loads(content)
        
        # Stelle sicher, dass ein Array zurückgegeben wird
        if not isinstance(entities, list):
            if isinstance(entities, dict) and "entities" in entities:
                entities = entities["entities"]
            else:
                entities = [entities]

        return entities
        
    except Exception as e:
        logging.error("Fehler bei der Entity-Extraktion: %s", e)
        return []

##############################################################################
# Funktion 2: Abrufen der Wikidata-ID über die Wikipedia-API
##############################################################################
def get_wikidata_id_from_wikipedia_url(wikipedia_url):
    try:
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia-URL hat unerwartetes Format: %s", wikipedia_url)
            return None
        title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Fehler beim Extrahieren des Titels aus URL %s: %s", wikipedia_url, e)
        return None

    try:
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            lang = domain.split('.')[0]
        else:
            lang = "de"
    except Exception as e:
        logging.error("Fehler beim Bestimmen der Sprache aus %s: %s", wikipedia_url, e)
        lang = "de"

    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageprops",
        "format": "json",
        "titles": title
    }
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            pageprops = page.get("pageprops", {})
            wikidata_id = pageprops.get("wikibase_item")
            if wikidata_id:
                return wikidata_id
        logging.warning("Keine Wikidata-ID gefunden für URL: %s", wikipedia_url)
        return None
    except Exception as e:
        logging.error("Fehler beim Abrufen der Wikidata-ID für %s: %s", wikipedia_url, e)
        return None

##############################################################################
# Funktion 3: Abrufen des Wikipedia-Artikeltextes (Extract)
##############################################################################
def get_wikipedia_extract(wikipedia_url):
    try:
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia-URL hat unerwartetes Format (Extract): %s", wikipedia_url)
            return None
        title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Fehler beim Extrahieren des Titels für den Extract: %s", e)
        return None

    try:
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            lang = domain.split('.')[0]
        else:
            domain = "de.wikipedia.org"
        lang = domain.split('.')[0]
    except Exception as e:
        logging.error("Fehler beim Bestimmen der Sprache für den Extract: %s", e)
        lang = "de"

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
        r = requests.get(api_url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            extract_text = page.get("extract", "")
            return extract_text
        return None
    except Exception as e:
        logging.error("Fehler beim Abrufen des Wikipedia-Excerpts für %s: %s", wikipedia_url, e)
        return None

##############################################################################
# Funktion 4: Abrufen der Wikidata-Beschreibung
##############################################################################
def get_wikidata_description(qid, lang="de"):
    api_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    try:
        r = requests.get(api_url, timeout=30)
        r.raise_for_status()
        data = r.json()
        entities = data.get("entities", {})
        entity = entities.get(qid, {})
        descriptions = entity.get("descriptions", {})
        description = descriptions.get(lang, {}).get("value")
        if not description and descriptions:
            description = list(descriptions.values())[0].get("value")
        return description
    except Exception as e:
        logging.error("Fehler beim Abrufen der Wikidata-Beschreibung für %s: %s", qid, e)
        return None

##############################################################################
# Funktion 5: Abrufen der Typen einer Entität aus Wikidata
##############################################################################
def get_entity_types_from_wikidata(entity_id, language="de"):
    """
    Ruft die Typen einer Entität von Wikidata ab.
    
    Args:
        entity_id: Die Wikidata-ID (z.B. Q312 für Apple Inc.)
        language: Die Sprache für die Typbezeichnungen ("de" oder "en")
        
    Returns:
        Eine Liste von Typen oder eine leere Liste im Fehlerfall
    """
    if not entity_id:
        return []
        
    wikidata_url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
    
    try:
        r = requests.get(wikidata_url, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        entity_data = data.get("entities", {}).get(entity_id, {})
        claims = entity_data.get("claims", {})
        
        # P31 steht für "instance of" (ist ein(e))
        instance_claims = claims.get("P31", [])
        
        types = []
        for claim in instance_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                datavalue = claim["mainsnak"]["datavalue"]
                if datavalue["type"] == "wikibase-entityid":
                    type_id = datavalue["value"]["id"]
                    # Abrufen des Labels für diesen Typ in der konfigurierten Sprache
                    type_label = get_wikidata_description(type_id, lang=language)
                    if type_label and type_label not in types:
                        types.append(type_label)
        
        return types
    except Exception as e:
        logging.error("Fehler beim Abrufen der Typen für %s: %s", entity_id, e)
        return []

##############################################################################
# Funktion: Abrufen von DBpedia-Informationen über das SPARQL-Endpoint
##############################################################################
def get_dbpedia_info_from_wikipedia_url(wikipedia_url, config=None):
    """
    Ruft Informationen von DBpedia zu einer Entität ab, die durch eine Wikipedia-URL identifiziert ist.
    
    Args:
        wikipedia_url: Die URL des Wikipedia-Artikels zur Entität
        config: Konfigurationsobjekt mit DBpedia-Einstellungen
        
    Returns:
        Ein Dictionary mit DBpedia-Informationen oder None im Fehlerfall
    """
    if not wikipedia_url:
        return None
    
    if config is None:
        config = DEFAULT_CONFIG
    
    # Konfigurationsoptionen auslesen
    timeout = config.get("DBPEDIA_TIMEOUT", 15)  # Standard: 15 Sekunden
    use_de_first = config.get("DBPEDIA_USE_DE", False)  # Standard: Englische DBpedia verwenden
    language = config.get("LANGUAGE", "de")  # Sprache: "de" oder "en"
    
    # Bei deutscher Sprache und DBPEDIA_USE_DE=True deutsche DBpedia zuerst verwenden
    # Bei englischer Sprache immer direkt die englische DBpedia verwenden
    if language == "de":
        use_de_first = config.get("DBPEDIA_USE_DE", True)  # Bei deutscher Sprache ist der Standard True
    else:  # language == "en"
        use_de_first = False  # Bei englischer Sprache immer englische DBpedia verwenden
    
    try:
        # Extrahiere den Titel und die Sprache aus der Wikipedia-URL
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia-URL hat unerwartetes Format (DBpedia): %s", wikipedia_url)
            return None
        original_title = splitted[1].split("#")[0]
        
        # Bestimme die Sprache aus der URL
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            orig_lang = domain.split('.')[0]
        else:
            orig_lang = "de"
        
        # Definiere die zu verwendenden Sprachen basierend auf der Konfiguration
        langs_to_try = []
        
        if language == "de":
            langs_to_try = ["de", "en"]
        else:  # language == "en"
            langs_to_try = ["en"]
            
        # Wenn die Originalsprache nicht Deutsch oder Englisch ist, füge sie hinzu
        if orig_lang not in langs_to_try and orig_lang not in ["de", "en"]:
            langs_to_try.append(orig_lang)
            
        # Versuche nacheinander die verschiedenen Sprachen
        for target_lang in langs_to_try:
            try:
                # Für jede Zielsprache müssen wir den passenden Titel in dieser Sprache bekommen
                if target_lang == orig_lang:
                    # Wenn die Zielsprache gleich der Originalsprache ist, können wir den Originaltitel verwenden
                    title_in_target_lang = original_title
                else:
                    # Ansonsten müssen wir den Titel in die Zielsprache übersetzen
                    title_in_target_lang = get_wikipedia_title_in_language(
                        original_title, 
                        from_lang=orig_lang, 
                        to_lang=target_lang, 
                        timeout=timeout
                    )
                    
                    if not title_in_target_lang:
                        logging.warning(f"Konnte keinen Titel in {target_lang} für {original_title} finden")
                        continue  # Versuche die nächste Sprache
                
                # Konstruiere die DBpedia-Ressourcen-URI und Endpoint-URL basierend auf der Zielsprache
                if target_lang == "de":
                    dbpedia_resource = f"http://de.dbpedia.org/resource/{title_in_target_lang}"
                    endpoint_url = "http://de.dbpedia.org/sparql"
                else:
                    dbpedia_resource = f"http://dbpedia.org/resource/{title_in_target_lang.replace(' ', '_')}"
                    endpoint_url = "http://dbpedia.org/sparql"
                
                # SPARQL-Query für grundlegende Informationen
                query = f"""
                PREFIX dbo: <http://dbpedia.org/ontology/>
                PREFIX dbp: <http://dbpedia.org/property/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?abstract ?label ?type WHERE {{
                  <{dbpedia_resource}> rdfs:label ?label .
                  OPTIONAL {{ <{dbpedia_resource}> dbo:abstract ?abstract }}
                  OPTIONAL {{ <{dbpedia_resource}> rdf:type ?type }}
                  
                  FILTER(LANG(?label) = "{target_lang}")
                  FILTER(LANG(?abstract) = "{target_lang}" || !BOUND(?abstract))
                }}
                LIMIT 10
                """
                
                # Sende SPARQL-Anfrage
                headers = {
                    "Accept": "application/sparql-results+json",
                    "User-Agent": "EntityExtractor/1.0"
                }
                
                logging.info(f"DBpedia-Abfrage in {target_lang} für {dbpedia_resource} gestartet...")
                r = requests.get(
                    endpoint_url, 
                    params={"query": query, "format": "json"}, 
                    headers=headers, 
                    timeout=timeout, 
                    verify=False
                )
                
                r.raise_for_status()
                data = r.json()
                
                # Extrahiere Informationen aus den Ergebnissen
                bindings = data.get("results", {}).get("bindings", [])
                if not bindings:
                    logging.info(f"Keine DBpedia-Informationen in {target_lang} gefunden für: {dbpedia_resource}")
                    continue  # Versuche die nächste Sprache
                    
                # Sammle Ergebnisse
                dbpedia_info = {
                    "resource_uri": dbpedia_resource,
                    "endpoint": endpoint_url,
                    "language": target_lang,
                    "title": title_in_target_lang,
                    "labels": [],
                    "abstract": None,
                    "types": []
                }
                
                for binding in bindings:
                    # Label sammeln (falls nicht schon vorhanden)
                    if "label" in binding and binding["label"].get("value") not in dbpedia_info["labels"]:
                        dbpedia_info["labels"].append(binding["label"].get("value"))
                        
                    # Abstract (nur den ersten verwenden)
                    if "abstract" in binding and not dbpedia_info["abstract"]:
                        dbpedia_info["abstract"] = binding["abstract"].get("value")
                        
                    # Typ hinzufügen (falls nicht schon vorhanden)
                    if "type" in binding and binding["type"].get("value") not in dbpedia_info["types"]:
                        dbpedia_info["types"].append(binding["type"].get("value"))
                
                logging.info(f"DBpedia-Informationen erfolgreich in {target_lang} abgerufen: {len(bindings)} Einträge")
                
                # Logge die ersten drei Typen zur Information
                if dbpedia_info["types"]:
                    top_types = dbpedia_info["types"][:3]
                    logging.info(f"Top DBpedia-Typen: {', '.join(top_types)}")
                
                return dbpedia_info
                
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout bei der DBpedia-Abfrage in {target_lang} nach {timeout} Sekunden")
                # Weiter mit der nächsten Sprache
            except Exception as e:
                logging.error(f"Fehler bei der DBpedia-Abfrage in {target_lang}: {e}")
                # Weiter mit der nächsten Sprache
        
        # Wenn wir hier ankommen, haben alle Sprachen fehlgeschlagen
        logging.warning(f"Alle DBpedia-Abfragen für {original_title} sind fehlgeschlagen")
        return {
            "resource_uri": f"http://dbpedia.org/resource/{original_title.replace('_', ' ')}",
            "error": "Alle DBpedia-Abfragen sind fehlgeschlagen"
        }
    
    except Exception as e:
        logging.error(f"Fehler beim Extrahieren des Titels oder Vorbereiten der DBpedia-Abfrage: {e}")
        return None

##############################################################################
# Hauptfunktion: Verknüpft erkannte Entitäten mit Wikidata
##############################################################################
def link_entities(text, config=None):
    # Bei Bedarf Standardkonfiguration verwenden
    if config is None:
        config = DEFAULT_CONFIG
        
    # Logging-Konfiguration aktualisieren
    configure_logging(config)
        
    # OpenAI-Client initialisieren
    api_key = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("Kein API-Key vorhanden. Bitte Umgebungsvariable OPENAI_API_KEY setzen.")
        raise ValueError("Kein OpenAI API-Key vorhanden.")
    
    openai_client = OpenAI(api_key=api_key)
    
    # Sprache aus der Konfiguration extrahieren
    language = config.get("LANGUAGE", "de")
    
    # LLM verwenden, um Entitäten zu extrahieren
    entities = extract_entities_with_openai(
        text, 
        openai_client, 
        model=config.get("MODEL", "gpt-4o-mini"),
        language=language
    )
    
    # Ergebnis-Liste initialisieren
    result = []
    
    # Jede Entität verarbeiten
    for entity_info in entities:
        entity_name = entity_info.get("entity")
        wikipedia_url = entity_info.get("wikipedia_url")
        entity_type = entity_info.get("entity_type", "")
        citation = entity_info.get("citation", "")
        
        # Für jede neue Entität den Wikipedia-Extract zurücksetzen
        wikipedia_extract = None
        
        # Leere Ergebnisse überspringen
        if not entity_name or not wikipedia_url:
            continue
        
        # Ermittle die Position des Zitats im Text
        citation_start = -1
        citation_end = -1
        
        if citation:
            citation_start = text.find(citation)
            if citation_start >= 0:
                citation_end = citation_start + len(citation)
            
        # Resultats-Objekt initialisieren mit Basisdetails
        entity_result = {
            "entity": entity_name,
            "details": {
                "typ": entity_type,
                "citation": citation,
                "citation_start": citation_start,
                "citation_end": citation_end
            },
            "sources": {}
        }
        
        # 1. Wikipedia-Informationen
        valid_url = is_valid_wikipedia_url(wikipedia_url)
        
        # Wenn die URL ungültig ist, versuche einen Fallback
        if not valid_url:
            logging.warning(f"Ungültige Wikipedia-URL: {wikipedia_url}")
            new_url = fallback_wikipedia_url(entity_name, language=language)
            if new_url:
                logging.info(f"Fallback erfolgreich: Neue URL für '{entity_name}': {new_url}")
                wikipedia_url = new_url
            else:
                logging.warning(f"Kein Fallback für '{entity_name}' gefunden. Überspringe Eintrag.")
                continue
    
        # Auch für gültige URLs: Prüfe, ob die Wikidata-ID gefunden werden kann
        entity_id = get_wikidata_id_from_wikipedia_url(wikipedia_url)
    
        # Wenn keine Wikidata-ID gefunden wurde, versuche einen Fallback
        if entity_id is None and config.get("USE_WIKIDATA", True):
            logging.warning(f"Keine Wikidata-ID für URL: {wikipedia_url} gefunden. Versuche alternativen Artikel.")
            new_url = fallback_wikipedia_url(entity_name, language=language)
        
            # Nur wenn ein anderer URL zurückkommt, diesen verwenden
            if new_url and new_url != wikipedia_url:
                logging.info(f"Alternativer Artikel gefunden: {new_url}")
                wikipedia_url = new_url
            
                # Wikipedia-Extrakt für den neuen URL abrufen
                wikipedia_extract = get_wikipedia_extract(wikipedia_url)
            
                # Wikidata-ID erneut versuchen
                entity_id = get_wikidata_id_from_wikipedia_url(wikipedia_url)
                
        # Wikipedia-Extrakt abrufen (falls noch nicht geschehen)
        if wikipedia_extract is None:
            wikipedia_extract = get_wikipedia_extract(wikipedia_url)
        
        entity_result["sources"]["wikipedia"] = {
            "url": wikipedia_url,
            "extract": wikipedia_extract
        }
        
        # 2. Wikidata-Integration
        if config.get("USE_WIKIDATA", False):
            try:
                # Wikidata-ID anhand der Wikipedia-URL ermitteln
                if entity_id:
                    # Wikidata-Integration
                    entity_result["sources"]["wikidata"] = {
                        "id": entity_id
                    }
                    
                    # Wikidata-Beschreibung abrufen
                    description = get_wikidata_description(entity_id, lang=language)
                    if description:
                        entity_result["sources"]["wikidata"]["description"] = description
                    
                    # Wikidata-Typen abrufen
                    types = get_entity_types_from_wikidata(entity_id, language=language)
                    if types:
                        entity_result["sources"]["wikidata"]["types"] = types
            except Exception as e:
                logging.error(f"Fehler bei der Wikidata-Integration für {entity_name}: {e}")
        
        # 3. DBpedia-Integration (optional)
        if config.get("USE_DBPEDIA", False):
            try:
                # DBpedia-Informationen abrufen
                dbpedia_info = get_dbpedia_info_from_wikipedia_url(wikipedia_url, config=config)
                if dbpedia_info:
                    entity_result["sources"]["dbpedia"] = dbpedia_info
            except Exception as e:
                logging.error(f"Fehler bei der DBpedia-Integration für {entity_name}: {e}")
        
        # Ergebnis der Liste hinzufügen
        result.append(entity_result)
    
    return result

##############################################################################
# Beispiel-Aufruf (falls Skript direkt ausgeführt wird)
##############################################################################
if __name__ == "__main__":
    example_text = (
        "Entity Linking (EL) ist eine Aufgabe, die benannte Entitäten im Text auf "
        "entsprechende Entitäten in einer Wissensdatenbank abbildet. Apple und Microsoft sind große Technologieunternehmen."
    )
   
    # Demo mit deutscher Konfiguration
    print("\nBeispiel: Entity Extraction")
    config = {
        "USE_WIKIPEDIA": True,     # Immer True, Wikipedia ist Pflicht
        "USE_WIKIDATA": True,      # Wikidata verwenden
        "USE_DBPEDIA": True,       # DBpedia verwenden
        "DBPEDIA_USE_DE": True,    # Deutsche DBpedia-Server verwenden
        "DBPEDIA_TIMEOUT": 15,     # Timeout in Sekunden für DBpedia-Anfragen
        "MODEL": "gpt-4.1-mini",    # LLM-Modell für die Entitätsextraktion
        "OPENAI_API_KEY": None,    # None = Aus Umgebungsvariable laden
        "LANGUAGE": "en",          # Deutsche (de) oder Englische (en) Ausgabesprache
        "SHOW_STATUS": True,       # Status-/Logging-Meldungen anzeigen
        "SUPPRESS_TLS_WARNINGS": True  # TLS-Warnungen von urllib3 unterdrücken
    }
      
    entities = link_entities(example_text, config=config)
    print("\nJSON-Output (formatiert):")
    print(json.dumps(entities, ensure_ascii=False, indent=2))
