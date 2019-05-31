import time
import subprocess as subp

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common import action_chains
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import NoSuchElementException

import reverse_image_search as ris


def browse(url, host=None, port=None,
           duration=None, stop='cont',
           browser_path='Google Chrome.app'):
    browser = ['open', '-a', browser_path, url]
    if host and port:
        browser.extend(['--args', '--proxy-server=%s:%s' % (host, port)])
    child = subp.Popen(browser)
    if duration:
        time.sleep(duration)
    else:
        while input() != stop:
            pass
    child.terminate()


def capabilities(ip=None, port='3128', ext=False):
    capabs = {}
    if ip:
        proxy = Proxy()
        proxy.proxy_type  = ProxyType.MANUAL
        proxy.http_proxy  = ip + ':' + port
        proxy.socks_proxy = ip + ':' + port
        proxy.ssl_proxy   = ip + ':' + port
        capabs = webdriver.DesiredCapabilities.CHROME
        proxy.add_to_capabilities(capabs)
    if ext: # FIXME
        capabs = {**capabs, **{'chromeOptions': {
            'useAutomationExtension': False,
            'forceDevToolsScreenshot': True,
            'args': ['--start-maximized',
                     '--disable-infobars']
        }}}
    return capabs or None


def options(no_automate=True,
            no_ext=False, maximize=False, no_infobars=False,
            cookies=None, no_sandbox=False, headless=False):
    if not any(locals().values()): return
    ops = webdriver.ChromeOptions()
    if no_automate:
        ops.add_experimental_option("excludeSwitches", ["enable-automation"])
        ops.add_experimental_option('useAutomationExtension', False)
    if no_ext:
        ops.add_argument("disable-extensions")
    if maximize:
        ops.add_argument("--start-maximized")
    if no_infobars:
        ops.add_argument("--disable-infobars")
    if cookies:
        ops.add_argument(cookies)
    if no_sandbox:
        ops.add_argument('--no-sandbox')
    if headless:
        ops.add_argument('--headless')
    return ops


def captcha(driver, url, click=False, after=3):
    driver.get(url)
    iframes = driver.find_elements_by_tag_name("iframe")
    driver.switch_to.frame(iframes[0])
    checkbox = None
    xpath = '//div[@class="recaptcha-checkbox-checkmark"' \
            ' and @role="presentation"]'
    try:
        checkbox = driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        print('no xpath found!')
        return
    if checkbox is not None:
        if click:
            checkbox.click()
        else:
            actor = action_chains.ActionChains(driver)
            actor.move_to_element_with_offset(checkbox, 7, 9)
            actor.send_keys(Keys.TAB, Keys.SPACE)
            actor.perform()
    time.sleep(after)


def paused_browser(driver, url, stop='cont', duration=None,
                   after=5, get=True, on_solve=None):
    if get:
        driver.get(url)
    if duration:
        time.sleep(duration)
    else:
        while input('Enter "cont" to continue:') != stop:
            pass
    info = on_solve(driver) if on_solve else None
    driver.quit()
    time.sleep(after)
    return info


def parse_reverse_selenium(driver):
    return ris.parse_reverse_prediction(driver.page_source,
                                        from_request=False)


def reverse_search_selenium(ip, url, stop='cont',
                            duration=None, after=5):
    driver = proxy_driver(ip)
    driver.get(url)
    try:
        pred = parse_reverse_selenium(driver)
        driver.quit()
        return pred
    except: pass
    try:
        return paused_browser(driver, url, stop, duration, after,
                              get=False, on_solve=parse_reverse_selenium)
    except: pass
    finally: driver.quit()


def proxy_driver(ip=None, chrome_path='/Applications/chromedriver'):
    return webdriver.Chrome(chrome_path,
                            options=options(),
                            desired_capabilities=capabilities(ip=ip))


if __name__ == '__main__':
    url = 'https://www.google.com/recaptcha/api2/demo'
    paused_browser(proxy_driver(), url)