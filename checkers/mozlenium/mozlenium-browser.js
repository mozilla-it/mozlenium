const { Storage } = require('@google-cloud/storage');
const $driver = require('selenium-webdriver');
const MozleniumLogger = require('./mozlenium-logger');
const fs = require('fs');

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
  static SCREENSHOT_FILE = 'screenshot.png';
  static SCREENSHOT_ERROR_FILE = 'screenshot-error.png';
  constructor(browser) {
    this.logger = new MozleniumLogger();
    this.storage = new Storage();
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
  async uploadScreenshot(filename) {
    const startTime = Date.now();
    const result = await this.storage
      .bucket(process.env.GCS_BUCKET)
      .upload(filename, {
        // Support for HTTP requests made with `Accept-Encoding: gzip`
        gzip: true,
        // By setting the option `destination`, you can change the name of the
        // object you are uploading to a bucket.
        metadata: {
          // Enable long-lived HTTP caching headers
          // Use only if the contents of the file will never change
          // (If the contents will change, use cacheControl: 'no-cache')
          cacheControl: 'public, max-age=31536000',
        },
      });
    const endTime = Date.now();
    this.logger.logTelemetry('gcs_bucket_upload', endTime - startTime);
    this.logger.success('uploaded screenshot');
    this.logger.logImage(filename.replace(/^\.\//, ''));
    return result;
  }
  screenShot(errorScreenshot = false) {
    const savedFile = `./${Date.now()}-${
      errorScreenshot
        ? MozleniumBrowser.SCREENSHOT_ERROR_FILE
        : MozleniumBrowser.SCREENSHOT_FILE
    }`;
    const startTime = Date.now();
    return new Promise((res, rej) => {
      this.$browser.takeScreenshot().then((data) => {
        fs.writeFile(savedFile, data, 'base64', (err) => {
          if (err) {
            this.logger.error('screenshot failure: ', err);
          }
          const endTime = Date.now();
          this.logger.logTelemetry('selenium_screenshot', endTime - startTime);
          res(savedFile);
        });
      });
    });
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
        .then(() => this.screenShot())
        .then((filename) => {
          this.logger.success('screenshot capture was successful');
          return this.uploadScreenshot(filename);
        })
        .then((result) => {
          this.logger.success('cloud storage upload was successful');
        })
        .catch((error) => {
          this.logger.error(`GET error for url: ${url}`, error);
          this.screenShot(true);
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
      await runner(this.$browser, $driver, $secure);
      const etime = Date.now();
      this.logger.logTelemetry('total_time', etime - stime);
      return true;
    } catch (e) {
      throw new Error(e);
    }
  }
}

module.exports = MozleniumBrowser;
