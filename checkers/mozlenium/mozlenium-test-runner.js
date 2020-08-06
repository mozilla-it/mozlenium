const fs = require('fs');

/**
 * Test runner that reads the script provided andtransforms it into something
 * that will be useful for selenium.
 */
class MozleniumTestRunner {
  static TEST_FILE = './test.js';
  static RUNNER_FILE = './check.js';
  constructor() {}
  getTestScript = async () =>
    new Promise((res, rej) => {
      fs.readFile(MozleniumTestRunner.TEST_FILE, (error, content) => {
        if (error) {
          console.log('found error: ', error);
          rej(error);
          return;
        }
        res(content.toString());
      });
    });
  transformTestScript = (scriptData) => {
    const transformedScript = scriptData.replace(
      /([\^\n\r])\$browser\./,
      '$1return $browser.',
    );
    return `async function runner($browser, $driver, $secure) { \n ${transformedScript} }\n\nmodule.exports = runner;`;
  };
  writeFinalScript = (transformedScript) =>
    new Promise((res, rej) => {
      fs.writeFile(
        MozleniumTestRunner.RUNNER_FILE,
        transformedScript,
        function (err, file) {
          if (err) {
            console.log('error writing script: ', err);
            rej(err);
            return;
          }
          console.log(`${MozleniumTestRunner.RUNNER_FILE} file created`);
          res(file);
        },
      );
    });
}

module.exports = MozleniumTestRunner;
