"""
title: Memory Store Tool
description: Store and retrieve persistent memories/notes. Useful for the LLM to remember facts, preferences, or context across conversations.
author: self-hosted-ai
version: 1.0.0
"""

import json
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        qdrant_url: str = Field(
            default="http://qdrant.ai-services:6333",
            description="Qdrant vector DB URL",
        )
        ollama_url: str = Field(
            default="http://ollama.ai-services:11434",
            description="Ollama URL for embeddings",
        )
        embed_model: str = Field(
            default="nomic-embed-text:latest",
            description="Embedding model name",
        )
        collection: str = Field(
            default="agent_memory",
            description="Qdrant collection name",
        )

    def __init__(self):
        self.valves = self.Valves()

    def save_memory(
        self,
        content: str,
        tags: str = "",
    ) -> str:
        """
        Save a piece of information to persistent memory. Use this to remember important facts,
        user preferences, or context that should be available in future conversations.

        :param content: The information to remember
        :param tags: Comma-separated tags for categorization (e.g., "preference,user,coding")
        :return: Confirmation that the memory was saved
        """
        import hashlib
        import time

        try:
            # Generate embedding
            embed_resp = requests.post(
                f"{self.valves.ollama_url}/api/embed",
                json={"model": self.valves.embed_model, "input": content},
                timeout=30,
            )
            embed_resp.raise_for_status()
            embedding = embed_resp.json().get("embeddings", [[]])[0]

            if not embedding:
                return "Failed to generate embedding for the memory."

            # Ensure collection exists
            requests.put(
                f"{self.valves.qdrant_url}/collections/{self.valves.collection}",
                json={
                    "vectors": {"size": len(embedding), "distance": "Cosine"},
                },
                timeout=10,
            )

            # Store in Qdrant
            point_id = int(hashlib.md5(content.encode()).hexdigest()[:8], 16)
            requests.put(
                f"{self.valves.qdrant_url}/collections/{self.valves.collection}/points",
                json={
                    "points": [
                        {
                            "id": point_id,
                            "vector": embedding,
                            "payload": {
                                "content": content,
                                "tags": [t.strip() for t in tags.split(",") if t.strip()],
                                "timestamp": time.time(),
                            },
                        }
                    ]
                },
                timeout=10,
            )

            return f"Memory saved: '{content[:100]}...'" if len(content) > 100 else f"Memory saved: '{content}'"

        except requests.exceptions.ConnectionError:
            return "Memory service not available. Qdrant or Ollama may be down."
        except Exception as e:
            return f"Error saving memory: {str(e)}"

    def recall_memory(
        self,
        query: str,
        limit: int = 5,
    ) -> str:
        """
        Search persistent memory for relevant information. Use this to recall previously saved
        facts, preferences, or context.

        :param query: What to search for in memory
        :param limit: Maximum number of memories to return (default 5)
        :return: Relevant memories found
        """
        try:
            # Generate embedding for query
            embed_resp = requests.post(
                f"{self.valves.ollama_url}/api/embed",
                json={"model": self.valves.embed_model, "input": query},
                timeout=30,
            )
            embed_resp.raise_for_status()
            embedding = embed_resp.json().get("embeddings", [[]])[0]

            if not embedding:
                return "Failed to generate embedding for the query."

            # Search Qdrant
            search_resp = requests.post(
                f"{self.valves.qdrant_url}/collections/{self.valves.collection}/points/search",
                json={
                    "vector": embedding,
                    "limit": min(limit, 10),
                    "with_payload": True,
                },
                timeout=10,
            )
            search_resp.raise_for_status()
            results = search_resp.json().get("result", [])

            if not results:
                return f"No memories found matching: {query}"

            output = f"Memories matching '{query}':\n\n"
            for i, r in enumerate(results, 1):
                payload = r.get("payload", {})
                score = r.get("score", 0)
                content = payload.get("content", "")
                tags = payload.get("tags", [])
                output += f"{i}. [{score:.2f}] {content}"
                if tags:
                    output += f" (tags: {', '.join(tags)})"
                output += "\n"

            return output

        except requests.exceptions.ConnectionError:
            return "Memory service not available. Qdrant or Ollama may be down."
        except Exception as e:
            return f"Error recalling memory: {str(e)}"
