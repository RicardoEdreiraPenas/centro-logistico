#!/bin/bash
set -e
exec > /var/log/user-data.log 2>&1

dnf install -y docker
systemctl enable docker
systemctl start docker

docker run -d \
  --name metabase \
  --restart always \
  -p 3000:3000 \
  metabase/metabase:v0.44.6
