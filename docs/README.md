# costco-crawler Docs

이 폴더는 public crawler 운영 문서 모음입니다.

## 문서 목록
- `automation-flow.md`: public crawler -> private deploy 자동화 흐름
- `operations-runbook.md`: 일상 운영 절차 (수동 실행/검증)
- `troubleshooting.md`: 자주 발생하는 실패와 대응
- `xai-image-poc.md`: xAI 기반 이미지 처리 PoC 설계/운영 가이드

## 현재 운영 기준 (2026-03-01)
- 스케줄: 4시간마다(`crawl.yml`)
- 업데이트 판정: 공지 API 해시 기반 `check`
- 수동 `force=true`: 데이터 변경이 없어도 private dispatch 실행
- private 배포 후 해시 검증: `products.json`, `categories.json`
