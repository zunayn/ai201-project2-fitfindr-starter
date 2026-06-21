"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    listings = load_listings()
    filtered_listings = []

    # Filter by size and max price first
    for item in listings:
        # Price filter
        if max_price is not None and item.get("price", float('inf')) > max_price:
            continue
            
        # Size filter (case-insensitive substring match)
        if size is not None:
            item_size = item.get("size", "").lower()
            if size.lower() not in item_size:
                continue
                
        filtered_listings.append(item)

    # Score by keyword overlap with the description
    keywords = set(description.lower().split())
    scored_listings = []

    for item in filtered_listings:
        # Combine relevant text fields to search against
        searchable_text = (
            item.get("title", "") + " " + 
            item.get("description", "") + " " + 
            " ".join(item.get("style_tags", []))
        ).lower()

        # Count how many keywords appear in the item's text
        score = sum(1 for kw in keywords if kw in searchable_text)
        
        if score > 0:
            # Attach score temporarily for sorting
            item["_match_score"] = score
            scored_listings.append(item)

    # Sort by score (highest first)
    scored_listings.sort(key=lambda x: x["_match_score"], reverse=True)

    # Clean up the temporary score key before returning
    for item in scored_listings:
        del item["_match_score"]

    return scored_listings


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    client = _get_groq_client()
    items = wardrobe.get("items", [])
    
    item_details = f"Item: {new_item.get('title')} (Colors: {', '.join(new_item.get('colors', []))}, Style: {', '.join(new_item.get('style_tags', []))})"

    if not items:
        # Fallback for an empty wardrobe
        prompt = (
            f"The user is considering buying this item: {item_details}. "
            "Their wardrobe is currently empty in the system. Suggest 1-2 general outfit ideas "
            "and vibe recommendations for how to style this piece."
        )
    else:
        # Format the user's wardrobe into a readable list
        wardrobe_str = "\n".join([f"- {i['name']} ({', '.join(i['colors'])})" for i in items])
        prompt = (
            f"The user is considering buying this item: {item_details}.\n\n"
            f"Here is their current wardrobe:\n{wardrobe_str}\n\n"
            "Suggest 1-2 specific outfit combinations using the new item and the named pieces from their wardrobe."
        )

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful, stylish fashion assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Styling service temporarily unavailable: {str(e)}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not outfit.strip():
        return "Error: Outfit suggestion is missing. Cannot generate a fit card."

    client = _get_groq_client()
    
    prompt = (
        f"Item Name: {new_item.get('title')}\n"
        f"Price: ${new_item.get('price')}\n"
        f"Platform: {new_item.get('platform')}\n"
        f"Outfit Idea: {outfit}\n\n"
        "Write a 2-3 sentence casual, authentic Instagram/TikTok caption for this outfit. "
        "It must mention the item name, the price, and the platform it was thrifted from. "
        "Capture the specific vibe of the outfit. Keep it natural, like a real OOTD post, not a product description."
    )

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a Gen Z fashion influencer writing an OOTD caption."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9, # Higher temperature for varied, creative captions
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Caption generation failed: {str(e)}"
    



if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe
    
    # 1. Test Search
    results = search_listings(description="vintage graphic tee", size="M", max_price=30.0)
    print(f"Found {len(results)} items.")
    
    if results:
        top_item = results[0]
        print(f"Top item: {top_item['title']}")
        
        # 2. Test Outfit Suggestion
        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(top_item, wardrobe)
        print(f"\nOutfit Suggestion:\n{outfit}")
        
        # 3. Test Fit Card
        card = create_fit_card(outfit, top_item)
        print(f"\nFit Card:\n{card}")