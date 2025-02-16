from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# Create a Service object with the path to the ChromeDriver
service = Service('chromedriver.exe')

# Initialize the Chrome WebDriver with the Service object
driver = webdriver.Chrome(service=service)

# Open a webpage
driver.get('https://www.google.com')

# Print the page title
print("Page title is:", driver.title)

# Close the browser
driver.quit()
