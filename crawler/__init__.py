# Crawler Package
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# 새로운 구조
VERSIONS_DIR = DATA_DIR / "versions"
MASTER_DIR = DATA_DIR / "master"
CONFIG_DIR = PROJECT_ROOT / "config"

# 하위 호환성을 위한 정의 (점진적 제거 예정)
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
IMAGES_DIR = DATA_DIR / "images"

# 디렉토리 생성
for dir_path in [VERSIONS_DIR, MASTER_DIR, RAW_DIR, PROCESSED_DIR, IMAGES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
