# DigitalTwin Database Schema Documentation

## Overview
This document describes the database schema for the DigitalTwin project, which handles user management, meeting automation, calendar integration, and AI-powered digital twins for meeting assistance.

## Entity Relationship Diagram (ERD) Structure

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Users    │ 1───n │  Meetings   │ 1───n │    Bots     │
└─────────────┘       └─────────────┘       └─────────────┘
       │                       │                     
       │ 1                     │ 1                   
       │                       │                     
       n                       n                     
┌─────────────┐       ┌─────────────┐                
│Calendar     │       │ Documents   │                
│Events       │       │             │                
└─────────────┘       └─────────────┘                
       │                       │                     
       │ 1                     │ 1                   
       │                       │                     
       n                       n                     
┌─────────────┐       ┌─────────────┐                
│   Emails    │       │Document     │                
│             │       │Chunks       │                
└─────────────┘       └─────────────┘                
                              │                     
                              │ 1                   
                              │                     
                              n                     
                      ┌─────────────┐                
                      │ Embeddings  │                
                      │             │                
                      └─────────────┘                
```

## Tables

### 1. Users Table
**Purpose**: Stores user account information and OAuth credentials for Google integration.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique user identifier |
| `email` | STRING | NOT NULL, UNIQUE | User's email address |
| `full_name` | STRING | NULLABLE | User's display name |
| `google_id` | STRING | UNIQUE, NULLABLE | Google OAuth ID |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account status flag |
| `profile_picture` | STRING | NULLABLE | URL to user's profile image |
| `bot_name` | STRING | NULLABLE | Custom name for user's digital twin |
| `enable_backend_tasks` | BOOLEAN | DEFAULT TRUE | Enable automated background tasks |
| `oauth_tokens` | JSON | NULLABLE | Encrypted OAuth token storage |

**Relationships**:
- One-to-Many with `meetings` (user_id)
- One-to-Many with `bots` (user_id)
- One-to-Many with `calendar_events` (user_id)
- One-to-Many with `emails` (user_id)

### 2. Meetings Table
**Purpose**: Central table for managing meeting information, transcripts, and AI processing.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique meeting identifier |
| `user_id` | INTEGER | FOREIGN KEY, NOT NULL | Reference to users table |
| `title` | STRING | NOT NULL | Meeting title/subject |
| `description` | TEXT | NULLABLE | Meeting description |
| `meeting_url` | STRING | NOT NULL | URL for joining the meeting |
| `platform` | STRING | NOT NULL | Meeting platform (Zoom, Teams, etc.) |
| `scheduled_time` | DATETIME | NOT NULL | When the meeting is scheduled |
| `duration_minutes` | INTEGER | DEFAULT 60 | Expected meeting duration |
| `digital_twin_id` | INTEGER | NULLABLE | Associated digital twin identifier |
| `status` | STRING | DEFAULT 'scheduled' | Current meeting status |
| `auto_join` | BOOLEAN | DEFAULT TRUE | Auto-join meeting with bot |
| `transcript` | TEXT | NULLABLE | Full meeting transcript |
| `summary` | TEXT | NULLABLE | AI-generated meeting summary |
| `action_items` | JSON | NULLABLE | Extracted action items |
| `participants` | JSON | NULLABLE | List of meeting participants |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| `updated_at` | DATETIME | ON UPDATE CURRENT_TIMESTAMP | Last update time |

**Legacy Fields** (for backward compatibility):
| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `start_time` | DATETIME | NULLABLE | Legacy start time field |
| `end_time` | DATETIME | NULLABLE | Legacy end time field |
| `calendar_id` | STRING | NULLABLE | Legacy calendar identifier |
| `calendar_event_id` | STRING | NULLABLE | Legacy calendar event ID |

**Relationships**:
- Many-to-One with `users` (user_id)
- One-to-Many with `bots` (meeting_id)

### 3. Bots Table
**Purpose**: Manages AI bots that join meetings and process recordings.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique bot record identifier |
| `bot_id` | STRING | UNIQUE, NOT NULL | External bot service identifier |
| `user_id` | INTEGER | FOREIGN KEY, NOT NULL | Owner of the bot |
| `platform` | STRING | NULLABLE | Platform where bot operates |
| `bot_name` | STRING | NULLABLE | Custom bot name |
| `video_download_url` | STRING | NULLABLE | URL to download meeting recording |
| `transcript_url` | STRING | NULLABLE | URL to access transcript |
| `meeting_id` | INTEGER | FOREIGN KEY, NULLABLE | Associated meeting |

**Relationships**:
- Many-to-One with `users` (user_id)
- Many-to-One with `meetings` (meeting_id, SET NULL on delete)

### 4. Calendar Events Table
**Purpose**: Stores calendar events synchronized from Google Calendar.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique calendar event identifier |
| `user_id` | INTEGER | FOREIGN KEY, NOT NULL | Event owner |
| `event_id` | STRING | NULLABLE | Google Calendar event ID |
| `summary` | STRING | NULLABLE | Event title/summary |
| `start_time` | DATETIME | NULLABLE | Event start time |
| `end_time` | DATETIME | NULLABLE | Event end time |
| `meeting_url` | STRING | NULLABLE | Associated meeting URL |
| `participants` | JSON | NULLABLE | List of event attendees |

**Relationships**:
- Many-to-One with `users` (user_id)

### 5. Emails Table
**Purpose**: Stores email data for AI processing and automation.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique email record identifier |
| `user_id` | INTEGER | FOREIGN KEY, NOT NULL | Email owner |
| `message_id` | STRING | NULLABLE | Gmail message ID |
| `subject` | STRING | NULLABLE | Email subject line |
| `sender` | STRING | NULLABLE | Email sender address |
| `snippet` | TEXT | NULLABLE | Email preview snippet |

**Relationships**:
- Many-to-One with `users` (user_id)

## RAG (Retrieval-Augmented Generation) Tables

*Note: These tables are planned for future implementation to support AI-powered context retrieval from meeting transcripts and documents.*

### 6. Documents Table
**Purpose**: Stores document metadata for RAG system including meeting transcripts, summaries, and user-uploaded documents.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique document identifier |
| `user_id` | INTEGER | FOREIGN KEY, NOT NULL | Document owner |
| `meeting_id` | INTEGER | FOREIGN KEY, NULLABLE | Associated meeting (if applicable) |
| `title` | STRING | NOT NULL | Document title or meeting title |
| `document_type` | STRING | NOT NULL | Type: 'transcript', 'summary', 'upload', 'notes' |
| `content` | TEXT | NOT NULL | Full document content |
| `metadata` | JSON | NULLABLE | Document metadata and context |
| `file_path` | STRING | NULLABLE | Path to original file (if uploaded) |
| `file_size` | INTEGER | NULLABLE | File size in bytes |
| `mime_type` | STRING | NULLABLE | File MIME type |
| `is_processed` | BOOLEAN | DEFAULT FALSE | Whether document has been chunked |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Document creation time |
| `updated_at` | DATETIME | ON UPDATE CURRENT_TIMESTAMP | Last update time |

**Relationships**:
- Many-to-One with `users` (user_id)
- Many-to-One with `meetings` (meeting_id, SET NULL on delete)
- One-to-Many with `document_chunks` (document_id)

### 7. Document Chunks Table
**Purpose**: Stores text chunks from documents for efficient RAG retrieval and embedding generation.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique chunk identifier |
| `document_id` | INTEGER | FOREIGN KEY, NOT NULL | Parent document reference |
| `chunk_index` | INTEGER | NOT NULL | Order of chunk in document |
| `content` | TEXT | NOT NULL | Chunk text content |
| `content_hash` | STRING | NOT NULL | Hash for deduplication |
| `token_count` | INTEGER | NULLABLE | Number of tokens in chunk |
| `start_position` | INTEGER | NULLABLE | Character start position in document |
| `end_position` | INTEGER | NULLABLE | Character end position in document |
| `metadata` | JSON | NULLABLE | Chunk-specific metadata |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Chunk creation time |

**Relationships**:
- Many-to-One with `documents` (document_id, CASCADE on delete)
- One-to-One with `embeddings` (chunk_id)

### 8. Embeddings Table
**Purpose**: Stores vector embeddings for semantic search and retrieval in RAG system.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique embedding identifier |
| `chunk_id` | INTEGER | FOREIGN KEY, UNIQUE, NOT NULL | Associated document chunk |
| `embedding_model` | STRING | NOT NULL | Model used for embedding generation |
| `embedding_vector` | VECTOR/JSON | NOT NULL | High-dimensional embedding vector |
| `vector_dimensions` | INTEGER | NOT NULL | Number of dimensions in vector |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Embedding creation time |

**Relationships**:
- One-to-One with `document_chunks` (chunk_id, CASCADE on delete)

### 9. RAG Queries Table
**Purpose**: Logs user queries and retrieved contexts for analytics and system improvement.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique query identifier |
| `user_id` | INTEGER | FOREIGN KEY, NOT NULL | User who made the query |
| `query_text` | TEXT | NOT NULL | Original user query |
| `query_embedding` | VECTOR/JSON | NULLABLE | Query embedding vector |
| `retrieved_chunks` | JSON | NULLABLE | IDs of chunks retrieved for context |
| `response_generated` | TEXT | NULLABLE | AI-generated response |
| `relevance_scores` | JSON | NULLABLE | Similarity scores for retrieved chunks |
| `feedback_score` | INTEGER | NULLABLE | User feedback (1-5 rating) |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Query timestamp |

**Relationships**:
- Many-to-One with `users` (user_id)

## Foreign Key Constraints

### Cascade Behaviors
- **CASCADE DELETE**: When a user is deleted, all associated records are automatically deleted
  - `meetings.user_id` → `users.id`
  - `bots.user_id` → `users.id`
  - `calendar_events.user_id` → `users.id`
  - `emails.user_id` → `users.id`
  - `documents.user_id` → `users.id`
  - `rag_queries.user_id` → `users.id`

- **SET NULL**: When a meeting is deleted, associated records remain but meeting reference is nullified
  - `bots.meeting_id` → `meetings.id`
  - `documents.meeting_id` → `meetings.id`

- **CASCADE DELETE (RAG System)**: When documents are deleted, all related chunks and embeddings are removed
  - `document_chunks.document_id` → `documents.id`
  - `embeddings.chunk_id` → `document_chunks.id`

## Indexes and Performance

### Unique Constraints
- `users.email`: Ensures unique user accounts
- `users.google_id`: Prevents duplicate Google OAuth accounts
- `bots.bot_id`: Ensures unique bot identifiers

### Recommended Indexes (for performance optimization)
```sql
-- For user lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);

-- For meeting queries
CREATE INDEX idx_meetings_user_id ON meetings(user_id);
CREATE INDEX idx_meetings_scheduled_time ON meetings(scheduled_time);
CREATE INDEX idx_meetings_status ON meetings(status);

-- For bot operations
CREATE INDEX idx_bots_user_id ON bots(user_id);
CREATE INDEX idx_bots_meeting_id ON bots(meeting_id);

-- For calendar integration
CREATE INDEX idx_calendar_events_user_id ON calendar_events(user_id);
CREATE INDEX idx_calendar_events_start_time ON calendar_events(start_time);

-- For email processing
CREATE INDEX idx_emails_user_id ON emails(user_id);

-- For RAG system (future implementation)
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_meeting_id ON documents(meeting_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_hash ON document_chunks(content_hash);
CREATE INDEX idx_embeddings_chunk_id ON embeddings(chunk_id);
CREATE INDEX idx_embeddings_model ON embeddings(embedding_model);
CREATE INDEX idx_rag_queries_user_id ON rag_queries(user_id);
CREATE INDEX idx_rag_queries_created_at ON rag_queries(created_at);

-- Vector similarity search index (database-specific)
-- For PostgreSQL with pgvector:
-- CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding_vector);
-- For other databases, use appropriate vector indexing method
```

## Data Types and Storage

### JSON Fields
The schema uses JSON columns for flexible data storage:

1. **`users.oauth_tokens`**: Stores encrypted OAuth refresh/access tokens
   ```json
   {
     "access_token": "encrypted_token",
     "refresh_token": "encrypted_token",
     "expires_at": "2025-01-01T00:00:00Z"
   }
   ```

2. **`meetings.action_items`**: AI-extracted action items from meetings
   ```json
   [
     {
       "task": "Follow up with client",
       "assignee": "john@example.com",
       "due_date": "2025-01-15"
     }
   ]
   ```

3. **`meetings.participants`**: Meeting attendee information
   ```json
   [
     {
       "name": "John Doe",
       "email": "john@example.com",
       "role": "organizer"
     }
   ]
   ```

4. **`calendar_events.participants`**: Calendar event attendees
   ```json
   [
     {
       "email": "attendee@example.com",
       "status": "accepted"
     }
   ]
   ```

### RAG System JSON Fields (Future Implementation)

5. **`documents.metadata`**: Document metadata and processing information
   ```json
   {
     "original_filename": "meeting_notes.pdf",
     "processing_date": "2025-01-15T10:30:00Z",
     "language": "en",
     "keywords": ["meeting", "ai", "summary"],
     "meeting_date": "2025-01-15",
     "participants": ["john@example.com", "jane@example.com"]
   }
   ```

6. **`document_chunks.metadata`**: Chunk-specific context information
   ```json
   {
     "speaker": "John Doe",
     "timestamp": "00:15:30",
     "topic": "project timeline",
     "confidence_score": 0.95,
     "section_type": "discussion"
   }
   ```

7. **`embeddings.embedding_vector`**: High-dimensional vector representation
   ```json
   {
     "vector": [0.1234, -0.5678, 0.9012, ...],
     "model_version": "text-embedding-3-large",
     "dimension_count": 1536
   }
   ```

8. **`rag_queries.retrieved_chunks`**: Retrieved context for user queries
   ```json
   {
     "chunks": [
       {
         "chunk_id": 123,
         "relevance_score": 0.89,
         "content_preview": "The meeting discussed project timeline..."
       },
       {
         "chunk_id": 456,
         "relevance_score": 0.76,
         "content_preview": "Action items include follow-up with client..."
       }
     ],
     "total_retrieved": 5,
     "search_strategy": "semantic_similarity"
   }
   ```

9. **`rag_queries.relevance_scores`**: Similarity scores for quality analysis
   ```json
   {
     "max_score": 0.89,
     "min_score": 0.42,
     "avg_score": 0.67,
     "threshold_used": 0.5,
     "total_candidates": 50
   }
   ```

## Migration History

### Migration 001: Initial Schema
- Created base tables: `users`, `meetings`, `bots`, `calendar_events`, `emails`
- Established primary foreign key relationships

### Migration 002: Meeting Enhancement
- Added comprehensive meeting fields: `description`, `platform`, `scheduled_time`
- Added status tracking: `status`, `auto_join`, `digital_twin_id`
- Added AI processing fields: `action_items`, `participants`
- Added audit fields: `created_at`, `updated_at`

### Migration 003: OAuth Update
- Updated user authentication to OAuth-only model
- Removed legacy `hashed_password` field
- Added `is_active` status flag
- Migrated `credentials` to `oauth_tokens` with proper structure

### Future Migration: RAG System Implementation
- Add `documents`, `document_chunks`, `embeddings`, and `rag_queries` tables
- Implement vector similarity search indexes
- Add document processing pipeline
- Establish semantic search capabilities

## Security Considerations

1. **OAuth Token Encryption**: All OAuth tokens should be encrypted before storage
2. **Cascade Deletes**: User deletion permanently removes all associated data
3. **Data Retention**: Consider implementing soft deletes for audit trails
4. **PII Protection**: Email content and transcripts contain sensitive information
5. **RAG System Security** (Future Implementation):
   - **Vector Embedding Protection**: Secure storage of embedding vectors
   - **Content Access Control**: User-specific document access restrictions
   - **Query Logging**: Monitor and audit RAG system usage
   - **Similarity Threshold**: Prevent information leakage through similarity searches

## Usage Patterns

### Common Queries
1. **User Dashboard**: Fetch user with upcoming meetings
2. **Meeting Processing**: Join meetings → record → transcribe → summarize
3. **Calendar Sync**: Periodic sync of Google Calendar events
4. **Bot Management**: Track bot status across multiple meetings
5. **RAG Queries** (Future Implementation):
   - **Semantic Search**: Find relevant meeting contexts based on user queries
   - **Document Retrieval**: Fetch documents by type, date, or participant
   - **Context Aggregation**: Combine multiple document chunks for comprehensive answers

### Scaling Considerations
- **Transcript Storage**: Large text fields may require external storage
- **Recording Files**: Store video/audio files in cloud storage (URLs only in DB)
- **Historical Data**: Consider archiving old meetings and transcripts
- **RAG System Scaling** (Future Implementation):
  - **Vector Database**: Consider specialized vector databases (Pinecone, Weaviate, Chroma)
  - **Embedding Cache**: Cache frequently accessed embeddings
  - **Chunk Size Optimization**: Balance between context and performance
  - **Batch Processing**: Process documents in batches for efficiency

---

*This schema supports the DigitalTwin application's core functionality of automated meeting management, AI-powered assistance, seamless calendar integration, and future RAG-based context retrieval for enhanced AI interactions.*