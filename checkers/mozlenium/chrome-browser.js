// Build Chrome Driver for testing
var $driver = require('selenium-webdriver');
var chromeCapabilities = $driver.Capabilities.chrome();

// Create options to be sent into chrome browser
chromeCapabilities.set('chromeOptions', {
  args: [
    '--headless',
    'window-size=1024,768',
    '--disable-gpu',
    '--test-type',
    '--no-sandbox',
    '--disable-dev-shm-usage',
  ],
});

// Create chrome browser object
module.exports = new $driver.Builder()
  .forBrowser('chrome')
  .withCapabilities(chromeCapabilities)
  .build();
