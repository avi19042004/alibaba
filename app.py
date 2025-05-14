from flask import Flask, request, jsonify
from helper import (
    init_browser, login, cleanup,
    send_inquiry_flow, send_ai_response, random_delay
)
from selenium.webdriver.common.by import By
import logging

app = Flask(__name__)

@app.route('/')
def home():
    return {"message": "Welcome to Alibaba Flask Service!"}

@app.route('/send-inquiries', methods=['POST'])
def send_inquiries():
    data = request.get_json()
    urls = data.get("urls", [])
    driver = init_browser()
    login(driver)
    results = [send_inquiry_flow(driver, url) for url in urls]
    driver.quit()
    cleanup()
    return jsonify(results)

@app.route('/send-ai-messages', methods=['POST'])
def send_ai_messages():
    data = request.get_json()
    recipients = data.get("recipients", [])
    driver = init_browser()
    login(driver)
    random_delay(3, 7)

    close_pop=driver.find_elements(By.CLASS_NAME, "im-next-dialog-close")
    if close_pop:
        close_pop[0].click()
    
    close_pop=driver.find_elements(By.CLASS_NAME, "close-icon")
    if close_pop:
        close_pop[0].click()

    results = []
    for recipient in recipients:
        random_delay(3, 7)

        result = send_ai_response(driver, recipient)
        results.append(result)

    logging.info("All AI messages processed.")
    return {"results": results}

if __name__ == "__main__":
    app.run(debug=True, port=8000)