"""
Context Extractor - Uses Agent Zero's existing LLM infrastructure
Zero custom LLM clients, zero new dependencies.
"""

import json
from typing import Dict, Any, Optional


class ContextExtractor:
    """
    Extracts entities, topics, and context from conversations.
    Uses agent.call_utility_model() - existing Agent Zero infrastructure.
    """
    
    EXTRACTION_PROMPT = """Analyze this conversation and extract:
1. Key entities (people, products, projects, tools, concepts)
2. Main topics/themes (2-4 words each)
3. Thread identifier suggestion (group related conversations)
4. Importance score (0.0-1.0)

Return ONLY valid JSON in this exact format:
{
  "entities": ["entity1", "entity2", "entity3"],
  "topics": ["topic1", "topic2"],
  "suggested_thread_id": "descriptive-name",
  "importance": 0.8
}

Conversation to analyze:
"""

    async def extract(self, agent, conversation_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract context from conversation text using utility model.
        
        Args:
            agent: Agent Zero agent instance
            conversation_text: The conversation content to analyze
            
        Returns:
            Dict with entities, topics, thread_id, importance or None if failed
        """
        if not conversation_text or not agent:
            return None
        
        try:
            # Use Agent Zero's existing utility model call
            # This handles rate limiting, model selection, and error handling
            response = await agent.call_utility_model(
                system="You are a context extraction assistant. Extract key information from conversations.",
                message=self.EXTRACTION_PROMPT + conversation_text[:2000],  # Limit length
                background=True  # Non-blocking call
            )
            
            # Parse JSON response
            result = json.loads(response.strip())
            
            # Validate structure
            if "entities" in result and "topics" in result:
                return {
                    "entities": result.get("entities", []),
                    "topics": result.get("topics", []),
                    "suggested_thread_id": result.get("suggested_thread_id", "general"),
                    "importance": result.get("importance", 0.5)
                }
            
            return None
            
        except json.JSONDecodeError:
            # Invalid JSON response
            return None
        except Exception as e:
            # LLM call failed
            print(f"Context extraction error: {e}")
            return None
    
    async def extract_from_document(self, agent, doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract context from a memory document.
        
        Args:
            agent: Agent Zero agent
            doc: Memory document with 'content' and 'metadata'
            
        Returns:
            Enriched context dict or None
        """
        if not doc:
            return None
        
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        
        if not content:
            return None
        
        # Extract core context
        context = await self.extract(agent, content)
        
        if context:
            # Add document metadata
            context["document_id"] = metadata.get("id", "")
            context["timestamp"] = metadata.get("timestamp", "")
            context["original_thread_id"] = metadata.get("thread_id", "")
            
            # Use original thread_id if present, otherwise use suggested
            if context["original_thread_id"]:
                context["thread_id"] = context["original_thread_id"]
            else:
                context["thread_id"] = context["suggested_thread_id"]
        
        return context
