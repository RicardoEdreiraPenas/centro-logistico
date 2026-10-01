#!/bin/bash
set -e
exec > /var/log/user-data.log 2>&1

dnf install -y python3.11 git

git clone https://github.com/RicardoEdreiraPenas/Centro-Logistico.git /opt/logistics
chown -R ec2-user:ec2-user /opt/logistics

cd /opt/logistics
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cat > /etc/systemd/system/client-app.service << 'SVCEOF'
[Unit]
Description=Logistics client-app
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/logistics
Environment="RDS_HOST=${rds_host}"
Environment="RDS_PORT=${rds_port}"
Environment="RDS_DB=${rds_db}"
Environment="RDS_USER=${rds_user}"
Environment="RDS_PASSWORD=${rds_password}"
Environment="AWS_REGION=${sqs_region}"
Environment="CLIENT_API_PORT=8080"
Environment="ORDER_TTL_MINUTES=10"
ExecStart=/opt/logistics/.venv/bin/python -m client_app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable client-app
systemctl start client-app
