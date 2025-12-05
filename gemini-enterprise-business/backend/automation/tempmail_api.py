"""
Gemini Ultra Gateway - Temporary Email API Client
Supports multiple temporary email providers for automatic verification
"""

import re
import time
import json
import base64
import logging
from typing import Optional, Dict, List, Callable
from urllib.parse import urlparse, parse_qs

import httpx

logger = logging.getLogger("gemini.automation.tempmail")


class TempMailClient:
    """
    Client for interacting with temporary email services
    Used for automatic verification code retrieval
    """
    
    def __init__(
        self,
        tempmail_url: str,
        worker_url: Optional[str] = None,
    ):
        """
        Initialize the TempMail client
        
        Args:
            tempmail_url: URL with JWT token for the temp mail service
            worker_url: Optional worker URL for the temp mail service
        """
        self.tempmail_url = tempmail_url
        self.worker_url = worker_url
        self.jwt_token = self._extract_jwt_from_url(tempmail_url)
        self.email_address = self._extract_email_from_jwt(self.jwt_token)
        self.last_max_id = 0
        
        # HTTP client
        self._client = httpx.Client(timeout=30.0)
    
    def _extract_jwt_from_url(self, url: str) -> Optional[str]:
        """Extract JWT token from URL parameters"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'jwt' in params:
                return params['jwt'][0]
        except Exception as e:
            logger.debug(f"Failed to extract JWT from URL: {e}")
        return None
    
    def _extract_email_from_jwt(self, jwt_token: Optional[str]) -> Optional[str]:
        """Extract email address from JWT payload"""
        if not jwt_token:
            return None
        
        try:
            # JWT format: header.payload.signature
            parts = jwt_token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (base64)
            payload = parts[1]
            padding = '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding)
            data = json.loads(decoded)
            
            return data.get('address')
        except Exception as e:
            logger.debug(f"Failed to extract email from JWT: {e}")
        return None
    
    def get_email_address(self) -> Optional[str]:
        """Get the temporary email address"""
        return self.email_address
    
    def get_messages(self) -> List[Dict]:
        """
        Fetch messages from the temporary email inbox
        
        Returns:
            List of message dictionaries
        """
        if not self.jwt_token:
            logger.error("No JWT token available")
            return []
        
        try:
            # Determine API endpoint
            if self.worker_url:
                api_url = f"{self.worker_url}/api/messages"
            else:
                parsed = urlparse(self.tempmail_url)
                api_url = f"{parsed.scheme}://{parsed.netloc}/api/messages"
            
            response = self._client.get(
                api_url,
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch messages: {response.status_code}")
                return []
            
            data = response.json()
            return data.get('messages', data.get('data', []))
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def get_message_content(self, message_id: str) -> Optional[str]:
        """
        Get the content of a specific message
        
        Args:
            message_id: ID of the message to retrieve
            
        Returns:
            Message content as string
        """
        if not self.jwt_token:
            return None
        
        try:
            if self.worker_url:
                api_url = f"{self.worker_url}/api/messages/{message_id}"
            else:
                parsed = urlparse(self.tempmail_url)
                api_url = f"{parsed.scheme}://{parsed.netloc}/api/messages/{message_id}"
            
            response = self._client.get(
                api_url,
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Try different content fields
            content = (
                data.get('text') or 
                data.get('content') or 
                data.get('body') or
                data.get('html', '')
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Error fetching message content: {e}")
            return None
    
    def get_verification_code(
        self,
        timeout: int = 120,
        retry_mode: bool = False,
        extract_code_func: Optional[Callable[[str], Optional[str]]] = None,
    ) -> Optional[str]:
        """
        Wait for and extract verification code from incoming email
        
        Args:
            timeout: Maximum time to wait in seconds
            retry_mode: If True, only try once without waiting
            extract_code_func: Custom function to extract code from text
            
        Returns:
            Verification code if found, None otherwise
        """
        if extract_code_func is None:
            extract_code_func = self._default_extract_code
        
        start_time = time.time()
        max_attempts = 1 if retry_mode else (timeout // 10)
        
        for attempt in range(max_attempts):
            if time.time() - start_time > timeout:
                break
            
            # Fetch messages
            messages = self.get_messages()
            
            # Filter new messages
            new_messages = [
                m for m in messages 
                if int(m.get('id', 0)) > self.last_max_id
            ]
            
            # Update last seen ID
            if messages:
                max_id = max(int(m.get('id', 0)) for m in messages)
                if max_id > self.last_max_id:
                    self.last_max_id = max_id
            
            # Check each new message for verification code
            for msg in new_messages:
                subject = msg.get('subject', '').lower()
                
                # Skip non-verification emails
                if not any(kw in subject for kw in ['verif', 'code', 'otp', '验证']):
                    continue
                
                # Get message content
                msg_id = msg.get('id')
                content = self.get_message_content(str(msg_id))
                
                if content:
                    code = extract_code_func(content)
                    if code:
                        logger.info(f"Found verification code: {code}")
                        return code
            
            if not retry_mode:
                logger.debug(f"Waiting for verification email... ({attempt + 1}/{max_attempts})")
                time.sleep(10)
        
        logger.warning("Verification code not found within timeout")
        return None
    
    def _default_extract_code(self, text: str) -> Optional[str]:
        """
        Default function to extract verification code from text
        
        Supports various formats:
        - 6-digit alphanumeric codes
        - Chinese and English prompts
        """
        # Line-by-line matching
        lines = text.splitlines()
        for line in lines:
            line_lower = line.lower()
            
            # Check for verification code indicators
            indicators = [
                "一次性验证码为",
                "验证码为",
                "您的验证码是",
                "your one-time verification code is",
                "verification code is",
                "code is",
            ]
            
            for indicator in indicators:
                if indicator in line or indicator in line_lower:
                    # Find 6-character alphanumeric code after indicator
                    idx = line_lower.find(indicator.lower())
                    if idx >= 0:
                        sub = line[idx:]
                        matches = re.findall(r'[A-Z0-9]{6}', sub, re.IGNORECASE)
                        if matches:
                            code = matches[0].upper()
                            # Validate: must contain at least one letter
                            if any(c.isalpha() for c in code):
                                return code
        
        # Fallback: search entire text for patterns
        patterns = [
            r'验证码[为是：:]\s*([A-Z0-9]{6})',
            r'code[:\s]+([A-Z0-9]{6})',
            r'([A-Z0-9]{6})\s*is your',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                code = match.group(1).upper()
                if any(c.isalpha() for c in code):
                    return code
        
        return None
    
    def close(self):
        """Close the HTTP client"""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
