#!/bin/sh
set -eu

API_URL="${API_URL:-https://uddiejez3g.us-east-1.awsapprunner.com}"

cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = { API_URL: "${API_URL}" };
EOF

exec nginx -g "daemon off;"