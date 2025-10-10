# Transcript Endpoints

This document describes the available endpoints for retrieving meeting transcripts.

## Available Endpoints

### 1. Get All Transcripts from Recall API
```
GET /api/v1/meetings/recall/transcripts
```
**Description:** Fetches all transcripts from the Recall API  
**Response:** Returns all available transcripts

**Equivalent curl command:**
```bash
curl --request GET \
     --url https://us-east-1.recall.ai/api/v1/transcript/ \
     --header 'accept: application/json'
```

### 2. Get Transcript by ID
```
GET /api/v1/meetings/recall/transcripts/{transcript_id}
```
**Description:** Fetches a specific transcript by its ID  
**Parameters:** 
- `transcript_id` (string): The ID of the transcript to retrieve

**Equivalent curl command:**
```bash
curl --request GET \
     --url https://us-east-1.recall.ai/api/v1/transcript/{transcript_id}/ \
     --header 'accept: application/json'
```

### 3. Get Transcripts by Bot ID
```
GET /api/v1/meetings/recall/transcripts/bot/{bot_id}
```
**Description:** Fetches all transcripts for a specific bot ID  
**Parameters:** 
- `bot_id` (string): The ID of the bot to get transcripts for

**Example:** 
```
GET /api/v1/meetings/recall/transcripts/bot/14f39859-cd40-48f8-ae77-16a7244b6ddd
```

### 4. Debug Endpoints

#### Test Authentication
```
POST /api/v1/meetings/debug/test-auth
```
**Description:** Tests the Recall API authentication

#### Test Available Methods
```
GET /api/v1/meetings/debug/test-methods
```
**Description:** Shows which transcript methods are available and configuration details

#### Check Configuration
```
GET /api/v1/meetings/debug/config
```
**Description:** Shows current Recall API configuration

## Response Format

All transcript endpoints return a response in this format:

```json
{
  "success": true|false,
  "message": "Description of the result",
  "data": [...], // Array of transcripts or transcript details
  "bot_id": "bot_id", // Only for bot-specific requests
  "error_details": {} // Only present if there's an error
}
```

## Error Handling

If there are any errors:
- HTTP 500: Internal server error
- HTTP 404: Transcript or bot not found
- The response will include `"success": false` and error details

## Usage Examples

### Get transcripts for a specific bot:
```bash
curl -X GET "http://localhost:8000/api/v1/meetings/recall/transcripts/bot/14f39859-cd40-48f8-ae77-16a7244b6ddd"
```

### Get all transcripts:
```bash
curl -X GET "http://localhost:8000/api/v1/meetings/recall/transcripts"
```

### Get a specific transcript:
```bash
curl -X GET "http://localhost:8000/api/v1/meetings/recall/transcripts/transcript_123"
```

---

## Previous Functionality (Still Available)

### Receive Meeting Transcript
**POST** `/api/v1/meetings/transcript`

Receives and processes the complete meeting transcript from Recall API or other sources.
{
    "bot_id": "recall_bot_123",
    "meeting_url": "https://zoom.us/j/1234567890",
    "full_transcript": "Complete meeting transcript text...",
    "transcript_segments": [
        {
            "speaker": "John Doe",
            "text": "Hello everyone, let's start the meeting",
            "timestamp": 0.0,
            "start_time": 0.0,
            "end_time": 5.0
        },
        {
            "speaker": "Jane Smith",
            "text": "Thanks John, I have the quarterly report ready",
            "timestamp": 5.0,
            "start_time": 5.0,
            "end_time": 10.0
        }
    ],
    "participants": ["John Doe", "Jane Smith"],
    "status": "completed"
}
```

#### Response:
```json
{
    "success": true,
    "message": "Transcript processed successfully",
    "meeting_id": 123,
    "transcript_saved": true,
    "summary_generated": true,
    "action_items_extracted": true
}
```

### 2. Get Meeting Transcript by Bot ID
**GET** `/api/v1/meetings/transcript/{bot_id}`

Retrieves the transcript for a meeting using the bot ID (recommended approach).

#### Response:
```json
{
    "bot_id": "recall_bot_123",
    "meeting_id": 123,
    "title": "Quarterly Review Meeting",
    "meeting_url": "https://zoom.us/j/1234567890",
    "platform": "zoom",
    "transcript": "Complete meeting transcript...",
    "summary": "AI-generated meeting summary...",
    "action_items": [
        {
            "task": "Prepare Q4 budget proposal",
            "assignee": "John Doe",
            "deadline": "2025-10-15"
        }
    ],
    "participants": ["John Doe", "Jane Smith"],
    "created_at": "2025-09-06T10:00:00Z",
    "updated_at": "2025-09-06T11:30:00Z"
}
```

### 3. Get Meeting Transcript by Meeting ID
**GET** `/api/v1/meetings/{meeting_id}/transcript`

Retrieves the transcript for a meeting using the meeting ID (alternative approach).

#### Response:
```json
{
    "bot_id": "recall_bot_123",
    "meeting_id": 123,
    "title": "Quarterly Review Meeting",
    "meeting_url": "https://zoom.us/j/1234567890",
    "platform": "zoom",
    "transcript": "Complete meeting transcript...",
    "summary": "AI-generated meeting summary...",
    "action_items": [
        {
            "task": "Prepare Q4 budget proposal",
            "assignee": "John Doe",
            "deadline": "2025-10-15"
        }
    ],
    "participants": ["John Doe", "Jane Smith"],
    "created_at": "2025-09-06T10:00:00Z",
    "updated_at": "2025-09-06T11:30:00Z"
}
```

### 4. Get All Transcripts
**GET** `/api/v1/meetings/transcripts/all`

Retrieves all meetings with transcripts for the current user.

#### Response:
```json
{
    "total_transcripts": 5,
    "transcripts": [
        {
            "meeting_id": 123,
            "title": "Quarterly Review Meeting",
            "meeting_url": "https://zoom.us/j/1234567890",
            "platform": "zoom",
            "scheduled_time": "2025-09-06T10:00:00Z",
            "status": "completed",
            "transcript_available": true,
            "summary_available": true,
            "action_items_available": true,
            "created_at": "2025-09-06T09:00:00Z",
            "updated_at": "2025-09-06T11:30:00Z"
        }
    ]
}
```

## Integration with Recall API

The transcript endpoint is designed to work seamlessly with the Recall API webhook system. When Recall finishes processing a meeting recording, it can send the transcript data to your endpoint.

### Webhook Setup Example:
```python
# Example webhook handler that forwards to your transcript endpoint
@app.post("/webhooks/recall-transcript")
async def handle_recall_transcript(webhook_data: dict):
    transcript_request = MeetingTranscriptRequest(
        bot_id=webhook_data["bot_id"],
        meeting_url=webhook_data["meeting_url"],
        full_transcript=webhook_data["transcript"],
        transcript_segments=webhook_data.get("transcript_segments", []),
        participants=webhook_data.get("participants", []),
        status="completed"
    )
    
    # Forward to your transcript processing endpoint
    response = await process_transcript(transcript_request)
    return response
```

## Error Handling

The endpoints include comprehensive error handling:

- **404**: Bot not found, Meeting not found, No transcript available
- **400**: No transcript data provided
- **500**: Database errors, AI processing errors, Unexpected errors

## Authentication

Currently, the endpoints are using dummy user authentication (user_id = 1) for development purposes. In production, uncomment the authentication lines to enable proper user-based access control.

## Database Schema

The transcript data is stored in the following tables:

### meetings table:
- `transcript` (Text): Full meeting transcript
- `summary` (Text): AI-generated summary
- `action_items` (JSON): Extracted action items
- `participants` (JSON): List of meeting participants

### bots table:
- `bot_id` (String): Unique bot identifier from Recall API
- `transcript_url` (String): URL to transcript file (if available)
- `meeting_id` (Integer): Associated meeting ID

## AI Processing

The transcript processing includes:
1. **Knowledge Base Update**: Transcript is added to the digital twin's knowledge base
2. **Summary Generation**: AI generates a concise meeting summary
3. **Action Item Extraction**: AI identifies and extracts action items with assignments and deadlines

This enables the digital twin to reference meeting content in future conversations and follow up on action items.
