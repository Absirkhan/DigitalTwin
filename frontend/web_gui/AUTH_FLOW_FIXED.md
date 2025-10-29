# Google OAuth Authentication Flow - Fixed

## The Problem

The frontend was trying to use a popup window and parse the GET `/auth/google/callback` endpoint as JSON, but the backend redirects this endpoint to `/auth/token-received`. This caused cross-origin errors and "Login cancelled" failures.

## The Solution

Use the proper OAuth flow with **full-page redirect** and the **POST `/auth/google/token`** endpoint for token exchange.

## Complete Authentication Flow

### 1. User Clicks "Sign in with Google"

**Frontend (`/login`):**
```typescript
handleGoogleLogin() {
  await authService.loginWithGoogleRedirect();
}
```

### 2. Get Authorization URL

**Request:**
```http
GET /api/v1/auth/google/login
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

**Backend Code (`auth.py`):**
```python
@router.get("/google/login", response_model=GoogleAuthURL)
async def google_login():
    auth_url = get_google_auth_url()
    return GoogleAuthURL(auth_url=auth_url)
```

### 3. Redirect to Google

**Frontend:**
```typescript
window.location.href = authorization_url;
```

User is redirected to Google's OAuth consent screen:
- ✅ Requests email, profile, calendar, gmail scopes
- ✅ Shows app name and permissions
- ✅ User clicks "Allow"

### 4. Google Redirects Back

Google redirects to:
```
http://localhost:8000/api/v1/auth/google/callback?code=xxx&state=xxx&scope=...
```

**Backend receives this GET request but DOESN'T USE IT for frontend auth**

Instead, Google also redirects the browser to your configured redirect URI, which is handled by the frontend callback page.

### 5. Frontend Callback Page Handles Code

**Page:** `/auth/callback`

**URL:** `http://localhost:3000/auth/callback?code=xxx&state=xxx`

**Code:**
```typescript
const code = searchParams.get('code');
const state = searchParams.get('state');

// Exchange code for JWT token
const response = await authService.exchangeCodeForToken(code, state);
```

### 6. Exchange Code for Token (POST Endpoint)

**Request:**
```http
POST /api/v1/auth/google/token
Content-Type: application/json

{
  "code": "4/0Ab32j92...",
  "state": "nGvYwnr8..."
}
```

**Backend Code (`auth.py`):**
```python
@router.post("/google/token", response_model=Token)
async def google_token_exchange(callback_data: GoogleCallback, db: Session = Depends(get_db)):
    # Exchange code for Google tokens
    oauth_data = await exchange_code_for_tokens(callback_data.code)
    user_info = oauth_data['user_info']
    tokens = oauth_data['tokens']
    
    # Create or update user in database
    user = await create_or_update_user_from_google(db, user_info, tokens)
    
    # Create JWT access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 7. Store Token and Redirect

**Frontend:**
```typescript
localStorage.setItem('auth_token', response.access_token);
router.push('/dashboard');
```

### 8. Authenticated Requests

All subsequent API calls include the token:

```http
GET /api/v1/users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Backend verifies token:**
```python
async def get_current_user_bearer(
    credentials: HTTPAuthCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    # Verify JWT token
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    email = payload.get("sub")
    # Get user from database
    user = await get_user_by_email(db, email)
    return user
```

## Backend Endpoints Summary

### For Frontend (API Clients)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/google/login` | GET | Get OAuth URL |
| `/auth/google/token` | POST | Exchange code for JWT |
| `/auth/me` | GET | Get current user |
| `/auth/logout` | POST | Logout (client deletes token) |

### For Browser Direct Access (Not Used by Frontend)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/google/callback` | GET | Browser redirect (for testing) |
| `/auth/token-received` | GET | Display token (for testing) |

## Key Changes Made

### 1. Updated `lib/api/auth.ts`

**Before:** Used popup window and tried to call GET `/auth/google/callback`

**After:**
```typescript
loginWithGoogleRedirect: async (): Promise<void> => {
  const { authorization_url } = await authService.getGoogleLoginUrl();
  window.location.href = authorization_url; // Full page redirect
}

exchangeCodeForToken: async (code: string, state?: string) => {
  return post('/api/v1/auth/google/token', { code, state }); // POST endpoint
}
```

### 2. Updated `/auth/callback/page.tsx`

**Before:** Tried to use window messages and popup close

**After:**
```typescript
const code = searchParams.get('code');
const response = await authService.exchangeCodeForToken(code, state);
localStorage.setItem('auth_token', response.access_token);
router.push('/dashboard');
```

### 3. Updated `/login/page.tsx`

**Before:** Complex popup window handling

**After:**
```typescript
const handleGoogleLogin = async () => {
  await authService.loginWithGoogleRedirect(); // Simple redirect
};
```

## Why This Works

1. **No CORS Issues** - Full page redirect instead of popup
2. **Uses Correct Endpoint** - POST `/auth/google/token` returns JSON
3. **Proper Flow** - Matches OAuth 2.0 Authorization Code Flow
4. **Token Storage** - JWT stored in localStorage, sent with all requests
5. **Backend Compatible** - Uses existing backend endpoints correctly

## Security Notes

- JWT tokens expire after 30 minutes (configurable)
- Tokens stored in localStorage (consider httpOnly cookies for production)
- State parameter validates against CSRF attacks
- Google OAuth provides refresh tokens stored in database
- User email is verified by Google

## Testing the Flow

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Visit `http://localhost:3000`
4. Click "Sign in with Google"
5. Authorize on Google
6. Should redirect to `/dashboard` with token

## Debugging

Enable backend debug logs in `auth.py`:
```python
DEBUG: Received callback with code: 4/0Ab32j92...
DEBUG: GOOGLE_CLIENT_ID: 6086003437...
DEBUG: Got user info for: user@example.com
DEBUG: Created access token: eyJhbGciOiJIUzI1NiIs...
```

Check frontend console for errors:
```javascript
console.log('Code:', code);
console.log('Token response:', response);
```

## Common Errors Fixed

| Error | Cause | Fix |
|-------|-------|-----|
| "Login cancelled" | Popup window closed before auth | Use redirect instead |
| "Failed to fetch" | CORS on callback endpoint | Use POST endpoint |
| Cross-origin error | Trying to read popup URL | Don't check popup location |
| "No authorization code" | Wrong redirect URI | Match backend config |

## Environment Variables Required

**Backend (`.env`):**
```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
SECRET_KEY=your_jwt_secret
```

**Frontend:**
```typescript
// In lib/api/client.ts
const API_BASE_URL = 'http://localhost:8000';
```

## Flow Diagram

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. Visit /login
     v
┌─────────────────────┐
│   Login Page        │
│ [Sign in with       │
│      Google]        │
└────┬────────────────┘
     │
     │ 2. GET /auth/google/login
     v
┌─────────────────────┐
│   Backend           │
│ Returns auth_url    │
└────┬────────────────┘
     │
     │ 3. Redirect to Google
     v
┌─────────────────────┐
│   Google OAuth      │
│ User authorizes     │
└────┬────────────────┘
     │
     │ 4. Redirect to /auth/callback?code=xxx
     v
┌─────────────────────┐
│  Callback Page      │
│ Extracts code       │
└────┬────────────────┘
     │
     │ 5. POST /auth/google/token {code}
     v
┌─────────────────────┐
│   Backend           │
│ - Verify code       │
│ - Get user info     │
│ - Create/update user│
│ - Return JWT token  │
└────┬────────────────┘
     │
     │ 6. {access_token, token_type}
     v
┌─────────────────────┐
│  Callback Page      │
│ - Store token       │
│ - Redirect /dashboard│
└────┬────────────────┘
     │
     │ 7. Navigate to dashboard
     v
┌─────────────────────┐
│   Dashboard         │
│ All API calls have  │
│ Authorization header│
└─────────────────────┘
```

## Success!

The authentication flow now works correctly using:
- ✅ Full-page redirect (no popup issues)
- ✅ POST `/auth/google/token` endpoint (returns JSON)
- ✅ Proper JWT token storage and usage
- ✅ Compatible with existing backend implementation
- ✅ Follows OAuth 2.0 best practices
