const $driver = require('selenium-webdriver');
const MozleniumLogger = require('./mozlenium-logger');

const getExecuteScriptPromises = ($browser, scripts) =>
  scripts.reduce((acc, single) => {
    acc.push($browser.executeScript(single));
    return acc;
  }, []);

/**
 * Class: MozleniumBrowser
 * This class's job is to contain all the functionality of handling the browser be it firefox/chrome/etc
 */
class MozleniumBrowser {
  constructor(browser) {
    this.logger = new MozleniumLogger();
    // Add more browsers here as needed
    if (browser === 'chrome') {
      this.logger.status('using chrome browser');
      this.$browser = require('./chrome-browser.js');
    } else {
      this.logger.status('using firefox browser');
      this.$browser = require('./firefox-browser.js');
    }
    this.setup();
  }

  setup() {
    // Proxy $browser get to perform latency measures on "get" method
    this.$browser.unmeasuredGet = this.$browser.get;
    this.$browser.get = (url, timeoutMsOpt) =>
      this.$browser
        .unmeasuredGet(url, timeoutMsOpt)
        .then(() =>
          Promise.all(
            getExecuteScriptPromises(this.$browser, [
              'return window.performance.timing.navigationStart',
              'return window.performance.timing.responseStart',
              'return window.performance.timing.domComplete',
            ]),
          ),
        )
        .then(([navigationStart, responseStart, domComplete]) => {
          this.logger.logTelemetry('get_time', domComplete - navigationStart);
          this.logger.logTelemetry('latency', responseStart - navigationStart);
        })
        .catch((error) => {
          this.logger.error(`GET error for url: ${url}`, error);
          throw new Error(error);
        });

    // Proxy $browser to perform latency measures on "wait" method
    this.$browser.waitForElement = (locatorOrElement, timeoutMsOpt) =>
      this.$browser.wait(
        $driver.until.elementLocated(locatorOrElement),
        timeoutMsOpt || 1000,
        'Timed-out waiting for element to be located using: ' +
          locatorOrElement,
      );
    // Proxy $browser to perform latency measures on "find" method
    this.$browser.waitForAndFindElement = (locatorOrElement, timeoutMsOpt) => {
      let foundElement = null;
      return this.$browser
        .waitForElement(locatorOrElement, timeoutMsOpt)
        .then((element) => {
          foundElement = element;
          return this.$browser.wait(
            $driver.until.elementIsVisible(element),
            timeoutMsOpt || 1000,
            'Timed-out waiting for element to be visible using: ' +
              locatorOrElement,
          );
        })
        .then(() => foundElement)
        .catch((error) => {
          this.logger.log(`Error waiting for element ${locatorOrElement}`);
          throw new Error(error);
        });
    };
  }
  async initializeBrowser() {
    try {
      await this.$browser.wait(() =>
        this.$browser
          .executeScript('return document.readyState')
          .then((result) => result === 'complete'),
      );
      return true;
    } catch (e) {
      throw new Error(e);
    }
  }
  async executeRunner(runner, $driver, $secure) {
    try {
      await this.initializeBrowser();
      const stime = Date.now();
      if (!runner) {
        throw new Error('Error loading runner');
      }
      if (!$driver) {
        throw new Error(`Invalid $driver: ${$driver}`);
      }
      if (!$secure) {
        throw new Error(`Invalid env $secure: ${$secure}`);
      }
      const result = await runner(this.$browser, $driver, $secure);
      const etime = Date.now();
      this.logger.logTelemetry('total_time', etime - stime);
      return true;
    } catch (e) {
      throw new Error(e);
    }
  }
}

module.exports = MozleniumBrowser;
