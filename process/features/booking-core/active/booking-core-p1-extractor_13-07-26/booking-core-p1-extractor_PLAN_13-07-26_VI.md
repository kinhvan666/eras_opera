# Kế hoạch: Booking Core - Giai đoạn 1 Trình trích xuất dữ liệu

**Ngày:** 13-07-26
**Tính năng:** booking-core
**Giai đoạn:** 1 trên 3 (Trình trích xuất dữ liệu)
**Trạng thái:** BẢN NHÁP

## 1. Tổng quan & Mục tiêu

Tài liệu này phác thảo kế hoạch kỹ thuật chi tiết để triển khai Giai đoạn 1 của tính năng `booking-core`: tạo một trình trích xuất dữ liệu dựa trên Python mạnh mẽ cho Oracle OPERA Cloud.

Mục tiêu chính là xây dựng một dịch vụ có thể:
1.  Xác thực với API của OPERA Cloud.
2.  Trích xuất dữ liệu đặt phòng và hồ sơ liên quan.
3.  Xử lý phân trang API và giới hạn tốc độ một cách mượt mà.
4.  Tải dữ liệu JSON thô, chưa sửa đổi vào một bảng staging trong cơ sở dữ liệu PostgreSQL.

Kế hoạch này được thiết kế để một agent hoặc nhà phát triển khác thực thi mà không có sự mơ hồ nào. Tất cả nội dung tệp, lệnh và các bước xác minh đều được định nghĩa rõ ràng.

## 2. Điểm tiếp xúc & Vùng ảnh hưởng

-   **Điểm tiếp xúc:**
    -   Đây là một dự án hoàn toàn mới, vì vậy tất cả các tệp được tạo sẽ là mới. Sẽ không có mã hiện có nào được sửa đổi.
    -   Thư mục mới: `src/`, `src/extractors`
    -   Tệp mới: `src/client.py`, `src/config.py`, `src/database.py`, `src/extractors/reservations.py`, `src/main.py`, `src/models.py`, `Dockerfile`, `docker-compose.yml`, `.env`, `pyproject.toml`
-   **Hợp đồng công khai (Public Contracts):**
    -   Dịch vụ này sẽ không tự cung cấp API công khai nào.
    -   "Hợp đồng công khai" của nó là dữ liệu nó ghi vào bảng `raw.booking_core_reservations` trong PostgreSQL. Schema cho bảng này rất đơn giản: một ID, một dấu thời gian và một cột `jsonb` cho dữ liệu thô.
-   **Vùng ảnh hưởng (Blast Radius):**
    -   Phạm vi được chứa hoàn toàn trong dịch vụ Python mới và môi trường Docker tương ứng của nó.
    -   Nó sẽ tương tác với cơ sở dữ liệu PostgreSQL bằng cách ghi vào một schema mới, biệt lập (`raw`).
    -   Phân loại rủi ro: Thấp. Là một trình trích xuất chỉ đọc ghi vào một bảng staging mới, nó không có tác động đến các hệ thống hiện có.

## 3. Danh sách kiểm tra triển khai

### Giai đoạn 3.1: Thiết lập dự án

1.  **Tạo cấu trúc thư mục dự án:**
    ```bash
    mkdir -p src/extractors
    touch src/__init__.py src/client.py src/config.py src/database.py src/main.py src/models.py src/extractors/__init__.py src/extractors/reservations.py
    ```

2.  **Khởi tạo dự án Poetry và thêm các dependency:**
    ```bash
    # Đảm bảo bạn đang ở thư mục gốc của dự án ErasOpera
    poetry init --name "opera-extractor" --python "^3.11" -n
    poetry add httpx pydantic pydantic-settings tenacity psycopg2-binary python-dotenv
    ```
    Lệnh này sẽ tạo ra tệp `pyproject.toml`.

3.  **Tạo `Dockerfile`:**
    ```dockerfile
    # syntax=docker/dockerfile:1

    # Sử dụng một runtime Python chính thức làm image cha
    FROM python:3.11-slim

    # Đặt thư mục làm việc trong container
    WORKDIR /app

    # Cài đặt poetry
    RUN pip install poetry

    # Chỉ sao chép các tệp cần thiết để cài đặt dependency
    COPY pyproject.toml poetry.lock* ./

    # Cài đặt các dependency
    RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

    # Sao chép phần còn lại của mã nguồn ứng dụng
    COPY src/ ./src/

    # Lệnh để chạy ứng dụng
    CMD ["python", "src/main.py"]
    ```

4.  **Tạo `docker-compose.yml`:**
    ```yaml
    version: '3.8'

    services:
      db:
        image: postgres:15
        container_name: opera_db
        environment:
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
          POSTGRES_DB: opera_data
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

### Giai đoạn 3.2: Cấu hình

1.  **Tạo tệp `.env`:** (Thêm tệp này vào `.gitignore` nếu chưa có)
    ```dotenv
    # .env
    # --- Thông tin xác thực API OPERA Cloud ---
    OPERA_CLIENT_ID="your_client_id"
    OPERA_CLIENT_SECRET="your_client_secret"
    OPERA_APP_KEY="your_app_key"
    OPERA_BASE_URL="https://api.cloud.opera.com"
    OPERA_TOKEN_URL="https://api.cloud.opera.com/token" # Ví dụ, xác nhận lại URL chính xác
    OPERA_HOTEL_ID="your_hotel_id"

    # --- Cơ sở dữ liệu PostgreSQL ---
    DATABASE_URL="postgresql://user:password@db:5432/opera_data"
    ```

2.  **Tạo `src/config.py`:**
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

### Giai đoạn 3.3: Triển khai trình trích xuất

1.  **Tạo `src/models.py`:**
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
        # Thêm các trường đặt phòng liên quan khác từ SPEC khi cần thiết
    ```

2.  **Tạo `src/client.py`:**
    ```python
    # src/client.py
    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential
    from typing import Optional, List, Dict, Any

    from .config import settings

    class BaseOperaClient:
        def __init__(self):
            self._session = httpx.AsyncClient(base_url=settings.opera_base_url)
            self._token: Optional[str] = None

        async def _get_token(self) -> str:
            """Lấy một token OAuth từ OPERA Cloud."""
            if self._token:
                # Trong kịch bản thực tế, bạn sẽ kiểm tra hạn của token.
                # Đối với giai đoạn này, chúng ta chỉ lấy một lần.
                return self._token

            auth_data = {
                "grant_type": "client_credentials",
                "client_id": settings.opera_client_id,
                "client_secret": settings.opera_client_secret,
            }
            headers = {"x-app-key": settings.opera_app_key}
            
            response = await self._session.post(settings.opera_token_url, data=auth_data, headers=headers)
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token

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
            """Lấy tất cả các trang từ một endpoint có phân trang cho trước."""
            if not self._token:
                await self._set_auth_headers()

            all_results = []
            
            response = await self._session.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cấu trúc của payload phản hồi cần được xác nhận từ tài liệu API.
            # Đây là một mẫu phổ biến.
            items_key = next((key for key in data if isinstance(data.get(key), list)), None)
            if items_key:
                all_results.extend(data[items_key])

            # Logic phân trang dựa trên liên kết 'next' trong headers, một mẫu REST phổ biến.
            # Điều này có thể cần điều chỉnh dựa trên cách triển khai phân trang cụ thể của OPERA Cloud.
            while 'next' in response.links:
                next_url = response.links['next']['url']
                response = await self._session.get(next_url)
                response.raise_for_status()
                data = response.json()
                if items_key:
                    all_results.extend(data[items_key])
            
            return all_results
    ```

3.  **Tạo `src/extractors/reservations.py`:**
    ```python
    # src/extractors/reservations.py
    from typing import List
    from ..client import BaseOperaClient
    from ..models import Reservation

    class ReservationExtractor:
        def __init__(self, client: BaseOperaClient):
            self.client = client

        async def fetch_recent_reservations(self) -> List[dict]:
            """Lấy các đặt phòng được tạo trong ngày gần nhất."""
            # Endpoint và params cần được xác nhận từ tài liệu API của OPERA Cloud.
            # Ví dụ về endpoint và params:
            endpoint = "/res/v1/hotels/YOUR_HOTEL/reservations" 
            params = {
                "query": "createDate=ge:$(SYSDATE-1)",
                "limit": 100
            }
            
            raw_reservations = await self.client.fetch_all(endpoint=endpoint, params=params)
            
            # Đối với giai đoạn này, chúng ta trả về các dict thô. Việc xác thực bằng Pydantic có thể được thêm vào sau.
            # validated_reservations = [Reservation.model_validate(res) for res in raw_reservations]
            return raw_reservations
    ```

4.  **Tạo `src/database.py`:**
    ```python
    # src/database.py
    import psycopg2
    import psycopg2.extras
    import json
    from .config import settings

    class Database:
        def __init__(self):
            self.conn = psycopg2.connect(settings.database_url)

        def setup(self):
            """Tạo schema và các bảng cần thiết."""
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
            """Chèn một danh sách các đối tượng JSON thô vào cơ sở dữ liệu."""
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

5.  **Tạo `src/main.py`:**
    ```python
    # src/main.py
    import asyncio
    from .client import BaseOperaClient
    from .extractors.reservations import ReservationExtractor
    from .database import Database

    async def main():
        print("Bắt đầu quá trình trích xuất dữ liệu...")
        
        # Khởi tạo Cơ sở dữ liệu và thiết lập schema/bảng
        db = Database()
        print("Thiết lập schema và bảng cơ sở dữ liệu...")
        db.setup()
        
        # Khởi tạo client API và trình trích xuất
        opera_client = BaseOperaClient()
        reservation_extractor = ReservationExtractor(opera_client)

        # Lấy dữ liệu
        print("Đang lấy các đặt phòng gần đây...")
        reservations_data = await reservation_extractor.fetch_recent_reservations()
        print(f"Đã lấy được {len(reservations_data)} đặt phòng.")

        # Chèn dữ liệu vào cơ sở dữ liệu
        if reservations_data:
            print("Đang chèn dữ liệu vào PostgreSQL...")
            db.insert_raw_data(reservations_data)
            print("Hoàn tất việc chèn dữ liệu.")
        
        # Dọn dẹp
        db.close()
        print("Quá trình trích xuất đã kết thúc.")

    if __name__ == "__main__":
        asyncio.run(main())
    ```

## 4. Xác minh & Bằng chứng

Phần này phác thảo cách xác minh việc triển khai kế hoạch thành công.

| Cổng / Kịch bản | Chiến lược | Lệnh / Các bước | Chứng minh tiêu chí SPEC |
|---|---|---|---|
| **Xây dựng & Chạy** | Hybrid (Lai) | 1. `docker-compose up --build -d` <br> 2. `docker-compose logs -f extractor` | Môi trường ứng dụng có thể được xây dựng và khởi động thành công. |
| **Thiết lập CSDL** | Hybrid (Lai) | 1. Kết nối đến Postgres qua `psql "postgresql://user:password@localhost:5432/opera_data"` <br> 2. `\dt raw.*` | Bảng `raw.booking_core_reservations` được tạo chính xác. |
| **Trích xuất dữ liệu** | Agent Probe (Agent thăm dò) | 1. Kiểm tra `docker-compose logs extractor` để tìm "Extraction process finished." <br> 2. Quan sát logs để biết số lượng bản ghi đã lấy. | Kịch bản trích xuất chạy đến khi hoàn thành mà không có lỗi. |
| **Tải dữ liệu** | Hybrid (Lai) | 1. Chạy SQL trong `psql`: `SELECT count(*) FROM raw.booking_core_reservations;` <br> 2. Chạy `SELECT raw_data->>'confirmationNo' FROM raw.booking_core_reservations LIMIT 5;` | Dữ liệu thô được tải thành công vào cơ sở dữ liệu PostgreSQL. Số lượng phải > 0. |

## 5. Ghi chú cải thiện hạ tầng kiểm thử

-   Kế hoạch xác minh hiện tại là thủ công. Các giai đoạn sau nên giới thiệu kiểm thử tự động bằng `pytest`.
-   Một máy chủ giả lập cho API của OPERA Cloud sẽ hữu ích cho việc kiểm thử logic của client và trình trích xuất mà không cần gọi đến API thật.
-   Các kiểm thử cơ sở dữ liệu nên được thêm vào để chạy trên một cơ sở dữ liệu thử nghiệm, đảm bảo tính toàn vẹn và chuyển đổi dữ liệu (trong các giai đoạn sau).

## 6. Tiếp tục và Bàn giao thực thi

-   **Đường dẫn tệp kế hoạch đã chọn:** `process/features/booking-core/active/booking-core-p1-extractor_13-07-26/booking-core-p1-extractor_PLAN_13-07-26.md`
-   **Giai đoạn hoàn thành gần nhất:** PLAN (tài liệu này)
-   **Trạng thái Hợp đồng xác thực:** Đang chờ. `vc-validate-agent` phải chạy trước khi EXECUTE.
-   **Các tệp ngữ cảnh hỗ trợ:**
    -   `process/features/booking-core/active/booking-core_SPEC_13-07-26.md`
    -   `process/context/all-context.md`
-   **Bước tiếp theo:** Chạy `vc-validate-agent` để tạo `Hợp đồng xác thực` cho kế hoạch này. Sau đó, `ENTER EXECUTE MODE`.

## 7. Hợp đồng xác thực

(phần giữ chỗ — `vc-validate-agent` sẽ viết phần này trước khi EXECUTE)
