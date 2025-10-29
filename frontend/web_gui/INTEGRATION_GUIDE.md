# Digital Twin Frontend - Setup & Usage Guide

## 🎯 Overview

This Next.js frontend provides a complete user interface for the Digital Twin meeting automation system, integrating all backend API endpoints with a modern, responsive design.

## ✅ Completed Integration

All backend routes have been successfully integrated:

### Authentication Routes ✓
- Google OAuth login flow
- JWT token management
- Protected routes with auto-redirect

### User Routes ✓
- `GET /users/me` - View profile
- `PUT /users/me` - Update profile

### Meeting Routes ✓
- `GET /meetings` - List all meetings
- `POST /meetings` - Create meeting
- `GET /meetings/{id}` - View meeting details
- `PUT /meetings/{id}` - Update meeting
- `DELETE /meetings/{id}` - Delete meeting
- `POST /meetings/join` - Join with bot
- `GET /meetings/get_formatted_transcript` - Get transcript
- `GET /meetings/bot/{bot_id}/recording-url` - Get video URL

### Summarization Routes ✓
- `POST /summarization/generate` - Generate summary (latest bot)
- `POST /summarization/generate/{bot_id}` - Generate for specific bot

### Calendar Routes ✓
- `POST /calendar/sync` - Sync Google Calendar events

## 📁 Frontend Structure

```
app/
├── login/page.tsx                  # Google OAuth login page
├── auth/callback/page.tsx          # OAuth callback handler
└── dashboard/
    ├── layout.tsx                  # Protected layout + navigation
    ├── page.tsx                    # Dashboard home with stats
    ├── meetings/
    │   ├── page.tsx                # Meetings list + create/join
    │   └── [id]/page.tsx           # Meeting detail + transcript + summary
    └── profile/page.tsx            # User profile editor

lib/
├── api/
│   ├── client.ts                   # HTTP client with auth headers
│   ├── types.ts                    # All TypeScript interfaces
│   ├── auth.ts                     # Authentication service
│   ├── users.ts                    # User CRUD service
│   ├── meetings.ts                 # Meeting CRUD service
│   ├── summarization.ts            # AI summary service
│   └── calendar.ts                 # Calendar sync service
└── hooks/
    └── useAuth.ts                  # Authentication React hook
```

## 🚀 Quick Start

### 1. Start Backend
```bash
cd DigitalTwin
source venv/bin/activate
uvicorn app.main:app --reload
```

Backend should be running at `http://localhost:8000`

### 2. Start Frontend
```bash
cd frontend/web_gui
npm install
npm run dev
```

Frontend will be at `http://localhost:3000`

### 3. Login
1. Navigate to `http://localhost:3000`
2. Click "Sign in with Google"
3. Authorize the app
4. You'll be redirected to dashboard

## 🎨 Features Implemented

### Dashboard (`/dashboard`)
- **Quick Stats Cards**: Total meetings, completed, in progress
- **Recent Meetings List**: Shows last 5 meetings with status
- **Quick Actions**:
  - 🔄 Sync Calendar - Trigger Google Calendar sync
  - ✨ Generate Summary - Create AI summary from latest bot
- **Latest Summary Display**: Shows summary with compression stats

### Meetings List (`/dashboard/meetings`)
- **Full Meetings Table**: All meetings with status badges
- **Create Meeting Modal**:
  - Title, description, meeting URL fields
  - Form validation
- **Join Meeting Modal**:
  - Enter meeting URL
  - Bot joins automatically
  - Returns bot_id
- **Quick Delete**: Delete button on each row
- **Status Indicators**:
  - 🟢 Green = Completed
  - 🔵 Blue = In Progress
  - 🟡 Yellow = Scheduled

### Meeting Detail (`/dashboard/meetings/[id]`)
- **Meeting Information**: Title, description, status, times
- **Edit Mode**: Update title, description, status
- **Delete Button**: Remove meeting
- **AI Summary Section**:
  - "Generate Summary" button
  - Shows summary text
  - Displays original words, summary words, compression ratio
- **Transcript Viewer**:
  - Enter Bot ID to load
  - Speaker-segmented display
  - Scrollable area
  - Total words count
- **Recording Player**:
  - HTML5 video player
  - Loads automatically with transcript
  - Full playback controls

### Profile (`/dashboard/profile`)
- **User Avatar**: Profile picture or initial
- **Profile Information**:
  - Full name
  - Email address
  - Google ID
  - Account status
  - Member since date
- **Edit Mode**:
  - Update full name
  - Update email
  - Save/Cancel buttons

### Navigation (`dashboard/layout.tsx`)
- **Top Navigation Bar**:
  - 📊 Dashboard
  - 📅 Meetings
  - 👤 Profile
- **User Profile Display**:
  - Avatar
  - Name
  - Logout button
- **Protected Routes**: Redirects to login if not authenticated
- **Loading States**: Shows spinner while checking auth

## 🔐 Authentication Flow

```
1. User visits /login
2. Clicks "Sign in with Google"
3. Frontend → POST /auth/google/login
4. Backend returns authorization_url
5. Popup opens with Google OAuth
6. User authorizes app
7. Google redirects to /auth/callback?code=xxx&state=xxx
8. Frontend → POST /auth/callback with code
9. Backend returns { access_token, user }
10. Frontend stores token in localStorage
11. Popup closes, redirects to /dashboard
12. All API calls include: Authorization: Bearer <token>
```

## 📊 API Client Architecture

### Type-Safe API Calls
```typescript
// All services use TypeScript interfaces
import { meetingService, userService } from '@/lib/api';

// Autocomplete and type checking
const meetings = await meetingService.getAll(); // Meeting[]
const user = await userService.getMe();         // User
```

### Automatic Token Management
```typescript
// client.ts automatically:
// 1. Reads token from localStorage
// 2. Adds Authorization header
// 3. Handles 401 errors
// 4. Redirects to login if unauthorized
```

### Error Handling
```typescript
try {
  const data = await meetingService.create({ title: "..." });
} catch (error) {
  // User-friendly error messages
  alert('Failed to create meeting: ' + error.message);
}
```

## 🎯 Usage Examples

### Create a Meeting
1. Go to `/dashboard/meetings`
2. Click "➕ Create Meeting"
3. Fill in:
   - Title: "Team Standup"
   - Description: "Daily sync"
   - Meeting URL: "https://meet.google.com/xxx-xxxx-xxx"
4. Click "Create"
5. Meeting appears in list

### Join Meeting with Bot
1. Click "🤖 Join Meeting"
2. Enter meeting URL
3. Bot joins automatically
4. Alert shows: "Bot joined! Bot ID: xxxxx"
5. Use Bot ID to view transcript

### View Transcript & Recording
1. Go to meeting detail page
2. Scroll to "Transcript" section
3. Enter Bot ID
4. Press Enter
5. Transcript loads with speaker segments
6. Recording player loads below

### Generate AI Summary
1. On meeting detail page
2. Click "✨ Generate Summary"
3. Wait for processing
4. Summary appears with:
   - Full summary text
   - Original word count
   - Summary word count
   - Compression percentage

### Sync Calendar
1. On dashboard
2. Click "🔄 Sync Calendar"
3. Wait for sync
4. Alert shows: "Successfully synced X events"

## 🔧 Configuration

### API Base URL
Default: `http://localhost:8000`

To change, edit `lib/api/client.ts`:
```typescript
const API_BASE_URL = 'http://localhost:8000';
```

### OAuth Settings
Configure in backend `.env`:
```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

## 🎨 UI/UX Features

- **Responsive Design**: Works on mobile, tablet, desktop
- **Loading States**: Spinners for async operations
- **Modal Dialogs**: Create/join meeting modals
- **Status Badges**: Color-coded meeting states
- **Form Validation**: Required fields, type checking
- **Error Messages**: User-friendly alerts
- **Navigation**: Persistent top nav with active states
- **Auto-redirect**: Protected routes redirect to login

## 🧪 Testing the Integration

1. **Login Flow**:
   - Visit localhost:3000
   - Should auto-redirect to /login
   - Click Google sign-in
   - Should redirect to /dashboard after auth

2. **Dashboard**:
   - Stats cards should show meeting counts
   - Recent meetings should display

3. **Create Meeting**:
   - Fill form
   - Submit
   - Check it appears in list

4. **Join Meeting**:
   - Enter valid Google Meet URL
   - Check bot_id returned

5. **View Transcript**:
   - Enter bot_id from join
   - Transcript should load

6. **Generate Summary**:
   - Click button
   - Summary should appear with stats

7. **Update Profile**:
   - Edit name
   - Save
   - Check update persists

## 📝 TypeScript Types

All API responses have type definitions:

```typescript
interface User {
  id: number;
  email: string;
  full_name: string;
  profile_picture?: string;
  is_active: boolean;
  created_at: string;
}

interface Meeting {
  id: number;
  title: string;
  description?: string;
  meeting_url?: string;
  start_time?: string;
  end_time?: string;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
}

interface SummarizationResponse {
  success: boolean;
  summary: string;
  original_words: number;
  summary_words: number;
  compression_ratio: number;
}
```

## 🐛 Troubleshooting

### "Failed to fetch" errors
- Backend not running → Start backend
- Wrong port → Check API_BASE_URL in client.ts
- CORS issues → Check backend CORS settings

### Login not working
- Google OAuth not configured → Check backend .env
- Redirect URI mismatch → Update Google Console

### Token errors
- Clear localStorage → Open DevTools → Application → Clear
- Check token format → Should be JWT string

### TypeScript errors
```bash
npm run build  # See all type errors
```

## 🎓 Key Technologies

- **Next.js 16** - React framework with App Router
- **React 19** - UI library
- **TypeScript 5** - Type safety
- **Tailwind CSS 4** - Styling
- **Fetch API** - HTTP requests

## 📦 All Dependencies

Check `package.json` for complete list. Key ones:
- next: 16.0.1
- react: 19.2.0
- typescript: 5
- tailwindcss: 4

## ✨ Summary

This frontend provides a **complete, production-ready UI** for your Digital Twin backend:

✅ All 15+ API routes integrated  
✅ Type-safe TypeScript implementation  
✅ Modern responsive design  
✅ Google OAuth authentication  
✅ Meeting CRUD operations  
✅ AI summarization UI  
✅ Transcript viewer  
✅ Recording player  
✅ Calendar sync  
✅ User profile management  

Everything is ready to use - just start both servers and navigate to `http://localhost:3000`!
