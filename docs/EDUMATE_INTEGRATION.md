# EduMate App and Standalone Integration Guide

## 1. Overview
This document explains how EduMate-RAG integrates with the main EduMate application and how it can still run as a standalone service.

There are two supported modes:

- Standalone mode: Flutter calls EduMate-RAG directly and uses `X-Session-Token`.
- Backend integration mode: Flutter calls the .NET backend, and .NET calls EduMate-RAG through `/api/integrations/query`.

For the main app flow, use backend integration mode. The .NET backend owns users, conversations, and durable message storage. EduMate-RAG only performs retrieval and answer generation.

## 2. .NET Integration Contract

### Responsibility split

The .NET backend owns:

- User identity
- Conversation creation and deletion
- Conversation listing
- Message history retrieval
- Durable message storage

EduMate-RAG owns:

- PDF retrieval
- Answer generation
- Source attribution
- Per-request short-term context from the messages sent by .NET

EduMate-RAG should not be the source of truth for integration conversation history.

### Ask question

Endpoint:

```http
POST /api/integrations/query
```

Request body:

```json
{
  "userId": "user-123",
  "conversationId": "conv-456",
  "message": "Explain instruction pipelining",
  "messages": [
    {
      "question": "What is CPU architecture?",
      "answer": "CPU architecture describes the structure and behavior of the processor."
    }
  ]
}
```

Rules:

- `message` is the current user question.
- `messages` contains previous Q&A pairs only, ordered oldest to newest.
- `.NET` should send only the latest 5 previous Q&A pairs.
- EduMate-RAG also caps the received history to the latest 5 pairs as a defensive guard.
- `numContextDocs` is optional in the integration request and defaults to `3` when omitted.

Response body:

```json
{
  "userId": "user-123",
  "conversationId": "conv-456",
  "question": "Explain instruction pipelining",
  "answer": "...",
  "sources": ["computer Architecture Book.pdf"],
  "isGeneral": false,
  "latencyMs": 2410.7,
  "timingsMs": {
    "retrieval": 120.3,
    "generation": 2200.1,
    "total": 2408.5
  }
}
```

After receiving this response, `.NET` should save the new message row.

Recommended table shape:

```text
Messages
Id
ConversationId
Question
Answer
SourcesJson
CreatedAt
```

Storing `SourcesJson` matters. Without it, the app loses citation and audit value, which is the point of a RAG system.

### Conversation endpoints

These should be implemented on the .NET backend side:

- New conversation: request `userId`, optional `name`; response `conversationId`
- Delete conversation: request `conversationId`; response `204 No Content`
- Get conversations by user
- Get messages inside a conversation

EduMate-RAG does not need to create, list, or delete integration conversations.

## 3. Standalone API Endpoints
The following endpoints are the core integration points for Flutter:

- `POST /api/query`
  - Use for asking questions and continuing a conversation.
  - Body: `{ "question": "..." }`
  - Headers: `Content-Type: application/json`, `X-Session-Token: <token>`

- `GET /api/conversation/history`
  - Retrieve the current session's conversation history.
  - Headers: `X-Session-Token: <token>`

- `POST /api/conversation/new?title=<title>`
  - Start a new conversation thread.
  - Headers: `X-Session-Token: <token>`

- `GET /api/conversation/list?limit=<n>`
  - List saved conversations for a session.
  - Headers: `X-Session-Token: <token>`

- `POST /api/conversation/load/{conversation_id}`
  - Load a saved conversation into active memory.
  - Headers: `X-Session-Token: <token>`

- `DELETE /api/conversation/{conversation_id}`
  - Delete a saved conversation.
  - Headers: `X-Session-Token: <token>`

- `POST /api/conversation/clear`
  - Clear the current conversation memory for this session.
  - Headers: `X-Session-Token: <token>`

- `POST /api/index`
  - Trigger PDF indexing. Usually used by admin or maintenance workflows.
  - Headers: `X-Session-Token: <token>` (optional but recommended)

## 4. Session Token Strategy
EduMate uses `X-Session-Token` to isolate users and conversations.

### Flutter integration pattern
- Generate or obtain a unique token for each user or app instance.
- Store the token locally (secure storage or shared preferences).
- Send the same token with every request.

### Example token handling
- Use authenticated user ID if available: `user-12345`
- Or create a random UUID for anonymous users.

## 5. Example Flutter HTTP calls
### Using `http` package
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

final apiBase = 'http://localhost:8000';
final sessionToken = '<user-session-token>';

Future<Map<String, dynamic>> queryEduMate(String question) async {
  final response = await http.post(
    Uri.parse('\$apiBase/api/query'),
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': sessionToken,
    },
    body: jsonEncode({ 'question': question }),
  );

  if (response.statusCode != 200) {
    throw Exception('Query failed: \\${response.body}');
  }

  return jsonDecode(response.body) as Map<String, dynamic>;
}
```

### Load conversation history
```dart
Future<List<dynamic>> getConversationHistory() async {
  final response = await http.get(
    Uri.parse('\$apiBase/api/conversation/history'),
    headers: {
      'X-Session-Token': sessionToken,
    },
  );

  if (response.statusCode != 200) {
    throw Exception('Failed to load history');
  }

  return jsonDecode(response.body)['messages'] as List<dynamic>;
}
```

### Start new conversation
```dart
Future<void> createNewConversation(String title) async {
  final response = await http.post(
    Uri.parse('\$apiBase/api/conversation/new?title=\$title'),
    headers: {
      'X-Session-Token': sessionToken,
    },
  );

  if (response.statusCode != 200) {
    throw Exception('Could not start new conversation');
  }
}
```

## 6. Conversation state in Flutter
A Flutter integration should maintain these values locally:

- `sessionToken` — current user session ID
- `currentConversationId` — active conversation identifier
- `messages` — chat history loaded from `GET /api/conversation/history`
- `sources` — latest answer sources returned by `/api/query`
- `turnCount` — conversation turn number

### Recommended flow
1. On app start, get or create `sessionToken`.
2. Optionally call `/health` to verify backend.
3. Load saved conversations with `/api/conversation/list`.
4. If user selects a saved conversation, call `/api/conversation/load/{id}`.
5. Send questions via `/api/query`.
6. Store UI state and refresh history from `/api/conversation/history`.

## 7. Notes for Flutter developers
- Always send `X-Session-Token` with every request.
- Keep the token stable while the user is active.
- Use `SharedPreferences` or secure storage to persist the token.
- Treat the token as the isolation key for conversation history.
- If using authentication, prefer a stable user identifier.

## 8. Recommended architecture
- `AuthService` or `SessionService` to manage session tokens
- `EduMateApiClient` to perform REST calls
- `ConversationRepository` to map backend messages into UI chat models
- `ConversationBloc` / `Provider` / `Riverpod` to manage conversation state

## 9. Summary
For the main app, Flutter should call the .NET backend, and .NET should call `POST /api/integrations/query` with the current question plus the latest 5 previous Q&A pairs. Use the standalone `/api/query` and conversation endpoints only when running EduMate-RAG without the .NET backend.
