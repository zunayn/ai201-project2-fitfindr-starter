"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.
"""

import re
from tools import search_listings, suggest_outfit, create_fit_card

# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,              
        "parsed": {},                
        "search_results": [],        
        "selected_item": None,       
        "wardrobe": wardrobe,        
        "outfit_suggestion": None,   
        "fit_card": None,            
        "error": None,               
    }

# ── helper function ───────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extracts description, size, and max_price from the natural language query 
    using regex so we can pass clean arguments to search_listings().
    """
    query_lower = query.lower()
    
    # Extract max_price (e.g., "under $30", "under 40")
    max_price = None
    price_match = re.search(r'under\s*\$?\s*(\d+(\.\d{2})?)', query_lower)
    if price_match:
        max_price = float(price_match.group(1))

    # Extract size (e.g., "size M", "size xxs")
    size = None
    size_match = re.search(r'size\s+([a-z0-9/]+)', query_lower)
    if size_match:
        size = size_match.group(1).upper()

    # The description is whatever is left after stripping price and size terms
    description = re.sub(r'under\s*\$?\s*\d+(\.\d{2})?', '', query_lower)
    description = re.sub(r'size\s+[a-z0-9/]+', '', description)
    
    return {
        "description": description.strip(),
        "size": size,
        "max_price": max_price
    }

# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """Runs the FitFindr planning loop for a single user interaction."""
    
    # Initialize the session
    session = _new_session(query, wardrobe)

    # Parse the user's query
    session["parsed"] = _parse_query(query)

    # Call search_listings
    session["search_results"] = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"]
    )

    # Handle the empty results failure mode
    if not session["search_results"]:
        session["error"] = (
            "I couldn't find any listings matching your search criteria. "
            "Try loosening your price limit or removing the size filter!"
        )
        return session  # Early return! Do not proceed to the other tools.

    # Select the top item
    session["selected_item"] = session["search_results"][0]

    # Call suggest_outfit passing state directly from the session
    session["outfit_suggestion"] = suggest_outfit(
        new_item=session["selected_item"], 
        wardrobe=session["wardrobe"]
    )

    # Call create_fit_card passing state directly from the session
    session["fit_card"] = create_fit_card(
        outfit=session["outfit_suggestion"], 
        new_item=session["selected_item"]
    )

    # Return the completed session
    return session

# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")