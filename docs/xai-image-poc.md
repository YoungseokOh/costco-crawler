# xAI Image Processing PoC

## 어디서 진행할까?
`costco-crawler`에서 진행하는 것이 맞습니다.

이유:
- 이미지 생성/변환은 크롤링 산출물 파이프라인에 속함
- 버전별 결과를 `data/versions`에 함께 관리 가능
- private repo는 배포 오케스트레이션에 집중 가능

## 목표
- 첫 단계에서는 원본 대비 변환 품질을 빠르게 확인
- 품질 통과 후에만 전체 백필/증분 운영을 진행
- 처리 시간, 실패율, 비용은 smoke artifact에 함께 기록

## 현재 도입 단계
1. `image_transform_smoke.yml` manual workflow 실행
2. `data/current/products.json`에서 distinct `image_hash` 3개 랜덤 샘플 선택
3. xAI `grok-imagine-image`로 각도 변경 편집 실행
4. `before/after`와 `summary`를 artifact로 검수
5. 품질 통과 전까지 commit, dispatch, deploy는 하지 않음

## Smoke Test 출력 구조
- 원본 복사본: `artifacts/image-transform-smoke/before/`
- 변환 결과: `artifacts/image-transform-smoke/after/`
- 메타데이터: `artifacts/image-transform-smoke/summary.json`
- 리뷰용 요약: `artifacts/image-transform-smoke/summary.md`

현재 smoke 단계에서는 `products.json` tracked 데이터를 수정하지 않습니다.

## 샘플 선정 규칙
- `image_status`가 `downloaded` 또는 `cached`
- `local_image_path` 파일이 실제로 존재
- 같은 `image_hash`는 1개 대표 상품만 선택
- 기본 샘플 수는 `3`

## 운영 반영 기준(권장)
- 상품 본체가 바뀌지 않을 것
- 각도 변화가 육안으로 분명할 것
- 배경/광원 품질이 유지될 것
- 텍스트, 라벨, 로고가 심하게 깨지지 않을 것
- smoke 3장 검수 통과 후에만 전체 백필을 승인할 것
