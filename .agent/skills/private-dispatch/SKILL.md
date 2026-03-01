# Skill: Dispatch to Private Deploy (Public Repo)

이 스킬은 public crawler workflow가 private repo 배포를 트리거하는 절차입니다.

## 관련 워크플로
- `.github/workflows/crawl.yml`

## 동작 요약
1. crawl 성공 후 `data` 변경분 커밋/푸시
2. `public_sha=$(git rev-parse HEAD)` 저장
3. `repository_dispatch`로 private repo 호출

## 필수 secret
- `PRIVATE_REPO_DISPATCH_TOKEN`

## 실패 시 우선 확인
- dispatch step 로그의 HTTP status
- 403이면 토큰 권한/대상 repo 접근 재확인
- payload에 전달된 `public_sha`가 최신 데이터 커밋인지 확인
