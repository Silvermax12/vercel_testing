#!/usr/bin/env python3
"""
Integration script for M3U8 scraping with the existing anime batch downloader
This script demonstrates how to use the M3U8Scraper to get .m3u8 links for episodes
"""

import json
import os
from typing import List, Dict
from m3u8_scraper import M3U8Scraper
from api_client import search_anime, get_all_episodes
from session_mgr import SessionManager


def get_episode_urls(anime_session: str, episode_numbers: List[int] = None) -> List[str]:
    """
    Get episode URLs for a specific anime
    
    Args:
        anime_session: The anime session ID
        episode_numbers: List of specific episode numbers to get (None for all)
        
    Returns:
        List of episode URLs
    """
    try:
        # Get session manager
        session_manager = SessionManager()
        
        # Get all episodes for the anime
        episodes = get_all_episodes(session_manager, anime_session)
        
        if not episodes:
            print(f"❌ No episodes found for anime session: {anime_session}")
            return []
        
        # Filter episodes if specific numbers are requested
        if episode_numbers:
            episodes = [ep for ep in episodes if ep['episode'] in episode_numbers]
        
        # Build episode URLs
        episode_urls = []
        for episode in episodes:
            url = f"https://animepahe.ru/play/{anime_session}/{episode['session']}"
            episode_urls.append(url)
        
        print(f"✅ Found {len(episode_urls)} episode URLs")
        return episode_urls
        
    except Exception as e:
        print(f"❌ Error getting episode URLs: {e}")
        return []


def scrape_m3u8_for_anime(anime_session: str, episode_numbers: List[int] = None, 
                          headless: bool = True, output_file: str = None) -> Dict:
    """
    Scrape .m3u8 links for all episodes of an anime
    
    Args:
        anime_session: The anime session ID
        episode_numbers: List of specific episode numbers to scrape (None for all)
        headless: Whether to run browser in headless mode
        output_file: Output file path for results (None for default)
        
    Returns:
        Dictionary containing scraping results
    """
    print(f"🎬 Starting .m3u8 scraping for anime session: {anime_session}")
    
    # Get episode URLs
    episode_urls = get_episode_urls(anime_session, episode_numbers)
    
    if not episode_urls:
        print("❌ No episode URLs to scrape")
        return {}
    
    # Create output filename if not provided
    if not output_file:
        output_file = f"m3u8_links_{anime_session}.json"
    
    # Scrape .m3u8 links
    with M3U8Scraper(headless=headless, max_retries=3) as scraper:
        try:
            results = scraper.scrape_multiple_episodes(episode_urls)
            
            # Save results
            scraper.save_results(results, output_file)
            
            # Print summary
            print(f"\n📊 Scraping Summary for {anime_session}:")
            total_links = 0
            for url, links in results.items():
                episode_name = url.split('/')[-1] if '/' in url else url
                link_count = len(links)
                total_links += link_count
                print(f"  {episode_name}: {link_count} .m3u8 links found")
            
            print(f"\n🎯 Total .m3u8 links found: {total_links}")
            print(f"💾 Results saved to: {output_file}")
            
            return results
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return {}


def batch_scrape_multiple_anime(anime_sessions: List[str], episode_numbers: List[int] = None,
                               headless: bool = True) -> Dict:
    """
    Batch scrape .m3u8 links for multiple anime
    
    Args:
        anime_sessions: List of anime session IDs
        episode_numbers: List of specific episode numbers to scrape (None for all)
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary containing all scraping results
    """
    all_results = {}
    
    for i, anime_session in enumerate(anime_sessions):
        print(f"\n{'='*50}")
        print(f"🎬 Processing anime {i+1}/{len(anime_sessions)}: {anime_session}")
        print(f"{'='*50}")
        
        try:
            results = scrape_m3u8_for_anime(
                anime_session=anime_session,
                episode_numbers=episode_numbers,
                headless=headless,
                output_file=f"m3u8_links_{anime_session}.json"
            )
            
            all_results[anime_session] = results
            
        except Exception as e:
            print(f"❌ Failed to scrape anime {anime_session}: {e}")
            all_results[anime_session] = {}
    
    # Save combined results
    combined_file = "m3u8_links_combined.json"
    try:
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Combined results saved to: {combined_file}")
    except Exception as e:
        print(f"❌ Error saving combined results: {e}")
    
    return all_results


def main():
    """Example usage of the M3U8 integration"""
    
    # Example 1: Scrape specific episodes for one anime
    print("🎬 Example 1: Scrape specific episodes for one anime")
    anime_session = "example_anime_session"  # Replace with actual session ID
    episode_numbers = [1, 2, 3]  # Replace with actual episode numbers
    
    results = scrape_m3u8_for_anime(
        anime_session=anime_session,
        episode_numbers=episode_numbers,
        headless=False,  # Set to True for headless mode
        output_file="example_anime_m3u8.json"
    )
    
    # Example 2: Batch scrape multiple anime (uncomment to use)
    # print("\n🎬 Example 2: Batch scrape multiple anime")
    # anime_sessions = [
    #     "anime_session_1",
    #     "anime_session_2",
    #     "anime_session_3"
    # ]
    # 
    # batch_results = batch_scrape_multiple_anime(
    #     anime_sessions=anime_sessions,
    #     episode_numbers=[1, 2, 3, 4, 5],  # First 5 episodes
    #     headless=True
    # )


if __name__ == "__main__":
    main()
