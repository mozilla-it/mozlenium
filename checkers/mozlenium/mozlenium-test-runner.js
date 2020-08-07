const fs = require('fs');
const MozleniumLogger = require('./mozlenium-logger');
/**
 * Test runner that reads the script provided and transforms it into something
 * that will be useful for selenium.
 */
class MozleniumTestRunner {
  static TEST_FILE = '/checks/check.js';
  static RUNNER_FILE = './check.js';
  constructor({ from, to }) {
    if (!from) {
      from = MozleniumTestRunner.TEST_FILE;
    }
    if (!to) {
      to = MozleniumTestRunner.RUNNER_FILE;
    }
    this.testFile = from;
    this.runnerFile = to;
    this.logger = new MozleniumLogger();
  }
  async getTestScript() {
    return new Promise((res, rej) => {
      fs.readFile(this.testFile, (error, content) => {
        if (error) {
          this.logger.error(error);
          rej(error);
          return;
        }
        res(content.toString());
      });
    });
  }
  transformTestScript(scriptData) {
    const transformedScript = scriptData.replace(
      /([\^\n\r])\$browser\./,
      '$1return $browser.',
    );
    return `async function runner($browser, $driver, $secure) { \n ${transformedScript} }\n\nmodule.exports = runner;`;
  }
  writeFinalScript(transformedScript) {
    return new Promise((res, rej) => {
      fs.writeFile(this.runnerFile, transformedScript, (err, file) => {
        if (err) {
          this.logger.error(err);
          rej(err);
          return;
        }
        this.logger.log(`${this.runnerFile} file created`);
        res(file);
      });
    });
  }
}

module.exports = MozleniumTestRunner;
