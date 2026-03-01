"""
이미지 다운로드 스크립트
master/products.json의 모든 이미지를 다운로드합니다.
"""

import json
import hashlib
import time
import requests
from pathlib import Path
from datetime import datetime

# 경로 설정
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
MASTER_IMAGES_DIR = MASTER_DIR / "images" / "products"
WEB_FRONTEND_DIR = PROJECT_ROOT / "web"
WEB_DATA_DIR = WEB_FRONTEND_DIR / "data" / "current"
WEB_IMAGES_DIR = WEB_DATA_DIR / "images" / "products"

# 디렉토리 생성
MASTER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
WEB_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

MAX_RETRIES = 3
RETRY_DELAY = 1
TIMEOUT = 10


def download_images():
    """모든 상품 이미지 다운로드"""
    products_file = MASTER_DIR / "products.json"
    
    if not products_file.exists():
        print("[ERROR] products.json not found")
        return
    
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.cocodalin.com/"
    })
    
    total = len(products)
    completed = 0
    cached = 0
    failed = 0
    
    print(f"[INFO] Starting image download for {total} products")
    
    for i, product in enumerate(products):
        product_id = product['product_id']
        image_url = product.get('image_url')
        
        if not image_url:
            failed += 1
            continue
        
        master_path = MASTER_IMAGES_DIR / f"{product_id}.jpg"
        web_path = WEB_IMAGES_DIR / f"{product_id}.jpg"
        
        # 이미 다운로드된 경우 캐시 사용
        if master_path.exists():
            cached += 1
            # 웹 디렉토리에 복사
            if not web_path.exists():
                import shutil
                shutil.copy(master_path, web_path)
            
            # products.json에 로컬 경로 추가
            product['local_image_path'] = f"images/products/{product_id}.jpg"
            product['image_status'] = 'cached'
            continue
        
        # 다운로드 시도
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                response = session.get(image_url, timeout=TIMEOUT)
                
                if response.status_code == 200:
                    content = response.content
                    if len(content) < 500:
                        break  # 너무 작은 파일
                    
                    # 저장
                    with open(master_path, 'wb') as f:
                        f.write(content)
                    
                    # 웹 디렉토리에도 복사
                    import shutil
                    shutil.copy(master_path, web_path)
                    
                    product['local_image_path'] = f"images/products/{product_id}.jpg"
                    product['image_status'] = 'downloaded'
                    product['image_hash'] = hashlib.sha256(content).hexdigest()[:16]
                    
                    completed += 1
                    success = True
                    break
                    
                elif response.status_code in [403, 404]:
                    break
                    
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        if not success:
            failed += 1
            product['image_status'] = 'failed'
        
        # 진행 상황 출력
        done = i + 1
        if done % 50 == 0 or done == total:
            print(f"       Progress: {done}/{total} (new: {completed}, cached: {cached}, failed: {failed})")
        
        # 서버 부하 방지
        if not cached:
            time.sleep(0.1)
    
    # products.json 업데이트
    with open(products_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    # 웹 프론트엔드에도 복사
    web_products_file = WEB_DATA_DIR / "products.json"
    with open(web_products_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"\n[INFO] Download completed!")
    print(f"       Total: {total}")
    print(f"       New downloads: {completed}")
    print(f"       Cached: {cached}")
    print(f"       Failed: {failed}")
    print(f"       Master dir: {MASTER_IMAGES_DIR}")
    print(f"       Web dir: {WEB_IMAGES_DIR}")


if __name__ == "__main__":
    download_images()
