# DramaCard Technical Overview

This repository is an open-source-safe snapshot of the DramaCard project. It keeps the application and pipeline logic, but removes private datasets, video/audio assets, generated outputs, model weights, build artifacts, APKs, local IDE files, and real cloud storage URLs.

## Modules

- `android-client/`: Android client for episode playback, highlight-card collection, ending-choice interaction, voting, profile state, and local persistence.
- `demo/`: command-line video analysis pipeline for timelines, OCR, story segmentation, highlight detection, and ending-choice prompt generation.
- `video-audit-platform/`: Flask-based review/audit platform and model-service integration code.
- `audio-drama-pipeline/`: lightweight audio-drama backend and UI prototype.

## Removed From The Public Copy

- Raw drama videos and audio files.
- Generated frames, cards, comics, OCR outputs, and reports.
- Model weights and local virtual environments.
- Real cloud bucket names and private CDN/COS URLs.
- `.env`, `local.properties`, APKs, zip archives, IDE cache files, and Gradle build outputs.

## Configuration Pattern

Use `.env.example` files as templates. Do not commit real API keys or secrets.

For Android media playback and card images, replace the placeholder asset base URL in:

- `android-client/app/src/main/java/com/dramacard/client/data/repo/LocalDramaRepository.kt`
- `android-client/app/src/main/java/com/dramacard/client/player/PlayerScreen.kt`
- `android-client/app/src/main/java/com/dramacard/client/player/PlayerUiState.kt`

The public snapshot uses `https://example.com/dramacard-assets` as a placeholder.

## Content Policy For Contributors

Keep copyrighted drama videos, generated images, production data, and private cloud endpoints outside git. Use external storage, local test files, or small synthetic fixtures when developing locally.
