"""
Image Downloader (Selenium Version)
실제 브라우저에서 이미지를 로드하여 다운로드
"""

import os
import json
import hashlib
import time
import base64
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from crawler import DATA_DIR


class ImageDownloaderSelenium:
    """Selenium 기반 이미지 다운로더"""
    
    TIMEOUT = 30
    
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
        
        self.driver = None
    
    def _init_driver(self):
        """Selenium WebDriver 초기화"""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Playwright가 설치한 Chromium 경로 사용
        chrome_path = "/home/seok436/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome"
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(self.TIMEOUT)
    
    def _close_driver(self):
        """WebDriver 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
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
        
        print(f"[INFO] Downloading images for version {version} using Selenium")
        print(f"       Total products: {len(products)}")
        
        try:
            self._init_driver()
            
            # 세션 수립을 위해 메인 페이지 방문
            print("[INFO] Opening cocodalin.com to establish session...")
            self.driver.get("https://www.cocodalin.com/")
            time.sleep(3)
            
            # 각 이미지 다운로드
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
                if done % 10 == 0 or done == len(products):
                    print(f"       Progress: {done}/{len(products)} "
                          f"(success: {self.progress['completed']}, failed: {self.progress['failed']})")
                
        finally:
            self._close_driver()
        
        # 결과 저장
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        self._update_manifest(version)
        
        self.progress['in_progress'] = False
        self.progress['last_updated'] = datetime.now().isoformat()
        
        progress_file = version_dir / "image_download_progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)
        
        print(f"[INFO] Download completed: {self.progress['completed']} success, "
              f"{self.progress['failed']} failed")
        
        return self.progress
    
    def _download_single_image(self, product: Dict, 
                               version_images_dir: Path) -> tuple:
        """단일 이미지 다운로드 (JavaScript 이용)"""
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
        
        try:
            # JavaScript로 이미지를 fetch하고 base64로 변환
            script = f'''
            return new Promise((resolve, reject) => {{
                fetch("{image_url}")
                    .then(response => {{
                        if (!response.ok) {{
                            reject("HTTP " + response.status);
                            return;
                        }}
                        return response.blob();
                    }})
                    .then(blob => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.onerror = () => reject("Read error");
                        reader.readAsDataURL(blob);
                    }})
                    .catch(err => reject(err.toString()));
            }});
            '''
            
            result = self.driver.execute_async_script(f'''
                var callback = arguments[arguments.length - 1];
                {script}.then(callback).catch(e => callback("ERROR:" + e));
            ''')
            
            if result and result.startswith("data:image"):
                # Base64 디코딩
                base64_data = result.split(",")[1]
                image_content = base64.b64decode(base64_data)
                
                if len(image_content) < 500:
                    return ('failed:too_small', None)
                
                # 저장
                with open(version_path, 'wb') as f:
                    f.write(image_content)
                
                if not master_path.exists():
                    with open(master_path, 'wb') as f:
                        f.write(image_content)
                
                image_hash = hashlib.sha256(image_content).hexdigest()
                return ('downloaded', image_hash)
            
            elif result and result.startswith("ERROR:"):
                return (f"failed:{result[6:]}", None)
            else:
                return ('failed:unknown_response', None)
                
        except Exception as e:
            return (f"error:{str(e)[:50]}", None)
    
    def _calculate_hash(self, file_path: Path) -> str:
        """파일 해시 계산"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _update_manifest(self, version: str) -> None:
        """매니페스트 업데이트"""
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
