"""截图工具"""
import os, sys
os.makedirs("D:/Deep Xcode/ai-engineer-hotlist/docs/screenshots", exist_ok=True)

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8899"
OUT = "D:/Deep Xcode/ai-engineer-hotlist/docs/screenshots"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    
    # Full page
    page.screenshot(path=f"{OUT}/01-fullpage.png", full_page=True)
    print(f"[OK] fullpage: {os.path.getsize(f'{OUT}/01-fullpage.png')} bytes")
    
    # Top bar
    hb = page.locator(".stats-bar").bounding_box()
    if hb:
        clip = {"x": 0, "y": 0, "width": 1440, "height": hb["y"] + hb["height"] + 10}
        page.screenshot(path=f"{OUT}/02-topbar.png", clip=clip)
        print(f"[OK] topbar")
    
    # First card section
    section = page.locator(".section").first
    section.screenshot(path=f"{OUT}/03-section.png")
    print(f"[OK] section")
    
    # Mobile viewport
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=f"{OUT}/04-mobile.png", full_page=True)
    print(f"[OK] mobile")
    
    b.close()
print("ALL DONE")
