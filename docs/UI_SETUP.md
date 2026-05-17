# EduMate RAG - Modern Web UI

A beautiful, modern web interface for the EduMate RAG system with real-time chat, conversation memory, and source attribution.

## Features

 **Modern UI**
- Beautiful gradient design with dark theme
- Smooth animations and transitions
- Responsive layout across all screen sizes

 **Real-time Chat**
- Interactive conversation interface
- Multi-turn conversation support
- Automatic scrolling to latest messages

 **Source Attribution**
- View all referenced course materials
- Document statistics and context tracking
- Turn-based conversation history

 **Conversation Management**
- Clear chat history with one click
- Re-index PDFs on demand
- Real-time connection status

## Setup

### 1. Ensure Backend Server is Running

```bash
python main.py
```

This starts the FastAPI server on `http://localhost:8000` with hot reload.

### 2. Access the UI

Open your browser and navigate to:
```
http://localhost:8000
```

The UI will automatically load from `src/api/static/index.html`.

## Usage

### Asking Questions

1. Type your question in the input field at the bottom
2. Press Enter or click the "Ask" button
3. The assistant will retrieve relevant course materials and provide an answer
4. Sources are displayed in the right panel

### Conversation History

- The left sidebar shows conversation statistics
- Each turn is tracked and numbered
- Previous messages inform the context for follow-up questions

### Managing Conversations

**Clear Chat:** Removes all conversation history and starts fresh
**Index PDFs:** Re-indexes all PDFs in the course_pdfs folder

## UI Components

### Left Sidebar
- **EduMate Logo**: Quick access branding
- **Conversation Stats**: Turn count and status
- **History**: Quick view of conversation history
- **Action Buttons**: Clear and Index controls

### Main Chat Area
- **Messages Panel**: All conversation messages
- **Input Field**: Type your questions
- **Send Button**: Submit your question

### Right Panel (Sources)
- **Sources List**: All referenced course materials
- **Statistics**: Number of context documents and turn number

## Styling

The UI uses:
- **Tailwind CSS** for styling (via CDN)
- **Gradient backgrounds** with purple/blue theme
- **Glass-morphism effects** for modern look
- **Smooth animations** for better UX
- **Dark theme** for comfortable late-night studying

## Keyboard Shortcuts

- **Enter**: Send question (when focused on input)
- **Escape**: (Optional - you can extend this)

## Error Handling

The UI includes error handling for:
- Network failures
- API errors
- Empty questions
- Backend unavailability

If the backend is not running, you'll see a warning message.

## Browser Compatibility

Works on:
- Chrome/Chromium (Latest)
- Firefox (Latest)
- Safari (Latest)
- Edge (Latest)

## Troubleshooting

### "Cannot connect to backend"
- Ensure FastAPI server is running: `python main.py`
- Check if the server is on `http://localhost:8000`
- Check browser console for CORS errors (usually not an issue, CORS is enabled)

### Questions not being answered
- Ensure PDFs are indexed: Click "Index PDFs" button
- Check if PDFs are in `./assets/course_pdfs` folder
- Verify `.env` file has `GROQ_API_KEY` set

### Slow responses
- This is normal for Groq API on first request
- Check internet connection
- Large PDFs may take time to process

## Customization

To customize the UI, edit `src/api/static/index.html`:

1. **Colors**: Search for `#667eea` and `#764ba2` (gradient colors)
2. **API Endpoint**: Change `API_BASE` variable at the top of the script section
3. **Fonts**: Modify Tailwind CSS classes
4. **Layout**: Adjust sidebar widths, panel sizes, etc.

## API Endpoints Used

- `GET /health` - Check backend status
- `POST /api/query` - Send a question
- `GET /api/conversation/history` - Get chat history
- `POST /api/conversation/clear` - Clear memory
- `POST /api/index` - Re-index PDFs
- `GET /api/conversation/info` - Get conversation stats

## Performance Tips

1. **Optimize PDFs**: Large PDFs take longer to index
2. **Slim vectors**: The system uses Groq's embeddings, which are fast
3. **Network**: A stable internet connection is required for Groq API

## Future Enhancements

Potential improvements:
- Dark/Light theme toggle
- Export conversation to PDF
- Search previous conversations
- File upload directly from UI
- Advanced search filters
- Code snippet highlighting for technical content
- Voice input/output support
