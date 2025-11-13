from supabase import create_client, Client  # type: ignore
from typing import Optional
from app.config import settings


def get_supabase_client(use_service_role: bool = True) -> Client:
    """
    Get Supabase client.
    
    Args:
        use_service_role: When True (default), use the service role key if available
            to ensure backend operations bypass RLS restrictions intended for public clients.
    """
    if use_service_role and settings.supabase_service_role_key:
        key = settings.supabase_service_role_key
    else:
        key = settings.supabase_key
    return create_client(settings.supabase_url, key)


def get_supabase_admin_client() -> Optional[Client]:
    """Get Supabase client with service role key (admin access)"""
    if not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# Default client instances
supabase_client = get_supabase_client()
supabase_admin: Optional[Client] = get_supabase_admin_client()


