"""
title: Web Search Tool
description: Search the web using the private SearXNG instance. Returns relevant search results for any query.
author: self-hosted-ai
version: 1.0.0
"""

import json
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        searxng_url: str = Field(
            default="http://searxng.ai-services:8080",
            description="SearXNG base URL",
        )
        timeout: int = Field(default=15, description="Request timeout in seconds")
        max_results: int = Field(default=5, description="Maximum results to return")

    def __init__(self):
        self.valves = self.Valves()

    def search_web(
        self,
        query: str,
        categories: str = "general",
    ) -> str:
        """
        Search the web using the private SearXNG search engine.
        Use this when the user asks a question that requires current information, news, or web lookup.

        :param query: The search query
        :param categories: Search categories: general, news, images, science, it (default: general)
        :return: Search results with titles, URLs, and snippets
        """
        try:
            response = requests.get(
                f"{self.valves.searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": categories,
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                return f"No results found for: {query}"

            output = f"Search results for: {query}\n\n"
            for i, r in enumerate(results[: self.valves.max_results], 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                content = r.get("content", "No description")
                output += f"{i}. **{title}**\n   {url}\n   {content}\n\n"

            return output

        except requests.exceptions.ConnectionError:
            return "SearXNG search is not available. The search service may be down."
        except Exception as e:
            return f"Search error: {str(e)}"
