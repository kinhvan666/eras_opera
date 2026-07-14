# tests/test_client.py
import pytest
import respx
from httpx import Response
from src.client import BaseOperaClient, OperaAuthError
from src.config import settings

@pytest.mark.asyncio
@respx.mock
async def test_get_token_auth_failure():
    """
    Tests that the client raises OperaAuthError on a 401 response from the token endpoint.
    """
    # Mock the token endpoint to return a 401 Unauthorized
    respx.post(settings.opera_token_url).mock(return_value=Response(401, json={"error": "invalid_client"}))

    client = BaseOperaClient()

    with pytest.raises(OperaAuthError, match="Failed to get token: 401"):
        await client._get_token()