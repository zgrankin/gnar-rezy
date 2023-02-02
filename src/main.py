#
# Created in 2020 by Jake Johnson and Preston Windfeldt
# Filename: main.py
# Purpose:  Main program that constantly checks if mountain
#           reservations become available on the Ikon pass.
#

from ikon_scraper import IkonReserve

import argparse
import re
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Web Driver Mode
# Must be set to True if running on virtual server
HEADLESS = False

def main():
    """
    Main function. initializes web driver, logs into ikon site,
    and runs an infinite loop checking for openings of dates specified
    by user.
    """
    args = parseArguments()
    ikon_email = args.get("email")
    ikon_password = args.get("password")

    # Basic email validation
    if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", ikon_email):
        print("Hey, your email isn't valid!")
        return False

    # initialize web driver
    if HEADLESS:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument("window-size=1024,768")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=options)
    else:
        options = Options()
        driver = webdriver.Chrome(options=options)

    # set page load timeout
    driver.set_page_load_timeout(20)

    ikon_reserve = IkonReserve(driver)

    # login to ikon website
    login_status = ikon_reserve.login(email=ikon_email, password=ikon_password)
    if not login_status:
        print("ERROR: Failed to login")
        return False

    # Constantly check for openings in reservations
    while True:
        ikon_reserve.checkForOpenings()
        print("Still checking")

        # sleep so CPU processing doesn't get taken up
        time.sleep(2)

    # close driver
    driver.quit()

    # quit app
    sys.exit()


def parseArguments():
    parser = argparse.ArgumentParser(description='Automate the Ikon Reservation system!')
    parser.add_argument('-e', '--email', type=str,
                        help='Provide Ikon login email address', required=True)
    parser.add_argument('-p', '--password', type=str,
                        help='Provide Ikon login password', required=True)
    return vars(parser.parse_args())


if __name__ == "__main__":
    main()
