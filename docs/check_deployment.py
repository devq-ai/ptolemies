#!/usr/bin/env python3
"""
Deployment Verification Script for Ptolemies Status System
Checks if the new status page has been deployed to GitHub Pages
"""

import requests
import time
import json
from datetime import datetime

def check_deployment():
    """Check if new status system is deployed."""
    url = "https://devq-ai.github.io/ptolemies/"
    json_url = "https://devq-ai.github.io/ptolemies/status.json"

    print("🔍 Checking Ptolemies GitHub Pages deployment...")
    print(f"📍 URL: {url}")
    print(f"📊 JSON: {json_url}")
    print()

    try:
        # Check main page
        print("1️⃣ Checking main page...")
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            content = response.text.lower()

            # Check if it's the new status page
            if "ptolemies status" in content and "knowledge management system" in content:
                if "interactive status dashboard" in content or "status-card" in content:
                    print("✅ New status page is live!")
                    new_page = True
                else:
                    print("⚠️  Page loaded but might be cached old version")
                    new_page = False
            else:
                print("❌ Old status page is still showing")
                new_page = False
        else:
            print(f"❌ Page not accessible (HTTP {response.status_code})")
            new_page = False

    except requests.RequestException as e:
        print(f"❌ Failed to check main page: {e}")
        new_page = False

    try:
        # Check JSON endpoint
        print("\n2️⃣ Checking JSON endpoint...")
        response = requests.get(json_url, timeout=10)

        if response.status_code == 200:
            try:
                data = response.json()
                if 'system' in data and 'knowledge_base' in data:
                    print("✅ JSON endpoint is working!")
                    timestamp = data.get('timestamp', 'Unknown')
                    print(f"📅 Last updated: {timestamp}")

                    # Show key metrics
                    if 'system' in data:
                        print(f"🏛️  System: {data['system'].get('name', 'Unknown')}")
                        print(f"📦 Version: {data['system'].get('version', 'Unknown')}")

                    if 'knowledge_base' in data:
                        kb = data['knowledge_base']
                        print(f"📚 Knowledge Base: {kb.get('total_chunks', 0)} chunks")

                    if 'ai_detection' in data:
                        ai = data['ai_detection']
                        print(f"🤖 AI Detection: {ai.get('accuracy_rate', 'Unknown')}")

                    json_working = True
                else:
                    print("❌ JSON structure doesn't match expected format")
                    json_working = False
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                json_working = False
        else:
            print(f"❌ JSON endpoint not accessible (HTTP {response.status_code})")
            json_working = False

    except requests.RequestException as e:
        print(f"❌ Failed to check JSON endpoint: {e}")
        json_working = False

    # Summary
    print("\n" + "="*50)
    print("📋 DEPLOYMENT STATUS SUMMARY")
    print("="*50)

    if new_page and json_working:
        print("🎉 SUCCESS: New status system is fully deployed!")
        print("🌍 Live at: https://devq-ai.github.io/ptolemies/")
        return True
    elif new_page:
        print("⚠️  PARTIAL: New page is live but JSON has issues")
        return False
    elif json_working:
        print("⚠️  PARTIAL: JSON works but old page still showing")
        return False
    else:
        print("❌ FAILED: Deployment not yet complete")
        return False

def wait_for_deployment(max_wait_minutes=10):
    """Wait for deployment to complete."""
    print(f"⏳ Waiting up to {max_wait_minutes} minutes for deployment...")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60

    while time.time() - start_time < max_wait_seconds:
        if check_deployment():
            elapsed = int(time.time() - start_time)
            print(f"\n🎯 Deployment completed in {elapsed} seconds!")
            return True

        print("\n⏸️  Waiting 30 seconds before next check...")
        time.sleep(30)

    print(f"\n⏰ Timeout: Deployment not completed in {max_wait_minutes} minutes")
    return False

def show_urls():
    """Show important URLs for the deployment."""
    print("\n🔗 Important URLs:")
    print("📊 Live Dashboard: https://devq-ai.github.io/ptolemies/")
    print("📋 JSON API: https://devq-ai.github.io/ptolemies/status.json")
    print("🐙 GitHub Repo: https://github.com/devq-ai/ptolemies")
    print("⚙️  GitHub Actions: https://github.com/devq-ai/ptolemies/actions")

def main():
    """Main function."""
    import sys

    print("🚀 Ptolemies Deployment Verification")
    print("=" * 40)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        wait_time = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        success = wait_for_deployment(wait_time)
    else:
        success = check_deployment()

    show_urls()

    if success:
        print("\n✨ All systems ready!")
        sys.exit(0)
    else:
        print("\n🔧 Deployment still in progress or failed")
        print("💡 Try: python check_deployment.py --wait 10")
        sys.exit(1)

if __name__ == "__main__":
    main()
