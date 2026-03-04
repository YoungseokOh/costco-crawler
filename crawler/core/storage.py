"""
Storage
데이터 저장 및 로드를 담당합니다.
"""

import json
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

from crawler import MASTER_DIR, RAW_DIR, VERSIONS_DIR
from crawler.core.config import config


class Storage:
    """데이터 저장소"""
    
    IMAGE_BASE_URL = "https://image.cocodalin.com/product"
    
    def __init__(self):
        self.master_dir = MASTER_DIR
        self.versions_dir = VERSIONS_DIR
        self.raw_dir = RAW_DIR
    
    def generate_image_url(self, product: Dict) -> Optional[str]:
        """상품 이미지 URL 생성"""
        product_image = product.get('product_image')
        if not product_image:
            return None
        
        # 실제 사이트에서 사용하는 /sm/ 경로 적용
        encoded = urllib.parse.quote(product_image)
        return f"{self.IMAGE_BASE_URL}/sm/{encoded}.jpg"

    
    def add_image_urls(self, products: List[Dict]) -> List[Dict]:
        """상품에 이미지 URL 추가"""
        for product in products:
            product['image_url'] = self.generate_image_url(product)
        return products
    
    def save_products(self, products: List[Dict]):
        """상품 데이터 저장 (Master에 반영)"""
        # 이미지 URL 추가
        products = self.add_image_urls(products)
        
        # 최신 파일 저장 (Master)
        products_file = self.master_dir / 'products.json'
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"[INFO] Saved {len(products)} products to {products_file}")
    
    def save_categories(self, categories: List[Dict]):
        """카테고리 데이터 저장"""
        cat_file = self.raw_dir / config.get('storage.categories_file', 'categories.json')
        with open(cat_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
    
    def save_crawl_log(
        self,
        notice_hash: Optional[str],
        products_count: int,
        catalog_hash: Optional[str] = None,
        catalog_count: Optional[int] = None,
        check_reason: Optional[str] = None,
    ):
        """크롤링 로그 저장 (Master)"""
        log_file = self.master_dir / 'crawl_log.json'
        existing: Dict[str, Any] = {}
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        now = datetime.now().isoformat()
        log = dict(existing)

        if notice_hash is not None:
            log['last_notice_hash'] = notice_hash
        if catalog_hash is not None:
            log['last_catalog_hash'] = catalog_hash
        if catalog_count is not None:
            log['last_catalog_count'] = catalog_count
        if check_reason:
            log['check_reason'] = check_reason

        log['last_check_at'] = now
        log['last_crawl_at'] = now
        log['products_count'] = products_count

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    
    def load_products(self) -> List[Dict]:
        """상품 데이터 로드"""
        products_file = self.raw_dir / config.get('storage.raw_data_file', 'products.json')
        if products_file.exists():
            with open(products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def load_categories(self) -> List[Dict]:
        """카테고리 데이터 로드"""
        cat_file = self.raw_dir / config.get('storage.categories_file', 'categories.json')
        if cat_file.exists():
            with open(cat_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
