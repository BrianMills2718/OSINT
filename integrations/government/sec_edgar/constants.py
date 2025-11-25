#!/usr/bin/env python3
"""
SEC EDGAR constants and utility functions.

Company aliases and name normalization for SEC database lookups.
"""

import re
from typing import Dict, List


# Common company name aliases and variations for defense contractors
# Maps: normalized search name → list of possible SEC database variations
COMPANY_ALIASES: Dict[str, List[str]] = {
    # Defense contractors
    "northrop grumman": ["NORTHROP GRUMMAN", "NORTHROP GRUMMAN CORP"],
    "raytheon": ["RAYTHEON", "RAYTHEON TECHNOLOGIES", "RTX CORP", "RAYTHEON CO"],
    "lockheed martin": ["LOCKHEED MARTIN", "LOCKHEED MARTIN CORP"],
    "boeing": ["BOEING CO", "BOEING"],
    "general dynamics": ["GENERAL DYNAMICS", "GENERAL DYNAMICS CORP"],
    "l3harris": ["L3HARRIS", "L3HARRIS TECHNOLOGIES", "HARRIS CORP"],
    "bae systems": ["BAE SYSTEMS", "BAE SYSTEMS PLC"],
    "huntington ingalls": ["HUNTINGTON INGALLS", "HUNTINGTON INGALLS INDUSTRIES"],
    "leidos": ["LEIDOS", "LEIDOS HOLDINGS"],
    "booz allen": ["BOOZ ALLEN", "BOOZ ALLEN HAMILTON"],
    "caci": ["CACI", "CACI INTERNATIONAL"],
    "saic": ["SAIC", "SCIENCE APPLICATIONS INTERNATIONAL"],
    "textron": ["TEXTRON", "TEXTRON INC"],
    "kratos": ["KRATOS", "KRATOS DEFENSE"],
    "anduril": ["ANDURIL", "ANDURIL INDUSTRIES"],
    "palantir": ["PALANTIR", "PALANTIR TECHNOLOGIES"],
    # Tech companies (common in research queries)
    "microsoft": ["MICROSOFT", "MICROSOFT CORP"],
    "amazon": ["AMAZON", "AMAZON COM INC"],
    "google": ["ALPHABET", "GOOGLE", "ALPHABET INC"],
    "meta": ["META", "META PLATFORMS", "FACEBOOK"],
    "apple": ["APPLE", "APPLE INC"],
}


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for matching.

    Strips common suffixes and standardizes format.

    Args:
        name: Raw company name

    Returns:
        Normalized name (lowercase, no suffixes)
    """
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower().strip()

    # Remove common suffixes (order matters - longer first)
    suffixes = [
        " corporation",
        " incorporated",
        " holdings",
        " technologies",
        " industries",
        " international",
        " solutions",
        " services",
        " systems",
        " group",
        " corp",
        " inc",
        " ltd",
        " llc",
        " plc",
        " co",
        ",",
        ".",
    ]

    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()

    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized
