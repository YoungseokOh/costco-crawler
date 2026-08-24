# costco-crawler Docs

이 폴더는 public crawler 운영 문서 모음입니다.

## 문서 목록
- `automation-flow.md`: public crawler -> private deploy 자동화 흐름
- `operations-runbook.md`: 일상 운영 절차 (수동 실행/검증)
- `troubleshooting.md`: 자주 발생하는 실패와 대응
- `xai-image-poc.md`: xAI 기반 이미지 처리 PoC 설계/운영 가이드

## 현재 운영 기준 (2026-08-24)
- 스케줄: 4시간마다(`crawl.yml`)
- 업데이트 판정: 공지와 전체 카탈로그 해시 기반 `check`
- 급감/원본 불일치: 자동 commit과 dispatch 전 차단
- 수동 `force=true`: 안전장치를 유지한 채 강제 수집/dispatch
- `allow_unsafe_drop=true`: 코코달인 직접 대조 후에만 사용하는 별도 승인
- 원본 parity: 상품 ID와 카테고리별 실제 목록 수를 commit 전에 검증
- private 배포 후 해시 검증: `products.json`, `categories.json`
- 수동 이미지 smoke test: `image_transform_smoke.yml`이 3개 샘플만 artifact로 생성, commit/dispatch 없음
