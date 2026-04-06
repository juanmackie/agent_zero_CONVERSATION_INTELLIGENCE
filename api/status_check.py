"""
Conversation Intelligence Plugin - Status Check API
Provides diagnostic information for the plugin UI
"""

import os
import glob
import json
from datetime import datetime
from helpers.api import ApiHandler, Request, Response
from helpers import kvp
from helpers.context_store import ContextStore


class StatusCheckHandler(ApiHandler):
    """
    API handler for checking Conversation Intelligence plugin status.
    Returns detailed diagnostic information for the web UI.
    """
    
    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Handle status check request
        
        Args:
            input: Request data with optional 'action'
            request: HTTP request object
            
        Returns:
            Status data as dict or Response object
        """
        payload = input if isinstance(input, dict) else {}
        action = payload.get("action", "get_status")
        
        if action == "get_status":
            return await self._get_status()
        else:
            return Response(status=400, response=f"Unknown action: {action}")
    
    async def _get_status(self) -> dict:
        """
        Collect comprehensive plugin status data
        
        Returns:
            Dictionary with all diagnostic information
        """
        status = {
            "installed": False,
            "first_run_complete": False,
            "last_processed": None,
            "last_processed_human": None,
            "conversations_analyzed": 0,
            "thread_count": 0,
            "threads": [],
            "storage": {
                "context_graph_size_kb": 0,
                "memory_files": 0,
                "memory_size_mb": 0
            },
            "recent_activity": {
                "last_analysis": None,
                "conversations_processed": 0
            },
            "analysis": {
                "state": "idle",
                "mode": None,
                "message": "Idle",
                "processed_count": 0,
                "total_count": 0,
                "progress_percent": 0,
                "started_at": None,
                "finished_at": None,
                "last_error": None,
            },
            "schedule": {
                "type": "job_loop",
                "interval": "Every hour",
                "status": "active"
            },
            "error": None
        }
        
        try:
            # Check plugin installation
            plugin_path = "usr/plugins/conversation_intelligence"
            required_files = [
                f"{plugin_path}/plugin.yaml",
                f"{plugin_path}/helpers/context_store.py",
                f"{plugin_path}/helpers/context_extractor.py",
                f"{plugin_path}/helpers/memory_documents.py",
                f"{plugin_path}/extensions/python/job_loop/_50_context_analysis.py",
            ]
            
            status["installed"] = all(os.path.exists(f) for f in required_files)
            
            if not status["installed"]:
                status["error"] = "Plugin files not found"
                return status
            
            # Check KVP data
            first_run = kvp.get_persistent("conversation_intelligence_first_run_complete", default=False)
            status["first_run_complete"] = first_run

            analysis = ContextStore.get_analysis_status()
            total_count = analysis.get("total_count", 0) or 0
            processed_count = analysis.get("processed_count", 0) or 0
            progress_percent = 0
            if total_count > 0:
                progress_percent = min(100, round((processed_count / total_count) * 100))

            analysis["progress_percent"] = progress_percent
            status["analysis"] = analysis
            
            now = datetime.now()
            last_processed = kvp.get_persistent("conversation_intelligence_last_processed_timestamp", default=None)
            if last_processed:
                dt = datetime.fromtimestamp(last_processed)
                status["last_processed"] = dt.isoformat()
                status["last_processed_human"] = self._format_time_ago(dt)
            
            # Get context graph
            context_graph = kvp.get_persistent("conversation_context_graph", default=None)
            if context_graph:
                contexts = context_graph.get("contexts", [])
                threads = context_graph.get("threads", {})
                
                status["conversations_analyzed"] = len(contexts)
                status["thread_count"] = len(threads)
                
                # Process thread list
                thread_list = []
                for thread_id, thread_data in threads.items():
                    thread_info = {
                        "id": thread_id,
                        "conversation_count": thread_data.get("conversation_count", 0),
                        "last_activity": thread_data.get("last_activity", ""),
                        "last_activity_human": self._format_time_ago_str(thread_data.get("last_activity", "")),
                        "entities": thread_data.get("entities", [])[:5],  # Top 5 entities
                        "importance": thread_data.get("average_importance", 0.5)
                    }
                    thread_list.append(thread_info)
                
                # Sort by conversation count (most active first)
                thread_list.sort(key=lambda x: x["conversation_count"], reverse=True)
                status["threads"] = thread_list[:10]  # Top 10 threads
                
                # Calculate storage size
                try:
                    import sys
                    graph_size = len(json.dumps(context_graph))
                    status["storage"]["context_graph_size_kb"] = round(graph_size / 1024, 2)
                except:
                    pass
            
            # Check memory system
            memory_path = "usr/memory/default"
            if os.path.exists(memory_path):
                faiss_files = glob.glob(f"{memory_path}/*")
                status["storage"]["memory_files"] = len(faiss_files)
                
                # Calculate total size
                total_size = 0
                for file in faiss_files:
                    if os.path.isfile(file):
                        total_size += os.path.getsize(file)
                status["storage"]["memory_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            # Check recent activity
            if last_processed:
                last_dt = datetime.fromtimestamp(last_processed)
                diff_hours = (now - last_dt).total_seconds() / 3600
                
                if diff_hours < 1:
                    status["recent_activity"]["last_analysis"] = f"{int(diff_hours * 60)} minutes ago"
                elif diff_hours < 24:
                    status["recent_activity"]["last_analysis"] = f"{int(diff_hours)} hours ago"
                else:
                    status["recent_activity"]["last_analysis"] = f"{int(diff_hours / 24)} days ago"

                if diff_hours > 2:
                    status["schedule"]["status"] = "inactive"

            if analysis.get("state") == "running":
                status["recent_activity"]["last_analysis"] = analysis.get("message", "Running")
                status["schedule"]["status"] = "active"
                
                # Estimate conversations processed in last run (this is approximate)
                if context_graph:
                    # Recent contexts (last 24 hours)
                    recent_count = 0
                    for ctx in context_graph.get("contexts", []):
                        ts = ctx.get("timestamp", "")
                        if ts:
                            try:
                                ctx_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                                if (now - ctx_dt).total_seconds() < 86400:  # 24 hours
                                    recent_count += 1
                            except:
                                pass
                    status["recent_activity"]["conversations_processed"] = recent_count
            
            return status
            
        except Exception as e:
            status["error"] = f"Error collecting status: {str(e)}"
            return status
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as human-readable time ago"""
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
    
    def _format_time_ago_str(self, timestamp_str: str) -> str:
        """Format timestamp string as human-readable time ago"""
        if not timestamp_str:
            return "unknown"
        
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            return self._format_time_ago(dt)
        except:
            return "unknown"
