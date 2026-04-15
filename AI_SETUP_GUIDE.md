# AI Assistant Integration Setup Guide

## 🎯 What You Just Got

Your GEB app now has an **AI Assistant** integrated that can:
- 📝 **Summarize** articles
- 🏷️ **Generate Tags** for articles
- 📊 **Analyze Sentiment** of article content
- ❓ **Answer Questions** about articles

The AI runs **locally** using Ollama, so there are **no API costs** and your data stays private.

---

## 📋 Setup Instructions

### Step 1: Install Ollama

**macOS/Linux/Windows:**
1. Download Ollama from [ollama.ai](https://ollama.ai)
2. Install and launch the application
3. It will start the service at `http://localhost:11434`

**Verify it's running:**
```bash
curl http://localhost:11434/api/tags
```

You should see a JSON response with available models.

### Step 2: Download a Model

Ollama has several models optimized for different tasks:

**For Speed (Recommended for summaries):**
```bash
ollama pull mistral
```
- Size: ~4GB
- Speed: Fast
- Quality: Excellent

**Or for Better Quality:**
```bash
ollama pull neural-chat
```
- Size: ~4GB
- Speed: Moderate
- Quality: Better

**Or for Maximum Speed:**
```bash
ollama pull orca-mini
```
- Size: ~2GB
- Speed: Very Fast
- Quality: Good

### Step 3: Configure Environment

Update your `.env` file in `/backend/`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

If you're using a different model, change `mistral` to your model name.

### Step 4: Restart the Backend

The backend will auto-detect the changes. If it doesn't:
```bash
# Kill the current server and restart
cd /Users/philipdewanto/Downloads/Code/GEB/backend
/Users/philipdewanto/Downloads/Code/GEB/.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 💬 How to Use

### In the Article Page

1. Open any article
2. Look for the **✨ AI Assistant** button in the bottom-right corner
3. Click it to open the chat interface
4. Try one of these commands:

**Quick Actions:**
- Click "📝 Summarize" → AI creates a summary
- Click "🏷️ Tags" → AI generates relevant tags
- Click "📊 Sentiment" → AI analyzes the article's tone

**Ask Questions:**
- "What is this article about?"
- "Who is the main person mentioned?"
- "List the key points"
- "Is this positive or negative news?"
- Any other question about the article!

---

## 🏗️ Architecture

### Frontend
- **`AIChat.tsx`** - Floating chat widget component
- Integrated into article pages
- Handles user input and displays responses

### Backend API Endpoints
- `POST /api/ai/summarize` - Summarize an article
- `POST /api/ai/tags` - Generate tags
- `POST /api/ai/sentiment` - Analyze sentiment
- `POST /api/ai/ask` - Ask a question about an article
- `GET /api/ai/health` - Check if AI service is available

### AI Service
- **`ai_service.py`** - Calls Ollama API
- Manages prompts and responses
- Handles errors gracefully

---

## ⚙️ Advanced Configuration

### Use a Different Model

Change in `.env`:
```env
OLLAMA_MODEL=neural-chat
```

Download the model:
```bash
ollama pull neural-chat
```

Restart the backend.

### Use Remote Ollama Server

If you want to run Ollama on a different machine:

1. Start Ollama on remote machine (ensure it's accessible)
2. Update `.env`:
   ```env
   OLLAMA_BASE_URL=http://your-server-ip:11434
   OLLAMA_MODEL=mistral
   ```

### Adjust AI Behavior

Edit `/backend/app/services/ai_service.py` to modify:
- **Temperature** (0.0-1.0): Higher = more creative, Lower = more consistent
- **Max tokens**: Longer responses
- **Prompt format**: Customize how questions are asked

---

## 🚨 Troubleshooting

### "AI service unavailable" Error

**Solution:** Make sure Ollama is running:
```bash
# Check if running
curl http://localhost:11434/api/tags

# If not, restart Ollama app
```

### Model Takes Too Long to Download

- **Mistral**: ~4 GB (5-10 minutes on good internet)
- **Orca-mini**: ~2 GB (faster download)
- Try the smaller model if impatient

### Responses Are Slow

**Solutions:**
1. Use a smaller model: `ollama pull orca-mini`
2. Close other apps to free up RAM
3. Reduce max_length in the frontend (default: 250)
4. Lower temperature for faster inference

### Memory Issues

Ollama needs at least **4GB RAM** free.

**Check available memory:**
```bash
# macOS
vm_stat

# Linux
free -h
```

If low on memory, close other apps or use a smaller model.

---

## 📊 Supported Models

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| orca-mini | 2GB | ⚡⚡⚡ | 🌟🌟 | Speed |
| mistral | 4GB | ⚡⚡ | 🌟🌟🌟 | Balance |
| neural-chat | 4GB | ⚡ | 🌟🌟🌟🌟 | Quality |
| dolphin-mixtral | 26GB | 🐢 | 🌟🌟🌟🌟🌟 | Best (requires GPU) |

---

## 🔄 Future Enhancements

You can extend this further:

1. **User Preferences**
   - Save favorite summaries
   - Custom prompt templates
   - Preferred response length

2. **AI Features**
   - Multi-language support
   - Generate tweets/social posts
   - Create study guides
   - Extract quotes

3. **Integration**
   - Share AI summaries
   - Export to markdown/PDF
   - Integration with note apps

---

## 📚 API Examples

### Summarize an Article
```bash
curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "article_id": "article-id-here",
    "max_length": 200
  }'
```

### Ask a Question
```bash
curl -X POST http://localhost:8000/api/ai/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "article_id": "article-id-here",
    "question": "What is the main topic?"
  }'
```

---

## ✅ You're All Set!

Now go to `http://localhost:3000`, click on any article, and start using the AI Assistant! 🚀
