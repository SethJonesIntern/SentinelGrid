#!/bin/sh
set -eu

API_URL="${API_URL:-http://localhost:8000}"

cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = { API_URL: "${API_URL}" };
EOF

exec nginx -g "daemon off;"