# costco-crawler

Public crawler repository for Costco deal data.

## What this repo does

- Crawls latest product/discount data
- Stores versioned datasets under `data/versions/`
- Maintains `data/current` as the latest version pointer
- Runs on GitHub Actions (public minutes)
- Notifies private deploy repo after successful update

## Quick start

```bash
python3 -m pip install -e ".[dev]"
python3 -m crawler.cli check
python3 -m crawler.cli crawl
python3 scripts/validate_products_schema.py
```

## Repo layout

```text
crawler/                  # crawler package
config/default.yaml       # crawler settings
scripts/                  # utility scripts
tests/                    # tests
data/current              # symlink to latest version
data/versions             # versioned datasets
```

## GitHub Actions

- `test.yml`: runs lint/tests/schema checks on push/PR
- `crawl.yml`: scheduled crawling + optional dispatch to private repo

### Required secret for dispatch

Set this in this public repo if you want automatic private deployment:

- `PRIVATE_REPO_DISPATCH_TOKEN`:
  Personal Access Token with permission to dispatch workflows to
  `YoungseokOh/hack-the-costco`.

Private repo side must have:

- `.github/workflows/deploy_from_crawler.yml`
- `FIREBASE_TOKEN` secret configured

## License

MIT
