"""
Version Manager
데이터 버전 관리를 담당합니다.
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import Counter

from crawler import DATA_DIR


class VersionManager:
    """버전별 데이터 관리"""
    
    def __init__(self):
        self.versions_dir = DATA_DIR / "versions"
        self.master_dir = DATA_DIR / "master"
        self.current_link = DATA_DIR / "current"
        
        # 디렉토리 생성
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.master_dir.mkdir(parents=True, exist_ok=True)
        (self.master_dir / "images" / "products").mkdir(parents=True, exist_ok=True)
    
    def get_version_name(self, products: List[Dict]) -> str:
        """상품 목록에서 버전명 추출 (할인 시작일 기준)"""
        from_dates = [p.get('from_date', '') for p in products if p.get('from_date')]
        if not from_dates:
            return datetime.now().strftime('%Y-%m-%d')
        
        # 가장 흔한 시작일 찾기
        most_common = Counter(from_dates).most_common(1)[0][0]
        # 2026.01.05 -> 2026-01-05
        return most_common.replace('.', '-')
    
    def get_discount_period(self, products: List[Dict]) -> Dict[str, str]:
        """할인 기간 추출"""
        from_dates = [p.get('from_date', '') for p in products if p.get('from_date')]
        to_dates = [p.get('to_date', '') for p in products if p.get('to_date')]
        
        return {
            "from": min(from_dates) if from_dates else "",
            "to": max(to_dates) if to_dates else ""
        }
    
    def get_next_crawl_date(self, products: List[Dict]) -> Optional[str]:
        """다음 크롤링 권장일 계산 (할인 종료일 + 1일)"""
        to_dates = [p.get('to_date', '') for p in products if p.get('to_date')]
        if not to_dates:
            return None
        
        # 가장 흔한 종료일
        most_common = Counter(to_dates).most_common(1)[0][0]
        try:
            end_date = datetime.strptime(most_common, '%Y.%m.%d')
            from datetime import timedelta
            next_date = end_date + timedelta(days=1)
            return next_date.strftime('%Y-%m-%d')
        except:
            return None
    
    def create_version(self, products: List[Dict], categories: List[Dict]) -> str:
        """새 버전 생성"""
        version_name = self.get_version_name(products)
        version_dir = self.versions_dir / version_name
        
        # 버전 디렉토리 생성
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "images" / "products").mkdir(parents=True, exist_ok=True)
        
        # 히스토리 로드
        history = self.load_discount_history()
        previous_products = self.load_current_products()
        
        # 상품 분류
        categorized = self.categorize_products(products, previous_products, history)
        
        # 상품에 메타데이터 추가
        products = self.enrich_products(products, history, version_name)
        
        # 상품 저장
        products_file = version_dir / "products.json"
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        # 카테고리 저장
        categories_file = version_dir / "categories.json"
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        
        # 매니페스트 생성
        manifest = self.create_manifest(
            version_name, products, categories, categorized
        )
        manifest_file = version_dir / "manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        # 히스토리 업데이트
        self.update_discount_history(products, version_name, history)
        
        # current 심볼릭 링크 업데이트
        self.update_current_link(version_name)
        
        print(f"[INFO] Created version: {version_name}")
        print(f"       Products: {len(products)}")
        print(f"       New: {len(categorized['new'])}, Returning: {len(categorized['returning'])}")
        
        return version_name
    
    def create_manifest(self, version: str, products: List[Dict], 
                       categories: List[Dict], categorized: Dict) -> Dict:
        """매니페스트 생성"""
        discount_period = self.get_discount_period(products)
        next_crawl = self.get_next_crawl_date(products)
        
        # 이전 버전 찾기
        versions = self.list_versions()
        prev_version = versions[-1] if versions and versions[-1] != version else None
        
        products_json = json.dumps(products, sort_keys=True, ensure_ascii=False)
        products_hash = hashlib.sha256(products_json.encode()).hexdigest()
        
        return {
            "version": version,
            "created_at": datetime.now().isoformat(),
            "discount_period": discount_period,
            "stats": {
                "products_count": len(products),
                "images_count": 0,  # 이미지 다운로드 후 업데이트
                "images_downloaded": 0,
                "images_failed": 0,
                "new_products": len(categorized['new']),
                "returning_products": len(categorized['returning']),
                "continuing_products": len(categorized['continuing']),
                "categories_count": len(categories)
            },
            "files": {
                "products": "products.json",
                "categories": "categories.json",
                "images_dir": "images/products/"
            },
            "checksum": {
                "products": f"sha256:{products_hash[:16]}..."
            },
            "previous_version": prev_version,
            "next_crawl_suggested": next_crawl
        }
    
    def categorize_products(self, current: List[Dict], previous: List[Dict], 
                           history: Dict) -> Dict[str, Set[int]]:
        """상품 분류: new, returning, continuing, removed"""
        current_ids = {p['product_id'] for p in current}
        previous_ids = {p['product_id'] for p in previous}
        all_seen_ids = set(int(k) for k in history.keys())
        
        new = current_ids - all_seen_ids
        returning = (current_ids - previous_ids) & all_seen_ids
        continuing = current_ids & previous_ids
        removed = previous_ids - current_ids
        
        return {
            'new': new,
            'returning': returning,
            'continuing': continuing,
            'removed': removed
        }
    
    def enrich_products(self, products: List[Dict], history: Dict, 
                       version: str) -> List[Dict]:
        """상품에 메타데이터 추가"""
        for product in products:
            pid = str(product['product_id'])
            
            if pid in history:
                product['first_seen_version'] = history[pid].get('first_seen', version)
                product['discount_count'] = len(history[pid].get('occurrences', [])) + 1
            else:
                product['first_seen_version'] = version
                product['discount_count'] = 1
            
            # 이미지 관련 필드 초기화
            product['local_image_path'] = f"images/products/{product['product_id']}.jpg"
            product['image_status'] = 'pending'
            product['image_hash'] = None
        
        return products
    
    def load_discount_history(self) -> Dict:
        """할인 히스토리 로드"""
        history_file = self.master_dir / "discount_history.json"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def update_discount_history(self, products: List[Dict], version: str, 
                               history: Dict) -> None:
        """할인 히스토리 업데이트"""
        for product in products:
            pid = str(product['product_id'])
            
            occurrence = {
                "version": version,
                "from_date": product.get('from_date', ''),
                "to_date": product.get('to_date', ''),
                "normal_price": product.get('normal_price', 0),
                "sale_price": product.get('sale_price', 0),
                "discount": product.get('discount', 0)
            }
            
            if pid not in history:
                history[pid] = {
                    "product_id": product['product_id'],
                    "product_name": product.get('product_name', ''),
                    "category_name": product.get('category_name', ''),
                    "first_seen": version,
                    "last_seen": version,
                    "occurrences": [occurrence]
                }
            else:
                # 같은 버전이 이미 있으면 스킵
                existing_versions = [o['version'] for o in history[pid]['occurrences']]
                if version not in existing_versions:
                    history[pid]['occurrences'].append(occurrence)
                    history[pid]['last_seen'] = version
        
        # 저장
        history_file = self.master_dir / "discount_history.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def load_current_products(self) -> List[Dict]:
        """현재 버전의 상품 로드"""
        if not self.current_link.exists():
            return []
        
        products_file = self.current_link / "products.json"
        if products_file.exists():
            with open(products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def update_current_link(self, version: str) -> None:
        """current 심볼릭 링크 업데이트"""
        version_dir = self.versions_dir / version
        
        # 기존 링크 제거
        if self.current_link.exists() or self.current_link.is_symlink():
            self.current_link.unlink()
        
        # 새 링크 생성 (상대 경로)
        self.current_link.symlink_to(f"versions/{version}")
        print(f"[INFO] Updated current -> versions/{version}")
    
    def list_versions(self) -> List[str]:
        """모든 버전 목록"""
        if not self.versions_dir.exists():
            return []
        
        versions = [d.name for d in self.versions_dir.iterdir() 
                   if d.is_dir() and (d / "manifest.json").exists()]
        return sorted(versions)
    
    def get_version_info(self, version: str) -> Optional[Dict]:
        """버전 정보 조회"""
        manifest_file = self.versions_dir / version / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
