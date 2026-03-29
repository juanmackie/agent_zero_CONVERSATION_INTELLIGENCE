"""
Conversation Search Tool - Agent Zero Tool Implementation
Extends memory_load with date-range and thread filtering.
"""

from helpers.tool import Tool, Response
try:
    from usr.plugins.conversation_intelligence.helpers.conversation_search import ConversationSearch
except ModuleNotFoundError:
    from plugins.conversation_intelligence.helpers.conversation_search import ConversationSearch

DEFAULT_THRESHOLD = 0.7
DEFAULT_LIMIT = 10


class ConversationSearchTool(Tool):
    """
    Tool for searching conversations by date range and thread.
    Backward compatible with existing memory_load.
    """
    
    async def execute(
        self,
        query: str = "",
        date_from: str = "",
        date_to: str = "",
        thread_id: str = "",
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = DEFAULT_LIMIT,
        **kwargs
    ):
        """
        Execute conversation search.
        
        Args:
            query: Semantic search text
            date_from: Start date (YYYY-MM-DD), optional
            date_to: End date (YYYY-MM-DD), optional
            thread_id: Thread identifier, optional
            threshold: Similarity threshold 0.0-1.0
            limit: Maximum results
        """
        try:
            # Convert empty strings to None
            date_from = date_from if date_from else None
            date_to = date_to if date_to else None
            thread_id = thread_id if thread_id else None
            
            # Perform search using helper
            docs = await ConversationSearch.search(
                agent=self.agent,
                query=query,
                date_from=date_from,
                date_to=date_to,
                thread_id=thread_id,
                threshold=threshold,
                limit=limit
            )
            
            # Format results
            result = ConversationSearch.format_results(docs)
            
        except Exception as e:
            result = f"Error: {str(e)}"
        
        return Response(message=result, break_loop=False)
