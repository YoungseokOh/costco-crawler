# Troubleshooting

## `catalog_safety_blocked`
증상:
- workflow가 crawl/commit 전에 exit code 2로 실패
- 로그에 `total_catalog_drop`, `category_catalog_drop`, 또는
  `upstream_count_mismatch`가 표시됨

조치:
1. `python scripts/verify_source_parity.py` 실행
2. 코코달인 `/saleSummary` 표시 수와 `/productList/{category_id}` 실제 수 확인
3. 일시적인 원본 이상이면 승인하지 말고 다음 스케줄까지 기존 공개본 유지
4. 실제 카탈로그 변경이면 수동 workflow의 `allow_unsafe_drop=true`로 명시적 승인

`force=true`만으로는 안전장치가 해제되지 않습니다.

## 403 on dispatch
증상:
- `Resource not accessible by personal access token`

원인:
- `PRIVATE_REPO_DISPATCH_TOKEN` 권한 부족 또는 대상 레포 접근 불가

조치:
1. 토큰 권한 확인 (private repo dispatch 가능해야 함)
2. 토큰 값을 public repo secret에 재등록
3. `crawl.yml` 재실행

## force 실행했는데 private가 안 붙음
현재는 패치로 해결됨.

기준:
- 수동 실행 + `force=true`면 dispatch 실행

확인 포인트:
- `Dispatch private deployment workflow` step 결론이 `success`인지 확인

## schema file not found (`data/current/products.json`)
- private CI에서 데이터가 없어서 생기는 오류
- 현재 private CI는 public crawler 데이터를 checkout + sync 후 schema/test 실행하도록 수정 완료

## deploy 성공인데 데이터가 구버전
확인 순서:
1. public dispatch payload의 `public_sha`가 최신인지
2. private deploy run이 해당 `public_sha`를 checkout 했는지
3. 배포 후 해시 검증 결과가 통과했는지

동일 할인 시작일 안에서 내용이 변경된 경우 `data/current`가
`YYYY-MM-DD--<revision>` 디렉토리를 가리키는 것은 정상입니다. 기존 주차
디렉토리를 덮어쓰지 않고 이전 스냅샷을 보존하기 위한 동작입니다.
