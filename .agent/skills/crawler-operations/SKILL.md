# Skill: Crawler Operations (Public Repo)

이 스킬은 `costco-crawler`의 일상 운영(수동 실행/검증/커밋 기준)을 다룹니다.

## 주요 명령
- 설치: `python3 -m pip install -e ".[dev]"`
- 변경 체크: `python3 -m crawler.cli check`
- 크롤링: `python3 -m crawler.cli crawl`
- 강제 크롤링: `python3 -m crawler.cli crawl --force`
- 스키마 검증: `python3 scripts/validate_products_schema.py`

## 데이터 구조
- `data/current`는 최신 버전을 가리키는 심볼릭 링크
- 실제 데이터는 `data/versions/<version>/`에 저장

## 로컬 검증
1. `readlink data/current`로 타겟 버전 확인
2. `data/current/products.json`/`categories.json` 존재 확인
3. 스키마 검증 실행
