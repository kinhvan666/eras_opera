
# Plan: Booking Core - Phase 1 Data Extractor

**Date:** 13-07-26
**Feature:** booking-core
**Phase:** 1 of 3 (Data Extractor)
**Status:** DRAFT

## 1. Overview & Goals

This document outlines the detailed technical plan for implementing Phase 1 of the `booking-core` feature: creating a robust Python-based data extractor for Oracle OPERA Cloud.

The primary goal is to build a service that can:
1.  Authenticate with the OPERA Cloud API.
2.  Extract reservation and related profile data.
3.  Handle API pagination and rate-limiting gracefully.
4.  Load the raw, unmodified JSON data into a staging table in a PostgreSQL database.

This plan is designed to be executed by another agent or developer with no ambiguity. All file contents, commands, and verification steps are explicitly defined.

## 2. Touchpoints & Blast Radius

-   **Touchpoints:**
    -   This is a greenfield project, so all files created will be new. No existing code will be modified.
    -   New directories: `src/`, `src/extractors`, `tests/`
    -   New files: `src/client.py`, `src/config.py`, `src/database.py`, `src/extractors/reservations.py`, `src/main.py`, `src/models.py`, `tests/__init__.py`, `tests/test_client.py`, `tests/test_database.py`, `Dockerfile`, `docker-compose.yml`, `.env`, `pyproject.toml`
-   **Public Contracts:**
    -   The service will expose no public API itself.
    -   Its "public contract" is the data it writes to the `raw.booking_core_reservations` table in PostgreSQL. The schema for this is simple: an ID, a timestamp, and a `jsonb` column for the raw data.
-   **Blast Radius:**
    -   The scope is contained entirely within the new Python service and its corresponding Docker environment.
    -   It will interact with the PostgreSQL database by writing to a new, isolated schema (`raw`).
    -   Risk Class: Low. As a read-only extractor writing to a new staging table, it has no impact on existing systems.

## 3. Implementation Checklist

### Phase 3.1: Project Setup

1.  **Create Project Directory Structure:**
    ```bash
    mkdir -p src/extractors tests
    touch src/__init__.py src/client.py src/config.py src/database.py src/main.py src/models.py src/extractors/__init__.py src/extractors/reservations.py
    touch tests/__init__.py tests/test_client.py tests/test_database.py
    ```

2.  **Initialize Poetry Project and Add Dependencies:**
    ```bash
    # Make sure you are in the root of the ErasOpera project
    poetry init --name "opera-extractor" --python "^3.11" -n
    poetry add httpx pydantic pydantic-settings tenacity psycopg2-binary python-dotenv
    poetry add --group dev pytest pytest-asyncio respx
    ```
    This will create `pyproject.toml`.

3.  **Create `Dockerfile`:**
    ```dockerfile
    # syntax=docker/dockerfile:1

    # Use an official Python runtime as a parent image
    FROM python:3.11-slim

    # Set the working directory in the container
    WORKDIR /app

    # Install poetry
    RUN pip install poetry

    # Copy only the files needed for dependency installation
    COPY pyproject.toml poetry.lock* ./

    # Install dependencies
    RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

    # Copy the rest of the application's source code
    COPY src/ ./src/

    # Command to run the application
    CMD ["python", "src/main.py"]
    ```

4.  **Create `docker-compose.yml`:**
    ```yaml
    version: '3.8'

    services:
      db:
        image: postgres:15
        container_name: opera_db
        environment:
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
          POSTGRES_DB: erg_opera_data
        ports:
          - "5432:5432"
        volumes:
          - postgres_data:/var/lib/postgresql/data

      extractor:
        build: .
        container_name: opera_extractor
        depends_on:
          - db
        env_file:
          - .env
        volumes:
          - ./src:/app/src

    volumes:
      postgres_data:
    ```

### Phase 3.2: Configuration

1.  **Create `.env` file:** (Add this to `.gitignore` if not already present)
    ```dotenv
    # .env
    # --- OPERA Cloud API Credentials ---
    OPERA_CLIENT_ID="your_client_id"
    OPERA_CLIENT_SECRET="your_client_secret"
    OPERA_APP_KEY="your_app_key"
    OPERA_BASE_URL="https://api.cloud.opera.com"
    OPERA_TOKEN_URL="https://api.cloud.opera.com/token" # Example, confirm correct URL
    OPERA_HOTEL_ID="your_hotel_id"

    # --- PostgreSQL Database ---
    DATABASE_URL="postgresql://user:password@db:5432/erg_opera_data"
    ```

2.  **Create `src/config.py`:**
    ```python
    # src/config.py
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        # OPERA Cloud API
        opera_client_id: str
        opera_client_secret: str
        opera_app_key: str
        opera_base_url: str
        opera_token_url: str
        opera_hotel_id: str

        # PostgreSQL
        database_url: str

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

    settings = Settings()
    ```

### Phase 3.3: Extractor Implementation

1.  **Create `src/models.py`:**
    ```python
    # src/models.py
    from pydantic import BaseModel, Field
    from typing import Optional, List

    class ProfileName(BaseModel):
        name_id: int = Field(..., alias='nameId')
        name_type: str = Field(..., alias='nameType')
        first_name: Optional[str] = Field(None, alias='firstName')
        last_name: str = Field(..., alias='lastName')

    class ReservationName(BaseModel):
        profile: ProfileName

    class Reservation(BaseModel):
        reservation_id: str = Field(..., alias='reservationId')
        confirmation_no: str = Field(..., alias='confirmationNo')
        reservation_name_list: List[ReservationName] = Field(..., alias='reservationNameList')
        # Add other relevant reservation fields from the SPEC as needed
    ```

2.  **Create `src/client.py`:**
    ```python
    # src/client.py
    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential
    from typing import Optional, List, Dict, Any

    from .config import settings

    class OperaAuthError(Exception):
        """Custom exception for authentication errors."""
        pass

    class BaseOperaClient:
        def __init__(self):
            self._session = httpx.AsyncClient(base_url=settings.opera_base_url)
            self._token: Optional[str] = None

        async def _get_token(self) -> str:
            """Fetches an OAuth token from OPERA Cloud."""
            if self._token:
                # In a real scenario, you'd check for token expiry.
                # For this phase, we fetch it once.
                return self._token

            auth_data = {
                "grant_type": "client_credentials",
                "client_id": settings.opera_client_id,
                "client_secret": settings.opera_client_secret,
            }
            headers = {"x-app-key": settings.opera_app_key}
            
            try:
                response = await self._session.post(settings.opera_token_url, data=auth_data, headers=headers)
                response.raise_for_status()
                self._token = response.json()["access_token"]
                return self._token
            except httpx.HTTPStatusError as e:
                raise OperaAuthError(f"Failed to get token: {e.response.status_code} {e.response.text}") from e


        async def _set_auth_headers(self):
            token = await self._get_token()
            self._session.headers.update({
                "Authorization": f"Bearer {token}",
                "x-app-key": settings.opera_app_key,
                "x-hotelid": settings.opera_hotel_id,
                "Content-Type": "application/json",
            })

        @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
        async def fetch_all(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[Any, Any]]:
            """Fetches all pages from a given paginated endpoint."""
            if not self._token:
                await self._set_auth_headers()

            all_results = []
            
            response = await self._session.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # The structure of the response payload needs to be confirmed from API docs.
            # This is a common pattern.
            items_key = next((key for key in data if isinstance(data.get(key), list)), None)
            if items_key:
                all_results.extend(data[items_key])

            # Pagination logic based on 'next' link in headers, a common REST pattern.
            # This may need adjustment based on OPERA Cloud's specific pagination implementation.
            while 'next' in response.links:
                next_url = response.links['next']['url']
                response = await self._session.get(next_url)
                response.raise_for_status()
                data = response.json()
                if items_key:
                    all_results.extend(data[items_key])
            
            return all_results
    ```

3.  **Create `src/extractors/reservations.py`:**
    ```python
    # src/extractors/reservations.py
    from typing import List
    from ..client import BaseOperaClient
    from ..models import Reservation

    class ReservationExtractor:
        def __init__(self, client: BaseOperaClient):
            self.client = client

        async def fetch_recent_reservations(self) -> List[dict]:
            """Fetches reservations created in the last day."""
            # The endpoint and params need to be confirmed from the OPERA Cloud API documentation.
            # Example endpoint and params:
            endpoint = "/res/v1/hotels/YOUR_HOTEL/reservations" 
            params = {
                "query": "createDate=ge:$(SYSDATE-1)",
                "limit": 100
            }
            
            raw_reservations = await self.client.fetch_all(endpoint=endpoint, params=params)
            
            # For this phase, we return raw dicts. Pydantic validation can be added later.
            # validated_reservations = [Reservation.model_validate(res) for res in raw_reservations]
            return raw_reservations
    ```

4.  **Create `src/database.py`:**
    ```python
    # src/database.py
    import psycopg2
    import psycopg2.extras
    import json
    from .config import settings

    class DatabaseConnectionError(Exception):
        """Custom exception for database connection errors."""
        pass

    class Database:
        def __init__(self):
            try:
                self.conn = psycopg2.connect(settings.database_url)
            except psycopg2.OperationalError as e:
                raise DatabaseConnectionError(f"Could not connect to database: {e}") from e


        def setup(self):
            """Creates the necessary schema and tables."""
            with self.conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS raw.booking_core_reservations (
                        id SERIAL PRIMARY KEY,
                        extracted_at TIMESTAMPTZ DEFAULT NOW(),
                        raw_data JSONB NOT NULL
                    );
                """)
                self.conn.commit()

        def insert_raw_data(self, data: list[dict]):
            """Inserts a list of raw JSON objects into the database."""
            if not data:
                return
            
            with self.conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    "INSERT INTO raw.booking_core_reservations (raw_data) VALUES %s",
                    [(json.dumps(item),) for item in data]
                )
                self.conn.commit()
        
        def close(self):
            self.conn.close()

    ```

5.  **Create `src/main.py`:**
    ```python
    # src/main.py
    import asyncio
    import sys
    from .client import BaseOperaClient, OperaAuthError
    from .extractors.reservations import ReservationExtractor
    from .database import Database, DatabaseConnectionError

    async def main():
        print("Starting data extraction process...")
        
        try:
            # Initialize Database and setup schema/tables
            db = Database()
            print("Setting up database schema and tables...")
            db.setup()
            
            # Initialize API client and extractor
            opera_client = BaseOperaClient()
            reservation_extractor = ReservationExtractor(opera_client)

            # Fetch data
            print("Fetching recent reservations...")
            reservations_data = await reservation_extractor.fetch_recent_reservations()
            print(f"Fetched {len(reservations_data)} reservations.")

            # Insert data into database
            if reservations_data:
                print("Inserting data into PostgreSQL...")
                db.insert_raw_data(reservations_data)
                print("Data insertion complete.")
            
            # Clean up
            db.close()
            print("Extraction process finished.")

        except (OperaAuthError, DatabaseConnectionError) as e:
            print(f"A critical error occurred: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)

    if __name__ == "__main__":
        asyncio.run(main())
    ```

6.  **Create `tests/test_client.py`:**
    ```python
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

    ```

7.  **Create `tests/test_database.py`:**
    ```python
    # tests/test_database.py
    import pytest
    import psycopg2
    from src.database import Database, DatabaseConnectionError

    def test_database_connection_failure(monkeypatch):
        """
        Tests that the Database class raises DatabaseConnectionError on a connection failure.
        """
        # Mock psycopg2.connect to raise an OperationalError
        def mock_connect(*args, **kwargs):
            raise psycopg2.OperationalError("Mock connection error")

        monkeypatch.setattr(psycopg2, "connect", mock_connect)

        with pytest.raises(DatabaseConnectionError, match="Could not connect to database"):
            Database()
    ```

## 4. Verification & Evidence

This section outlines how to verify the successful implementation of the plan.

| Gate / Scenario | Strategy | Command / Steps | Proves SPEC criterion |
|---|---|---|---|
| **Automated Tests** | Fully-Automated | `poetry run pytest` | The application handles API and database connection failures gracefully. |
| **Build & Run** | Hybrid | 1. `docker-compose up --build -d` <br> 2. `docker-compose logs -f extractor` | The application environment can be built and started successfully. |
| **Database Setup** | Hybrid | 1. Connect to Postgres via `psql "postgresql://user:password@localhost:5432/erg_opera_data"` <br> 2. `\dt raw.*` | The `raw.booking_core_reservations` table is created correctly. |
| **Data Extraction** | Agent Probe | 1. Check `docker-compose logs extractor` for "Extraction process finished." <br> 2. Observe logs for the number of records fetched. | The extractor script runs to completion without errors. |
| **Data Loading** | Hybrid | 1. Run SQL in `psql`: `SELECT count(*) FROM raw.booking_core_reservations;` <br> 2. Run `SELECT raw_data->>'confirmationNo' FROM raw.booking_core_reservations LIMIT 5;` | Raw data is successfully loaded into the PostgreSQL database. The count should be > 0. |

## 5. Test Infra Improvement Notes

-   The current verification plan is now partially automated.
-   A mock server for the OPERA Cloud API is being used via `respx` for testing failure scenarios.
-   Database connection tests are being handled via `monkeypatch`.

## 6. Resume and Execution Handoff

-   **Selected Plan File Path:** `process/features/booking-core/active/booking-core-p1-extractor_13-07-26/booking-core-p1-extractor_PLAN_13-07-26.md`
-   **Last Completed Phase:** PLAN (this document)
-   **Validate Contract Status:** Pending. `vc-validate-agent` must run before EXECUTE.
-   **Supporting Context Files:**
    -   `process/features/booking-core/active/booking-core_SPEC_13-07-26.md`
    -   `process/context/all-context.md`
-   **Next Step:** Run `vc-validate-agent` to create the `Validate Contract` for this plan. After that, `ENTER EXECUTE MODE`.

## Validate Contract

Status: CONDITIONAL
Date: 13-07-26
date: 2026-07-13
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: Score 2/7 (S6, S7). The work is contained in a single new service, making a sequential approach efficient.

Test gates:
- Automated Tests: Fully-automated: `poetry run pytest`
- Build & Run: Hybrid: `docker-compose up --build -d` then `docker-compose logs -f extractor`
- Database Setup: Hybrid: Connect with `psql "postgresql://user:password@localhost:5432/erg_opera_data"` then run `\dt raw.*`
- Data Extraction: Agent-probe: Check `docker-compose logs extractor` for "Extraction process finished."
- Data Loading: Hybrid: Run SQL `SELECT count(*) FROM raw.booking_core_reservations;`

Dimension findings:
- Infra fit: PASS — Docker and Python configurations are standard and sound.
- Test coverage: PASS — The plan includes a reasonable mix of automated, hybrid, and probe-based tests.
- Breaking changes: PASS — This is a greenfield service and introduces no breaking changes.
- Security surface: PASS — Secrets are handled via `.env` and `pydantic-settings`, which is appropriate.
- Feasibility: PASS — All implementation steps are mechanically feasible and use standard libraries.

Open gaps:
- The plan relies on placeholder API endpoints and query parameters (e.g., `/res/v1/hotels/YOUR_HOTEL/reservations`). These will need to be replaced with actual values from the OPERA Cloud API documentation during implementation.
- The pagination logic in `src/client.py` is based on a common REST pattern but may need adjustment for OPERA Cloud's specific implementation.

What this coverage does NOT prove:
- Correctness of the actual API endpoint for reservations.
- Correctness of the API query parameters.
- The exact pagination mechanism used by OPERA Cloud.
- The full schema of the reservation data beyond the fields included in `src/models.py`.

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution)
- CONCERN: The structural plan validator script (`validate-plan-artifact.mjs`) failed with a file-not-found error, which may indicate a toolchain or pathing issue. The plan was validated manually.
- The plan contains placeholder values for API endpoints and parameters that must be resolved during execution.
