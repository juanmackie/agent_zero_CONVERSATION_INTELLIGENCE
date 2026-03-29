"""
Conversation Context Injection - Uses Agent Zero's system_prompt extension
Silently injects recent conversation context into agent's awareness.
Zero prompt hacking, uses official extension point.
"""

from helpers.extension import Extension
try:
    from usr.plugins.conversation_intelligence.helpers.context_store import ContextStore
except ModuleNotFoundError:
    from plugins.conversation_intelligence.helpers.context_store import ContextStore


class ConversationContextPrompt(Extension):
    """
    Extension that injects conversation context into system prompt.
    Allows agent to naturally carry context across conversations.
    """
    
    # Maximum threads to include in prompt
    MAX_THREADS = 3
    
    # Maximum characters per thread summary
    MAX_SUMMARY_LENGTH = 200
    
    async def execute(self, system_prompt: list, **kwargs):
        """
        Called when building system prompt.
        Adds recent conversation context naturally.
        
        Args:
            system_prompt: List of prompt strings (mutable)
        """
        try:
            # Get top active threads
            top_threads = ContextStore.get_top_threads(self.MAX_THREADS)
            
            if not top_threads:
                return
            
            # Build context section
            context_lines = ["Recent conversation context:"]
            
            for i, thread in enumerate(top_threads, 1):
                thread_id = thread.get("thread_id", "unknown")
                last_activity = thread.get("last_activity", "")
                conversation_count = thread.get("conversation_count", 0)
                
                # Format time ago
                time_ago = self._format_time_ago(last_activity)
                
                # Build summary line
                summary = f"{i}. Thread '{thread_id}': {conversation_count} conversations (last: {time_ago})"
                
                # Truncate if too long
                if len(summary) > self.MAX_SUMMARY_LENGTH:
                    summary = summary[:self.MAX_SUMMARY_LENGTH - 3] + "..."
                
                context_lines.append(summary)
            
            # Add note about using context naturally
            context_lines.append("Use this context naturally when relevant to the current conversation.")
            
            # Add to system prompt
            context_section = "\n".join(context_lines)
            system_prompt.append(context_section)
            
        except Exception as e:
            # Silent fail - don't break prompt building
            print(f"Context injection error: {e}")
    
    def _format_time_ago(self, timestamp: str) -> str:
        """
        Format timestamp as human-readable time ago.
        
        Returns:
            String like "2 hours ago", "yesterday", "today"
        """
        if not timestamp:
            return "unknown time"
        
        try:
            from datetime import datetime
            
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = now - dt
            
            if diff.days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    if minutes == 0:
                        return "just now"
                    return f"{minutes} minutes ago"
                return f"{hours} hours ago"
            elif diff.days == 1:
                return "yesterday"
            elif diff.days < 7:
                return f"{diff.days} days ago"
            else:
                return dt.strftime("%Y-%m-%d")
                
        except Exception:
            return "unknown time"
