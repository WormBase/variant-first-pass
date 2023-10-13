#!/usr/bin/env bash

declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /container.env
chmod 0644 /etc/cron.d/vfp-cron
touch /var/log/vfp_pipeline.log
crontab /etc/cron.d/vfp-cron
cron

tail -f /dev/null