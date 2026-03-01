# xAI Image Processing PoC

## 어디서 진행할까?
`costco-crawler`에서 진행하는 것이 맞습니다.

이유:
- 이미지 생성/변환은 크롤링 산출물 파이프라인에 속함
- 버전별 결과를 `data/versions`에 함께 관리 가능
- private repo는 배포 오케스트레이션에 집중 가능

## 목표
- 원본 대비 변환 품질, 처리 시간, 실패율, 비용을 측정
- 본 운영 반영 여부를 데이터로 결정

## 권장 브랜치
- `feature/xai-image-poc`

## 권장 출력 구조
- 원본: `data/versions/<version>/images/products/`
- PoC 결과: `data/versions/<version>/images/products_xai/`

`products.json`에는 PoC 필드 추가를 권장:
- `xai_image_path`
- `xai_status`

## 최소 실험 설계
1. 샘플 30~50개로 소규모 처리
2. 처리 실패 케이스 분류 (timeout, malformed, API error)
3. 비용/시간/품질 지표 기록
4. 운영 반영 전 rollback 경로 확인 (원본 이미지 fallback)

## 운영 반영 기준(권장)
- 성공률 99%+
- 배치 시간 SLA 충족
- 비용 허용 범위 내
- 실패 시 원본 fallback 100% 보장
