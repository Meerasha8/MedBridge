from supabase import create_client, Client
import config

_anon_client: Client | None = None
_service_client: Client | None = None


def get_supabase() -> Client:
    """Anon-key client. Use for auth.sign_in / auth.sign_up calls."""
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    return _anon_client


def get_supabase_admin() -> Client:
    """Service-role client. Bypasses RLS. Use for all server-side data access
    in this app, since FastAPI (not the browser) is the trusted backend."""
    global _service_client
    if _service_client is None:
        _service_client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    return _service_client
