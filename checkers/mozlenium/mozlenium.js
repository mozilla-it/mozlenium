/**
 * Mozlenium Library
 * This is the running library that combines the browser, runner, and logger
 * to run the necessary given test
 */
const webDriver = require('selenium-webdriver');
const MozleniumBrowser = require('./mozlenium-browser');
const MozleniumTestRunner = require('./mozlenium-test-runner');
const MozleniumLogger = require('./mozlenium-logger');
const getArgs = require('./get-args');

// Process and store environment variables
const SECURE = Object.keys(process.env).reduce((acc, key) => {
  acc[key] = process.env[key];
  return acc;
}, {});
const logger = new MozleniumLogger();

/**
 * Class: Mozlenium
 * Contain all the functionality necessary to run the full test.
 * Should only have to call .run() to make things go
 */
class Mozlenium {
  constructor() {
    this.mozBrowser = new MozleniumBrowser(getArgs('browser'));
    this.mozTestRunner = new MozleniumTestRunner({
      from: getArgs('from'),
      to: getArgs('to'),
    });
  }

  /**
   * Method: processTestFile
   * Transform given test file to file that selenium can execute.
   */
  async processTestFile() {
    try {
      let scriptData = await this.mozTestRunner.getTestScript();
      scriptData = this.mozTestRunner.transformTestScript(scriptData);
      await this.mozTestRunner.writeFinalScript(scriptData);
      return true;
    } catch (e) {
      logger.error('error processing test file: ', e);
      throw new Error(e);
    }
  }

  /**
   * Method: executeRunner
   * Run the transformed test
   */
  async executeRunner() {
    try {
      const runner = require(this.mozTestRunner.runnerFile);
      await this.mozBrowser.executeRunner(runner, webDriver, SECURE);
      return true;
    } catch (e) {
      logger.error('error executing runner: ', e);
      throw new Error(e);
    }
  }
  async run() {
    try {
      await this.processTestFile();
      await this.executeRunner();
      return true;
    } catch (e) {
      throw new Error(e);
    }
  }
}

const mozlenium = new Mozlenium();
mozlenium
  .run()
  .then(() => {
    logger.success('test complete');
  })
  .catch((e) => {
    logger.error('Mozlenium error: ', e);
    process.exit(2);
  });
