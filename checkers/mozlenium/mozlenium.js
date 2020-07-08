/**
 * Mozlenium Library
 * Goal: Extend $browser object to provide timing/logging functionality to selenium
 */

let [, , selectedBrowser] = process.argv;
if (!selectedBrowser) {
  selectedBrowser = 'firefox';
}
const $driver = require('selenium-webdriver');
let $browser;
// Add more browsers here as needed
if (selectedBrowser === 'chrome') {
  $browser = require('./chrome-browser.js');
} else {
  $browser = require('./firefox-browser.js');
}

// Get a list of promises executing array of commands sent through 'scripts'
const getExecuteScriptPromises = ($browser, scripts) =>
  scripts.reduce((acc, single) => {
    acc.push($browser.executeScript(single));
    return acc;
  }, []);

// Proxy $browser get to perform latency measures on "get" method
$browser.unmeasuredGet = $browser.get;
$browser.get = (url, timeoutMsOpt) =>
  $browser
    .unmeasuredGet(url, timeoutMsOpt)
    .then(() =>
      Promise.all(
        getExecuteScriptPromises($browser, [
          'return window.performance.timing.navigationStart',
          'return window.performance.timing.responseStart',
          'return window.performance.timing.domComplete',
        ]),
      ),
    )
    .then(([navigationStart, responseStart, domComplete]) => {
      console.log('TELEMETRY: get_time', domComplete - navigationStart);
      console.log('TELEMETRY: latency', responseStart - navigationStart);
    });

// Proxy $browser to perform latency measures on "wait" method
$browser.waitForElement = (locatorOrElement, timeoutMsOpt) =>
  $browser.wait(
    $driver.until.elementLocated(locatorOrElement),
    timeoutMsOpt || 1000,
    'Timed-out waiting for element to be located using: ' + locatorOrElement,
  );

// Proxy $browser to perform latency measures on "find" method
$browser.waitForAndFindElement = (locatorOrElement, timeoutMsOpt) => {
  let foundElement = null;
  return $browser
    .waitForElement(locatorOrElement, timeoutMsOpt)
    .then((element) => {
      foundElement = element;
      return $browser.wait(
        $driver.until.elementIsVisible(element),
        timeoutMsOpt || 1000,
        'Timed-out waiting for element to be visible using: ' +
          locatorOrElement,
      );
    })
    .then(() => foundElement)
    .catch((error) => {
      console.log('Error waiting for elment: ', error);
    });
};

module.exports = {
  $browser,
  $driver,
  // Send over a map of all the environment variable keys
  $secure: Object.keys(process.env).reduce((acc, key) => {
    acc[key] = process.env[key];
    return acc;
  }, {}),
};
