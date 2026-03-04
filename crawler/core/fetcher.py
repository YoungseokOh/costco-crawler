"""
API Fetcher
코코달인 API에서 데이터를 가져옵니다.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

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

        self._crawl_log = self._load_crawl_log()
        self._last_notice_hash = self._crawl_log.get('last_notice_hash')
        self._last_catalog_hash = self._crawl_log.get('last_catalog_hash')
        try:
            raw_last_catalog_count = self._crawl_log.get('last_catalog_count')
            self._last_catalog_count = (
                int(raw_last_catalog_count) if raw_last_catalog_count is not None else None
            )
        except (TypeError, ValueError):
            self._last_catalog_count = None
        self._last_check_result: Dict[str, Any] = {}
    
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
    
    def _save_crawl_log(
        self,
        notice_hash: Optional[str],
        products_count: int,
        catalog_hash: Optional[str] = None,
        catalog_count: Optional[int] = None,
        check_reason: Optional[str] = None,
    ):
        """크롤링 로그 저장"""
        log_file = MASTER_DIR / config.get('storage.crawl_log_file', 'crawl_log.json')
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

    @property
    def last_check_result(self) -> Dict[str, Any]:
        """최근 check_update 결과"""
        return self._last_check_result

    def _short_hash(self, value: Optional[str]) -> str:
        if not value:
            return 'none'
        return value[:8]

    def _build_catalog_fingerprint(self) -> Tuple[Optional[str], Optional[int]]:
        """상품 스냅샷 해시 계산용 카탈로그 지문 생성"""
        categories = self._request('categories')
        if categories is None:
            print("[WARN] Catalog snapshot skipped: categories endpoint unavailable")
            return None, None

        all_products: List[Dict] = []
        for cat in categories:
            category_id = cat.get('category_id')
            if category_id is None:
                continue
            products = self._request('products_by_category', category_id=category_id)
            if products is None:
                print(
                    "[WARN] Catalog snapshot skipped: "
                    f"products endpoint unavailable for category {category_id}"
                )
                return None, None
            all_products.extend(products)

        unique_products: Dict[Any, Dict] = {}
        for product in all_products:
            product_id = product.get('product_id')
            if product_id is None:
                continue
            if product_id not in unique_products:
                unique_products[product_id] = product

        normalized: List[Dict[str, Any]] = []
        for product_id in sorted(unique_products):
            product = unique_products[product_id]
            normalized.append({
                'product_id': product_id,
                'sale_price': product.get('sale_price'),
                'normal_price': product.get('normal_price'),
                'discount': product.get('discount'),
                'from_date': product.get('from_date'),
                'to_date': product.get('to_date'),
            })

        payload = json.dumps(
            normalized,
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        catalog_hash = hashlib.sha256(payload.encode()).hexdigest()
        return catalog_hash, len(normalized)
    
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
            except requests.RequestException:
                print(f"[ERROR] Request failed ({attempt+1}/{self.max_retries}): {url}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        return None
    
    def check_update(self) -> tuple[bool, Optional[str]]:
        """업데이트 확인"""
        print("[INFO] Checking for updates...")
        notices = self._request('notice')

        if notices is None:
            self._last_check_result = {
                'should_crawl': False,
                'reason': 'notice_unavailable',
                'notice_changed': False,
                'catalog_changed': False,
                'notice_hash': None,
                'catalog_hash': None,
                'catalog_count': None,
            }
            print("[WARN] Notice endpoint unavailable. Treating as no update.")
            print(
                "CHECK_RESULT "
                "reason=notice_unavailable "
                "should_crawl=false "
                "notice_changed=false "
                "catalog_changed=false "
                "notice_hash=none "
                "catalog_hash=none "
                "catalog_count=unknown"
            )
            return False, None

        notice_str = json.dumps(notices, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        notice_hash = hashlib.md5(notice_str.encode()).hexdigest()
        catalog_hash, catalog_count = self._build_catalog_fingerprint()

        notice_changed = self._last_notice_hash != notice_hash
        if catalog_hash is None:
            catalog_changed = False
        elif self._last_catalog_hash is None:
            # 기존 로그에 카탈로그 해시가 없을 때 최초 1회 기준선을 만들기 위해 변경으로 간주
            catalog_changed = True
        else:
            catalog_changed = self._last_catalog_hash != catalog_hash

        should_crawl = notice_changed or catalog_changed
        catalog_count_change_ratio: Optional[float] = None
        if (
            catalog_count is not None
            and self._last_catalog_count is not None
            and self._last_catalog_count > 0
        ):
            catalog_count_change_ratio = (
                abs(catalog_count - self._last_catalog_count) / self._last_catalog_count
            )
            if catalog_count_change_ratio >= 0.2:
                print(
                    "[WARN] Catalog size changed significantly: "
                    f"previous={self._last_catalog_count}, current={catalog_count}, "
                    f"delta={catalog_count_change_ratio * 100:.1f}%"
                )

        if should_crawl:
            if notice_changed and catalog_changed:
                reason = 'notice_and_catalog_changed'
            elif notice_changed:
                reason = 'notice_changed'
            else:
                reason = 'catalog_changed'
        elif catalog_hash is None:
            reason = 'notice_unchanged_catalog_unavailable'
        else:
            reason = 'notice_unchanged_catalog_unchanged'

        self._last_check_result = {
            'should_crawl': should_crawl,
            'reason': reason,
            'notice_changed': notice_changed,
            'catalog_changed': catalog_changed,
            'notice_hash': notice_hash,
            'catalog_hash': catalog_hash,
            'catalog_count': catalog_count,
            'catalog_count_change_ratio': catalog_count_change_ratio,
        }

        print(
            f"[INFO] Notice hash: {self._short_hash(notice_hash)} "
            f"({'changed' if notice_changed else 'unchanged'})"
        )
        if catalog_hash is None:
            print("[INFO] Catalog hash: unavailable (fallback to notice-only)")
        else:
            print(
                f"[INFO] Catalog hash: {self._short_hash(catalog_hash)} "
                f"({'changed' if catalog_changed else 'unchanged'}) "
                f"/ products={catalog_count}"
            )
        print(f"[INFO] Check reason: {reason}")
        print(
            "CHECK_RESULT "
            f"reason={reason} "
            f"should_crawl={'true' if should_crawl else 'false'} "
            f"notice_changed={'true' if notice_changed else 'false'} "
            f"catalog_changed={'true' if catalog_changed else 'false'} "
            f"notice_hash={self._short_hash(notice_hash)} "
            f"catalog_hash={self._short_hash(catalog_hash)} "
            f"catalog_count={catalog_count if catalog_count is not None else 'unknown'}"
        )

        if should_crawl:
            print("[INFO] Update detected")
        else:
            print("[INFO] No updates detected")
        return should_crawl, notice_hash
    
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
