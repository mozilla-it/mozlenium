// Build Firefox Driver for testing
const $driver = require('selenium-webdriver');
const $firefox = require('selenium-webdriver/firefox');
const isCLI = process.env.IS_CLI === 'true';
// Create Options to be sent to Firefox
var options = new $firefox.Options();

if (!isCLI) {
  options.addArguments('-headless');
}
options.addArguments('--window-size=1024,768');
options.addArguments('--disable-gpu');
options.addArguments('--test-type');
options.addArguments('--no-sandbox');
options.addArguments('--disable-dev-shm-usage');

// Create firefox browser object
if (!isCLI) {
  module.exports = new $driver.Builder()
    .forBrowser('firefox')
    .setFirefoxOptions(options)
    .build();
} else {
  module.exports = new $driver.Builder().forBrowser('firefox').build();
}
