import re
import time
import json
import os
from typing import Dict, List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from browser import create_stealth_driver, guarded_click, cleanup_browser_data


class M3U8Scraper:
    """Scraper for extracting .m3u8 links after clicking 'Click to load' elements"""
    
    def __init__(self, headless: bool = True, max_retries: int = 3):
        self.headless = headless
        self.max_retries = max_retries
        self.driver = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        
    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                cleanup_browser_data(self.driver)
                self.driver.quit()
            except Exception as e:
                print(f"⚠️ Error closing driver: {e}")
            finally:
                self.driver = None
    
    def scrape_episode_m3u8_links(self, episode_url: str) -> Dict[str, str]:
        """
        Scrape .m3u8 links for a single episode after clicking 'Click to load' elements
        
        Args:
            episode_url: URL of the episode page
            
        Returns:
            Dictionary mapping quality_language to .m3u8 URL
        """
        print(f"🌐 Scraping .m3u8 links from: {episode_url}")
        
        for attempt in range(self.max_retries):
            try:
                if not self.driver:
                    self.driver = create_stealth_driver(headless=self.headless)
                
                self.driver.get(episode_url)
                
                # Wait for page to load
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Look for "Click to load" elements
                click_to_load_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div.click-to-load"
                )
                
                if not click_to_load_elements:
                    print("⚠️ No 'Click to load' elements found")
                    return {}
                
                print(f"🔍 Found {len(click_to_load_elements)} 'Click to load' elements")
                
                m3u8_links = {}
                
                # Process each "Click to load" element
                for i, element in enumerate(click_to_load_elements):
                    try:
                        print(f"🖱️ Clicking element {i+1}/{len(click_to_load_elements)}")
                        
                        # Scroll element into view
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", 
                            element
                        )
                        
                        # Wait a moment for any animations
                        time.sleep(1)
                        
                        # Click the element
                        try:
                            element.click()
                        except Exception as e:
                            print(f"⚠️ Direct click failed, trying guarded click: {e}")
                            guarded_click(self.driver, element, max_retries=3)
                        
                        # Wait for content to load (look for video player or iframe)
                        time.sleep(3)
                        
                        # Look for video player or iframe that might contain .m3u8
                        video_sources = self._extract_video_sources()
                        
                        if video_sources:
                            print(f"✅ Found video sources for element {i+1}")
                            m3u8_links.update(video_sources)
                        else:
                            print(f"⚠️ No video sources found for element {i+1}")
                            
                    except Exception as e:
                        print(f"⚠️ Error processing element {i+1}: {e}")
                        continue
                
                if m3u8_links:
                    print(f"✅ Successfully extracted {len(m3u8_links)} .m3u8 links")
                    return m3u8_links
                else:
                    print(f"⚠️ No .m3u8 links found on attempt {attempt + 1}")
                    
            except TimeoutException as ex:
                print(f"⚠️ Timeout on attempt {attempt + 1}: {ex}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Page load timeout after {self.max_retries} attempts")
                    
            except Exception as ex:
                print(f"⚠️ Error on attempt {attempt + 1}: {ex}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Failed to scrape .m3u8 links: {str(ex)}")
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                print(f"⏳ Waiting before retry...")
                time.sleep(2 ** attempt + 1)
        
        return {}
    
    def _extract_video_sources(self) -> Dict[str, str]:
        """
        Extract video sources from the page after clicking 'Click to load'
        
        Returns:
            Dictionary mapping quality_language to .m3u8 URL
        """
        sources = {}
        
        if not self.driver:
            print("⚠️ No driver available")
            return sources
        
        try:
            # Method 1: Look for video elements with src attributes
            video_elements = self.driver.find_elements(By.TAG_NAME, "video")
            for video in video_elements:
                src = video.get_attribute("src")
                if src and ".m3u8" in src:
                    sources["video_src"] = src
            
            # Method 2: Look for source elements
            source_elements = self.driver.find_elements(By.TAG_NAME, "source")
            for source in source_elements:
                src = source.get_attribute("src")
                if src and ".m3u8" in src:
                    sources["source_src"] = src
            
            # Method 3: Look for iframes that might contain video players
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    src = iframe.get_attribute("src")
                    if src and ("player" in src.lower() or "embed" in src.lower()):
                        # Switch to iframe context
                        self.driver.switch_to.frame(iframe)
                        
                        # Look for video sources in iframe
                        iframe_video = self.driver.find_elements(By.TAG_NAME, "video")
                        for video in iframe_video:
                            src = video.get_attribute("src")
                            if src and ".m3u8" in src:
                                sources["iframe_video"] = src
                        
                        # Switch back to main context
                        self.driver.switch_to.default_content()
                        
                except Exception as e:
                    print(f"⚠️ Error processing iframe: {e}")
                    # Make sure we're back in main context
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
            
            # Method 4: Look for JavaScript variables or data attributes that might contain .m3u8 URLs
            page_source = self.driver.page_source
            m3u8_matches = re.findall(r'https?://[^"\s]+\.m3u8[^"\s]*', page_source)
            
            for i, match in enumerate(m3u8_matches):
                if match not in sources.values():
                    sources[f"js_extracted_{i}"] = match
            
            # Method 5: Look for any elements with data attributes containing .m3u8
            data_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "[data-src*='.m3u8'], [data-url*='.m3u8'], [data-source*='.m3u8']"
            )
            
            for element in data_elements:
                for attr in ["data-src", "data-url", "data-source"]:
                    value = element.get_attribute(attr)
                    if value and ".m3u8" in value:
                        sources[f"data_attr_{attr}"] = value
            
        except Exception as e:
            print(f"⚠️ Error extracting video sources: {e}")
        
        return sources
    
    def scrape_multiple_episodes(self, episode_urls: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Scrape .m3u8 links for multiple episodes
        
        Args:
            episode_urls: List of episode URLs to scrape
            
        Returns:
            Dictionary mapping episode URL to its .m3u8 links
        """
        results = {}
        
        for i, url in enumerate(episode_urls):
            print(f"\n📺 Processing episode {i+1}/{len(episode_urls)}")
            try:
                episode_links = self.scrape_episode_m3u8_links(url)
                results[url] = episode_links
                
                # Small delay between episodes to avoid overwhelming the server
                if i < len(episode_urls) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Failed to scrape episode {i+1}: {e}")
                results[url] = {}
        
        return results
    
    def save_results(self, results: Dict[str, Dict[str, str]], filename: str = "m3u8_links.json"):
        """Save scraping results to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"💾 Results saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")


def main():
    """Example usage of the M3U8Scraper"""
    
    # Example episode URLs (replace with actual URLs)
    episode_urls = [
        "https://animepahe.ru/play/example_anime_session/episode_1_session",
        "https://animepahe.ru/play/example_anime_session/episode_2_session",
        # Add more episode URLs as needed
    ]
    
    # Create scraper instance
    with M3U8Scraper(headless=False, max_retries=2) as scraper:
        try:
            # Scrape .m3u8 links for all episodes
            results = scraper.scrape_multiple_episodes(episode_urls)
            
            # Save results
            scraper.save_results(results)
            
            # Print summary
            print("\n📊 Scraping Summary:")
            for url, links in results.items():
                episode_name = url.split('/')[-1] if '/' in url else url
                print(f"  {episode_name}: {len(links)} .m3u8 links found")
                
        except Exception as e:
            print(f"❌ Scraping failed: {e}")


if __name__ == "__main__":
    main()
