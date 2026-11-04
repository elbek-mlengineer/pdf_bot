#!/usr/bin/env bash
# Run from the server checkout. An optional SHA identifies the tested main commit.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
exec 9>.git/deploy.lock
flock -w 300 9
target=${1:-}
if [[ -n "$target" ]]; then
    [[ "$target" =~ ^[0-9a-f]{40}$ ]]
    git fetch --quiet origin main
    if [[ "$(git rev-parse FETCH_HEAD)" != "$target" ]]; then
        echo "A newer main revision exists. Skipping superseded deployment."
        exit 0
    fi
    git merge --ff-only "$target"
fi
docker compose config --quiet
docker compose build
docker compose up -d --wait postgres redis
backup_dir="${BACKUP_DIR:-$HOME/pdfbot-backups}"
mkdir -p "$backup_dir"
backup=$(mktemp "$backup_dir/predeploy-XXXXXXXX.dump")
if ! docker compose exec -T postgres pg_dump -U pdfuser -Fc pdfbot > "$backup"; then
    echo "Database backup failed. Deployment stopped." >&2
    exit 1
fi
# The trusted local socket also permits upgrading installations with the former
# default password. No database password is printed or passed on the command line.
docker compose exec -T postgres psql -X -q -v ON_ERROR_STOP=1 -U pdfuser -d pdfbot <<'SQL'
\getenv new_password POSTGRES_PASSWORD
ALTER ROLE pdfuser PASSWORD :'new_password';
SQL
docker compose up -d --wait --wait-timeout 180
docker compose exec -T worker python -m app.converters.smoke
git rev-parse HEAD > .git/deployed-revision
