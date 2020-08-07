/**
 * Mozlenium Library
 * This is the running library that combines the browser, runner, and logger
 * to run the necessary given test
 */
const $driver = require('selenium-webdriver');
const MozleniumBrowser = require('./mozlenium-browser');
const MozleniumTestRunner = require('./mozlenium-test-runner');
const MozleniumLogger = require('./mozlenium-logger');
const getArgs = require('./get-args');

const $secure = Object.keys(process.env).reduce((acc, key) => {
  acc[key] = process.env[key];
  return acc;
}, {});
const logger = new MozleniumLogger();
const mozBrowser = new MozleniumBrowser(getArgs('browser'));

const testRunner = new MozleniumTestRunner({
  from: getArgs('from'),
  to: getArgs('to'),
});

const processTestFile = async () => {
  try {
    let scriptData = await testRunner.getTestScript();
    scriptData = testRunner.transformTestScript(scriptData);
    await testRunner.writeFinalScript(scriptData);
    return true;
  } catch (e) {
    logger.error('error processing test file: ', e);
    throw new Error(e);
  }
};

const executeRunner = async () => {
  try {
    const runner = require(testRunner.runnerFile);
    await mozBrowser.executeRunner(runner, $driver, $secure);
    return true;
  } catch (e) {
    logger.error('error executing runner: ', e);
    throw new Error(e);
  }
};

processTestFile()
  .then(() => executeRunner())
  .then(() => {
    logger.success('test complete');
  })
  .catch((e) => {
    logger.error('Test error: ', e);
    process.exit(2);
  });
