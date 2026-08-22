# Harbor-shaped task image: Dockerfile + instruction + test.
#
# The local harness runs the same task against SQLite with no container at
# all; this image is the path for the SkyRL/Harbor executor, where the agent
# gets a shell and the snapshot backend is an overlayfs upper dir rather than
# a directory copy.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends sqlite3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /task
COPY repo/ /task/repo/
COPY seed.sql task.json /task/

ENV TASK_DB=/task/db.sqlite
RUN sqlite3 "$TASK_DB" < /task/seed.sql

WORKDIR /task/repo
CMD ["python", "verify.py"]
