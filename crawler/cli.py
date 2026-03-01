"""
크롤러 CLI v2
버전 관리 기능이 포함된 크롤러
"""

import argparse
from datetime import datetime

from crawler.core.fetcher import Fetcher
from crawler.core.storage import Storage
from crawler.core.version_manager import VersionManager
from crawler.core.image_downloader import ImageDownloader


class CrawlerV2:
    """버전 관리 기능이 포함된 크롤러"""
    
    def __init__(self):
        self.fetcher = Fetcher()
        self.storage = Storage()
        self.version_manager = VersionManager()
        self.image_downloader = ImageDownloader()

    
    def run(self, force: bool = False, download_images: bool = True):
        """크롤링 실행"""
        print("=" * 60)
        print(f"[START] COSTIT Crawler v2 - {datetime.now().isoformat()}")
        print("=" * 60)
        
        # 1. 업데이트 확인
        has_update, notice_hash = self.fetcher.check_update()
        
        if not force and not has_update:
            print("[END] No updates. Exiting.")
            return None
        
        # 2. 카테고리 조회
        categories = self.fetcher.fetch_categories()
        if not categories:
            print("[ERROR] Failed to fetch categories")
            return None
        
        # 3. 상품 조회
        products = self.fetcher.fetch_all_products(categories)
        if not products:
            print("[ERROR] No products found")
            return None
        
        # 4. 이미지 URL 추가
        products = self.storage.add_image_urls(products)
        
        # 4.5. 상품명 파싱 추가
        from crawler.utils.name_parser import parse_product_name
        for p in products:
            parsed = parse_product_name(p.get('product_name', ''))
            p['core_name'] = parsed['core_name']
            p['origin'] = parsed['origin']
            p['weight_volume'] = parsed['weight_volume']
            p['quantity'] = parsed['quantity']
            p['others'] = parsed['others']
        
        # 5. 버전 생성
        version = self.version_manager.create_version(products, categories)
        
        # 6. 크롤 로그 저장
        if notice_hash:
            self.storage.save_crawl_log(notice_hash, len(products))
        
        # 7. 이미지 다운로드 (선택적)
        if download_images:
            print("\n[INFO] Starting image download...")
            self.image_downloader.download_for_version(version)
        
        print("=" * 60)
        print(f"[END] Crawling completed - Version: {version}")
        print("=" * 60)
        
        return version
    
    def list_versions(self):
        """모든 버전 목록 출력"""
        versions = self.version_manager.list_versions()
        
        if not versions:
            print("No versions found.")
            return
        
        print(f"Found {len(versions)} versions:\n")
        print(f"{'Version':<15} {'Products':>10} {'Images':>10} {'New':>8} {'Return':>8}")
        print("-" * 55)
        
        for v in versions:
            info = self.version_manager.get_version_info(v)
            if info:
                stats = info.get('stats', {})
                print(f"{v:<15} {stats.get('products_count', 0):>10} "
                      f"{stats.get('images_downloaded', 0):>10} "
                      f"{stats.get('new_products', 0):>8} "
                      f"{stats.get('returning_products', 0):>8}")
    
    def download_images(self, version: str = None):
        """이미지 다운로드"""
        if version is None:
            # 최신 버전
            versions = self.version_manager.list_versions()
            if not versions:
                print("[ERROR] No versions found")
                return
            version = versions[-1]
        
        print(f"[INFO] Downloading images for version: {version}")
        self.image_downloader.download_for_version(version)


def main():
    parser = argparse.ArgumentParser(description='COSTIT Crawler v2')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # crawl 명령어
    crawl_parser = subparsers.add_parser('crawl', help='Run crawler')
    crawl_parser.add_argument('--force', '-f', action='store_true',
                              help='Force crawl regardless of updates')
    crawl_parser.add_argument('--no-images', action='store_true',
                              help='Skip image download')
    
    # list 명령어
    subparsers.add_parser('list', help='List all versions')
    
    # images 명령어
    images_parser = subparsers.add_parser('images', help='Download images')
    images_parser.add_argument('--version', '-v', type=str,
                               help='Version to download images for')
    
    # check 명령어
    subparsers.add_parser('check', help='Check for updates')
    
    args = parser.parse_args()
    
    crawler = CrawlerV2()
    
    if args.command == 'crawl':
        crawler.run(force=args.force, download_images=not args.no_images)
    elif args.command == 'list':
        crawler.list_versions()
    elif args.command == 'images':
        crawler.download_images(args.version)
    elif args.command == 'check':
        has_update, _ = crawler.fetcher.check_update()
        exit(0 if has_update else 1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
