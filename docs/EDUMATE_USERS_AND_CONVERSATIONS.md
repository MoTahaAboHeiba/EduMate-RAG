# EduMate Users and Conversations

## 1. How EduMate handles multiple users
Yes — EduMate can handle multiple users using the same backend instance, as long as each user uses a unique session token.

### Current isolation design
EduMate isolates users by session token. The backend expects every request to include a header:

- `X-Session-Token: <user-token>`

This token is used to:
- separate conversation memory
- separate saved conversation files
- keep the current active conversation per user

### Storage behavior
Saved conversations are written to disk in separate session directories:
```
assets/conversations/<session-token>/conv_<timestamp>.json
```
That means user A and user B do not share conversation history if they use distinct tokens.

## 2. What happens when users use EduMate simultaneously
EduMate supports concurrent use by different users:

- each request is handled independently by FastAPI
- conversation history is loaded from the token-specific session folder
- chat memory is stored separately per token in backend memory maps
- multiple users can ask questions at the same time

### Important caveat
If two clients send the same `X-Session-Token`, they will share the same conversation history. For full isolation, ensure each user has a unique token.

## 3. Conversation lifecycle
The backend provides these conversation management operations:

- `POST /api/conversation/new?title=<title>`
  - start a new conversation for this session
- `GET /api/conversation/list?limit=<n>`
  - list saved conversations for the current session
- `POST /api/conversation/load/{conversation_id}`
  - load a saved conversation into active session memory
- `GET /api/conversation/history`
  - retrieve all messages for the active conversation
- `POST /api/conversation/clear`
  - clear the current conversation buffer
- `DELETE /api/conversation/{conversation_id}`
  - delete a saved conversation permanently

## 4. Session token vs user identity
The current app stores session data by the `X-Session-Token` header.

### Recommended production pattern
For a real Flutter app, use one of these methods:

- Use the authenticated user ID as the session token
- Use a JWT value that uniquely identifies the current user
- Use a stable UUID stored in secure local storage for anonymous users

Then send it on every request:
```http
X-Session-Token: user-1234
```

## 5. Auto-created conversations
EduMate automatically creates a new conversation when the first question is asked and no active conversation exists.

- This happens in `rag_chain.query(...)`
- It writes a new `conv_<timestamp>.json` file
- It attaches the first Q&A turn to that conversation

## 6. What is stored for each conversation
Each saved conversation file contains:
- `id`
- `title`
- `created_at`
- `updated_at`
- `messages`

Each message contains:
- `role` (`student` or `assistant`)
- `content`
- `timestamp`
- assistant messages may include `sources` and `context_docs`

## 7. How to manage user conversations in Flutter
### Recommended flow
1. Generate or obtain `sessionToken`.
2. Call `/api/conversation/list` to show saved chats.
3. When selecting a chat, call `/api/conversation/load/{id}`.
4. After load, refresh UI using `/api/conversation/history`.
5. Send new questions with `/api/query`.
6. If user wants a fresh start, call `/api/conversation/clear` or `/api/conversation/new`.
7. To delete a chat, call `/api/conversation/{id}`.

## 8. End of task note
EduMate is designed to support multi-user use through token-based isolation. The backend can share one server across many users, provided each user carries a unique `X-Session-Token` in their Flutter integration.
