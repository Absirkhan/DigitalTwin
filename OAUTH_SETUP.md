# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for the Digital Twin application.

## Quick Setup

1. **Run the setup script:**
   ```bash
   python setup_oauth.py
   ```

2. **Follow the prompts to configure Google OAuth credentials**

3. **Start the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Test the login at:** http://localhost:8000

## Manual Setup

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google+ API
   - Gmail API
   - Google Calendar API

### 2. Create OAuth 2.0 Client ID

1. Navigate to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client ID**
3. Choose **Web application** as the application type
4. Add authorized redirect URI:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
5. Copy the **Client ID** and **Client Secret**

### 3. Environment Configuration

1. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Update the following variables in `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   SECRET_KEY=your-super-secret-key
   ```

### 4. Database Migration

Run the database migration to update the user table:
```bash
alembic upgrade head
```

## API Endpoints

### Authentication Endpoints

- `GET /api/v1/auth/google/login` - Get Google OAuth URL
- `GET /api/v1/auth/google/callback` - Handle OAuth callback
- `POST /api/v1/auth/google/token` - Exchange code for JWT token
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/refresh-tokens` - Refresh Google tokens
- `POST /api/v1/auth/logout` - Logout

### Frontend Pages

- `/` - Login page
- `/login` - Login page
- `/auth/success` - Success redirect
- `/auth/error` - Error redirect

## Usage Examples

### Frontend Integration

```javascript
// Get Google OAuth URL
const response = await fetch('/api/v1/auth/google/login');
const data = await response.json();
window.location.href = data.auth_url;

// Check user authentication
const token = localStorage.getItem('access_token');
const userResponse = await fetch('/api/v1/auth/me', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
const user = await userResponse.json();
```

### API Client Integration

```python
import httpx

# Exchange authorization code for token
async with httpx.AsyncClient() as client:
    response = await client.post('/api/v1/auth/google/token', 
        json={'code': authorization_code})
    token_data = response.json()
    access_token = token_data['access_token']

# Use token for authenticated requests
headers = {'Authorization': f'Bearer {access_token}'}
user_response = await client.get('/api/v1/auth/me', headers=headers)
```

## Security Features

- **JWT tokens** for session management
- **Google OAuth 2.0** for secure authentication
- **Automatic token refresh** for Google API access
- **Secure token storage** in database
- **CORS protection** for web clients

## Database Schema

The user table includes the following OAuth-related fields:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    full_name VARCHAR,
    google_id VARCHAR UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    profile_picture VARCHAR,
    oauth_tokens JSON,
    bot_name VARCHAR,
    enable_backend_tasks BOOLEAN DEFAULT TRUE
);
```

## Troubleshooting

### Common Issues

1. **"Invalid redirect URI"**
   - Ensure the redirect URI in Google Console matches exactly: 
     `http://localhost:8000/api/v1/auth/google/callback`

2. **"Invalid client ID"**
   - Check that `GOOGLE_CLIENT_ID` in `.env` is correct
   - Ensure the client ID includes the full domain (`.apps.googleusercontent.com`)

3. **"Token verification failed"**
   - Check that `SECRET_KEY` is set in `.env`
   - Ensure the JWT token hasn't expired

4. **Database errors**
   - Run `alembic upgrade head` to apply migrations
   - Check database connection settings in `.env`

### Testing

1. Visit http://localhost:8000
2. Click "Sign in with Google"
3. Complete OAuth flow
4. Verify user information is displayed

## Production Deployment

For production deployment, update the following:

1. **Change redirect URI** to your production domain
2. **Update CORS settings** in `main.py`
3. **Use HTTPS** for all OAuth redirects
4. **Set secure SECRET_KEY**
5. **Configure proper database settings**

```env
# Production settings
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/google/callback
ALLOWED_HOSTS=["yourdomain.com"]
SECRET_KEY=your-production-secret-key
```