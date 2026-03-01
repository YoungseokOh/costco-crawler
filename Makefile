.PHONY: setup crawl crawl-force check validate test format clean

setup:
	python3 -m pip install -e ".[dev]"

crawl:
	python3 -m crawler.cli crawl

crawl-force:
	python3 -m crawler.cli crawl --force

check:
	python3 -m crawler.cli check

validate:
	python3 scripts/validate_products_schema.py

test:
	python3 -m pytest tests/ -v

format:
	black crawler/ tests/ scripts/
	ruff check crawler/ tests/ scripts/ --fix

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
