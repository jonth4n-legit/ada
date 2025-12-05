"""
Gemini Ultra Gateway - Session Manager
Manages Gemini Business API sessions and file uploads
"""

import json
import time
import uuid
import logging
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx

from .config import Config, GeminiEndpoints
from .account_pool import Account, get_http_client

logger = logging.getLogger("gemini.session")


def get_common_headers(jwt: str) -> Dict[str, str]:
    """Get common headers for Gemini Business API requests
    
    These headers exactly match what the Gemini Business web app sends.
    """
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "authorization": f"Bearer {jwt}",
        "content-type": "application/json",
        "origin": "https://business.gemini.google",
        "referer": "https://business.gemini.google/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "x-server-timeout": "1800",
    }


@dataclass
class Session:
    """Represents a Gemini Business session"""
    name: str  # Full session name from API
    account_name: str
    config_id: str
    created_at: float
    last_used_at: float
    file_ids: List[str]
    
    @property
    def session_id(self) -> str:
        """Extract session ID from full name"""
        return self.name.split("/")[-1] if "/" in self.name else self.name
    
    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if the session is expired"""
        return time.time() - self.last_used_at > max_age_seconds


class SessionManager:
    """Manages Gemini Business API sessions"""
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}  # conversation_key -> Session
        self._http_client = get_http_client()
    
    async def create_session(self, account: Account) -> Session:
        """Create a new Gemini Business session"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        body = {
            "configId": account.config_id,
            "additionalParams": {"token": "-"},
            "createSessionRequest": {
                "session": {"name": "", "displayName": ""}
            },
        }
        
        logger.debug(f"Creating session for account: {account.name}")
        
        response = await self._http_client.post(
            GeminiEndpoints.CREATE_SESSION,
            headers=headers,
            json=body,
        )
        
        if response.status_code != 200:
            logger.error(f"createSession failed [{account.name}]: {response.status_code} {response.text}")
            if response.status_code in (401, 403, 429):
                account.mark_quota_error(response.status_code, response.text)
            raise Exception(f"createSession failed: {response.status_code}")
        
        data = response.json()
        session_name = data["session"]["name"]
        
        session = Session(
            name=session_name,
            account_name=account.name,
            config_id=account.config_id,
            created_at=time.time(),
            last_used_at=time.time(),
            file_ids=[],
        )
        
        logger.info(f"Session created: {session.session_id} [{account.name}]")
        return session
    
    async def get_or_create_session(
        self, 
        account: Account, 
        conversation_key: str
    ) -> Session:
        """Get existing session or create new one for a conversation"""
        # Check cache
        if conversation_key in self._sessions:
            session = self._sessions[conversation_key]
            if not session.is_expired() and session.account_name == account.name:
                session.last_used_at = time.time()
                return session
            else:
                del self._sessions[conversation_key]
        
        # Create new session
        session = await self.create_session(account)
        self._sessions[conversation_key] = session
        return session
    
    async def upload_file(
        self,
        account: Account,
        session: Session,
        mime_type: str,
        base64_content: str,
    ) -> str:
        """Upload a file to the session, returns file_id"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        ext = mime_type.split("/")[-1] if "/" in mime_type else "bin"
        file_name = f"upload_{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
        
        body = {
            "configId": account.config_id,
            "additionalParams": {"token": "-"},
            "addContextFileRequest": {
                "name": session.name,
                "fileName": file_name,
                "mimeType": mime_type,
                "fileContents": base64_content,
            },
        }
        
        logger.info(f"Uploading file [{mime_type}] to session [{session.session_id}]")
        
        response = await self._http_client.post(
            GeminiEndpoints.ADD_CONTEXT_FILE,
            headers=headers,
            json=body,
        )
        
        if response.status_code != 200:
            logger.error(f"Upload failed [{account.name}]: {response.status_code} {response.text}")
            if response.status_code in (401, 403, 429):
                account.mark_quota_error(response.status_code, response.text)
            raise Exception(f"Upload failed: {response.status_code}")
        
        data = response.json()
        file_id = data.get("addContextFileResponse", {}).get("fileId")
        
        if file_id:
            session.file_ids.append(file_id)
            logger.info(f"File uploaded: {file_id}")
        
        return file_id
    
    async def upload_file_by_url(
        self,
        account: Account,
        session: Session,
        file_url: str,
    ) -> str:
        """Upload a file by URL to the session, returns file_id"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        body = {
            "configId": account.config_id,
            "additionalParams": {"token": "-"},
            "addContextFileRequest": {
                "name": session.name,
                "fileUri": file_url,
            },
        }
        
        logger.info(f"Uploading file by URL to session [{session.session_id}]")
        
        response = await self._http_client.post(
            GeminiEndpoints.ADD_CONTEXT_FILE,
            headers=headers,
            json=body,
        )
        
        if response.status_code != 200:
            logger.error(f"URL upload failed [{account.name}]: {response.status_code} {response.text}")
            if response.status_code in (401, 403, 429):
                account.mark_quota_error(response.status_code, response.text)
            raise Exception(f"URL upload failed: {response.status_code}")
        
        data = response.json()
        file_id = data.get("addContextFileResponse", {}).get("fileId")
        
        if file_id:
            session.file_ids.append(file_id)
            logger.info(f"File uploaded by URL: {file_id}")
        
        return file_id
    
    async def list_session_files(
        self,
        account: Account,
        session: Session,
        filter_type: str = "file_origin_type = AI_GENERATED",
    ) -> List[Dict[str, Any]]:
        """List files in a session"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        body = {
            "configId": account.config_id,
            "additionalParams": {"token": "-"},
            "listSessionFileMetadataRequest": {
                "name": session.name,
                "filter": filter_type,
            },
        }
        
        response = await self._http_client.post(
            GeminiEndpoints.LIST_FILE_METADATA,
            headers=headers,
            json=body,
        )
        
        if response.status_code != 200:
            logger.error(f"List files failed: {response.status_code} {response.text}")
            return []
        
        data = response.json()
        files = data.get("listSessionFileMetadataResponse", {}).get("fileMetadata", [])
        return files
    
    async def download_file(
        self,
        account: Account,
        session: Session,
        file_id: str,
    ) -> Optional[bytes]:
        """Download a file from the session"""
        jwt = await account.jwt_mgr.get()
        headers = get_common_headers(jwt)
        
        # First, get the file metadata to find the download URL
        files = await self.list_session_files(account, session)
        
        full_session = None
        for f in files:
            if f.get("fileId") == file_id:
                full_session = f.get("session")
                break
        
        if not full_session:
            logger.error(f"File not found: {file_id}")
            return None
        
        download_url = (
            f"https://biz-discoveryengine.googleapis.com/download/v1alpha/"
            f"{full_session}:downloadFile?fileId={file_id}&alt=media"
        )
        
        response = await self._http_client.get(download_url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Download failed: {response.status_code} {response.text}")
            return None
        
        return response.content
    
    def get_conversation_key(self, messages: List[Dict]) -> str:
        """Generate a conversation key from messages for session affinity"""
        if not messages:
            return f"empty_{uuid.uuid4().hex[:8]}"
        
        # Use first message to generate key
        first_msg = messages[0].copy()
        content = first_msg.get("content", "")
        
        if isinstance(content, list):
            text_parts = [
                x.get("text", "") 
                for x in content 
                if isinstance(x, dict) and x.get("type") == "text"
            ]
            content = "".join(text_parts)
        
        # Hash the content to create a stable key
        key_data = f"{first_msg.get('role', '')}:{content[:500]}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions"""
        expired_keys = [
            k for k, v in self._sessions.items()
            if v.is_expired(max_age_seconds)
        ]
        for k in expired_keys:
            del self._sessions[k]
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        return {
            "total_sessions": len(self._sessions),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "account": s.account_name,
                    "age_seconds": int(time.time() - s.created_at),
                    "file_count": len(s.file_ids),
                }
                for s in self._sessions.values()
            ],
        }


# Global session manager
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
