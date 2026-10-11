# Save as /opt/naveens-school/deploy/gunicorn/gunicorn.conf.py
# Workers: (2 x CPU cores) + 1 is the usual starting point; override with GUNICORN_WORKERS.
import multiprocessing
import os

bind = "0.0.0.0:8000"  # reachable only from the Nginx server (see UFW rule in the guide)
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = os.environ.get("NGINX_SERVER_IP", "127.0.0.1")
