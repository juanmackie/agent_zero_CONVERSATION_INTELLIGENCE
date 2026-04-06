"""
Conversation Intelligence Plugin - Lifecycle Hooks
Uses Agent Zero's existing plugin system - zero custom infrastructure.
"""

from helpers import kvp

_FIRST_RUN_KEY = "conversation_intelligence_first_run_complete"
_LAST_PROCESSED_KEY = "conversation_intelligence_last_processed_timestamp"


def initialize_plugin(agent=None):
    """Called when plugin is loaded by Agent Zero."""
    # Keep initialization lightweight; job_loop owns all analysis work.
    if kvp.get_persistent("conversation_intelligence_analysis_status", default=None) is None:
        kvp.set_persistent(
            "conversation_intelligence_analysis_status",
            {
                "state": "idle",
                "mode": None,
                "message": "Idle",
                "processed_count": 0,
                "total_count": 0,
                "started_at": None,
                "finished_at": None,
                "last_error": None,
            },
        )

    return True


def uninstall():
    """Called when plugin is uninstalled."""
    kvp.remove_persistent(_FIRST_RUN_KEY)
    kvp.remove_persistent(_LAST_PROCESSED_KEY)
    kvp.remove_persistent("conversation_context_graph")
    kvp.remove_persistent("conversation_thread_index")
    kvp.remove_persistent("conversation_intelligence_analysis_status")

    return True
