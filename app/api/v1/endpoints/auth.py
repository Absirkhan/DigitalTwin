"""
Authentication endpoints with Google OAuth
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import Token, UserResponse, GoogleAuthURL, GoogleCallback
from app.services.auth import (
    get_google_auth_url,
    exchange_code_for_tokens,
    create_or_update_user_from_google,
    create_access_token,
    get_current_user_bearer,
    refresh_google_tokens
)

router = APIRouter()


@router.get("/google/login", response_model=GoogleAuthURL)
async def google_login():
    """Get Google OAuth authorization URL"""
    auth_url = get_google_auth_url()
    return GoogleAuthURL(auth_url=auth_url)


@router.get("/google/callback")
async def google_callback(code: str, state: str = None, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        print(f"DEBUG: Received callback with code: {code[:10]}...")  # Log first 10 chars
        
        # Debug: Check if settings are loaded correctly
        from app.core.config import settings
        print(f"DEBUG: GOOGLE_CLIENT_ID: {settings.GOOGLE_CLIENT_ID[:10]}..." if settings.GOOGLE_CLIENT_ID else "DEBUG: GOOGLE_CLIENT_ID is empty!")
        print(f"DEBUG: GOOGLE_CLIENT_SECRET: {'***' if settings.GOOGLE_CLIENT_SECRET else 'DEBUG: GOOGLE_CLIENT_SECRET is empty!'}")
        print(f"DEBUG: GOOGLE_REDIRECT_URI: {settings.GOOGLE_REDIRECT_URI}")
        
        # Exchange code for tokens and user info
        oauth_data = await exchange_code_for_tokens(code)
        user_info = oauth_data['user_info']
        tokens = oauth_data['tokens']
        
        print(f"DEBUG: Got user info for: {user_info.get('email')}")
        
        # Create or update user
        user = await create_or_update_user_from_google(db, user_info, tokens)
        
        print(f"DEBUG: Created/updated user with ID: {user.id}")
        
        # Create JWT access token
        access_token = create_access_token(data={"sub": user.email})
        
        print(f"DEBUG: Created access token: {access_token[:20]}...")
        
        # Return redirect with token in URL - you can copy this token from the browser address bar
        redirect_url = f"http://localhost:8000/api/v1/auth/token-received?access_token={access_token}&user_id={user.id}&email={user.email}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        print(f"DEBUG: Error in callback: {str(e)}")
        print(f"DEBUG: Error type: {type(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        # Redirect to error page with detailed error
        error_url = f"http://localhost:8000/auth/error?error={str(e)}"
        return RedirectResponse(url=error_url)


@router.post("/google/token", response_model=Token)
async def google_token_exchange(callback_data: GoogleCallback, db: Session = Depends(get_db)):
    """Exchange Google authorization code for JWT token (for API clients)"""
    try:
        # Exchange code for tokens and user info
        oauth_data = await exchange_code_for_tokens(callback_data.code)
        user_info = oauth_data['user_info']
        tokens = oauth_data['tokens']
        
        # Create or update user
        user = await create_or_update_user_from_google(db, user_info, tokens)
        
        # Create JWT access token
        access_token = create_access_token(data={"sub": user.email})
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/token-received")
async def token_received(access_token: str, user_id: int = None, email: str = None):
    """Endpoint to receive the access token after OAuth callback"""
    return {
        "message": "Authentication successful! Use the access_token below for API requests.",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": email,
        "usage_instructions": {
            "header": "Authorization: Bearer " + access_token,
            "example_request": f"curl -H 'Authorization: Bearer {access_token}' http://localhost:8000/api/v1/auth/me"
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user_bearer)):
    """Get current user information"""
    return current_user


@router.get("/debug/tokens")
async def debug_user_tokens(current_user = Depends(get_current_user_bearer)):
    """Debug endpoint to check user's stored tokens"""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "has_tokens": bool(current_user.oauth_tokens),
        "token_keys": list(current_user.oauth_tokens.keys()) if current_user.oauth_tokens else [],
        "bot_name": current_user.bot_name
    }


@router.post("/refresh-tokens", response_model=dict)
async def refresh_tokens(current_user = Depends(get_current_user_bearer), db: Session = Depends(get_db)):
    """Refresh Google OAuth tokens"""
    try:
        tokens = await refresh_google_tokens(db, current_user)
        return {"message": "Tokens refreshed successfully", "tokens": tokens}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/logout")
async def logout(current_user = Depends(get_current_user_bearer)):
    """Logout user (client should delete the token)"""
    return {"message": "Logged out successfully"}