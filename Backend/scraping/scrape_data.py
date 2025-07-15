from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import os
import requests
import logging
import sys
import subprocess


logging.getLogger('WDM').propagate = False
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


#Function to return mutual funds details which we scrape
#Input -> Nothing
#Ouput -> List of dictionary of values of each mutual funds
def mutual_funds():
    try:
        options = ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--log-level=3")  # Suppresses most browser logs
        options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suppress DevTools logging
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--headless=new")  # Use new headless mode (Chrome 109+)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/chromium-browser"

        chrome_bin = os.environ.get('GOOGLE_CHROME_BIN')
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')

        if chrome_bin and chromedriver_path:
            options.binary_location = chrome_bin
        

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(BASE_DIR, "logs.txt")
        if not os.path.exists(log_file_path):
            with open(log_file_path, 'w') as f:
                f.write('')

        service = ChromeService(chromedriver_path) if chromedriver_path else ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.get("https://www.etmoney.com/mutual-funds/all-funds-listing")
        wait = WebDriverWait(driver, 10)
        total_funds = driver.find_element(By.CLASS_NAME, "total-hidden-funds-count").text.strip()
        cnt = int(total_funds)//20

        for i in range(10):
            try:
                load_more = wait.until(EC.presence_of_element_located((By.ID, "load_more_nav")))

                # Scroll into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more)
                time.sleep(1)  # Give time for scroll animation or transition

                # Perform click via JS
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(2)  # Wait for new funds to load

            except Exception as e:
                print(e)
                break
        time.sleep(2)
        results = []
        fund_cards = driver.find_elements(By.CLASS_NAME, "mfFund-block")  # <-- update with actual class if different
        for card in fund_cards:
            try:
                title_elem = card.find_element(By.CSS_SELECTOR, ".scheme-name a")
                title = title_elem.get_attribute("title")
                title = title.lower() if title else ""
                tag_elements = card.find_elements(By.CSS_SELECTOR, ".mf-category-tags a")
                tags = []
                for tag in tag_elements:
                    val = tag.get_attribute("title")
                    val = val.lower() if val else ""
                    if "thematic" in val:
                        val = "thematic"
                    elif "sectoral" in val:
                        val = "sectoral"
                    tags.append(val)
                    
                aum_elem = card.find_element(By.XPATH, ".//span[text()='AUM']/following-sibling::strong/span")
                aum = aum_elem.text
                image = card.find_element(By.CSS_SELECTOR,'.item-value img')
                source = image.get_attribute('src')
                dec = False
                if source and 'red' in source:
                    dec = True
                returns = card.find_element(By.CSS_SELECTOR, ".sip-returns .item-value.active")
                retval = returns.text.strip()
                expense_container = card.find_element(By.CLASS_NAME, "mfFund-double")
                expense_elem = expense_container.find_element(By.CLASS_NAME, "item-value")
                expense_ratio = expense_elem.text.strip()


                listval = {
                    "title": title,
                    "tags": tags,
                    "aum": aum,
                    "decrease from last time": dec,
                    "return": retval,
                    "expense ratio": expense_ratio
                }
                results.append(listval)
            except Exception as e:
                pass
        
        if len(results) == 0:
            raise Exception("No mutual funds obtained")
        # # Close browser
        driver.quit()
        return results
    except Exception as e:
        print(f"outside {e}")
        return {}

#Function to return at the minimum of last 6 years of gold and silver value
#Input -> None
#Output -> Dictionary of values -> gold and silver -> Each having dictionaries of date and costs
def gold_silver_details():
    try:
        options = ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--log-level=3")  # Suppresses most browser logs
        options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suppress DevTools logging
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--headless=new")  # Use new headless mode (Chrome 109+)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/chromium-browser"

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(BASE_DIR, "logs.txt")
        if not os.path.exists(log_file_path):
            with open(log_file_path, 'w') as f:
                f.write('')

        
        # Redirect stdout and stderr to log file
        sys.stderr = open(log_file_path, 'a', encoding='utf-8')



        chrome_bin = os.environ.get('GOOGLE_CHROME_BIN')
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')

        if chrome_bin and chromedriver_path:
            options.binary_location = chrome_bin
        

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(BASE_DIR, "logs.txt")
        if not os.path.exists(log_file_path):
            with open(log_file_path, 'w') as f:
                f.write('')

        service = ChromeService(chromedriver_path) if chromedriver_path else ChromeService(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.goldpriceindia.com/gold-price-history.php")
        tables = driver.find_elements(By.TAG_NAME,'tbody')
        
        goldval = []
        silverval = []
        gold = True
        for table in tables:
            rows = table.find_elements(By.TAG_NAME,'tr')
            if rows:
                iterval = min(6,len(rows))
                for row_count in range(iterval):
                    value = {}
                    value['date'] = ''
                    value['cost'] = ''
                    row = rows[row_count]
                    tdele = row.find_elements(By.TAG_NAME,'td')
                    for ele in tdele:
                        spanval = ele.find_elements(By.TAG_NAME,'span')
                        boldval = ele.find_elements(By.TAG_NAME,'b') or ele.find_elements(By.TAG_NAME,'strong')
                        if spanval:
                            value['date'] = spanval[0].text.strip()
                        if boldval:
                            value['cost'] = boldval[0].text.strip()

                    if value['date']:
                        if gold:
                            goldval.append(value)
                        else:
                            silverval.append(value)
            
                gold = False
        
        final = {}
        final['gold'] = goldval
        final['silver'] = silverval
        if len(goldval) == 0 or len(silverval) == 0:
            raise Exception("There are no details obtained in gold/silver")
        return final
    except Exception as e:
        return {}

#Function to return the list of information about each of the types of mutual fund
#No input
#Output -> Set of dictionary values
def mutual_fund_details():
    try:
        url = 'https://www.etmoney.com/learn/mutual-funds/mutual-fund-types/'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        retval = {}
        list_of_ele = soup.find_all(["h2","p","h3"])
        currh2 = ""
        currh3 = ""
        currp = ""
        for element in list_of_ele:
            if element.name == "h2":
                if len(currh3)!=0 and len(currp)!=0:
                    retval[currh2][currh3] = currp

                currh2 = element.get_text(strip=True).lower()

                if "based on" in currh2:
                    idx = currh2.find("based on")
                    idx = idx+9
                    currh2 = currh2[idx:]
                    retval[currh2] = {}
                else:
                    currh2 = ""

                currp = ""
                currh3 = ""
            elif element.name=="h3":
                if len(currh2)!=0 and len(currh3)!=0:
                    retval[currh2][currh3] = currp
                
                currh3 = element.get_text(strip=True).lower()
                retval[currh2][currh3] = ""
                currp = ""
            else:
                if len(currh3) != 0:
                    currp = currp+ " "+ element.get_text(strip=True).lower()
        if len(retval) == 0:
            raise Exception("There are no recorded data")
        return retval
    except Exception as e:
        return {}


def debug_chrome_installation():
    print("=== Chrome Installation Debug ===")
    
    # Check what Chrome binaries exist
    chrome_locations = [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable', 
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/app/.chrome-for-testing/chrome-linux64/chrome',
        '/app/.chrome/chrome'
    ]
    
    print("Chrome binary locations:")
    for location in chrome_locations:
        exists = os.path.exists(location)
        print(f"  {location}: {'✓' if exists else '✗'}")
    
    # Check chromedriver
    chromedriver_locations = [
        '/usr/bin/chromedriver',
        '/app/.chromedriver/chromedriver'
    ]
    
    print("ChromeDriver locations:")
    for location in chromedriver_locations:
        exists = os.path.exists(location)
        print(f"  {location}: {'✓' if exists else '✗'}")
    
    # Check environment variables
    print("Environment variables:")
    print(f"  GOOGLE_CHROME_BIN: {os.environ.get('GOOGLE_CHROME_BIN', 'Not set')}")
    print(f"  CHROMEDRIVER_PATH: {os.environ.get('CHROMEDRIVER_PATH', 'Not set')}")
