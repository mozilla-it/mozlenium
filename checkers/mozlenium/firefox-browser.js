// Build Firefox Driver for testing
const $driver = require('selenium-webdriver');
const $firefox = require('selenium-webdriver/firefox');

// Create Options to be sent to Firefox
var options = new $firefox.Options();

options.addArguments('-headless');
options.addArguments('--window-size=1024,768');
options.addArguments('--disable-gpu');
options.addArguments('--test-type');
options.addArguments('--no-sandbox');
options.addArguments('--disable-dev-shm-usage');

// Create firefox browser object
module.exports = new $driver.Builder()
  .forBrowser('firefox')
  .setFirefoxOptions(options)
  .build();
