# Anime Batch Downloader API

A FastAPI backend service for downloading anime episodes from AnimePagehe.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
python main.py
```
The server will start at `http://localhost:8000`

### 3. View API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📋 API Endpoints

### 🔍 Search Anime
**POST** `/search`
```json
{
  "query": "Sakamoto Days"
}
```

**Response:**
```json
[
  {
    "title": "Sakamoto Days",
    "type": "TV Series",
    "episodes": "12",
    "id": "123",
    "session": "abc123"
  }
]
```

### 📺 Get Episodes
**POST** `/episodes`
```json
{
  "anime_session": "abc123"
}
```

**Response:**
```json
[
  {
    "episode": 1,
    "session": "ep123"
  },
  {
    "episode": 2,
    "session": "ep124"
  }
]
```

### 🎥 Get Available Qualities
**POST** `/qualities`
```json
{
  "anime_session": "abc123",
  "episode_session": "ep123"
}
```

**Response:**
```json
{
  "available_qualities": {
    "720": ["eng", "jpn"],
    "1080": ["eng"]
  },
  "raw_links": {
    "720_eng": "https://...",
    "720_jpn": "https://...",
    "1080_eng": "https://..."
  }
}
```

### 📥 Start Download
**POST** `/download`
```json
{
  "anime_session": "abc123",
  "episodes": [1, 2, 3],
  "quality": "720",
  "language": "eng",
  "download_directory": "./"
}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "message": "Download started for 3 episodes"
}
```

### 📊 Check Download Status
**GET** `/download/{task_id}`

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "running",
  "progress": 45.5,
  "current_episode": 2,
  "total_episodes": 3,
  "created_at": "2024-01-01T12:00:00",
  "completed_at": null,
  "error_message": null
}
```

### 📋 List All Downloads
**GET** `/downloads`

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "uuid-string",
      "status": "completed",
      "progress": 100.0,
      "total_episodes": 3,
      ...
    }
  ]
}
```

### ❌ Cancel Download
**DELETE** `/download/{task_id}`

**Response:**
```json
{
  "message": "Download task cancelled"
}
```

## 🔧 Task Status Values
- **`pending`**: Task created but not started
- **`running`**: Currently downloading
- **`completed`**: All episodes downloaded successfully
- **`failed`**: Download failed with error
- **`cancelled`**: Task was cancelled

## 🎯 Example Usage with cURL

### Search for anime:
```bash
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "Sakamoto Days"}'
```

### Start download:
```bash
curl -X POST "http://localhost:8000/download" \
     -H "Content-Type: application/json" \
     -d '{
       "anime_session": "abc123",
       "episodes": [1, 2, 3],
       "quality": "720",
       "language": "eng"
     }'
```

### Check status:
```bash
curl "http://localhost:8000/download/your-task-id"
```

## 🐍 Python Client Example
See `api_example.py` for a complete Python client implementation.

## 🎉 Features
- ✅ **Headless operation** - No browser windows
- ✅ **Background downloads** - Non-blocking API calls
- ✅ **Progress tracking** - Real-time download status
- ✅ **Resume capability** - Automatic resume of interrupted downloads
- ✅ **Retry logic** - Robust error handling with retries
- ✅ **Multiple episodes** - Batch download support
- ✅ **Quality selection** - Choose resolution and language
- ✅ **Task management** - Track multiple download tasks

## 🛠️ Development
The API runs on port 8000 by default. You can change this in `main.py` or by setting environment variables.
