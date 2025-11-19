"""
Configuration for adaptive spaced repetition based on algorithm rarity and difficulty.

This module defines multipliers that adjust review intervals based on:
1. Algorithm rarity (how often you use these algorithms in practice)
2. Problem difficulty (based on acceptance rate)
"""

# Algorithm rarity categories
# Algorithms are categorized by how frequently they appear in real-world coding
ALGORITHM_RARITY = {
    # Rare algorithms - need more frequent practice (30% shorter intervals)
    "rare": {
        "keywords": [
            # Graph algorithms
            "graph",
            "dijkstra",
            "bellman-ford",
            "floyd-warshall",
            "kruskal",
            "prim",
            "topological sort",
            "strongly connected components",
            "articulation points",
            "bridges",
            "minimum spanning tree",
            "shortest path",
            # Tree algorithms
            "segment tree",
            "fenwick tree",
            "binary indexed tree",
            "trie",
            "suffix tree",
            "suffix array",
            # Advanced data structures
            "union find",
            "disjoint set",
            "red-black tree",
            "avl tree",
            "b-tree",
            # Advanced algorithms
            "network flow",
            "max flow",
            "bipartite matching",
            "convex hull",
            "line sweep",
            "kmp",
            "rabin-karp",
            "z-algorithm",
            "aho-corasick",
        ],
        "interval_multiplier": 0.7,  # Review 30% more frequently
    },
    # Common patterns - standard practice frequency
    "common": {
        "keywords": [
            "two pointers",
            "sliding window",
            "binary search",
            "sorting",
            "greedy",
            "backtracking",
            "bfs",
            "dfs",
            "dynamic programming",
            "dp",
            "recursion",
            "divide and conquer",
            "heap",
            "priority queue",
            "monotonic stack",
            "monotonic queue",
        ],
        "interval_multiplier": 1.0,  # Normal intervals
    },
    # Basic patterns - can space out more (20% longer intervals)
    "basic": {
        "keywords": [
            "array",
            "string",
            "hashmap",
            "hash table",
            "linked list",
            "stack",
            "queue",
            "math",
            "bit manipulation",
            "simulation",
        ],
        "interval_multiplier": 1.2,  # Review 20% less frequently
    },
}

# Difficulty multipliers based on acceptance rate
# Lower acceptance rate = harder problem = more frequent reviews
DIFFICULTY_MULTIPLIERS = {
    "very_hard": {
        "acceptance_range": (0.0, 0.25),
        "multiplier": 0.7,  # 30% shorter intervals
    },
    "hard": {
        "acceptance_range": (0.25, 0.40),
        "multiplier": 0.85,  # 15% shorter intervals
    },
    "medium": {
        "acceptance_range": (0.40, 0.60),
        "multiplier": 1.0,  # Normal intervals
    },
    "easy": {
        "acceptance_range": (0.60, 0.75),
        "multiplier": 1.15,  # 15% longer intervals
    },
    "very_easy": {
        "acceptance_range": (0.75, 1.0),
        "multiplier": 1.3,  # 30% longer intervals
    },
}


def get_difficulty_from_acceptance_rate(acceptance_rate: float) -> str:
    """
    Get difficulty category from acceptance rate.

    Args:
        acceptance_rate: Acceptance rate (0.0 to 1.0)

    Returns:
        Difficulty category string
    """
    for difficulty, config in DIFFICULTY_MULTIPLIERS.items():
        min_rate, max_rate = config["acceptance_range"]
        if min_rate <= acceptance_rate < max_rate:
            return difficulty
    return "medium"  # Default


def get_rarity_category(tags: list[str]) -> str:
    """
    Determine algorithm rarity category from tags.

    Args:
        tags: List of tags for the card

    Returns:
        Rarity category ('rare', 'common', or 'basic')
    """
    if not tags:
        return "common"

    # Check tags against each category (rare has priority)
    for tag in tags:
        tag_lower = tag.lower()

        # Check rare first (highest priority)
        for keyword in ALGORITHM_RARITY["rare"]["keywords"]:
            if keyword in tag_lower:
                return "rare"

    # Check common
    for tag in tags:
        tag_lower = tag.lower()
        for keyword in ALGORITHM_RARITY["common"]["keywords"]:
            if keyword in tag_lower:
                return "common"

    # Check basic
    for tag in tags:
        tag_lower = tag.lower()
        for keyword in ALGORITHM_RARITY["basic"]["keywords"]:
            if keyword in tag_lower:
                return "basic"

    # Default to common
    return "common"
