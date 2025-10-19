"""
Authentication service with Google OAuth
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenData, UserCreate

# OAuth2 Bearer token scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login", 
    auto_error=False,
    description="Enter your Bearer token (without 'Bearer ' prefix)"
)

# HTTP Bearer scheme for cleaner Swagger UI
bearer_scheme = HTTPBearer(auto_error=False, description="JWT Bearer Token")

# Google OAuth2 configuration
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
    }
}

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile', 
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly'
]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def get_google_auth_url() -> str:
    """Generate Google OAuth authorization URL"""
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    # Generate a random state parameter for security
    state = secrets.token_urlsafe(32)
    
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state,
        prompt='consent'
    )
    
    return authorization_url


async def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify Google ID token and return user info"""
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        return idinfo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token: {str(e)}"
        )


async def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access tokens"""
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    try:
        # Suppress OAuth scope warnings
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="oauthlib")
            flow.fetch_token(code=code)
        
        # Get user info using the access token
        credentials = flow.credentials
        
        # Get user profile information
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://www.googleapis.com/oauth2/v1/userinfo',
                headers={'Authorization': f'Bearer {credentials.token}'}
            )
            response.raise_for_status()
            user_info = response.json()
        
        return {
            'user_info': user_info,
            'tokens': {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code for tokens: {str(e)}"
        )


async def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


async def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    return db.query(User).filter(User.google_id == google_id).first()


async def create_or_update_user_from_google(db: Session, user_info: Dict[str, Any], tokens: Dict[str, Any]) -> User:
    """Create or update user from Google OAuth data"""
    google_id = user_info.get('id')
    email = user_info.get('email')
    full_name = user_info.get('name', '')
    profile_picture = user_info.get('picture')
    
    print(f"DEBUG: Looking for user with Google ID: {google_id} or email: {email}")
    
    # Check if user exists by Google ID first, then by email
    user = await get_user_by_google_id(db, google_id)
    if not user:
        user = await get_user_by_email(db, email)
    
    if user:
        # Update existing user
        print(f"DEBUG: Updating existing user {user.id} with new tokens")
        print(f"DEBUG: Old tokens: {bool(user.oauth_tokens)}")
        user.google_id = google_id
        user.email = email
        user.full_name = full_name
        user.profile_picture = profile_picture
        user.oauth_tokens = tokens  # This should update the tokens
        user.is_active = True
        print(f"DEBUG: New tokens set: {bool(tokens)}")
    else:
        # Create new user
        print(f"DEBUG: Creating new user for email: {email}")
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            profile_picture=profile_picture,
            oauth_tokens=tokens,
            is_active=True
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    print(f"DEBUG: User saved/updated with tokens: {bool(user.oauth_tokens)}")
    return user


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current user from JWT token"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_bearer(credentials = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
    """Get current user from Bearer token (for Swagger UI)"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def refresh_google_tokens(db: Session, user: User) -> Dict[str, Any]:
    """Refresh Google OAuth tokens"""
    if not user.oauth_tokens or 'refresh_token' not in user.oauth_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'refresh_token': user.oauth_tokens['refresh_token'],
                    'grant_type': 'refresh_token'
                }
            )
            response.raise_for_status()
            tokens = response.json()
        
        # Update stored tokens
        user.oauth_tokens.update({
            'access_token': tokens['access_token'],
            'token_type': tokens.get('token_type', 'Bearer')
        })
        
        if 'refresh_token' in tokens:
            user.oauth_tokens['refresh_token'] = tokens['refresh_token']
        
        db.commit()
        return user.oauth_tokens
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to refresh tokens: {str(e)}"
        )