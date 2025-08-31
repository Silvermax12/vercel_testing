# M3U8 Scraper for Anime Batch Downloader

This directory contains scripts for scraping `.m3u8` links from anime episode pages after clicking the "Click to load" elements.

## Files Overview

### 1. `m3u8_scraper.py`
The core scraper class that handles:
- Finding and clicking "Click to load" elements (`<div class="click-to-load">`)
- Extracting `.m3u8` links from video players, iframes, and page source
- Handling multiple episodes and retry logic
- Saving results to JSON files

### 2. `m3u8_integration.py`
Integration script that shows how to use the scraper with the existing anime batch downloader:
- Get episode URLs from anime sessions
- Batch scrape multiple anime series
- Save results in organized JSON files

### 3. `test_m3u8.py`
Existing test script for handling `.m3u8` files (downloading, decrypting, converting to MP4)

## Features

- **Smart Element Detection**: Automatically finds and clicks "Click to load" elements
- **Multiple Extraction Methods**: 
  - Video elements with `src` attributes
  - Source elements
  - Iframe content
  - JavaScript variables in page source
  - Data attributes
- **Retry Logic**: Handles failures with exponential backoff
- **Resource Management**: Proper browser cleanup and memory management
- **Batch Processing**: Can handle multiple episodes and anime series
- **JSON Output**: Structured results for easy processing

## Usage Examples

### Basic Usage - Single Episode

```python
from m3u8_scraper import M3U8Scraper

# Create scraper instance
with M3U8Scraper(headless=False) as scraper:
    # Scrape .m3u8 links for a single episode
    episode_url = "https://animepahe.ru/play/anime_session/episode_session"
    results = scraper.scrape_episode_m3u8_links(episode_url)
    
    # Save results
    scraper.save_results(results, "episode_m3u8.json")
```

### Integration with Existing System

```python
from m3u8_integration import scrape_m3u8_for_anime

# Scrape specific episodes for an anime
results = scrape_m3u8_for_anime(
    anime_session="your_anime_session_id",
    episode_numbers=[1, 2, 3, 4, 5],
    headless=True,
    output_file="my_anime_m3u8.json"
)
```

### Batch Processing Multiple Anime

```python
from m3u8_integration import batch_scrape_multiple_anime

# Scrape multiple anime series
anime_sessions = ["session1", "session2", "session3"]
results = batch_scrape_multiple_anime(
    anime_sessions=anime_sessions,
    episode_numbers=[1, 2, 3],  # First 3 episodes
    headless=True
)
```

## Output Format

The scraper generates JSON files with the following structure:

```json
{
  "episode_url_1": {
    "video_src": "https://example.com/video.m3u8",
    "iframe_video": "https://example.com/iframe_video.m3u8",
    "js_extracted_0": "https://example.com/js_video.m3u8"
  },
  "episode_url_2": {
    "source_src": "https://example.com/source.m3u8"
  }
}
```

## Configuration Options

### M3U8Scraper Parameters

- `headless`: Run browser in headless mode (default: True)
- `max_retries`: Number of retry attempts for failed scrapes (default: 3)

### Browser Options

The scraper uses the existing `browser.py` utilities:
- Stealth Chrome driver with anti-detection
- Unique user data directories to avoid conflicts
- Proper cleanup and resource management

## Error Handling

The scraper includes comprehensive error handling:
- **Timeout Exceptions**: Page load timeouts with retry logic
- **Element Not Found**: Graceful handling when "Click to load" elements aren't present
- **Click Failures**: Fallback to guarded click methods
- **Iframe Errors**: Safe iframe context switching with fallback
- **Resource Cleanup**: Ensures browser resources are properly cleaned up

## Dependencies

Required packages (already in `requirements.txt`):
- `selenium` - Web automation
- `requests` - HTTP requests
- `m3u8` - M3U8 playlist parsing (for test_m3u8.py)

## Integration Points

### With Existing Scraper
The new M3U8 scraper complements the existing `scraper.py`:
- `scraper.py` gets download links from the download menu
- `m3u8_scraper.py` gets `.m3u8` links from video players

### With Download System
The extracted `.m3u8` links can be used with:
- `test_m3u8.py` for downloading and converting to MP4
- Future integration with the main download pipeline

## Best Practices

1. **Rate Limiting**: Include delays between episodes to avoid overwhelming servers
2. **Headless Mode**: Use headless mode for production, non-headless for debugging
3. **Error Logging**: Monitor the console output for any scraping issues
4. **Resource Management**: Always use the context manager (`with` statement) for proper cleanup
5. **Output Organization**: Use descriptive filenames for different anime series

## Troubleshooting

### Common Issues

1. **"Click to load" elements not found**
   - Check if the page structure has changed
   - Verify the CSS selector is still correct
   - Ensure the page has fully loaded

2. **No .m3u8 links extracted**
   - The video player might use a different format
   - Check if the content is loaded in an iframe
   - Verify the page source contains .m3u8 URLs

3. **Browser crashes or timeouts**
   - Reduce the number of concurrent operations
   - Increase timeout values
   - Check system resources

### Debug Mode

Run with `headless=False` to see what's happening in the browser:
```python
scraper = M3U8Scraper(headless=False)
```

## Future Enhancements

Potential improvements for the M3U8 scraper:
- **Quality Detection**: Automatically detect video quality from .m3u8 playlists
- **Language Detection**: Identify audio language options
- **Parallel Processing**: Scrape multiple episodes simultaneously
- **Proxy Support**: Add proxy rotation for large-scale scraping
- **Database Integration**: Store results in a database instead of JSON files
- **API Endpoint**: Add FastAPI endpoint for the scraper functionality
