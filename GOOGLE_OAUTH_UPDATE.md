# IMPORTANT: Update Google Cloud Console OAuth Settings

## You MUST update your Google Cloud Console settings!

Since we changed the redirect URI from backend to frontend, you need to update your authorized redirect URIs in Google Cloud Console:

### Steps:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to **APIs & Services** → **Credentials**
4. Click on your OAuth 2.0 Client ID
5. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:3000/auth/callback
   ```
6. **Keep the old one** for backward compatibility:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
7. Click **SAVE**

### Current Configuration:

**`.env` file:**
```
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback
```

### Why This Change?

- **Before**: Google → Backend → Shows JSON
- **After**: Google → Frontend → Extracts code → Backend API → Stores token → Redirects to dashboard

### Testing:

After updating Google Cloud Console:
1. Restart the backend server (it needs to reload .env)
2. Clear browser localStorage
3. Try signing in again
4. Should now redirect to dashboard properly!

### If You Get "redirect_uri_mismatch" Error:

This means the redirect URI in Google Cloud Console doesn't match. Make sure you:
1. Added `http://localhost:3000/auth/callback` to authorized redirect URIs
2. Saved the changes
3. Waited a few seconds for changes to propagate
4. Restarted the backend server
