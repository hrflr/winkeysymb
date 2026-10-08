"""Search engine for special characters combining curated symbols and Unicode database."""

import unicodedata
from typing import List, Dict, Any
from winkeysymb.data.symbols import CURATED_SYMBOLS

# Pre-process curated symbols for instant searching
_INDEXED_SYMBOLS: List[Dict[str, Any]] = []

for item in CURATED_SYMBOLS:
    char = item["char"]
    code_point = f"U+{ord(char):04X}"
    name = item["name"]
    latex = item.get("latex", "")
    tags = item.get("tags", [])
    category = item.get("category", "General")
    
    # Pre-lowercased search tokens
    tokens = set()
    tokens.add(char.lower())
    for t in tags:
        tokens.add(t.lower())
    if latex:
        tokens.add(latex.lower())
        tokens.add(latex.lstrip("\\").lower())
    for word in name.lower().split():
        tokens.add(word)
        
    _INDEXED_SYMBOLS.append({
        "char": char,
        "name": name,
        "code_point": code_point,
        "latex": latex,
        "tags": tags,
        "category": category,
        "tokens": tokens,
        "search_str": f"{name} {latex} {' '.join(tags)} {code_point}".lower(),
    })


def score_item(item: Dict[str, Any], query: str) -> float:
    """Calculate match score for an item against query (higher is better)."""
    q = query.lower()
    char = item["char"]
    
    # Exact character
    if q == char:
        return 1000.0
        
    # Exact latex command (e.g. \alpha or alpha when query is \alpha)
    latex = item["latex"].lower()
    if latex and (q == latex or q == latex.lstrip("\\")):
        return 500.0
        
    # Exact tag match (e.g. "alpha", "->", "approx", "!=")
    for tag in item["tags"]:
        t_low = tag.lower()
        if q == t_low:
            return 450.0
            
    # Prefix match on tag
    for tag in item["tags"]:
        t_low = tag.lower()
        if t_low.startswith(q):
            # Prefer shorter tags that match prefix
            return 300.0 + (len(q) / len(t_low)) * 50.0

    # Prefix match on latex
    if latex and latex.lstrip("\\").startswith(q.lstrip("\\")):
        return 280.0
        
    # Prefix match on name words
    name_words = item["name"].lower().split()
    for word in name_words:
        if word.startswith(q):
            return 200.0 + (len(q) / len(word)) * 30.0

    # Substring in tags
    for tag in item["tags"]:
        if q in tag.lower():
            return 120.0

    # Substring in name
    if q in item["name"].lower():
        return 100.0

    # Code point match e.g. U+03B1 or 03b1
    cp = item["code_point"].lower()
    if q == cp or q == cp.replace("u+", ""):
        return 350.0
    if q in cp:
        return 80.0
        
    return 0.0


def search_symbols(query: str, recent_chars: List[str] = None, max_results: int = 40) -> List[Dict[str, Any]]:
    """Search for matching characters.
    
    If query is empty, returns recent characters followed by popular curated symbols.
    """
    recent_chars = recent_chars or []
    q = query.strip()
    
    if not q:
        # Show recent characters first
        results = []
        seen = set()
        
        # Add recent items
        curated_map = {item["char"]: item for item in _INDEXED_SYMBOLS}
        for char in recent_chars:
            if char in curated_map and char not in seen:
                results.append(curated_map[char])
                seen.add(char)
            elif char not in seen:
                try:
                    name = unicodedata.name(char, "Unicode Character").title()
                except ValueError:
                    name = "Character"
                results.append({
                    "char": char,
                    "name": name,
                    "code_point": f"U+{ord(char):04X}",
                    "latex": "",
                    "tags": ["recent"],
                    "category": "Recent",
                })
                seen.add(char)
                
        # Supplement with curated favorites
        for item in _INDEXED_SYMBOLS:
            if item["char"] not in seen:
                results.append(item)
                seen.add(item["char"])
            if len(results) >= max_results:
                break
                
        return results

    # Scored search through curated symbols
    scored: List[tuple[float, Dict[str, Any]]] = []
    seen = set()
    
    for item in _INDEXED_SYMBOLS:
        score = score_item(item, q)
        if score > 0:
            # Bonus for recently used characters
            if item["char"] in recent_chars:
                score += 40.0
            scored.append((score, item))
            seen.add(item["char"])

    # If few results and query has >= 3 chars, query unicodedata
    if len(scored) < max_results and len(q) >= 3 and not q.startswith("\\"):
        q_clean = q.upper()
        # Scan common unicode blocks
        try:
            # Check characters in BMP (Basic Multilingual Plane)
            # Scan select useful ranges: Latin-1, Greek, Math, Arrows, Misc Symbols
            ranges = [
                (0x00A0, 0x02AF),   # Latin supplement & extended
                (0x0370, 0x03FF),   # Greek
                (0x2000, 0x206F),   # General punctuation
                (0x2070, 0x209F),   # Super and subscripts
                (0x20A0, 0x20CF),   # Currency
                (0x2100, 0x214F),   # Letterlike symbols
                (0x2150, 0x218F),   # Number forms (fractions)
                (0x2190, 0x21FF),   # Arrows
                (0x2200, 0x22FF),   # Mathematical operators
                (0x2300, 0x23FF),   # Miscellaneous technical
                (0x25A0, 0x25FF),   # Geometric shapes
                (0x2600, 0x26FF),   # Misc symbols
                (0x2700, 0x27BF),   # Dingbats
            ]
            for start, end in ranges:
                for cp in range(start, end):
                    ch = chr(cp)
                    if ch in seen:
                        continue
                    try:
                        u_name = unicodedata.name(ch)
                    except ValueError:
                        continue
                    if q_clean in u_name:
                        score = 50.0
                        if u_name.startswith(q_clean):
                            score = 90.0
                        scored.append((score, {
                            "char": ch,
                            "name": u_name.title(),
                            "code_point": f"U+{cp:04X}",
                            "latex": "",
                            "tags": [w.lower() for w in u_name.split()[:4]],
                            "category": "Unicode",
                        }))
                        seen.add(ch)
                        if len(scored) >= max_results * 2:
                            break
                if len(scored) >= max_results * 2:
                    break
        except Exception:
            pass

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:max_results]]
