"""
API Fetcher
코코달인 API에서 데이터를 가져옵니다.
"""

import requests
import json
import time
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime

from crawler import MASTER_DIR, RAW_DIR
from crawler.core.config import config


class Fetcher:
    """API 데이터 Fetcher"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.request.get('headers', {}))
        
        self.base_url = config.get('api.base_url')
        self.endpoints = config.get('api.endpoints', {})
        self.delay = config.get('request.delay', 0.5)
        self.max_retries = config.get('request.max_retries', 3)
        self.timeout = config.get('request.timeout', 10)
        
        self._last_notice_hash = self._load_crawl_log().get('last_notice_hash')
    
    def _load_crawl_log(self) -> Dict:
        """크롤링 로그 로드"""
        log_name = config.get('storage.crawl_log_file', 'crawl_log.json')
        primary_log_file = MASTER_DIR / log_name
        legacy_log_file = RAW_DIR / log_name

        for log_file in (primary_log_file, legacy_log_file):
            if not log_file.exists():
                continue
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                # Legacy 위치(raw)에서 읽었으면 master로 승격해 경로를 통일한다.
                if log_file == legacy_log_file and not primary_log_file.exists():
                    with open(primary_log_file, 'w', encoding='utf-8') as f:
                        json.dump(log_data, f, ensure_ascii=False, indent=2)
                return log_data
            except Exception:
                continue
        return {}
    
    def _save_crawl_log(self, notice_hash: str, products_count: int):
        """크롤링 로그 저장"""
        log_file = MASTER_DIR / config.get('storage.crawl_log_file', 'crawl_log.json')
        log = {
            'last_notice_hash': notice_hash,
            'last_crawl_at': datetime.now().isoformat(),
            'products_count': products_count
        }
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    
    def _request(self, endpoint_key: str, **kwargs) -> Optional[Any]:
        """API 요청"""
        endpoint = self.endpoints.get(endpoint_key, '')
        url = self.base_url + endpoint.format(**kwargs)
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                time.sleep(self.delay)
                return response.json()
            except requests.RequestException as e:
                print(f"[ERROR] Request failed ({attempt+1}/{self.max_retries}): {url}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        return None
    
    def check_update(self) -> tuple[bool, Optional[str]]:
        """업데이트 확인"""
        print("[INFO] Checking for updates...")
        notices = self._request('notice')
        
        if not notices:
            return False, None
        
        notice_str = json.dumps(notices, sort_keys=True, ensure_ascii=False)
        current_hash = hashlib.md5(notice_str.encode()).hexdigest()
        
        if self._last_notice_hash == current_hash:
            print("[INFO] No updates detected")
            return False, current_hash
        
        print(f"[INFO] Update detected! (hash: {current_hash[:8]}...)")
        return True, current_hash
    
    def fetch_categories(self) -> List[Dict]:
        """카테고리 목록 조회"""
        print("[INFO] Fetching categories...")
        categories = self._request('categories')
        if categories:
            print(f"[INFO] Found {len(categories)} categories")
        return categories or []
    
    def fetch_products_by_category(self, category_id: int) -> List[Dict]:
        """카테고리별 상품 조회"""
        return self._request('products_by_category', category_id=category_id) or []
    
    def fetch_all_products(self, categories: List[Dict]) -> List[Dict]:
        """모든 카테고리의 상품 조회"""
        print("[INFO] Fetching all products...")
        all_products = []
        
        for cat in categories:
            products = self.fetch_products_by_category(cat['category_id'])
            print(f"       - {cat['category_name']}: {len(products)} products")
            all_products.extend(products)
        
        # 중복 제거
        seen = set()
        unique = []
        for p in all_products:
            if p['product_id'] not in seen:
                seen.add(p['product_id'])
                unique.append(p)
        
        print(f"[INFO] Total unique products: {len(unique)}")
        return unique
    
    def fetch_popular(self) -> List[Dict]:
        """인기 상품 조회"""
        return self._request('popular') or []
