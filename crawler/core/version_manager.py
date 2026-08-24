"""
Version Manager
데이터 버전 관리를 담당합니다.
"""

import hashlib
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from crawler import DATA_DIR


class VersionManager:
    """버전별 데이터 관리"""

    def __init__(self):
        self.versions_dir = DATA_DIR / 'versions'
        self.master_dir = DATA_DIR / 'master'
        self.current_link = DATA_DIR / 'current'

        # 디렉토리 생성
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.master_dir.mkdir(parents=True, exist_ok=True)
        (self.master_dir / 'images' / 'products').mkdir(parents=True, exist_ok=True)

    def get_version_name(self, products: List[Dict]) -> str:
        """상품 목록에서 버전명 추출 (할인 시작일 기준)"""
        from_dates = [p.get('from_date', '') for p in products if p.get('from_date')]
        if not from_dates:
            return datetime.now().strftime('%Y-%m-%d')

        # 가장 흔한 시작일 찾기
        most_common = Counter(from_dates).most_common(1)[0][0]
        # 2026.01.05 -> 2026-01-05
        return most_common.replace('.', '-')

    @staticmethod
    def get_data_revision(products: List[Dict]) -> str:
        """상품 내용으로부터 결정적인 데이터 revision을 생성한다.

        할인 주차를 나타내는 ``version``은 같은 값으로 유지될 수 있으므로,
        클라이언트 캐시 무효화에는 상품 내용 전체의 해시를 별도로 사용한다.
        상품 순서만 달라진 경우에는 같은 revision을 유지한다.
        """
        normalized_products = sorted(
            products,
            key=lambda product: str(product.get('product_id', '')),
        )
        payload = json.dumps(
            normalized_products,
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        return f'sha256:{hashlib.sha256(payload.encode()).hexdigest()}'

    @staticmethod
    def get_catalog_revision(products: List[Dict]) -> str:
        """Generate a revision from source-derived catalog fields only.

        Image download state and historical annotations change after a snapshot
        is created, so they must not decide the immutable snapshot directory.
        """
        generated_fields = {
            'discount_count',
            'first_seen_version',
            'image_hash',
            'image_status',
            'local_image_path',
        }
        normalized_products = sorted(
            (
                {
                    key: value
                    for key, value in product.items()
                    if key not in generated_fields
                }
                for product in products
            ),
            key=lambda product: str(product.get('product_id', '')),
        )
        payload = json.dumps(
            normalized_products,
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        return f'sha256:{hashlib.sha256(payload.encode()).hexdigest()}'

    def get_discount_period(self, products: List[Dict]) -> Dict[str, str]:
        """할인 기간 추출"""
        from_dates = [p.get('from_date', '') for p in products if p.get('from_date')]
        to_dates = [p.get('to_date', '') for p in products if p.get('to_date')]

        return {
            'from': min(from_dates) if from_dates else '',
            'to': max(to_dates) if to_dates else '',
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
        except (TypeError, ValueError):
            return None

    def create_version(self, products: List[Dict], categories: List[Dict]) -> str:
        """새 버전 생성"""
        sale_version = self.get_version_name(products)
        previous_storage_version = self.get_current_storage_version()

        # 히스토리 로드
        history = self.load_discount_history()
        previous_products = self.load_current_products()

        # 상품 분류
        categorized = self.categorize_products(products, previous_products, history)

        catalog_revision = self.get_catalog_revision(products)

        # 상품에 메타데이터 추가
        products = self.enrich_products(products, history, sale_version)
        storage_version = self.get_storage_version_name(sale_version, catalog_revision)
        version_dir = self.versions_dir / storage_version

        # 같은 할인 주차라도 내용이 다르면 revision suffix가 붙은 새 디렉토리를
        # 사용한다. 이미 배포된 스냅샷을 절대 덮어쓰지 않는다.
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / 'images' / 'products').mkdir(parents=True, exist_ok=True)

        # 상품 저장
        products_file = version_dir / 'products.json'
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        # 카테고리 저장
        categories_file = version_dir / 'categories.json'
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

        # 매니페스트 생성
        manifest = self.create_manifest(
            sale_version,
            products,
            categories,
            categorized,
            storage_version=storage_version,
            previous_version=self.get_previous_version_for_snapshot(
                storage_version, previous_storage_version
            ),
            catalog_revision=catalog_revision,
        )
        manifest_file = version_dir / 'manifest.json'
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # 히스토리 업데이트
        self.update_discount_history(products, sale_version, history)

        # current 심볼릭 링크 업데이트
        self.update_current_link(storage_version)

        print(f'[INFO] Created version: {storage_version}')
        print(f'       Sale version: {sale_version}')
        print(f'       Products: {len(products)}')
        print(f'       New: {len(categorized["new"])}, Returning: {len(categorized["returning"])}')

        return storage_version

    def get_current_storage_version(self) -> Optional[str]:
        """현재 symlink가 가리키는 불변 스냅샷 디렉토리 이름."""
        if not self.current_link.is_symlink():
            return None
        try:
            return Path(os.readlink(self.current_link)).name
        except OSError:
            return None

    def get_previous_version_for_snapshot(
        self,
        storage_version: str,
        current_storage_version: Optional[str],
    ) -> Optional[str]:
        if current_storage_version != storage_version:
            return current_storage_version
        existing_manifest = self.get_version_info(storage_version) or {}
        return existing_manifest.get('previous_version')

    def _read_catalog_revision(self, version_dir: Path) -> Optional[str]:
        manifest_file = version_dir / 'manifest.json'
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            catalog_revision = manifest.get('catalog_revision')
            if catalog_revision:
                return catalog_revision
            with open(version_dir / 'products.json', 'r', encoding='utf-8') as f:
                return self.get_catalog_revision(json.load(f))
        except (OSError, ValueError, TypeError):
            return None

    def get_storage_version_name(self, sale_version: str, catalog_revision: str) -> str:
        """내용이 다른 동일 주차 스냅샷에 revision suffix를 부여한다."""
        base_dir = self.versions_dir / sale_version
        base_manifest = base_dir / 'manifest.json'
        if not base_manifest.exists():
            return sale_version

        if self._read_catalog_revision(base_dir) == catalog_revision:
            return sale_version

        revision_hash = catalog_revision.removeprefix('sha256:')
        for prefix_length in (12, 16, 24, 64):
            candidate = f'{sale_version}--{revision_hash[:prefix_length]}'
            candidate_dir = self.versions_dir / candidate
            manifest_file = candidate_dir / 'manifest.json'
            if not manifest_file.exists():
                return candidate
            if self._read_catalog_revision(candidate_dir) == catalog_revision:
                return candidate

        raise RuntimeError(f'Unable to allocate immutable snapshot for {sale_version}')

    def create_manifest(
        self,
        version: str,
        products: List[Dict],
        categories: List[Dict],
        categorized: Dict,
        storage_version: Optional[str] = None,
        previous_version: Optional[str] = None,
        catalog_revision: Optional[str] = None,
    ) -> Dict:
        """매니페스트 생성"""
        discount_period = self.get_discount_period(products)
        next_crawl = self.get_next_crawl_date(products)

        data_revision = self.get_data_revision(products)

        return {
            'version': version,
            'storage_version': storage_version or version,
            'catalog_revision': catalog_revision or self.get_catalog_revision(products),
            'data_revision': data_revision,
            'created_at': datetime.now().isoformat(),
            'discount_period': discount_period,
            'stats': {
                'products_count': len(products),
                'images_count': 0,  # 이미지 다운로드 후 업데이트
                'images_downloaded': 0,
                'images_failed': 0,
                'new_products': len(categorized['new']),
                'returning_products': len(categorized['returning']),
                'continuing_products': len(categorized['continuing']),
                'categories_count': len(categories),
            },
            'files': {
                'products': 'products.json',
                'categories': 'categories.json',
                'images_dir': 'images/products/',
            },
            'checksum': {'products': data_revision},
            'previous_version': previous_version,
            'next_crawl_suggested': next_crawl,
        }

    def categorize_products(
        self, current: List[Dict], previous: List[Dict], history: Dict
    ) -> Dict[str, Set[int]]:
        """상품 분류: new, returning, continuing, removed"""
        current_ids = {p['product_id'] for p in current}
        previous_ids = {p['product_id'] for p in previous}
        all_seen_ids = set(int(k) for k in history.keys())

        new = current_ids - all_seen_ids
        returning = (current_ids - previous_ids) & all_seen_ids
        continuing = current_ids & previous_ids
        removed = previous_ids - current_ids

        return {'new': new, 'returning': returning, 'continuing': continuing, 'removed': removed}

    def enrich_products(self, products: List[Dict], history: Dict, version: str) -> List[Dict]:
        """상품에 메타데이터 추가"""
        for product in products:
            pid = str(product['product_id'])

            if pid in history:
                product['first_seen_version'] = history[pid].get('first_seen', version)
                occurrences = history[pid].get('occurrences', [])
                occurrence_versions = {item.get('version') for item in occurrences}
                product['discount_count'] = len(occurrences) + (
                    0 if version in occurrence_versions else 1
                )
            else:
                product['first_seen_version'] = version
                product['discount_count'] = 1

            # 이미지 관련 필드 초기화
            product['local_image_path'] = f'images/products/{product["product_id"]}.jpg'
            product['image_status'] = 'pending'
            product['image_hash'] = None

        return products

    def load_discount_history(self) -> Dict:
        """할인 히스토리 로드"""
        history_file = self.master_dir / 'discount_history.json'
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def update_discount_history(self, products: List[Dict], version: str, history: Dict) -> None:
        """할인 히스토리 업데이트"""
        for product in products:
            pid = str(product['product_id'])

            occurrence = {
                'version': version,
                'from_date': product.get('from_date', ''),
                'to_date': product.get('to_date', ''),
                'normal_price': product.get('normal_price', 0),
                'sale_price': product.get('sale_price', 0),
                'discount': product.get('discount', 0),
            }

            if pid not in history:
                history[pid] = {
                    'product_id': product['product_id'],
                    'product_name': product.get('product_name', ''),
                    'category_name': product.get('category_name', ''),
                    'first_seen': version,
                    'last_seen': version,
                    'occurrences': [occurrence],
                }
            else:
                # 같은 버전이 이미 있으면 스킵
                existing_versions = [o['version'] for o in history[pid]['occurrences']]
                if version not in existing_versions:
                    history[pid]['occurrences'].append(occurrence)
                    history[pid]['last_seen'] = version

        # 저장
        history_file = self.master_dir / 'discount_history.json'
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def load_current_products(self) -> List[Dict]:
        """현재 버전의 상품 로드"""
        if not self.current_link.exists():
            return []

        products_file = self.current_link / 'products.json'
        if products_file.exists():
            with open(products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def update_current_link(self, version: str) -> None:
        """current 심볼릭 링크 업데이트"""
        # 기존 링크 제거
        if self.current_link.exists() or self.current_link.is_symlink():
            self.current_link.unlink()

        # 새 링크 생성 (상대 경로)
        self.current_link.symlink_to(f'versions/{version}')
        print(f'[INFO] Updated current -> versions/{version}')

    def list_versions(self) -> List[str]:
        """모든 버전 목록"""
        if not self.versions_dir.exists():
            return []

        versions = [
            d.name
            for d in self.versions_dir.iterdir()
            if d.is_dir() and (d / 'manifest.json').exists()
        ]
        return sorted(versions)

    def get_version_info(self, version: str) -> Optional[Dict]:
        """버전 정보 조회"""
        manifest_file = self.versions_dir / version / 'manifest.json'
        if manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
