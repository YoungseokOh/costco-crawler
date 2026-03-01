"""
설정 로더
YAML 설정 파일을 로드하고 관리합니다.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from crawler import CONFIG_DIR


class Config:
    """설정 관리 클래스"""
    
    _instance: Optional["Config"] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """설정 파일 로드"""
        default_config = CONFIG_DIR / "default.yaml"
        
        if default_config.exists():
            with open(default_config, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
    
    @property
    def api(self) -> Dict[str, Any]:
        return self._config.get('api', {})
    
    @property
    def request(self) -> Dict[str, Any]:
        return self._config.get('request', {})
    
    @property
    def storage(self) -> Dict[str, Any]:
        return self._config.get('storage', {})
    
    def get(self, key: str, default: Any = None) -> Any:
        """점 표기법으로 설정 값 가져오기 (예: 'api.base_url')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default


# 싱글톤 인스턴스
config = Config()
