"""
Thread Detector - Auto-detect conversation groupings
Groups conversations by entity overlap and semantic similarity.
Zero new infrastructure - uses existing context data.
"""

from typing import Dict, List, Any, Set
from datetime import datetime


class ThreadDetector:
    """
    Automatically detects and manages conversation thread groupings.
    Groups by entity overlap (60%+ match) and temporal proximity.
    """
    
    # Threshold for entity overlap to consider same thread
    ENTITY_OVERLAP_THRESHOLD = 0.6
    
    # Time window for temporal grouping (hours)
    TEMPORAL_WINDOW_HOURS = 24
    
    def __init__(self):
        self.threads: Dict[str, Dict[str, Any]] = {}
    
    def calculate_entity_overlap(self, entities1: List[str], entities2: List[str]) -> float:
        """
        Calculate Jaccard similarity between two entity sets.
        
        Returns:
            Float 0.0-1.0 representing overlap percentage
        """
        if not entities1 or not entities2:
            return 0.0
        
        set1 = set(e.lower() for e in entities1)
        set2 = set(e.lower() for e in entities2)
        
        intersection = set1 & set2
        union = set1 | set2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def is_temporally_related(self, timestamp1: str, timestamp2: str) -> bool:
        """
        Check if two timestamps are within temporal window.
        
        Returns:
            True if within 24 hours of each other
        """
        try:
            dt1 = datetime.strptime(timestamp1, "%Y-%m-%d %H:%M:%S")
            dt2 = datetime.strptime(timestamp2, "%Y-%m-%d %H:%M:%S")
            
            diff_hours = abs((dt1 - dt2).total_seconds()) / 3600
            return diff_hours <= self.TEMPORAL_WINDOW_HOURS
        except (ValueError, TypeError):
            return False
    
    def find_best_thread_match(self, context: Dict[str, Any]) -> str:
        """
        Find the best matching thread for a context.
        
        Returns:
            Thread ID or None if no good match
        """
        entities = context.get("entities", [])
        timestamp = context.get("timestamp", "")
        suggested_thread = context.get("suggested_thread_id", "")
        
        # If there's already an original thread_id, use it
        original_thread = context.get("original_thread_id", "")
        if original_thread:
            return original_thread
        
        best_match = None
        best_score = 0.0
        
        for thread_id, thread_data in self.threads.items():
            # Check entity overlap with thread
            thread_entities = thread_data.get("entities", [])
            overlap = self.calculate_entity_overlap(entities, thread_entities)
            
            # Check temporal proximity
            thread_last_time = thread_data.get("last_activity", "")
            temporal_match = self.is_temporally_related(timestamp, thread_last_time)
            
            # Boost score if suggested thread name is similar
            name_match = 0.0
            if suggested_thread and thread_id:
                # Simple string similarity
                if suggested_thread.lower() in thread_id.lower() or thread_id.lower() in suggested_thread.lower():
                    name_match = 0.3
            
            # Calculate total score
            score = overlap + (0.2 if temporal_match else 0) + name_match
            
            # Must have at least 60% entity overlap or temporal + name match
            if overlap >= self.ENTITY_OVERLAP_THRESHOLD or (temporal_match and name_match > 0):
                if score > best_score:
                    best_score = score
                    best_match = thread_id
        
        return best_match
    
    def add_to_thread(self, context: Dict[str, Any], thread_id: str):
        """
        Add a context to an existing thread.
        
        Args:
            context: Context data with entities, topics, timestamp
            thread_id: Thread to add to
        """
        if thread_id not in self.threads:
            # Create new thread
            self.threads[thread_id] = {
                "entities": context.get("entities", []),
                "topics": context.get("topics", []),
                "conversation_count": 1,
                "average_importance": context.get("importance", 0.5),
                "last_activity": context.get("timestamp", ""),
                "document_ids": [context.get("document_id", "")]
            }
        else:
            # Update existing thread
            thread = self.threads[thread_id]
            
            # Merge entities (keep unique)
            existing_entities = set(thread["entities"])
            new_entities = set(context.get("entities", []))
            thread["entities"] = list(existing_entities | new_entities)
            
            # Merge topics
            existing_topics = set(thread["topics"])
            new_topics = set(context.get("topics", []))
            thread["topics"] = list(existing_topics | new_topics)
            
            # Update stats
            thread["conversation_count"] += 1
            
            # Update average importance
            old_avg = thread["average_importance"]
            new_importance = context.get("importance", 0.5)
            thread["average_importance"] = (old_avg + new_importance) / 2
            
            # Update last activity
            thread["last_activity"] = context.get("timestamp", thread["last_activity"])
            
            # Add document ID
            thread["document_ids"].append(context.get("document_id", ""))
    
    def update_threads(self, contexts: List[Dict[str, Any]]):
        """
        Process a batch of contexts and update thread groupings.
        
        Args:
            contexts: List of context dicts from extractor
        """
        for context in contexts:
            if not context:
                continue
            
            # Try to find existing thread
            existing_thread = self.find_best_thread_match(context)
            
            if existing_thread:
                # Add to existing thread
                self.add_to_thread(context, existing_thread)
            else:
                # Create new thread using suggested or generated ID
                suggested = context.get("suggested_thread_id", "")
                timestamp = context.get("timestamp", "")
                
                if suggested and suggested != "general":
                    new_thread_id = suggested
                else:
                    # Generate from entities
                    entities = context.get("entities", [])
                    if entities:
                        new_thread_id = f"{'-'.join(entities[:2]).lower()[:30]}"
                    else:
                        # Use timestamp-based ID
                        try:
                            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                            new_thread_id = f"thread-{dt.strftime('%Y%m%d')}"
                        except:
                            new_thread_id = "general"
                
                self.add_to_thread(context, new_thread_id)
    
    def get_all_threads(self) -> Dict[str, Dict[str, Any]]:
        """Return all thread groupings."""
        return self.threads
    
    def get_thread_for_document(self, document_id: str) -> str:
        """
        Find which thread a document belongs to.
        
        Returns:
            Thread ID or "general"
        """
        for thread_id, thread_data in self.threads.items():
            if document_id in thread_data.get("document_ids", []):
                return thread_id
        return "general"
