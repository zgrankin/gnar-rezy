#
# Created in 2020 by Jake Johnson and Preston Windfeldt
# Filename: ikon_scraper.py
# Purpose:  Provide web scraping interface for interacting with
#           Ikon website
#

import sys
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import email_interface
import time
import datetime

# class name if the day is available
AVAILABLE = 'DayPicker-Day'
# class name if available and day is today
AVAILABLE_TODAY = 'DayPicker-Day DayPicker-Day--today'

# macro for if user wants all mountain openings to be emailed to them.
# Not just ones in their dates to reserve.
ALERT_ALL_OPENINGS = False

# Reservation Page Url
MAKE_RES_URL = "https://account.ikonpass.com/en/myaccount/add-reservations/"

# Login Page Url
LOGIN_URL = "https://account.ikonpass.com/en/login"

class IkonReserve:
	
	def __init__(self, driver):
		self.driver = driver
		self.email = ""
		self.password = ""
		
		self._mountains_to_dates = {}
		self._addDatesToReserveToList()

	def login(self, email: str, password: str):
		"""
		Logs into Ikon website and clicks the 'make reservation' button.
		"""
		self.email = email
		self.password = password

		# open login page
		self.driver.get(LOGIN_URL)

		# If Ikon is using captcha, attempt to run the script 5+ times, then they
		# will ask for captcha right when bot gets to site. Uncomment this timer
		# and manually enter captcha, then bot will run after. Make sure headless
		# mode is off
		# input()

		# send login parameters
		email_elems = self.driver.find_elements(By.NAME, "email")
		password_elems = self.driver.find_elements(By.NAME, "password")
		if not email_elems or not password_elems:
			print("ERROR: Couldn't locate email or password elements")
			return False
		email_field = email_elems[0]
		password_field = password_elems[0]

		email_field.send_keys(self.email)
		password_field.send_keys(self.password)
		password_field.send_keys(Keys.RETURN)

		# click 'Make a Reservation' button
		try:
			# wait for page to load
			resButton = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//span[text()="Make a Reservation"]')))
		except:
			print("Error: Timed out")
			email_interface.sendErrorEmail("Error logging in", email)
			sys.exit()
		time.sleep(10) # wait an additional several seconds before clicking
		self.driver.execute_script("arguments[0].click();", resButton)
		return True

	def checkForOpenings(self):
		"""
		Checks if any reserved days have become available by scraping Ikon site 
		and comparing to the current stored available dates in our list. Reserves 
		days that are set in database if they become available.
		"""
		self._updateRequestedDateAvailability()

		url = "https://account.ikonpass.com/en/myaccount/add-reservations/"
		for mountain, dates in self._mountains_to_dates.items():
			for date in dates:
				day = date["day"]
				month = date["month"]
				year = date["year"]
				isAvailable = date["available"]
				if isAvailable:
					# reserve it or notify
					self.get(url)
					self._selectMountain(mountain) # click the mountain
					self._selectMonth(month, year)
					# confirm that it is available
					if self._isDayAvailable(month, day, year):
						reserveSuccess = self._reserveDay(month, day, year, mountain)
						# return to make reservation page
						self.get(MAKE_RES_URL)

						dayOfWeek = datetime.date(year, month, day).strftime("%A")
						# send alert
						if reserveSuccess:
							print(f"WOO! Got your date at {mountain} reserved: {day}/{month}/{year}")
							email_interface.sendDateToReserveAlertEmail([], mountain, month, str(day), str(year), dayOfWeek, self.email)
						# send alerts if desired
						if ALERT_ALL_OPENINGS:
							email_interface.sendReservationOpenAlertEmail(
								self.email, mountain, self._months_to_check[month], str(day), str(year), dayOfWeek, self.email)
	
	def _isDayAvailable(self, month: int, day: int, year: int):
		"""
		Checks if a day is available. The scraper must be on the make reservation
		page with the dates available to check (ie _selectMonth() must be called first).
		"""
		monthStr = datetime.date(year, month, day).strftime("%B")
		# abbreviated month str since that is how it is labeled in the Ikon page HTML
		monthSearch = monthStr[:3]

		try:
			# wait for page to load
			dayElement = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, f'//div[contains(@aria-label,"{monthSearch} {day:02d}")]')))
		except:
			print("Error: Timed out")
			email_interface.sendErrorEmail(f"Error checking day availability for {monthStr} {day:02d} {year}", self.email)
			sys.exit()
		
		# check if day is available by reading element class. Class will be
		# 'DayPicker-Day' if available
		# return if day is available or not
		if (dayElement.get_attribute('class') == AVAILABLE or dayElement.get_attribute('class') == AVAILABLE_TODAY):
			return True
		else:
			return False

	def _updateRequestedDateAvailability(self):
		"""
		Scrapes Ikon site and adds available dates to list.
		"""
		selected_month = -1
		# check reserved dates for each mountain. Only check Jan-June
		# TODO: make this scalable to whatever current year is
		for mountain, dates in self._mountains_to_dates.items():
			# reload to allow new mountain selection
			self.driver.get(MAKE_RES_URL)
			self._selectMountain(mountain)
			for date in dates:
				day = date["day"]
				month = date["month"]
				year = date["year"]
				if month != selected_month:
					self._selectMonth(month, year)
					selected_month = month
				if self._isDayAvailable(month, day, year):
					print(f"Requested date [{day}/{month}/{year}] is available")
					date["available"] = True
				else:
					print(f"Requested date [{day}/{month}/{year}] is not available")
					date["available"] = False

	def _reserveDay(self, month: int, day: int, year: int, mountain: str):
		"""
		Reserves a day in Ikon if available.
		"""
		monthStr = datetime.date(year, month, day).strftime("%B")
		# abbreviated month str since that is how it is labeled in the Ikon page HTML
		monthSearch = monthStr[:3]

		# Select the day
		try:
			# wait for page to load
			dayElement = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, f'//div[contains(@aria-label,"{monthSearch} {day:02d}")]')))
			self.driver.execute_script("arguments[0].click();", dayElement)
		except:
			email_interface.sendErrorEmail(f"Error reserving {mountain} on {monthStr} {day:02d} {year}", self.email)
			return False

		# click save button
		try:
			# wait for page to load
			saveButton = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//span[text()="Save"]')))
			self.driver.execute_script("arguments[0].click();", saveButton)
		except:
			email_interface.sendErrorEmail(f"Error reserving {mountain} on {monthStr} {day:02d} {year}", self.email)
			return False

		# give time for button click
		time.sleep(1)

		# click confirm button
		try:
			# wait for page to load
			confirmButton = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//span[text()="Continue to Confirm"]')))
			self.driver.execute_script("arguments[0].click();", confirmButton)
		except:
			email_interface.sendErrorEmail(f"Error reserving {mountain} on {monthStr} {day:02d} {year}", self.email)
			return False

		# give time for button click
		time.sleep(1)

		# click confirm checkbox
		try:
			# wait for page to load
			confirmCheckbox = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/main/section[2]/div/div[2]/div[4]/div/div[4]/label/input')))
			self.driver.execute_script("arguments[0].click();", confirmCheckbox)
		except:
			email_interface.sendErrorEmail(f"Error reserving {mountain} on {monthStr} {day:02d} {year}", self.email)
			return True

		# give time for button click
		time.sleep(1)

		# click confirm button again
		try:
			# wait for page to load
			confirmButton = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/main/section[2]/div/div[2]/div[4]/div/div[5]/button/span')))
			self.driver.execute_script("arguments[0].click();", confirmButton)
		except:
			email_interface.sendErrorEmail(f"Error reserving {mountain} on {monthStr} {day:02d} {year}", self.email)
			return False

		return True

	def _addDatesToReserveToList(self):
		# get path to datesToReserve.txt file. Should be in directory above this script
		path = "./datesToReserve.txt"

		# open file and add contents to list
		with open(path, 'r') as f:
			for entry in f:
				entry = entry.rstrip()
				entry = entry.split(',')
				date = entry[0]
				mountain = entry[1]
				email = entry[2]
				month, day, year = [int(num) for num in date.split("/")]
				dates_for_mountain = self._mountains_to_dates.get(mountain, [])
				dates_for_mountain.append({
					"day": day,
					"month": month,
					"year": year,
					"available": False
				})
				self._mountains_to_dates[mountain] = dates_for_mountain

	def _selectMountain(self, mountain):
		"""
		Selects mountain on the 'make reservation' page. From here, _selectMonth() 
		and then _isDayAvailable() can be called.
		"""
		# select mountain
		try:
			# wait for page to load
			mountain = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, f'//span[text()="{mountain}"]')))
		except:
			print("Error: Timed out")
			email_interface.sendErrorEmail(f"Error selecting mountain: {mountain}", self.email)
			sys.exit()
		self.driver.execute_script("arguments[0].click();", mountain)

		# click 'Continue' button
		try:
			# wait for page to load
			contButton = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//span[text()="Continue"]')))
		except:
			print("Error: Timed out")
			email_interface.sendErrorEmail(f"Error selecting mountain: {mountain}", self.email)
			sys.exit()
		self.driver.execute_script("arguments[0].click();", contButton)

	def _selectMonth(self, month: int, year: int):
		"""
		Selects month by bringing scraper to the page displaying the dates for that
		month.
		"""
		monthStr = datetime.date(year, month, 1).strftime("%B")

		# check what month is currently being checked on Ikon site.
		try:
			# wait for page to load
			monthBeingChecked = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.XPATH, '//span[@class="sc-pkSSX kurWGw"]')))
		except:
			print("Error: Timed out")
			email_interface.sendErrorEmail(f"Error selecting month {monthStr}", self.email)
			sys.exit()

		# loop through months until correct month is being checked.
		# Will start from month entered and increment until June 2021.
		while (monthBeingChecked.get_attribute('innerHTML') != (f"{monthStr} {year}")):
			# if we have reached June and that was not desired month, return
			if monthBeingChecked.get_attribute('innerHTML') == ("June {year}") and monthStr != "June":
				print("Error: Failed to select month")
				return

			# go to next month
			nextMonthButton = self.driver.find_element(By.XPATH, '//i[@class="amp-icon icon-chevron-right"]')
			self.driver.execute_script("arguments[0].click();", nextMonthButton)
			try:
				monthBeingChecked = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, '//span[@class="sc-pkSSX kurWGw"]')))
			except:
				print("Error: Timed out")
				email_interface.sendErrorEmail(f"Error selecting month {month}", self.email)
				sys.exit()


	# def checkSpecificReservation(self, mountain, month, day, year):
	# 	"""Checks for specific reservation and reserves if available
	# 	"""
	# 	# reload to allow new mountain selection
	# 	self.driver.get(MAKE_RES_URL)

	# 	self._selectMountain(mountain)

	# 	self._selectMonth(self._months_to_check[month], year)

	# 	if self._isDayAvailable(month, day, year):
	# 		# reserve day
	# 		reserveSuccess = self._reserveDay(month, day, year, mountain)
	# 		# return to make reservation page
	# 		self.driver.get(MAKE_RES_URL)
	# 		# get day of week
	# 		dayOfWeek = datetime.date(year, month, day).strftime("%A")
	# 		# send alert
	# 		if reserveSuccess:
	# 			email_interface.sendDateToReserveAlertEmail(
	# 				self.email, mountain, month, str(day), str(year), dayOfWeek, self.email)