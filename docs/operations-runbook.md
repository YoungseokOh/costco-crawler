# Operations Runbook

## 1) 일상 운영
기본적으로 스케줄 실행에 맡깁니다.

- `crawl.yml`가 4시간마다 실행
- 공지 해시가 같으면 crawl skip
- 변경이 있으면 자동 배포 트리거

## 2) 수동 즉시 실행
즉시 확인 또는 강제 재실행이 필요할 때 사용합니다.

1. GitHub Actions -> `Crawl and Notify Private Deploy`
2. `Run workflow`
3. `force=true`로 실행

`force=true` 동작:
- 크롤링은 무조건 수행
- 현재 설정상 변경이 없어도 private dispatch 수행

## 3) 최종 반영 확인
다음 2개 파일 해시를 public 최신과 비교합니다.

- `https://costit-service.web.app/data/current/products.json`
- `https://costit-service.web.app/data/current/categories.json`

참고:
- `manifest.json`은 private 배포 시 별도 생성 메타 파일이라 public manifest와 동일하지 않아도 정상입니다.

## 4) 로컬 점검 명령
```bash
python3 -m pip install -e ".[dev]"
python3 -m crawler.cli check
python3 -m crawler.cli crawl --force
python3 scripts/validate_products_schema.py
python3 -m pytest tests -q
```
