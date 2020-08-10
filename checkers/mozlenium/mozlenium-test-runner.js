const fs = require('fs');
const MozleniumLogger = require('./mozlenium-logger');
/**
 * Test runner that reads the script provided and transforms it into something
 * that will be useful for selenium.
 */
class MozleniumTestRunner {
  static TEST_DIR = process.env.CHECKS_BASEDIR;
  static RUNNER_FILE = './check.js';
  constructor({ from, to }) {
    if (!from) {
      from = '';
    }
    if (!to) {
      to = MozleniumTestRunner.RUNNER_FILE;
    }
    this.testFile = from;
    this.runnerFile = to;
    this.logger = new MozleniumLogger();
  }

  /**
   * Method: getFile
   * If a file is directly passed in to the library, use the file
   * Otherwise, go to the default directory and use the first file available
   */
  getFile() {
    return new Promise((res, rej) => {
      if (this.testFile !== '') {
        this.logger.status(`using cli check file: ${this.testFile}`);
        res(this.testFile);
        return;
      }
      fs.readdir(MozleniumTestRunner.TEST_DIR, (err, files) => {
        if (!files.length) {
          this.logger.error(
            `Found no files in directory: ${MozleniumTestRunner.TEST_DIR}`,
          );
          rej();
          return;
        }
        const returnFile = `${MozleniumTestRunner.TEST_DIR}${
          files.reverse()[0]
        }`;
        this.logger.status(`using check file: ${returnFile}`);
        res(returnFile);
      });
    });
  }
  getTestScript() {
    return new Promise((res, rej) => {
      this.getFile()
        .then((file) => {
          fs.readFile(file, (error, content) => {
            if (error) {
              this.logger.error(error);
              rej(error);
              return;
            }
            res(content.toString());
          });
        })
        .catch((error) => {
          rej(error);
        });
    });
  }
  transformTestScript(scriptData) {
    const transformedScript = scriptData.replace(
      /([\^\n\r])\$browser(\.?)/,
      '$1return $browser$2',
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
