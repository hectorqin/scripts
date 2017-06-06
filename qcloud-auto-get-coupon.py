#!/usr/local/bin/python
# coding: utf-8
import time
import os

browserName = ''
username = 'test'
password = 'test'

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except:
    print "Please install selenium package, you can install it by execute : pip install -U selenium"
    os._exit(0)

for name in ['Chrome', 'Firefox', 'Safari', 'Ie', 'Edge', 'Opera', 'PhantomJS']:
    try:
        getattr(webdriver, name)().quit()
        browserName = name
        print "Get the browser driver:", browserName
        break
    except:
        continue

if not browserName:
    print "Please install one of the browser driver list: Chrome, Firefox, Safari, PhantomJS"
    print "Download website: https://www.npmjs.com/package/selenium-webdriver"
    os._exit(0)

if username == 'test':
    print "Please set the username and password"
    os._exit(0)


def waitToFind(driver, by):
    return WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(by)
    )


def getBrowser():
    return getattr(webdriver, browserName)()


def auto_get_txy_coupon(user, pwd):
    browser = getBrowser()
    browser.get("https://www.qcloud.com/act/campus")
    # show login box
    browser.find_elements_by_css_selector(".J_applyLongPackgeBtn")[0].click()
    waitToFind(browser, (By.CSS_SELECTOR, ".J-loginContentBox"))
    print 'Login box shown'
    # login
    print 'Input the username and passwd to login'
    user_input = browser.find_elements_by_class_name("J-username")[0]
    pwd_input = browser.find_elements_by_class_name("J-password")[0]
    user_input.clear()
    pwd_input.clear()
    user_input.send_keys(user)
    pwd_input.send_keys(pwd)
    browser.find_elements_by_class_name("J-loginBtn")[0].click()

    # isLogin
    waitToFind(browser, (By.CSS_SELECTOR, ".J-user-name"))
    print 'Login success'

    # get coupon
    print 'Get the coupon'
    browser.find_elements_by_css_selector(".J_campusPackageTab a")[1].click()
    browser.find_elements_by_css_selector(
        ".J_applayLimitedPackage")[0].click()

    time.sleep(3)
    browser.quit()

if __name__ == "__main__":
    auto_get_txy_coupon(username, password)
