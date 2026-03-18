# costco-crawler

Public crawler repository for Costco deal data.

## Overview

This repository:
- Crawls the latest product and discount data
- Stores versioned snapshots under `data/versions/`
- Maintains `data/current` as a symlink to the latest version
- Runs on GitHub Actions
- Dispatches private deployment after crawl completion

## Quick Start

```bash
python3 -m pip install -e ".[dev]"
python3 -m crawler.cli check
python3 -m crawler.cli crawl
python3 scripts/validate_products_schema.py
```

## Repository Layout

```text
crawler/                  # crawler package
config/default.yaml       # crawler settings
scripts/                  # utility scripts
tests/                    # tests
data/current              # symlink to latest version
data/versions             # versioned datasets
```

## GitHub Actions

- `test.yml`: schema validation and tests on push/PR
- `crawl.yml`: scheduled crawl and dispatch to private deployment workflow
- `image_transform_smoke.yml`: manual 3-image xAI transform smoke test that only uploads review artifacts

### Manual Force Run

If you run `crawl.yml` manually with `force=true`:
- Crawling is executed regardless of update-check result
- Private dispatch is also executed even when no data commit is created

## Required Secret (Public Repo)

- `PRIVATE_REPO_DISPATCH_TOKEN`
  - Personal access token that can call `repository_dispatch` on:
  - `YoungseokOh/hack-the-costco`
- `XAI_API_KEY`
  - Required only for `image_transform_smoke.yml`
  - Used to edit 3 sampled product images and upload before/after artifacts for review

## Required Setup (Private Repo)

- `.github/workflows/deploy_from_crawler.yml`
- `FIREBASE_TOKEN` secret

## Documentation

- See [docs/README.md](docs/README.md) for:
  - automation flow
  - operations runbook
  - troubleshooting
  - xAI image PoC notes

## License

MIT
