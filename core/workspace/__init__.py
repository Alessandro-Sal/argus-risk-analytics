"""ARGUS Workspace & Session Architecture Package."""
from core.workspace.context import (
    RiskSubContext,
    UIViewState,
    WealthSubContext,
    WorkspaceContext,
    get_canonical_db_fingerprint,
    prune_stale_session_caches,
    set_active_portfolio,
)
from core.workspace.demo_seeder import (
    clear_unified_archetype,
    execute_unified_archetype_load,
    render_unified_archetype_hud,
    seed_unified_demo_scenario,
)
from core.workspace.engine import (
    get_available_roles,
    get_role_profile,
    load_custom_workspace_layout,
    save_custom_workspace_layout,
)
from core.workspace.manager import (
    clear_session_cache,
    get_url_param,
    resolve_page_path,
    save_session_snapshot_to_cache,
    set_url_params,
)
from core.workspace.session import (
    ArgusSessionKeys,
    ArgusSessionManager,
    switch_profile_context,
)

__all__ = [
    "WorkspaceContext",
    "RiskSubContext",
    "WealthSubContext",
    "UIViewState",
    "get_canonical_db_fingerprint",
    "set_active_portfolio",
    "prune_stale_session_caches",
    "resolve_page_path",
    "get_url_param",
    "set_url_params",
    "save_session_snapshot_to_cache",
    "clear_session_cache",
    "ArgusSessionKeys",
    "ArgusSessionManager",
    "switch_profile_context",
    "save_custom_workspace_layout",
    "load_custom_workspace_layout",
    "get_role_profile",
    "get_available_roles",
    "seed_unified_demo_scenario",
    "execute_unified_archetype_load",
    "clear_unified_archetype",
    "render_unified_archetype_hud",
]
