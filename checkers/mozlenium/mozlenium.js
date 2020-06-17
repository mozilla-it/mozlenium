
var $driver = require('selenium-webdriver');

const chrome = require('selenium-webdriver/chrome');

const _ = require('lodash');

var chromeCapabilities = $driver.Capabilities.chrome();

chromeCapabilities.set('chromeOptions',{
    'args': ['--headless', 'window-size=1024,768', '--disable-gpu', '--test-type', '--no-sandbox', '--disable-dev-shm-usage']
});

var $browser = new $driver.Builder()
    .forBrowser('chrome')
    .withCapabilities(chromeCapabilities)
    .build();

var $secure = {}
_.each(process.env, (val,key) => {
    $secure[key] = val;
});

$browser.waitForElement = function (locatorOrElement, timeoutMsOpt) {
        return $browser.wait($driver.until.elementLocated(locatorOrElement), timeoutMsOpt || 1000, 'Timed-out waiting for element to be located using: ' + locatorOrElement);
};

$browser.waitForAndFindElement = function (locatorOrElement, timeoutMsOpt) {
      return $browser.waitForElement(locatorOrElement, timeoutMsOpt).then(function (element) {
          return $browser.wait($driver.until.elementIsVisible(element), timeoutMsOpt || 1000, 'Timed-out waiting for element to be visible using: ' + locatorOrElement).then(function () {
                return element;
          });
      });
};

module.exports = function() {
	this.$browser = $browser;
	this.$driver = $driver;
	this.$secure = $secure;
}

