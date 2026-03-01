# Skill: GitHub Actions Troubleshooting (Public Repo)

이 스킬은 `costco-crawler` Actions 실패를 빠르게 분류/조치하기 위한 체크리스트입니다.

## Crawler Tests 실패
- `test.yml` 실행 환경 Python 버전 확인
- `pip install -e ".[dev]"` 실패 여부 확인
- `scripts/validate_products_schema.py` 실패 지점 확인
- `pytest` 실패 테스트 케이스 확인

## Crawl workflow 실패
- `Decide whether to crawl` 결과 확인
- `Commit updated data`에서 실제 변경 감지 여부 확인
- `Dispatch private deployment workflow` HTTP status 확인

## 빈번한 에러
- `403 Resource not accessible by personal access token`
  - PAT 권한 또는 리포 접근권 미설정
- dispatch success인데 private 반영 없음
  - private workflow 수신 조건(`repository_dispatch`) 및 payload 점검
