#!/usr/bin/env python3
"""
OAuth Handler - Google API OAuth 2.0 驗證處理模組
此模組提供 Google API 統一的 OAuth 驗證流程
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, List

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class OAuthHandler:
    """
    Google OAuth 2.0 驗證處理器
    
    使用方式：
    ```python
    from oauth_handler import OAuthHandler
    
    handler = OAuthHandler(
        credentials_path='path/to/credentials.json',
        token_path='path/to/token.pickle'
    )
    
    # 獲取驗證後的 creds
    creds = handler.get_credentials()
    
    # 或使用上下文管理器
    with OAuthHandler() as handler:
        service = handler.build_service('calendar', 'v3')
    ```
    """
    
    DEFAULT_SCOPES = [
        'https://www.googleapis.com/auth/calendar',
    ]
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        scopes: Optional[List[str]] = None
    ):
        """
        初始化 OAuthHandler
        
        Args:
            credentials_path: Google Cloud Console 下載的 credentials.json 路徑
            token_path: 存儲 access token 的 pickle 文件路徑
            scopes: OAuth 權限範圍列表
        """
        self.workspace = Path.home() / '.openclaw' / 'workspace'
        
        # 預設路徑
        if credentials_path is None:
            credentials_path = self.workspace / 'scripts' / 'calendar' / 'credentials.json'
        if token_path is None:
            token_path = self.workspace / 'scripts' / 'calendar' / 'token.pickle'
        
        self.credentials_path = str(credentials_path)
        self.token_path = str(token_path)
        self.scopes = scopes or self.DEFAULT_SCOPES
        
        self._creds = None
    
    def get_credentials(self, force_reauth: bool = False):
        """
        獲取或刷新 Google API 認證憑證
        
        Args:
            force_reauth: 是否強制重新驗證（刪除現有 token）
            
        Returns:
            google.auth.credentials: 驗證通過的憑證對象，None 表示需要用户授权
        """
        creds = None
        
        # 檢查是否需要強制重新驗證
        if force_reauth and os.path.exists(self.token_path):
            os.remove(self.token_path)
            logger.info("已刪除舊 token，強制重新驗證")
        
        # 嘗試載入已存在的 token
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("已載入現有 token")
            except Exception as e:
                logger.warning(f"無法載入 token: {e}")
        
        # 驗證憑證是否有效
        if creds and creds.valid:
            return creds
        
        # 嘗試刷新過期憑證
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("正在刷新過期憑證...")
                creds.refresh(Request())
                self._save_credentials(creds)
                logger.info("憑證刷新成功")
                return creds
            except Exception as e:
                logger.warning(f"無法刷新憑證: {e}")
        
        # 需要用戶授權
        return None
    
    def authenticate(self, open_browser: bool = True):
        """
        執行完整的 OAuth 2.0 驗證流程
        
        Args:
            open_browser: 是否自動打開瀏覽器
            
        Returns:
            google.auth.credentials: 驗證後的憑證
            
        Raises:
            FileNotFoundError: credentials.json 不存在
        """
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"找不到 credentials.json: {self.credentials_path}\n"
                "請到 Google Cloud Console (https://console.cloud.google.com/) "
                "下載並放置於此路徑"
            )
        
        logger.info("啟動 OAuth 驗證流程...")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_path,
            self.scopes
        )
        
        if open_browser:
            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                prompt='consent'
            )
        else:
            creds = flow.run_console()
        
        self._save_credentials(creds)
        self._creds = creds
        
        logger.info("OAuth 驗證成功")
        return creds
    
    def build_service(self, service_name: str, version: str, credentials=None):
        """
        建立 Google API 服務對象
        
        Args:
            service_name: 服務名稱 (如 'calendar', 'sheets')
            version: API 版本 (如 'v3', 'v4')
            credentials: 可選的 credentials對象，若未提供則自動獲取
            
        Returns:
            googleapiclient.discovery.Resource: API 服務對象
        """
        from googleapiclient.discovery import build
        
        creds = credentials or self.get_credentials()
        
        if not creds or not creds.valid:
            creds = self.authenticate()
        
        service = build(service_name, version, credentials=creds)
        return service
    
    def _save_credentials(self, creds):
        """保存憑證到 token.pickle"""
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        with open(self.token_path, 'wb') as token:
            pickle.dump(creds, token)
        os.chmod(self.token_path, 0o600)  # 僅擁有者可讀寫
        logger.debug(f"憑證已保存至: {self.token_path}")
    
    def revoke(self):
        """撤銷當前憑證"""
        if self._creds and self._creds.valid:
            try:
                self._creds.revoke(Request())
                logger.info("憑證已撤銷")
            except Exception as e:
                logger.warning(f"無法撤銷憑證: {e}")
        
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
            logger.info(f"已刪除 token 文件: {self.token_path}")
    
    def is_authenticated(self) -> bool:
        """檢查是否已通過驗證"""
        creds = self.get_credentials()
        return creds is not None and creds.valid
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        pass  # 不自動關閉，保持長连接


# ============================================================
# 便捷函數
# ============================================================

def quick_auth(
    credentials_path: str = None,
    scopes: List[str] = None
):
    """
    快速驗證並返回 Calendar API service
    
    Args:
        credentials_path: credentials.json 路徑
        scopes: 權限範圍
        
    Returns:
        Google Calendar API service 對象
    """
    handler = OAuthHandler(
        credentials_path=credentials_path,
        scopes=scopes or ['https://www.googleapis.com/auth/calendar']
    )
    return handler.build_service('calendar', 'v3')


if __name__ == '__main__':
    # 測試範例
    print("Google Calendar OAuth Handler Test")
    print("=" * 50)
    
    handler = OAuthHandler()
    
    if handler.is_authenticated():
        print("✅ 已通過驗證")
        # 可以進一步操作
    else:
        print("❌ 未通過驗證，請運行 authenticate()")
        print(f"\n📝 請確保 credentials.json 位於：{handler.credentials_path}")
