"""
title: Web Page Fetcher
description: Fetch and extract content from web pages. Useful when users share URLs or ask about web content.
author: self-hosted-ai
version: 1.0.0
"""

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        timeout: int = Field(default=30, description="Request timeout in seconds")
        max_content_length: int = Field(
            default=8000, description="Max characters to return"
        )

    def __init__(self):
        self.valves = self.Valves()

    def fetch_url(self, url: str) -> str:
        """
        Fetch the content of a web page and return it as readable text.
        Use this when a user shares a URL and asks about its content, or when you
        need to look up documentation or references from the web.

        :param url: The URL to fetch
        :return: The text content of the web page
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; OpenWebUI/1.0; +https://ai.vectorweight.com)"
            }
            response = requests.get(
                url, headers=headers, timeout=self.valves.timeout, allow_redirects=True
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                # Simple HTML to text extraction
                text = response.text
                # Remove script and style tags
                import re

                text = re.sub(
                    r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL
                )
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                # Remove HTML tags
                text = re.sub(r"<[^>]+>", " ", text)
                # Clean up whitespace
                text = re.sub(r"\s+", " ", text).strip()
                # Truncate
                if len(text) > self.valves.max_content_length:
                    text = text[: self.valves.max_content_length] + "\n[...truncated]"
                return f"Content from {url}:\n\n{text}"
            elif "application/json" in content_type:
                import json

                data = response.json()
                text = json.dumps(data, indent=2)
                if len(text) > self.valves.max_content_length:
                    text = text[: self.valves.max_content_length] + "\n[...truncated]"
                return f"JSON from {url}:\n\n{text}"
            else:
                return f"Fetched {url} ({content_type}, {len(response.content)} bytes). Content type is not text/HTML."

        except requests.exceptions.ConnectionError:
            return f"Could not connect to {url}. The site may be down or unreachable."
        except requests.exceptions.Timeout:
            return f"Request to {url} timed out after {self.valves.timeout} seconds."
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"
