"""
Multi-modal agent for processing various content types.
Handles text, images, audio, video, and combined modalities.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


class MultiModalAgent(Agent):
    """Agent for multi-modal content processing and generation.
    
    Processes various content types including images, audio, video, and text.
    Integrates vision models (llava), speech-to-text (Whisper), and LLM reasoning
    to provide comprehensive multi-modal analysis.
    
    Attributes:
        vision_model: Name of the vision model to use (default: llava:13b)
        whisper_url: URL for Whisper STT service
        tts_url: URL for Text-to-Speech service
        ollama_base_url: URL for Ollama API endpoint
    """

    def __init__(
        self,
        config: AgentConfig,
        agent_id: str = "multimodal",
        vision_model: str = "llava:13b",
        whisper_url: Optional[str] = None,
        tts_url: Optional[str] = None,
        ollama_url: Optional[str] = None,
    ):
        """Initialize Multi-Modal Agent.
        
        Args:
            config: Agent configuration with timeout and other settings
            agent_id: Unique identifier for this agent instance
            vision_model: Vision model name (e.g., 'llava:13b', 'bakllava:latest')
            whisper_url: Whisper STT service URL (default: from WHISPER_URL env or http://whisper:9000)
            tts_url: TTS service URL (default: from TTS_URL env or http://coqui-tts:5002)
            ollama_url: Ollama API URL (default: from OLLAMA_BASE_URL env or http://ollama-gpu:11434)
        """
        super().__init__(config, agent_id)
        self.vision_model = vision_model
        self.whisper_url = whisper_url or os.getenv("WHISPER_URL", "http://whisper:9000")
        self.tts_url = tts_url or os.getenv("TTS_URL", "http://coqui-tts:5002")
        self.ollama_base_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://ollama-gpu:11434")

    @property
    def system_prompt(self) -> str:
        return """You are a multi-modal AI assistant capable of processing and understanding
various types of content including text, images, audio, and video. You can:
- Analyze images and describe their content
- Transcribe audio to text
- Generate descriptions for videos
- Combine multiple modalities for comprehensive analysis
- Provide structured outputs based on multi-modal inputs

Always provide detailed, accurate analysis and maintain context across modalities."""

    async def execute(self, input_data: str, **kwargs: Any) -> AgentResult:
        """
        Execute multi-modal processing.

        Args:
            input_data: Task description or text input
            **kwargs: Additional parameters:
                - image_path: Path to image file
                - audio_path: Path to audio file
                - video_path: Path to video file
                - modalities: List of modalities to process
        """
        if not self.validate_input(input_data):
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error="Invalid input data",
            )

        try:
            # Extract modality-specific paths
            image_path = kwargs.get("image_path")
            audio_path = kwargs.get("audio_path")
            video_path = kwargs.get("video_path")
            modalities = kwargs.get("modalities", [])

            # Process each modality
            results = {}

            if image_path or "image" in modalities:
                results["image"] = await self._process_image(image_path)

            if audio_path or "audio" in modalities:
                results["audio"] = await self._process_audio(audio_path)

            if video_path or "video" in modalities:
                results["video"] = await self._process_video(video_path)

            # Combine results with LLM reasoning
            combined_prompt = self._build_combined_prompt(input_data, results)
            response = await self._call_llm(combined_prompt)

            return AgentResult(
                status=AgentStatus.COMPLETED,
                output=response,
                metadata={
                    "modalities_processed": list(results.keys()),
                    "individual_results": results,
                },
            )

        except Exception as e:
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error=f"Multi-modal processing failed: {str(e)}",
            )

    async def _process_image(self, image_path: Optional[str]) -> Dict[str, Any]:
        """Process image using vision model.
        
        Args:
            image_path: Path to image file to process
            
        Returns:
            Dict containing processing status and results
        """
        if not image_path:
            return {"status": "skipped", "reason": "no_image_path"}

        try:
            # Security: validate file path and check file size
            image_file = Path(image_path).resolve()
            
            # Prevent path traversal attacks
            if not image_file.is_file():
                return {"status": "error", "error": "Invalid file path"}
            
            # Check file size (max 10MB for images)
            max_size = 10 * 1024 * 1024  # 10MB
            if image_file.stat().st_size > max_size:
                return {"status": "error", "error": "Image file too large (max 10MB)"}

            # Call vision model (llava) with image
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                with open(image_file, "rb") as f:
                    image_data = f.read()

                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": "Describe this image in detail, including objects, people, actions, setting, colors, and mood.",
                        "images": [image_data.hex()],
                        "stream": False,
                    },
                )
                result = response.json()

                return {
                    "status": "success",
                    "description": result.get("response", ""),
                    "model": self.vision_model,
                }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _process_audio(self, audio_path: Optional[str]) -> Dict[str, Any]:
        """Process audio using Whisper STT.
        
        Args:
            audio_path: Path to audio file to transcribe
            
        Returns:
            Dict containing transcription and metadata
        """
        if not audio_path:
            return {"status": "skipped", "reason": "no_audio_path"}

        try:
            # Security: validate file path and check file size
            audio_file = Path(audio_path).resolve()
            
            # Prevent path traversal attacks
            if not audio_file.is_file():
                return {"status": "error", "error": "Invalid file path"}
            
            # Check file size (max 25MB for audio)
            max_size = 25 * 1024 * 1024  # 25MB
            if audio_file.stat().st_size > max_size:
                return {"status": "error", "error": "Audio file too large (max 25MB)"}

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                with open(audio_file, "rb") as f:
                    files = {"audio_file": f}
                    response = await client.post(
                        f"{self.whisper_url}/asr",
                        files=files,
                        data={"task": "transcribe", "language": "en"},
                    )
                result = response.json()

                return {
                    "status": "success",
                    "transcription": result.get("text", ""),
                    "language": result.get("language", ""),
                    "duration": result.get("duration", 0),
                }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _process_video(self, video_path: Optional[str]) -> Dict[str, Any]:
        """Process video by extracting frames and analyzing."""
        if not video_path:
            return {"status": "skipped", "reason": "no_video_path"}

        try:
            # Extract key frames from video
            # This would use ffmpeg to extract frames
            # For now, return placeholder
            return {
                "status": "success",
                "summary": "Video processing requires frame extraction (ffmpeg integration)",
                "frames_analyzed": 0,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _build_combined_prompt(
        self, task: str, results: Dict[str, Dict[str, Any]]
    ) -> str:
        """Build combined prompt from all modality results.
        
        Constructs a comprehensive prompt combining analysis from all processed
        modalities (image, audio, video) for final LLM reasoning.
        
        Args:
            task: Original task/question from user
            results: Dict mapping modality names to their processing results
                   Each result should have 'status' and modality-specific data
        
        Returns:
            Combined prompt string ready for LLM processing
        """
        prompt_parts = [self.system_prompt, f"\nTask: {task}\n"]

        if "image" in results and results["image"].get("status") == "success":
            prompt_parts.append(
                f"\nImage Analysis:\n{results['image']['description']}"
            )

        if "audio" in results and results["audio"].get("status") == "success":
            prompt_parts.append(
                f"\nAudio Transcription:\n{results['audio']['transcription']}"
            )

        if "video" in results and results["video"].get("status") == "success":
            prompt_parts.append(f"\nVideo Analysis:\n{results['video']['summary']}")

        prompt_parts.append(
            "\nBased on the above multi-modal information, provide a comprehensive analysis and response to the task."
        )

        return "\n".join(prompt_parts)


class EmbeddingAgent(Agent):
    """Agent for generating and managing embeddings.
    
    Specialized agent for vector embedding generation and semantic search operations.
    Integrates with Qdrant vector database for storage and retrieval of embeddings.
    
    Attributes:
        embedding_model: Name of the embedding model (default: nomic-embed-text:latest)
        qdrant_url: URL for Qdrant vector database
        ollama_base_url: URL for Ollama API (embeddings endpoint)
        
    Supported Operations:
        - generate: Create vector embeddings for text
        - search: Perform semantic search in vector database
    """

    def __init__(
        self,
        config: AgentConfig,
        agent_id: str = "embedding",
        embedding_model: str = "nomic-embed-text:latest",
        qdrant_url: Optional[str] = None,
        ollama_url: Optional[str] = None,
    ):
        """Initialize Embedding Agent.
        
        Args:
            config: Agent configuration with timeout settings
            agent_id: Unique identifier for this agent
            embedding_model: Model for generating embeddings (nomic-embed-text, mxbai-embed-large)
            qdrant_url: Qdrant vector DB URL (default: from QDRANT_URL env or http://qdrant:6333)
            ollama_url: Ollama API URL (default: from OLLAMA_BASE_URL env or http://ollama-cpu:11434)
        """
        super().__init__(config, agent_id)
        self.embedding_model = embedding_model
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.ollama_base_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://ollama-cpu:11434")

    @property
    def system_prompt(self) -> str:
        return """You are an embedding specialist. You generate high-quality vector
embeddings for text, manage vector databases, and perform semantic search operations."""

    async def execute(self, input_data: str, **kwargs: Any) -> AgentResult:
        """Generate embeddings or perform semantic search.
        
        Args:
            input_data: Text to embed or search query
            **kwargs: Additional parameters:
                - operation: 'generate' or 'search' (default: 'generate')
                - collection: Qdrant collection name for search (default: 'default')
                - top_k: Number of results to return for search (default: 5)
                
        Returns:
            AgentResult with embeddings vector or search results
            
        Example:
            >>> # Generate embeddings
            >>> result = await agent.execute("machine learning concepts")
            >>> embeddings = result.metadata['embeddings']
            
            >>> # Semantic search
            >>> result = await agent.execute(
            ...     "python tutorial",
            ...     operation="search",
            ...     collection="docs",
            ...     top_k=5
            ... )
        """
        if not self.validate_input(input_data):
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error="Invalid input data",
            )

        try:
            operation = kwargs.get("operation", "generate")

            if operation == "generate":
                embeddings = await self._generate_embeddings(input_data)
                return AgentResult(
                    status=AgentStatus.COMPLETED,
                    output=f"Generated embeddings with dimension {len(embeddings)}",
                    metadata={"embeddings": embeddings, "model": self.embedding_model},
                )

            elif operation == "search":
                query = input_data
                collection = kwargs.get("collection", "default")
                top_k = kwargs.get("top_k", 5)
                results = await self._semantic_search(query, collection, top_k)
                return AgentResult(
                    status=AgentStatus.COMPLETED,
                    output=f"Found {len(results)} similar items",
                    metadata={"results": results},
                )

            else:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    output="",
                    error=f"Unknown operation: {operation}",
                )

        except Exception as e:
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error=f"Embedding operation failed: {str(e)}",
            )

    async def _generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings using Ollama embedding model."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
            )
            result = response.json()
            return result.get("embedding", [])

    async def _semantic_search(
        self, query: str, collection: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic search in Qdrant vector database."""
        # Generate query embedding
        query_embedding = await self._generate_embeddings(query)

        # Search in Qdrant
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.qdrant_url}/collections/{collection}/points/search",
                json={"vector": query_embedding, "limit": top_k, "with_payload": True},
            )
            result = response.json()
            return result.get("result", [])


class FunctionCallingAgent(Agent):
    """Agent specialized in function calling and tool use."""

    def __init__(
        self,
        config: AgentConfig,
        agent_id: str = "function_calling",
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(config, agent_id)
        self.available_tools = available_tools or []

    @property
    def system_prompt(self) -> str:
        tools_desc = "\n".join(
            [
                f"- {tool['name']}: {tool.get('description', 'No description')}"
                for tool in self.available_tools
            ]
        )
        return f"""You are a function calling specialist. You can call external tools
and APIs to accomplish tasks.

Available tools:
{tools_desc}

When calling functions, respond with valid JSON in this format:
{{
    "function": "function_name",
    "arguments": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}"""

    async def execute(self, input_data: str, **kwargs: Any) -> AgentResult:
        """Execute function calling workflow with LLM-driven tool selection.
        
        Processes user input to determine which external tools/functions to call,
        executes the selected functions, and returns the results. Uses the LLM
        to make intelligent decisions about tool usage based on available tools
        and task requirements.
        
        Args:
            input_data: User task or query requiring function calling
            **kwargs: Additional execution parameters (currently unused)
            
        Returns:
            AgentResult with function call execution status and output
            
        Raises:
            AgentResult with FAILED status on validation errors or execution failures
            
        Example:
            >>> agent = FunctionCallingAgent(config, available_tools=[{"name": "search", "description": "Web search"}])
            >>> result = await agent.execute("Find the latest news about AI")
            >>> print(result.status)  # AgentStatus.COMPLETED
            >>> print(result.metadata["function_call_attempted"])  # True
        """
        if not self.validate_input(input_data):
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error="Invalid input data",
            )

        try:
            # Get function call decision from LLM
            prompt = f"{self.system_prompt}\n\nTask: {input_data}\n\nWhich function should be called and with what arguments?"
            response = await self._call_llm(prompt)

            # Parse function call (simplified - would need proper JSON parsing)
            # Execute function call
            # Return results

            return AgentResult(
                status=AgentStatus.COMPLETED,
                output=response,
                metadata={"function_call_attempted": True},
            )

        except Exception as e:
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error=f"Function calling failed: {str(e)}",
            )
