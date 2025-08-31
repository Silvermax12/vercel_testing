import re
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from browser import create_stealth_driver, guarded_click, cleanup_browser_data


def scrape_download_links(anime_session, episode_session, max_retries=2):
    """Scrape download links with retry logic and better error handling"""
    url = f"https://animepahe.ru/play/{anime_session}/{episode_session}"
    
    for attempt in range(max_retries):
        driver = None
        try:
            print(f"🌐 Scraping attempt {attempt + 1}/{max_retries} for {url}")
            driver = create_stealth_driver(headless=True)
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for download button
            download_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "downloadMenu"))
            )
            
            # Click download button
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                download_button.click()
            except Exception as e:
                print(f"⚠️ Direct click failed, trying guarded click: {e}")
                guarded_click(driver, download_button, max_retries=3)
            
            # Wait for dropdown to appear
            dropdown = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.ID, "pickDownload"))
            )
            
            # Extract download links
            anchors = dropdown.find_elements(By.TAG_NAME, "a")
            links = {}
            
            for a in anchors:
                href = a.get_attribute("href")
                text = a.text.strip()
                match = re.search(r"(\d{3,4})p", text)
                if href and match:
                    quality = match.group(1)
                    if "eng" in text.lower():
                        lang = "eng"
                    elif "chi" in text.lower():
                        lang = "chi"
                    else:
                        lang = "jpn"
                    links[f"{quality}_{lang}"] = href
            
            if links:
                print(f"✅ Successfully scraped {len(links)} download links")
                return links
            else:
                print(f"⚠️ No download links found on attempt {attempt + 1}")
                
        except TimeoutException as ex:
            print(f"⚠️ Timeout on attempt {attempt + 1}: {ex}")
            if attempt == max_retries - 1:
                raise Exception(f"Page load timeout after {max_retries} attempts. The episode may not be available.")
                
        except Exception as ex:
            print(f"⚠️ Error on attempt {attempt + 1}: {ex}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to scrape download links: {str(ex)}")
                
        finally:
            if driver:
                try:
                    cleanup_browser_data(driver)  # Clean up temp directory first
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Error closing driver: {e}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            print(f"⏳ Waiting before retry...")
            time.sleep(2 ** attempt + 1)  # Exponential backoff + 1 second minimum
    
    return {}


def scrape_m3u8_links(anime_session, episode_session, quality="720", language="eng", max_retries=3):
    """
    Scrape .m3u8 links after clicking 'Click to load' elements and selecting quality/language

    Args:
        anime_session: Anime session ID
        episode_session: Episode session ID
        quality: Desired quality (360, 720, 1080)
        language: Desired language (eng, chi, jpn)
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary containing .m3u8 link info
    """
    url = f"https://animepahe.ru/play/{anime_session}/{episode_session}"

    for attempt in range(max_retries):
        driver = None
        try:
            print(f"🌐 Scraping .m3u8 links attempt {attempt + 1}/{max_retries} for {url}")
            driver = create_stealth_driver(headless=True)
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait for and click the "Click to load" element
            try:
                click_to_load = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.click-to-load"))
                )

                # Scroll element into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", click_to_load)
                time.sleep(1)

                # Click the element
                try:
                    click_to_load.click()
                except Exception as e:
                    print(f"⚠️ Direct click failed, trying guarded click: {e}")
                    guarded_click(driver, click_to_load, max_retries=3)

                print("✅ Clicked 'Click to load' element")

                # Wait for content to load and dropdown to appear
                time.sleep(3)

                # Look for the resolution dropdown menu
                resolution_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "resolutionMenu"))
                )

                # Find the active button that matches the desired quality and language
                active_button = None
                dropdown_items = resolution_menu.find_elements(By.CSS_SELECTOR, "button.dropdown-item")

                print(f"🔍 Looking for {quality}p {language.upper()} quality...")

                for button in dropdown_items:
                    data_resolution = button.get_attribute("data-resolution")
                    data_audio = button.get_attribute("data-audio")

                    # Check if this button matches our desired quality and language
                    if data_resolution == quality and data_audio == language:
                        active_button = button
                        break

                if not active_button:
                    print(f"⚠️ No matching {quality}p {language.upper()} quality found. Available options:")
                    for button in dropdown_items:
                        data_resolution = button.get_attribute("data-resolution") or "unknown"
                        data_audio = button.get_attribute("data-audio") or "unknown"
                        data_src = button.get_attribute("data-src") or "no-src"
                        print(f"  - {data_resolution}p {data_audio.upper()}: {data_src[:50]}...")

                    # If no exact match, try to find the active one or first available
                    active_buttons = [btn for btn in dropdown_items if "active" in (btn.get_attribute("class") or "")]
                    if active_buttons:
                        active_button = active_buttons[0]
                        print(f"🔄 Using active button: {active_button.get_attribute('data-resolution')}p {active_button.get_attribute('data-audio')}")
                    else:
                        active_button = dropdown_items[0] if dropdown_items else None
                        print("🔄 Using first available button")

                if active_button:
                    data_src = active_button.get_attribute("data-src")
                    data_resolution = active_button.get_attribute("data-resolution")
                    data_audio = active_button.get_attribute("data-audio")
                    data_fansub = active_button.get_attribute("data-fansub")

                    if data_src:
                        print(f"✅ Found .m3u8 link: {data_resolution}p {data_audio.upper()} from {data_fansub}")
                        return {
                            "m3u8_url": data_src,
                            "quality": data_resolution,
                            "language": data_audio,
                            "fansub": data_fansub,
                            "episode_session": episode_session,
                            "anime_session": anime_session
                        }
                    else:
                        print("⚠️ Active button found but no data-src attribute")
                else:
                    print("❌ No suitable button found in dropdown")

            except TimeoutException as e:
                print(f"⚠️ Timeout waiting for elements: {e}")
            except NoSuchElementException as e:
                print(f"⚠️ Element not found: {e}")
            except Exception as e:
                print(f"⚠️ Error during .m3u8 scraping: {e}")

        except Exception as ex:
            print(f"⚠️ Error on attempt {attempt + 1}: {ex}")

        finally:
            if driver:
                try:
                    cleanup_browser_data(driver)
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Error closing driver: {e}")

        # Wait before retry
        if attempt < max_retries - 1:
            print(f"⏳ Waiting before retry...")
            time.sleep(2 ** attempt + 1)

    return {}


def scrape_multiple_episodes_m3u8(anime_session, episode_sessions, quality="720", language="eng"):
    """
    Scrape .m3u8 links for multiple episodes

    Args:
        anime_session: Anime session ID
        episode_sessions: List of episode session IDs
        quality: Desired quality (360, 720, 1080)
        language: Desired language (eng, chi, jpn)

    Returns:
        Dictionary mapping episode numbers to .m3u8 link data
    """
    results = {}
    total_episodes = len(episode_sessions)

    for i, episode_session in enumerate(episode_sessions):
        print(f"\n📺 Processing episode {i+1}/{total_episodes}")

        try:
            m3u8_data = scrape_m3u8_links(anime_session, episode_session, quality, language)
            if m3u8_data:
                # Extract episode number from session or use index
                episode_num = i + 1  # Default to sequential numbering
                results[str(episode_num)] = m3u8_data
                print(f"✅ Episode {episode_num}: .m3u8 link extracted")
            else:
                print(f"❌ Episode {i+1}: Failed to extract .m3u8 link")

        except Exception as e:
            print(f"❌ Failed to scrape episode {i+1}: {e}")
            results[str(i+1)] = {}

        # Small delay between episodes to avoid overwhelming the server
        if i < total_episodes - 1:
            time.sleep(2)

    return results


def save_m3u8_results(results, filename="m3u8_links.json"):
    """Save m3u8 scraping results to a JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving results: {e}")
        return False


