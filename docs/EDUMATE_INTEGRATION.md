# EduMate Integration Guide

## 1. Overview
This document explains how a Flutter developer should integrate the EduMate backend into a main Flutter project.

EduMate exposes a REST API built with FastAPI. Flutter should connect using HTTP requests and include a per-user session token header for isolated conversation history.

## 2. Required API Endpoints
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

## 3. Session Token Strategy
EduMate uses `X-Session-Token` to isolate users and conversations.

### Flutter integration pattern
- Generate or obtain a unique token for each user or app instance.
- Store the token locally (secure storage or shared preferences).
- Send the same token with every request.

### Example token handling
- Use authenticated user ID if available: `user-12345`
- Or create a random UUID for anonymous users.

## 4. Example Flutter HTTP calls
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

## 5. Conversation state in Flutter
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

## 6. Notes for Flutter developers
- Always send `X-Session-Token` with every request.
- Keep the token stable while the user is active.
- Use `SharedPreferences` or secure storage to persist the token.
- Treat the token as the isolation key for conversation history.
- If using authentication, prefer a stable user identifier.

## 7. Recommended architecture
- `AuthService` or `SessionService` to manage session tokens
- `EduMateApiClient` to perform REST calls
- `ConversationRepository` to map backend messages into UI chat models
- `ConversationBloc` / `Provider` / `Riverpod` to manage conversation state

## 8. Summary
EduMate integration is straightforward: call the REST endpoints from Flutter, keep a stable session token for each user, and use the existing conversation endpoints to manage chat history and saved conversations.
