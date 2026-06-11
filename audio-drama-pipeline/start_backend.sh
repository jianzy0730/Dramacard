#!/usr/bin/env bash
set -euo pipefail

cd /home/gyfy/桌面/短剧/audio-drama-pipeline
source /home/gyfy/桌面/短剧/video-audit-platform/.venv/bin/activate
python -m audio_drama_pipeline
