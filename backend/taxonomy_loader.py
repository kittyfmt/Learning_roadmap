import json
import os

def load_taxonomy_and_lookup():
    """
    1. Load taxonomy from JSON.
    2. Build Alias -> Canonical lookup table.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "..", "data", "taxonomy.json")

    with open(json_path, 'r', encoding='utf-8') as f:
        taxonomy = json.load(f)

    lookup = {}
    for canonical, info in taxonomy.items():
        lookup[canonical.lower()] = canonical 
        for alias in info.get("aliases", []):
            lookup[alias.lower()] = canonical 
            
    return taxonomy, lookup

TAXONOMY, ALIAS_LOOKUP = load_taxonomy_and_lookup()