# Operations Runbook

## 1) 일상 운영
기본적으로 스케줄 실행에 맡깁니다.

- `crawl.yml`가 4시간마다 실행
- 공지와 카탈로그 해시가 같으면 crawl skip
- 변경이 있으면 자동 배포 트리거
- 급감 또는 코코달인 원본 내부 불일치가 감지되면 commit/dispatch 전에 실패

## 2) 수동 즉시 실행
즉시 확인 또는 강제 재실행이 필요할 때 사용합니다.

1. GitHub Actions -> `Crawl and Notify Private Deploy`
2. `Run workflow`
3. `force=true`로 실행

`force=true` 동작:
- 크롤링은 무조건 수행
- 현재 설정상 변경이 없어도 private dispatch 수행
- 급감 안전장치는 우회하지 않음

안전장치가 차단한 감소나 원본 요약 수 불일치를 승인해야 할 때만 다음을 수행합니다.

1. 코코달인 화면의 12개 카테고리 표시 수 확인
2. `python scripts/verify_source_parity.py`로 실제 상품 ID/수를 대조
3. 실제 `productList`가 원본 화면과 일치함을 확인한 뒤 수동 workflow에서
   `force=true`, `allow_unsafe_drop=true`를 함께 선택

`allow_unsafe_drop`은 단순 재시도 옵션이 아니라 운영자 승인 기록입니다.

## 2-1) 이미지 변환 smoke test
전체 반영 전에 품질만 빠르게 점검할 때 사용합니다.

1. GitHub Actions -> `Image Transform Smoke Test`
2. 필요하면 `seed`를 넣고, 아니면 비워둔 채 실행
3. 실행이 끝나면 artifact `image-transform-smoke-<run_id>` 다운로드
4. `before/`와 `after/` 이미지를 눈으로 비교
5. `summary.md`, `summary.json`에서 샘플 메타데이터와 예상 비용 확인

주의:
- 이 워크플로우는 항상 `3`개의 distinct `image_hash`만 처리합니다.
- tracked `data/`는 수정하지 않습니다.
- private repo dispatch나 Firebase 배포도 수행하지 않습니다.

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
python3 scripts/verify_source_parity.py
python3 scripts/run_transform_smoke_test.py --artifact-dir artifacts/image-transform-smoke
python3 -m pytest tests -q
```

정상 parity 출력은 `source_actual`과 `local`이 모든 카테고리에서 같고,
마지막에 `[PASS]`가 표시됩니다. `reported`는 코코달인 자체 필터 때문에
실제 목록보다 1~2개 많을 수 있습니다.
