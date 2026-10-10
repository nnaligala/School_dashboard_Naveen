# Naveen's School

Django school-management platform: public website, role-based portal, Celery + RabbitMQ background jobs,
Memcached caching, PostgreSQL, Nginx + Gunicorn.

## What is built so far (Phase 1 + 2)

| Area | Status |
|---|---|
| Project layout, settings (dev / production / test), env-driven config | Done, tested |
| Custom email-login user, 10 roles, capability matrix, object-level checks | Done, tested |
| Login, logout (POST), password change/reset, forced change, lockout, login history | Done, tested |
| Audit log (append-only), retention task | Done, tested |
| Public website: home, about, principal's message, vision, academics, admissions, facilities, FAQ, privacy, terms, contact/enquiry, sitemap, robots | Done, tested |
| Celery queues with dead-lettering, email task with exponential backoff | Done, tested (eager mode) |
| Health endpoints `/healthz/` `/readyz/`, Prometheus `/metrics` | Done, tested |
| Docker Compose dev stack | Written, **not run** in the build sandbox |
| Nginx / Gunicorn / systemd / backup scripts | Written, **not run** in the build sandbox |
| Students, admissions workflow, staff, academics, attendance, exams, fees, library, transport, reports, portals | **Not built yet** (next phases) |

Automated tests: 45 passing, 95% coverage (`pytest`).

## Quick start (Docker)

```bash
cp .env.example .env
# Edit .env: set DJANGO_SECRET_KEY, DB_PASSWORD, RABBITMQ_PASSWORD
python3 -c "import secrets;print(secrets.token_urlsafe(64))"   # use this for DJANGO_SECRET_KEY

docker compose up -d --build
docker compose exec web python manage.py seed_demo               # prints demo password
docker compose exec web python manage.py createsuperuser
```

Open http://localhost:8080 (site), http://localhost:8080/accounts/login/ (portal),
http://localhost:8080/manage-site/admin/ (Django admin), http://localhost:8025 (Mailpit inbox),
http://localhost:15672 (RabbitMQ UI).

Demo logins: `school_admin@example.com`, `principal@example.com`, `teacher@example.com`, `accountant@example.com`,
`librarian@example.com`, `transport_manager@example.com`, `receptionist@example.com`, `student@example.com`,
`parent@example.com` (shared password printed by `seed_demo`).

Validate:

```bash
curl -s localhost:8080/healthz/     # {"status": "ok"}
curl -s localhost:8080/readyz/      # {"database":"ok","cache":"ok","broker":"ok"}
docker compose logs -f worker       # shows queues default,email,sms,reports,imports
```

Test background email: submit the Contact form, then open Mailpit and see the acknowledgement.

Stop / reset:

```bash
docker compose stop            # stop
docker compose down            # remove containers, keep data
docker compose down -v         # RESET everything (destroys DB, queues, media)
docker compose up -d --build   # rebuild
```

## Run tests (no Docker needed)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
pytest
ruff check .
```

Tests use SQLite and in-memory cache for speed. Run against PostgreSQL in CI before release.

## Production on separate Ubuntu 24.04 servers

Create the environment file on every app/worker server at `/etc/naveens-school.env` (mode 600), based on `.env.example`,
with `DJANGO_SETTINGS_MODULE=config.settings.production` and **real private IPs/hostnames** (production settings refuse
`localhost`). Add `NGINX_SERVER_IP=<nginx server private IP>`.

1. **PostgreSQL server**
   ```bash
   sudo apt update && sudo apt install -y postgresql
   sudo -u postgres psql -c "CREATE USER naveens_app WITH PASSWORD 'STRONG_PASSWORD';"
   sudo -u postgres psql -c "CREATE DATABASE naveens_school OWNER naveens_app;"
   ```
   Edit `postgresql.conf`: `listen_addresses = '<private IP>'`; add to `pg_hba.conf`:
   `host naveens_school naveens_app <app-subnet>/24 scram-sha-256`. Then `sudo systemctl restart postgresql`.
2. **RabbitMQ server**
   ```bash
   sudo apt install -y rabbitmq-server
   sudo rabbitmqctl add_vhost naveens_vhost
   sudo rabbitmqctl add_user naveens 'STRONG_PASSWORD'
   sudo rabbitmqctl set_permissions -p naveens_vhost naveens ".*" ".*" ".*"
   ```
3. **Memcached server**: `sudo apt install -y memcached`; in `/etc/memcached.conf` set `-l <private IP>`; restart.
   Allow port 11211 only from app/worker servers (UFW).
4. **App servers (x2)**
   ```bash
   sudo useradd -r -m -d /opt/naveens-school naveens
   sudo apt install -y python3-venv git
   sudo -u naveens git clone <your-repo-url> /opt/naveens-school
   cd /opt/naveens-school && sudo -u naveens python3 -m venv .venv
   sudo -u naveens .venv/bin/pip install -r requirements/prod.txt
   set -a; source /etc/naveens-school.env; set +a
   sudo -E -u naveens .venv/bin/python manage.py migrate        # on ONE server only
   sudo -E -u naveens .venv/bin/python manage.py collectstatic --noinput
   sudo cp deploy/systemd/naveens-gunicorn.service /etc/systemd/system/
   sudo systemctl daemon-reload && sudo systemctl enable --now naveens-gunicorn
   curl -s http://127.0.0.1:8000/healthz/
   ```
5. **Worker server**: same checkout/venv, then copy `naveens-celery.service` and `naveens-celerybeat.service`;
   `sudo systemctl enable --now naveens-celery naveens-celerybeat`. Run Beat on one server only.
6. **Nginx server**: `sudo apt install -y nginx certbot`; copy `deploy/nginx/naveens-school.conf` to
   `/etc/nginx/sites-available/`, `deploy/nginx/naveens-proxy.conf` to `/etc/nginx/snippets/`; replace `APP1_PRIVATE_IP`,
   `APP2_PRIVATE_IP`, and `school.example.com`; put the two `limit_req_zone` lines in `/etc/nginx/conf.d/rate.conf`.
   Obtain a certificate (`sudo certbot certonly --webroot -w /var/www/certbot -d school.example.com`), then
   `sudo nginx -t && sudo systemctl reload nginx`.
7. **Media on multiple servers**: uploaded files will need shared storage (NFS or object storage) once upload features
   are added in later phases. Phase 1-2 has no uploads.
8. **Backups**: install `deploy/backup/backup_db.sh` on the DB server and schedule it nightly; test
   `restore_db.sh` into a scratch database monthly.

Logs: `journalctl -u naveens-gunicorn -f`, `journalctl -u naveens-celery -f`, `/var/log/nginx/naveens.*.log`.
Rollback an app deploy: `git checkout <previous-tag>`, `pip install -r requirements/prod.txt`,
`sudo systemctl restart naveens-gunicorn` (take a database backup before any migration).

## Caveats

* Exact patch versions in `requirements/` installed successfully at build time; run `pip-audit` before deploying.
* Bootstrap is loaded from the jsDelivr CDN without SRI hashes; vendor it locally for strict environments.
* Docker/Nginx/systemd/backup files have not been executed by the author; treat the first run as validation.
