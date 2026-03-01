"""
Image Downloader (Simplified Version)
상품 이미지 다운로드 및 관리
"""

import os
import json
import hashlib
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from crawler import DATA_DIR


class ImageDownloader:
    """이미지 다운로드 관리 (Requests 기반)"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    TIMEOUT = 10
    
    def __init__(self):
        self.versions_dir = DATA_DIR / "versions"
        self.master_dir = DATA_DIR / "master"
        self.master_images_dir = self.master_dir / "images" / "products"
        self.master_images_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress = {
            "started_at": None,
            "total": 0,
            "completed": 0,
            "failed": 0,
            "cached": 0,
            "in_progress": False,
            "failed_products": [],
            "last_updated": None
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.cocodalin.com/"
        })
    
    def download_for_version(self, version: str) -> Dict:
        """특정 버전의 모든 이미지 다운로드"""
        version_dir = self.versions_dir / version
        products_file = version_dir / "products.json"
        
        if not products_file.exists():
            print(f"[ERROR] Version {version} not found")
            return self.progress
        
        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        version_images_dir = version_dir / "images" / "products"
        version_images_dir.mkdir(parents=True, exist_ok=True)
        
        # 진행 상황 초기화
        self.progress = {
            "started_at": datetime.now().isoformat(),
            "total": len(products),
            "completed": 0,
            "failed": 0,
            "cached": 0,
            "in_progress": True,
            "failed_products": [],
            "last_updated": datetime.now().isoformat()
        }
        
        print(f"[INFO] Downloading images for version {version}")
        print(f"       Total products: {len(products)}")
        
        for i, product in enumerate(products):
            status, image_hash = self._download_single_image(
                product, version_images_dir
            )
            
            product['image_status'] = status
            product['image_hash'] = image_hash
            
            if status in ['downloaded', 'cached']:
                if status == 'cached':
                    self.progress['cached'] += 1
                self.progress['completed'] += 1
            else:
                self.progress['failed'] += 1
                self.progress['failed_products'].append({
                    'product_id': product['product_id'],
                    'error': status
                })
            
            # 진행 상황 출력
            done = i + 1
            if done % 20 == 0 or done == len(products):
                print(f"       Progress: {done}/{len(products)} "
                      f"(success: {self.progress['completed']}, failed: {self.progress['failed']})")
                
            # 서버 부하 방지
            time.sleep(0.1)
        
        # 결과 저장
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        self._update_manifest(version)
        
        self.progress['in_progress'] = False
        self.progress['last_updated'] = datetime.now().isoformat()
        
        print(f"[INFO] Download completed: {self.progress['completed']} success, "
              f"{self.progress['failed']} failed")
        
        return self.progress
    
    def _download_single_image(self, product: Dict, 
                               version_images_dir: Path) -> tuple:
        """단일 이미지 다운로드"""
        product_id = product['product_id']
        image_url = product.get('image_url')
        
        if not image_url:
            return ('failed:no_url', None)
        
        version_path = version_images_dir / f"{product_id}.jpg"
        master_path = self.master_images_dir / f"{product_id}.jpg"
        
        # 캐시 확인
        if master_path.exists():
            try:
                if not version_path.exists():
                    os.link(master_path, version_path)
                image_hash = self._calculate_hash(master_path)
                return ('cached', image_hash)
            except:
                pass
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(image_url, timeout=self.TIMEOUT)
                
                if response.status_code == 200:
                    content = response.content
                    if len(content) < 500:
                        return ('failed:too_small', None)
                    
                    with open(version_path, 'wb') as f:
                        f.write(content)
                    
                    if not master_path.exists():
                        with open(master_path, 'wb') as f:
                            f.write(content)
                            
                    image_hash = hashlib.sha256(content).hexdigest()
                    return ('downloaded', image_hash)
                
                elif response.status_code == 404:
                    return ('failed:404', None)
                elif response.status_code == 403:
                    return ('failed:403', None)
                    
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    return (f"error:{str(e)[:50]}", None)
                    
        return ('failed:unknown', None)
    
    def _calculate_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _update_manifest(self, version: str) -> None:
        manifest_file = self.versions_dir / version / "manifest.json"
        if not manifest_file.exists():
            return
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        manifest['stats']['images_count'] = self.progress['total']
        manifest['stats']['images_downloaded'] = self.progress['completed']
        manifest['stats']['images_failed'] = self.progress['failed']
        
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
