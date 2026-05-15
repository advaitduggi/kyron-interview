#!/usr/bin/env bash
set -e

# Build frontend
cd frontend
npm ci
npm run build
sudo cp -r dist /var/www/kyron/

# Restart backend
cd ../backend
pip install -r requirements.txt
sudo systemctl restart kyron-backend

# Reload nginx
sudo systemctl reload nginx
