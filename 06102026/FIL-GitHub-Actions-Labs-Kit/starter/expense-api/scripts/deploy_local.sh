#!/usr/bin/env bash
# Deploy the wheel in dist/ to a local "staging" folder and (re)start the service.
# Runs on a GitHub Actions runner (or any Linux/macOS shell with python3).
#
# Needs:  dist/expense_api-*.whl   (made by the Build stage)
#         JWT_SECRET                (injected from GitHub: env: JWT_SECRET: ${{ secrets.JWT_SECRET }})
set -euo pipefail

: "${JWT_SECRET:?JWT_SECRET is not set - add the secret and pass it with env: in the workflow}"
DEPLOY_DIR="${DEPLOY_DIR:-$HOME/staging/expense-api}"
APP_PORT="${APP_PORT:-8000}"
WHEEL="$(ls dist/expense_api-*.whl | head -n 1)"
echo ">> Deploying ${WHEEL} to ${DEPLOY_DIR} (port ${APP_PORT})"

mkdir -p "${DEPLOY_DIR}"

# 1) Stop the previous version (if it is running)
if [ -f "${DEPLOY_DIR}/app.pid" ] && kill -0 "$(cat "${DEPLOY_DIR}/app.pid")" 2>/dev/null; then
  echo ">> Stopping old version (pid $(cat "${DEPLOY_DIR}/app.pid"))"
  kill "$(cat "${DEPLOY_DIR}/app.pid")"
  sleep 2
fi

# 2) Fresh virtual environment with runtime dependencies + our wheel
rm -rf "${DEPLOY_DIR}/venv"
python3 -m venv "${DEPLOY_DIR}/venv"
"${DEPLOY_DIR}/venv/bin/pip" install -q --disable-pip-version-check -r requirements.txt
"${DEPLOY_DIR}/venv/bin/pip" install -q --disable-pip-version-check --no-deps "${WHEEL}"
cp seed/seed_data.json "${DEPLOY_DIR}/seed_data.json"
echo "${BUILD_NUMBER:-manual}" > "${DEPLOY_DIR}/DEPLOYED_BUILD"

# 3) Start in the background.
#    (JENKINS_NODE_COOKIE only matters on Jenkins; on GitHub the runner is discarded after the job.)
cd "${DEPLOY_DIR}"
JENKINS_NODE_COOKIE=dontKillMe \
APP_ENV=prod APP_PORT="${APP_PORT}" SEED_FILE="${DEPLOY_DIR}/seed_data.json" \
CORS_ALLOWED_ORIGINS="https://expenses.example.com" JWT_SECRET="${JWT_SECRET}" \
  nohup venv/bin/python -m app > app.log 2>&1 &
echo $! > app.pid
echo ">> Started pid $(cat app.pid); logs: ${DEPLOY_DIR}/app.log"
