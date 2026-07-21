# Hướng dẫn Triển khai Production

**Stack:** Ubuntu 22.04 · Docker · PostgreSQL native · Nginx native  
**Môi trường dev:** Windows + Docker Desktop (giữ nguyên `docker-compose.yml`)

---

## Architecture

```
Internet
    │
    ▼
Nginx (native, port 80/443)
    │  reverse proxy
    ▼
Dashboard container (127.0.0.1:8501)
    │
    ├──────────────────────────────┐
    │                              │
    ▼                              ▼
PostgreSQL native (port 5432)   Extractor container
    ▲                             (one-shot, cron 2AM)
    │                              │
    └──────────────────────────────┘
              │
    dbt (native venv, cron 3AM)
              │
              ▼
    analytics.* tables
```

**Dev vs Prod:**

| | Dev (Windows) | Prod (Ubuntu) |
|---|---|---|
| Compose file | `docker-compose.yml` | `docker-compose.prod.yml` |
| PostgreSQL | Container (port 5434) | Native (port 5432) |
| Dashboard port | 8502 (external) | 127.0.0.1:8501 (Nginx proxy) |
| Extractor | Manual / `docker compose run` | Cron job 2:00 AM |
| dbt | Manual | Cron job 3:00 AM |

---

## Files triển khai

```
docker-compose.prod.yml          ← compose file cho production
extractor/.env.prod.example      ← template env extractor (copy → .env.prod)
dashboard/.env.prod.example      ← template env dashboard (copy → .env.prod)
deploy/
  nginx/eras-dashboard.conf      ← nginx config
  scripts/
    run-extractor.sh             ← cron wrapper extractor
    run-dbt.sh                   ← cron wrapper dbt
    cleanup-logs.sh              ← dọn log cũ
```

---

## Phần 1 — Chuẩn bị server (chạy một lần)

### 1.1. SSH vào server

```bash
ssh your-user@your-server-ip
```

### 1.2. Cài Docker

```bash
# Cài dependencies
sudo apt update
sudo apt install -y ca-certificates curl gnupg

# Thêm Docker GPG key và repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Cài Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Cho phép user hiện tại dùng Docker không cần sudo
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 1.3. Cài Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 1.4. Kiểm tra PostgreSQL đang chạy

```bash
sudo systemctl status postgresql

# Nếu chưa cài:
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 1.5. Tạo PostgreSQL user và database cho project

```bash
sudo -u postgres psql
```

Trong psql console:

```sql
CREATE USER eras_user WITH PASSWORD 'your_strong_password_here';
CREATE DATABASE erg_opera_data OWNER eras_user;
GRANT ALL PRIVILEGES ON DATABASE erg_opera_data TO eras_user;

-- PostgreSQL 15+: grant schema permissions
\c erg_opera_data
GRANT ALL ON SCHEMA public TO eras_user;

\q
```

### 1.6. Cho phép PostgreSQL nhận connection từ Docker containers

Docker containers kết nối vào PostgreSQL native qua `host.docker.internal` (IP: 172.17.0.1). Cần cho phép địa chỉ này trong PostgreSQL config.

```bash
# Tìm file pg_hba.conf
sudo -u postgres psql -c "SHOW hba_file;"
# Thường là: /etc/postgresql/15/main/pg_hba.conf

sudo nano /etc/postgresql/15/main/pg_hba.conf
```

Thêm dòng này (sau các dòng local hiện có):

```
# Docker containers (host.docker.internal)
host    erg_opera_data  eras_user   172.17.0.0/16   md5
```

```bash
# Restart PostgreSQL để áp dụng
sudo systemctl restart postgresql

# Test connection
psql -h 127.0.0.1 -U eras_user -d erg_opera_data -c "SELECT 1;"
```

---

## Phần 2 — Deploy code

### 2.1. Clone repo

```bash
sudo mkdir -p /opt/eras-opera
sudo chown $USER:$USER /opt/eras-opera
cd /opt/eras-opera

git clone YOUR_GIT_REPO_URL .
```

### 2.2. Cấu hình environment files

**Extractor:**

```bash
cp extractor/.env.prod.example extractor/.env.prod
nano extractor/.env.prod
```

Điền đầy đủ credentials OPERA và thông tin PostgreSQL:

```ini
# Giữ nguyên OPERA credentials từ .env dev
OPERA_CLIENT_ID=79017BW-Production-...
# ...

# Sửa DATABASE_URL — dùng host.docker.internal thay vì postgres
POSTGRES_USER=eras_user
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=erg_opera_data
DATABASE_URL=postgresql://eras_user:your_strong_password_here@host.docker.internal:5432/erg_opera_data
```

**Dashboard:**

```bash
cp dashboard/.env.prod.example dashboard/.env.prod
nano dashboard/.env.prod
```

```ini
DATABASE_URL=postgresql://eras_user:your_strong_password_here@host.docker.internal:5432/erg_opera_data
```

**Permissions — bảo vệ secrets:**

```bash
chmod 600 extractor/.env.prod
chmod 600 dashboard/.env.prod
```

### 2.3. Cấu hình dbt profiles cho production

```bash
nano eras_dbt/profiles.yml
```

Thêm target `prod` (giữ nguyên `dev`, thêm bên dưới):

```yaml
eras_dbt:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: user
      password: "password"
      port: 5434
      dbname: erg_opera_data
      schema: analytics
      threads: 4
      keepalives_idle: 0
      connect_timeout: 10
      retries: 1
      sslmode: disable

    prod:
      type: postgres
      host: localhost        # dbt chạy native trên server, dùng localhost
      user: eras_user
      password: "your_strong_password_here"
      port: 5432             # PostgreSQL native port
      dbname: erg_opera_data
      schema: analytics
      threads: 4
      keepalives_idle: 0
      connect_timeout: 10
      retries: 1
      application_name: dbt_prod
      sslmode: disable
```

### 2.4. Cài dbt (native trên server)

```bash
cd /opt/eras-opera/eras_dbt

# Tạo virtualenv riêng cho dbt
python3 -m venv venv
source venv/bin/activate
pip install dbt-core dbt-postgres
dbt --version
deactivate
```

---

## Phần 3 — Build và khởi động containers

### 3.1. Build images

```bash
cd /opt/eras-opera

# Build cả 2 images
docker compose -f docker-compose.prod.yml build
```

### 3.2. Khởi động Dashboard

```bash
docker compose -f docker-compose.prod.yml up -d dashboard

# Kiểm tra đang chạy
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs dashboard
```

### 3.3. Test extractor chạy thủ công lần đầu

Chạy extractor one-shot để backfill data từ đầu năm:

```bash
# Backfill toàn bộ Jan–Jul 2026
docker compose -f docker-compose.prod.yml run --rm extractor \
  python -m src 2026-01-01 2026-07-21
```

Theo dõi output trực tiếp — chờ đến khi in `Extraction process finished.`

### 3.4. Chạy dbt lần đầu

```bash
cd /opt/eras-opera/eras_dbt
source venv/bin/activate
dbt run --target prod
dbt test --target prod
deactivate
```

### 3.5. Verify data trong PostgreSQL

```bash
psql -h localhost -U eras_user -d erg_opera_data -c "
SELECT
  (SELECT COUNT(*) FROM raw.booking_core_reservations) AS reservations,
  (SELECT COUNT(*) FROM raw.cashiering_postings)       AS postings,
  (SELECT COUNT(*) FROM analytics.fct_reservation_night) AS res_nights,
  (SELECT COUNT(*) FROM analytics.fct_folio_line)      AS folio_lines;
"
```

### 3.6. Test dashboard trước khi expose

```bash
# Kiểm tra dashboard trả HTTP 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501
# Kết quả mong đợi: 200
```

---

## Phần 4 — Cài đặt Nginx

### 4.1. Copy nginx config

```bash
sudo cp /opt/eras-opera/deploy/nginx/eras-dashboard.conf \
        /etc/nginx/sites-available/eras-dashboard
```

### 4.2. Sửa domain trong config

```bash
sudo nano /etc/nginx/sites-available/eras-dashboard
```

Sửa dòng `server_name`:

```nginx
server_name your-actual-domain.com;   # hoặc IP public nếu chưa có domain
```

### 4.3. Enable site và reload Nginx

```bash
sudo ln -s /etc/nginx/sites-available/eras-dashboard \
           /etc/nginx/sites-enabled/eras-dashboard

# Xóa default site nếu cần
sudo rm -f /etc/nginx/sites-enabled/default

# Kiểm tra config hợp lệ
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### 4.4. Truy cập dashboard

Mở trình duyệt: `http://your-domain.com`

Dashboard hiển thị → **thành công**.

### 4.5. (Khuyến nghị) Cài SSL với Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Auto-renew — certbot tự thêm cron, kiểm tra:
sudo certbot renew --dry-run
```

Sau khi cài SSL, dashboard truy cập qua `https://your-domain.com`.

---

## Phần 5 — Automation với Cron

### 5.1. Copy scripts

```bash
sudo cp /opt/eras-opera/deploy/scripts/run-extractor.sh /opt/eras-opera/
sudo cp /opt/eras-opera/deploy/scripts/run-dbt.sh       /opt/eras-opera/
sudo cp /opt/eras-opera/deploy/scripts/cleanup-logs.sh  /opt/eras-opera/

sudo chmod +x /opt/eras-opera/run-extractor.sh
sudo chmod +x /opt/eras-opera/run-dbt.sh
sudo chmod +x /opt/eras-opera/cleanup-logs.sh
```

### 5.2. Tạo log directory

```bash
sudo mkdir -p /var/log/eras-opera
sudo chown $USER:$USER /var/log/eras-opera
```

### 5.3. Cấu hình cron jobs

```bash
crontab -e
```

Thêm các dòng:

```cron
# Eras Opera — Extract data từ OPERA API mỗi ngày lúc 2:00 AM
0 2 * * * /opt/eras-opera/run-extractor.sh >> /var/log/eras-opera/cron.log 2>&1

# Eras Opera — dbt transformation mỗi ngày lúc 3:00 AM (sau extract xong)
0 3 * * * /opt/eras-opera/run-dbt.sh >> /var/log/eras-opera/cron.log 2>&1

# Eras Opera — Cleanup logs cũ hơn 30 ngày, mỗi Chủ nhật 4:00 AM
0 4 * * 0 /opt/eras-opera/cleanup-logs.sh >> /var/log/eras-opera/cron.log 2>&1
```

Lưu và verify:

```bash
crontab -l
```

---

## Phần 6 — Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # port 80 và 443
sudo ufw enable
sudo ufw status
```

**Lưu ý:** PostgreSQL (5432) và Dashboard (8501) **không** mở ra ngoài — chỉ accessible nội bộ qua Nginx.

---

## Phần 7 — Update code (routine)

Mỗi khi có thay đổi code trên git:

```bash
cd /opt/eras-opera

# Pull code mới
git pull origin main

# Rebuild và restart dashboard
docker compose -f docker-compose.prod.yml build dashboard
docker compose -f docker-compose.prod.yml up -d dashboard

# Nếu dbt models thay đổi, chạy lại dbt
cd eras_dbt
source venv/bin/activate
dbt run --target prod
deactivate
```

---

## Monitoring & Troubleshooting

### Xem logs dashboard

```bash
# Container logs (real-time)
docker compose -f /opt/eras-opera/docker-compose.prod.yml logs -f dashboard

# Nginx access/error logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Xem logs extractor và dbt

```bash
# Log files được tạo tự động bởi scripts
ls -lt /var/log/eras-opera/

# Xem log mới nhất của extractor
ls /var/log/eras-opera/extractor-*.log | tail -1 | xargs tail -50

# Xem log mới nhất của dbt
ls /var/log/eras-opera/dbt-*.log | tail -1 | xargs tail -50

# Theo dõi cron log
tail -f /var/log/eras-opera/cron.log
```

### Quick status check

```bash
# Container status
docker compose -f /opt/eras-opera/docker-compose.prod.yml ps

# PostgreSQL
sudo systemctl status postgresql

# Nginx
sudo systemctl status nginx

# Dashboard accessible?
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8501
```

### Vấn đề thường gặp

**Dashboard không lên sau deploy:**

```bash
docker compose -f /opt/eras-opera/docker-compose.prod.yml logs dashboard
# Thường do .env.prod thiếu biến hoặc sai DATABASE_URL
```

**Extractor lỗi "connection refused":**

```bash
# Kiểm tra PostgreSQL cho phép connection từ Docker
psql -h 172.17.0.1 -U eras_user -d erg_opera_data -c "SELECT 1;"
# Nếu fail → kiểm tra lại pg_hba.conf (Phần 1.6)
```

**Nginx 502 Bad Gateway:**

```bash
# Dashboard container có đang chạy không?
docker compose -f /opt/eras-opera/docker-compose.prod.yml ps
# Nếu không → restart
docker compose -f /opt/eras-opera/docker-compose.prod.yml up -d dashboard
```

**dbt "connection refused":**

```bash
cd /opt/eras-opera/eras_dbt
source venv/bin/activate
dbt debug --target prod   # sẽ show chi tiết lỗi connection
deactivate
```

---

## Checklist Deploy

### Chuẩn bị server
- [ ] Docker cài đặt, user trong group `docker`
- [ ] Nginx cài đặt và running
- [ ] PostgreSQL native running
- [ ] Database `erg_opera_data` và user `eras_user` đã tạo
- [ ] `pg_hba.conf` cho phép `172.17.0.0/16`

### Code & Config
- [ ] Repo cloned vào `/opt/eras-opera`
- [ ] `extractor/.env.prod` tạo từ example, điền đầy đủ
- [ ] `dashboard/.env.prod` tạo từ example, điền đầy đủ
- [ ] `eras_dbt/profiles.yml` có target `prod` với đúng credentials
- [ ] `chmod 600` cho cả 2 `.env.prod` files

### Containers & Data
- [ ] `docker compose -f docker-compose.prod.yml build` thành công
- [ ] Dashboard container running (`docker compose ps`)
- [ ] Extractor backfill chạy thành công (manual lần đầu)
- [ ] dbt run + test thành công
- [ ] Data có trong PostgreSQL (verify query Phần 3.5)

### Nginx & Access
- [ ] Nginx config copy và `server_name` đã sửa
- [ ] `sudo nginx -t` không có lỗi
- [ ] Dashboard accessible qua browser `http://your-domain.com`
- [ ] (Optional) SSL certificate cài xong, accessible qua `https://`

### Automation
- [ ] Scripts copy vào `/opt/eras-opera/` và `chmod +x`
- [ ] Log directory `/var/log/eras-opera/` tạo xong
- [ ] Cron jobs configured (`crontab -l` verify)
- [ ] Firewall UFW enabled, chỉ mở SSH + Nginx

---

## Cấu trúc files deploy

```
/opt/eras-opera/
├── docker-compose.prod.yml
├── run-extractor.sh          ← từ deploy/scripts/
├── run-dbt.sh                ← từ deploy/scripts/
├── cleanup-logs.sh           ← từ deploy/scripts/
├── extractor/
│   ├── .env.prod             ← KHÔNG có trong git
│   └── ...
├── dashboard/
│   ├── .env.prod             ← KHÔNG có trong git
│   └── ...
└── eras_dbt/
    ├── profiles.yml          ← có target prod
    ├── venv/                 ← dbt virtualenv
    └── ...

/var/log/eras-opera/
├── cron.log
├── extractor-20260721-020000.log
├── dbt-20260721-030000.log
└── ...
```
