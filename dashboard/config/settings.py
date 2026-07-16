import os
from pathlib import Path

# Load .env from repo root when running outside Docker (python-dotenv optional)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except ImportError:
    pass

# When running on the host machine, replace the Docker-internal hostname "postgres"
# with "localhost" and remap to the published port (5434 as per docker-compose.yml).
_raw_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@postgres:5432/erg_opera_data",
)

# Auto-patch: if the URL still points at the Docker service name and we're not inside
# a container (i.e. hostname "postgres" won't resolve), rewrite it for host access.
import socket as _socket
def _docker_host_reachable(host: str) -> bool:
    try:
        _socket.getaddrinfo(host, 5432)
        return True
    except _socket.gaierror:
        return False

if "@postgres:" in _raw_url and not _docker_host_reachable("postgres"):
    DATABASE_URL = _raw_url.replace("@postgres:5432", "@localhost:5434")
else:
    DATABASE_URL = _raw_url

CACHE_TTL_SECONDS = 300
DEFAULT_DATE_RANGE_DAYS = 90
