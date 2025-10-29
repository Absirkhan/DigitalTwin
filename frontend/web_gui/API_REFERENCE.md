# API Endpoints Quick Reference

## Base URL
```
http://localhost:8000
```

## Authentication Required
All endpoints except `/auth/*` require:
```
Authorization: Bearer <jwt_token>
```

---

## 🔐 Authentication

### Google Login
```http
POST /auth/google/login
Response: { "authorization_url": "https://..." }
```

### OAuth Callback
```http
POST /auth/callback
Body: { "code": "...", "state": "..." }
Response: { "access_token": "...", "token_type": "Bearer", "user": {...} }
```

---

## 👤 Users

### Get Current User
```http
GET /users/me
Response: {
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "google_id": "...",
  "profile_picture": "https://...",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

### Update Current User
```http
PUT /users/me
Body: {
  "full_name": "Jane Doe",
  "email": "jane@example.com"
}
Response: { ...updated user object... }
```

---

## 📅 Meetings

### List All Meetings
```http
GET /meetings
Response: [
  {
    "id": 1,
    "user_id": 1,
    "title": "Team Standup",
    "description": "Daily sync",
    "meeting_url": "https://meet.google.com/...",
    "start_time": "2024-01-01T10:00:00",
    "end_time": "2024-01-01T11:00:00",
    "status": "completed",
    "created_at": "2024-01-01T00:00:00"
  },
  ...
]
```

### Create Meeting
```http
POST /meetings
Body: {
  "title": "Team Standup",
  "description": "Daily sync",
  "meeting_url": "https://meet.google.com/xxx-xxxx-xxx",
  "start_time": "2024-01-01T10:00:00",
  "status": "scheduled"
}
Response: { ...new meeting object... }
```

### Get Meeting by ID
```http
GET /meetings/{id}
Response: { ...meeting object... }
```

### Update Meeting
```http
PUT /meetings/{id}
Body: {
  "title": "Updated Title",
  "status": "completed"
}
Response: { ...updated meeting object... }
```

### Delete Meeting
```http
DELETE /meetings/{id}
Response: { ...deleted meeting object... }
```

### Join Meeting with Bot
```http
POST /meetings/join
Body: {
  "meeting_url": "https://meet.google.com/xxx-xxxx-xxx",
  "bot_name": "Digital Twin Bot"
}
Response: {
  "success": true,
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Bot successfully joined the meeting",
  "meeting_id": 1
}
```

### Get Formatted Transcript
```http
GET /meetings/get_formatted_transcript
Response: {
  "success": true,
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "formatted_transcript": {
    "continuous_text": "Full transcript...",
    "clean_continuous_text": "Cleaned transcript...",
    "speaker_segments": [
      {
        "speaker": "John Doe",
        "text": "Hello everyone...",
        "timestamp": "00:00:15"
      },
      ...
    ],
    "total_words": 456
  }
}
```

### Get Recording URL
```http
GET /meetings/bot/{bot_id}/recording-url
Response: {
  "success": true,
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "video_url": "https://...",
  "expires_at": "2024-01-02T00:00:00",
  "message": "Recording URL retrieved successfully"
}
```

---

## ✨ Summarization

### Generate Summary (Latest Bot)
```http
POST /summarization/generate
Response: {
  "success": true,
  "summary": "The meeting discussed project updates and next steps...",
  "original_words": 456,
  "summary_words": 89,
  "compression_ratio": 0.195,
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Summary generated successfully"
}
```

### Generate Summary (Specific Bot)
```http
POST /summarization/generate/{bot_id}
Response: {
  "success": true,
  "summary": "The meeting discussed...",
  "original_words": 456,
  "summary_words": 89,
  "compression_ratio": 0.195,
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Summary generated successfully"
}
```

---

## 📆 Calendar

### Sync Google Calendar
```http
POST /calendar/sync
Response: {
  "success": true,
  "events_synced": 5,
  "message": "Calendar events synced successfully"
}
```

---

## 🎯 Frontend Usage Examples

### TypeScript/JavaScript

```typescript
import { meetingService, summarizationService } from '@/lib/api';

// Create meeting
const meeting = await meetingService.create({
  title: "Team Standup",
  description: "Daily sync",
  meeting_url: "https://meet.google.com/xxx-xxxx-xxx"
});

// Join with bot
const result = await meetingService.join({
  meeting_url: "https://meet.google.com/xxx-xxxx-xxx"
});
console.log(result.bot_id); // "550e8400-..."

// Get transcript
const transcript = await meetingService.getFormattedTranscript();

// Generate summary
const summary = await summarizationService.generate();
console.log(summary.summary);
console.log(`${summary.compression_ratio * 100}% compression`);

// Get all meetings
const meetings = await meetingService.getAll();

// Update meeting
const updated = await meetingService.update(1, {
  status: "completed"
});

// Delete meeting
await meetingService.delete(1);
```

---

## 📊 Status Values

### Meeting Status
- `scheduled` - Meeting is planned
- `in_progress` - Meeting is currently happening
- `completed` - Meeting has ended
- `cancelled` - Meeting was cancelled

---

## 🎨 Frontend Components Using These

- **Dashboard** - `getAll()`, `generate()`
- **Meetings List** - `getAll()`, `create()`, `join()`, `delete()`
- **Meeting Detail** - `getById()`, `update()`, `delete()`, `getFormattedTranscript()`, `getBotRecordingUrl()`, `generate()`
- **Profile** - `getMe()`, `updateMe()`
- **All Pages** - Calendar sync

---

## 🔧 Error Responses

All endpoints may return:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid data)
- `401` - Unauthorized (invalid/missing token)
- `404` - Not found
- `500` - Server error

---

## 🚀 Quick Test Sequence

1. Login → Get token
2. Create meeting → Get meeting_id
3. Join meeting → Get bot_id
4. Get transcript → See conversation
5. Generate summary → See AI summary
6. View recording → Watch video
7. Update profile → Change name
8. Sync calendar → Import events

---

## 📝 Notes

- All timestamps are in ISO 8601 format
- Bot IDs are UUIDs (string format)
- Meeting IDs are integers
- Tokens expire after configured duration
- Recording URLs may have expiration times
- Transcripts are only available after meeting ends
