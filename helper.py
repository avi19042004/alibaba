import os, sys, time, json, base64, random, subprocess, traceback, logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import messagebox
import psutil
import undetected_chromedriver as uc
import requests

# ------------------ CONFIG ------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.json")
LOG_FILE = os.path.join(BASE_DIR, "app.log")
ERROR_LOG = os.path.join(BASE_DIR, "error.log")
ACTIVITY_LOG = os.path.join(BASE_DIR, "activity.log")
OPENROUTER_API_KEY = "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"

CHROME_PID = None
BASE_URL = "https://alibaba.com/"
MAIN_URL = "https://onetalk.alibaba.com/message/weblitePWA.htm?isGray=1&from=menu&hideMenu=1#/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[
    logging.FileHandler(LOG_FILE),
    logging.StreamHandler()
])

# ------------------ HELPERS ------------------
def show_popup(message):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", message)

def log_error(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ERROR: {msg}\n")
        f.write(traceback.format_exc() + "\n\n")
    show_popup(msg)

def log_activity(msg):
    with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    logging.info("📘 " + msg)

def random_delay(min_sec=1, max_sec=5):
    delay = random.uniform(min_sec, max_sec)
    logging.info(f"⏳ Sleeping for {delay:.2f} seconds...")
    time.sleep(delay)

def cleanup():
    global CHROME_PID
    if CHROME_PID:
        try:
            psutil.Process(CHROME_PID).terminate()
            log_activity("✅ Closed Chrome.")
        except Exception as e:
            log_error(f"⚠️ Could not kill Chrome: {e}")

def init_browser():
    global CHROME_PID
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    # options.add_argument("--headless=new")
    options.add_argument('--enable-features=DnsOverHttps')
    options.add_argument('--dns-over-https-servers=https://dns.google/dns-query')


    driver = uc.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """
    })
    CHROME_PID = driver.browser_pid
    log_activity(f"🟢 Chrome started: PID={CHROME_PID}")
    return driver

def login(driver):
    driver.get(BASE_URL)
    random_delay(2, 4)
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
            for cookie in cookies:
                if "expiry" in cookie:
                    cookie["expiry"] = int(cookie["expiry"])
                driver.add_cookie(cookie)
        log_activity("✅ Cookies loaded.")
    else:
        show_popup("🔐 Login manually, then press OK.")
        time.sleep(15)
        with open(COOKIES_FILE, "w") as f:
            json.dump(driver.get_cookies(), f)
        log_activity("✅ Cookies saved.")
    driver.get(BASE_URL)

def solve_captcha(base64_img):
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "meta-llama/llama-4-maverick:free",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant master in captcha solving."},
                {"role": "user", "content": [
                    {"type": "text", "text": "extract text from image and get me text only as output in english"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
                ]}
            ]
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log_error(f"❌ CAPTCHA solving failed: {e}")
        return ""

def send_inquiry_flow(driver, url):
    try:
        driver.get(url)
        random_delay(3, 6)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Send inquiry']"))).click()
        time.sleep(6)
        iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.alitalk-dialog-iframe")))
        driver.switch_to.frame(iframe)
        tags = driver.find_elements(By.CSS_SELECTOR, "span.entry-tag")
        if tags:
            random.choice(tags[:-1]).click()
        time.sleep(2)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@class='finish-process-item' and img[contains(@src,'alicdn.com/imgextra')]]"))).click()
        time.sleep(2)
        return "Inquiry sent successfully"
    except Exception as e:
        log_error(f"❌ Flow error: {e}")
        return "Failed to send inquiry"

def send_ai_response(driver, recipient):
    try:
        driver.get(MAIN_URL)
        random_delay(3, 5)
        recipient_xpath = f"//div[@class='contact-item-container' and @data-name='{recipient}']"
        driver.find_element(By.XPATH, recipient_xpath).click()
        random_delay(3, 5)
        driver.find_element(By.ID, "assistant-entry-icon").click()
        random_delay(15, 25)
        driver.find_element(By.XPATH, "//button[contains(., 'Use this')]").click()
        random_delay(1, 2)
        ai_text = driver.find_element(By.CSS_SELECTOR, "#send-box-wrapper pre").get_attribute("textContent")
        driver.find_element(By.XPATH, "//button[contains(@class, 'send-tool-button')]").click()
        return {"recipient": recipient, "status": "success", "message": ai_text}
    except Exception as e:
        return {"recipient": recipient, "status": "failed", "error": str(e)}
