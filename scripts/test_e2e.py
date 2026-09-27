from playwright.sync_api import sync_playwright
import time
import sys

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to workspace...")
        page.goto("http://localhost:3000/workspace")
        
        print("Uploading Source Image...")
        # Find the input type=file for Source Image
        file_inputs = page.locator("input[type='file']").all()
        if len(file_inputs) >= 2:
            file_inputs[0].set_input_files("C:/Users/GOUSHIK/OneDrive/Desktop/SELORA/data/raw/demo_same_source.png")
            print("Uploading Reference Image...")
            file_inputs[1].set_input_files("C:/Users/GOUSHIK/OneDrive/Desktop/SELORA/data/raw/demo_same_reference.png")
        else:
            print(f"Error: Found only {len(file_inputs)} file inputs, expected at least 2.")
            sys.exit(1)
            
        time.sleep(1) # wait for UI to update
        print("Clicking Register Images button...")
        
        # Click the register button
        register_btn = page.get_by_role("button", name="REGISTER IMAGES")
        if register_btn.count() > 0:
            register_btn.first.click()
        else:
            print("Error: Could not find REGISTER IMAGES button.")
            sys.exit(1)
            
        print("Waiting for registration to complete (up to 30s)...")
        # Wait for some result element to appear
        try:
            # We can just wait for a text like "Metrics" or an image with alt "Registered Image"
            page.wait_for_selector("text=Metrics", timeout=30000)
            page.wait_for_selector("text=Inliers", timeout=10000)
            print("SUCCESS: UI elements appeared after registration.")
        except Exception as e:
            print(f"Error: UI elements did not appear. {e}")
            sys.exit(1)
            
        browser.close()

if __name__ == "__main__":
    run_test()
