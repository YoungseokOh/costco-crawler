# Automation Flow

## 개요
현재 파이프라인은 public crawler 레포를 데이터 소스로 사용하고, private 레포에서 실제 배포를 수행합니다.

1. public repo (`costco-crawler`)에서 `crawl.yml` 실행
2. 크롤링/검증 후 데이터 변경 시 `data` 커밋
3. public workflow가 private repo로 `repository_dispatch` 호출
4. private repo(`hack-the-costco`)의 `deploy_from_crawler.yml` 실행
5. public data 동기화 후 Firebase 배포
6. 배포 URL 해시 검증

## public workflow 핵심
파일: `.github/workflows/crawl.yml`

- 스케줄: `17 */4 * * *`
- 수동 입력: `force` (`true/false`)
- dispatch 조건:
  - 데이터 변경(`changed=true`)이거나
  - 수동 실행 + `force=true`

## dispatch payload
- `event_type`: `crawler_data_updated`
- `client_payload.public_repo`: 예) `YoungseokOh/costco-crawler`
- `client_payload.public_sha`: 크롤링 후 최신 커밋 SHA
- `client_payload.data_version`: `readlink data/current` 기반 버전명

## 필요한 시크릿
public repo:
- `PRIVATE_REPO_DISPATCH_TOKEN`

private repo:
- `FIREBASE_TOKEN`
