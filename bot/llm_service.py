"""
LLM Service using Ollama for natural language processing.

Handles:
- Parsing card creation commands
- Auto-generating flashcard content
- Smart tagging
- Answering questions during review
"""
import json
import re
from typing import Optional
import requests


class OllamaService:
    """Service for interacting with Ollama LLM."""

    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama service.

        Args:
            model: Model name (default: llama2)
            base_url: Ollama API URL (default: http://localhost:11434)
        """
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"

    def _call_ollama(self, prompt: str, system: str = "") -> str:
        """
        Call Ollama API with a prompt.

        Args:
            prompt: User prompt
            system: System message

        Returns:
            LLM response text
        """
        try:
            payload = {"model": self.model, "prompt": prompt, "system": system, "stream": False}

            response = requests.post(self.generate_url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama: {e}")
            return ""

    def parse_card_command(self, text: str) -> dict:
        """
        Parse natural language card creation command.

        Args:
            text: User's message

        Returns:
            dict with extracted fields: name, code, notes, links, tags
        """
        system_prompt = """You are a helpful assistant that parses user messages to extract flashcard information.
Extract the following fields from the user's message:
- name: The problem or algorithm name (required)
- code: Any code snippets (optional, preserve formatting)
- notes: Explanation or notes (optional)
- links: URLs (optional, return as array)
- tags: Relevant tags like difficulty, data structure, algorithm type (optional, return as array)

Return ONLY a valid JSON object with these fields. If a field is not found, omit it or set to null.
Example: {"name": "Two Sum", "code": "def two_sum()...", "notes": "Uses hashmap", "links": ["https://..."], "tags": ["array", "hashmap", "easy"]}
"""

        prompt = f"""Parse this flashcard creation message:

"{text}"

Return ONLY the JSON object, no other text."""

        response = self._call_ollama(prompt, system_prompt)

        # Extract JSON from response
        try:
            # Try to find JSON in response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed
            else:
                # Fallback: try to parse entire response
                return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to basic regex parsing
            return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> dict:
        """
        Fallback parser using regex if LLM fails.

        Args:
            text: User's message

        Returns:
            dict with extracted fields
        """
        result = {}

        # Extract code blocks
        code_match = re.search(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
        if code_match:
            result["code"] = code_match.group(1).strip()

        # Extract URLs
        url_pattern = r"https?://[^\s]+"
        links = re.findall(url_pattern, text)
        if links:
            result["links"] = links

        # Extract name (first line or before comma)
        lines = text.split("\n")
        first_line = lines[0].strip()
        # Remove command prefix like "add "
        first_line = re.sub(r"^(add|create|new)\s+", "", first_line, flags=re.IGNORECASE)
        result["name"] = first_line.split(",")[0].strip()

        return result

    def generate_flashcard_content(self, name: str, code: Optional[str] = None) -> dict:
        """
        Auto-generate notes and explanation for a flashcard.

        Args:
            name: Problem/algorithm name
            code: Code solution (optional)

        Returns:
            dict with generated: notes, tags
        """
        system_prompt = """You are an expert in algorithms and data structures.
Generate helpful flashcard content for spaced repetition learning.
Return ONLY a valid JSON object with these fields:
- notes: Brief explanation of the algorithm/approach (2-3 sentences)
- tags: Relevant tags (array of strings: data structure type, algorithm type, difficulty)

Example: {"notes": "Binary search uses divide and conquer...", "tags": ["binary search", "array", "easy"]}
"""

        code_info = f"\n\nCode:\n{code}" if code else ""
        prompt = f"""Generate flashcard content for: {name}{code_info}

Return ONLY the JSON object."""

        response = self._call_ollama(prompt, system_prompt)

        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except json.JSONDecodeError:
            # Return defaults
            return {"notes": "", "tags": []}

    def smart_tag(self, name: str, code: Optional[str] = None, notes: Optional[str] = None) -> list[str]:
        """
        Generate smart tags for a card.

        Args:
            name: Problem/algorithm name
            code: Code solution (optional)
            notes: User notes (optional)

        Returns:
            list of tag strings
        """
        system_prompt = """You are an expert at categorizing algorithms and data structures.
Generate relevant tags for this flashcard. Include:
- Data structure types (e.g., array, tree, graph, heap)
- Algorithm types (e.g., bfs, dfs, dynamic programming, greedy)
- Difficulty (easy, medium, hard)
- Problem patterns (e.g., sliding window, two pointers)

Return ONLY a JSON array of strings, e.g., ["graph", "bfs", "medium", "shortest path"]
"""

        code_info = f"\nCode: {code[:200]}..." if code else ""
        notes_info = f"\nNotes: {notes}" if notes else ""
        prompt = f"""Generate tags for: {name}{code_info}{notes_info}

Return ONLY the JSON array."""

        response = self._call_ollama(prompt, system_prompt)

        try:
            # Try to extract JSON array
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except json.JSONDecodeError:
            return []

    def answer_question(self, card_name: str, code: str, notes: str, question: str) -> str:
        """
        Answer a question about a flashcard during review.

        Args:
            card_name: Name of the card
            code: Code solution
            notes: Card notes
            question: User's question

        Returns:
            Answer text
        """
        system_prompt = """You are a helpful tutor for algorithms and data structures.
Answer the user's question about this flashcard clearly and concisely.
Provide hints rather than full solutions when possible."""

        prompt = f"""Flashcard: {card_name}

Code:
{code or 'No code provided'}

Notes:
{notes or 'No notes'}

User question: {question}

Provide a helpful answer:"""

        return self._call_ollama(prompt, system_prompt)


# Singleton instance
ollama_service = OllamaService()
