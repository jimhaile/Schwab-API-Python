
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

import selenium
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from time import sleep

URL = "https://gandalf.gammawizard.com/var2/"



LOGIN_USERNAME_FIELD = '/html/body/app-root/app-bouncer/app-login/mat-card/mat-card-content/form/p[1]/mat-form-field/div/div[1]/div/input'
LOGIN_PASSWORD_FIELD = '/html/body/app-root/app-bouncer/app-login/mat-card/mat-card-content/form/p[2]/mat-form-field/div/div[1]/div/input'
LOGIN_BUTTON = '/html/body/app-root/app-bouncer/app-login/mat-card/mat-card-content/form/p[3]/button'
USERNAME = 'jimhaile@mac.com'
PASSWORD = 'EWTXCAL1BER'

options = Options()
options.add_argument('headless')
options.add_argument('disable-infobars')

# options.add_argument('--headless')
myPath = '/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/chromedriver_126.0.6478.126'
driver = webdriver.Chrome(options=options)

def login():
    print(f'Logging in...')
    driver.get(URL)

    login = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, LOGIN_USERNAME_FIELD))
    )
    password = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, LOGIN_PASSWORD_FIELD))
    )

    login_button = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, LOGIN_BUTTON))
    )

    login.send_keys(USERNAME)
    password.send_keys(PASSWORD)

    login_button.click()

    print('Successfully logged in!')

def get_token():
    sleep(10)
    my_token = (driver.execute_script("return localStorage.getItem('id_token')"))

    if my_token is not None:
        token_string = "Bearer " + my_token
        print(token_string)
        file1 = open('/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/gandalf_token.txt', 'w')
        file1.write(token_string)
        file1.close()
    else:
        print("Could not find token")





login()
get_token()
driver.close()

