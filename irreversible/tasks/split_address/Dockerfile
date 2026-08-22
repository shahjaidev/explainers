# Harbor-shaped task image: Dockerfile + instruction + test.
#
# Two backends, one image. With no environment set the task runs against a
# SQLite file, which is what the local harness uses. Set TASK_DSN and the same
# repo code talks to Postgres through `psql` — see tasks/_shared/taskdb.py.
# Nothing in the task is backend-specific; the schema questions that are
# (which columns, which unique indexes) live behind taskdb.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends sqlite3 postgresql-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /task
COPY repo/ /task/repo/
COPY seed.sql task.json /task/

ENV TASK_DB=/task/db.sqlite
RUN sqlite3 "$TASK_DB" < /task/seed.sql

WORKDIR /task/repo
CMD ["python", "verify.py"]
