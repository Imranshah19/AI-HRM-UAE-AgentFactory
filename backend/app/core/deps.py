"""
AI-HRMS — deps shim.
Re-exports the most commonly used dependencies so routers can use
the shorter ``from app.core.deps import ...`` convention.
"""

from app.core.dependencies import (  # noqa: F401
    get_db,
    get_current_user,
    get_current_active_user,
    require_permission,
)
