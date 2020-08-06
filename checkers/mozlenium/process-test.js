const MozleniumTestRunner = require('./mozlenium-test-runner');
const fs = require('fs');

const testRunner = new MozleniumTestRunner();

const processTest = async () => {
  try {
    let scriptData = await testRunner.getTestScript();
    scriptData = testRunner.transformTestScript(scriptData);
    await testRunner.writeFinalScript(scriptData);
    return true;
  } catch (e) {
    throw new Error(e);
  }
};

processTest()
  .then((result) => {
    console.log('Successfully processed test!');
    process.exit();
  })
  .catch((error) => {
    console.log('Error processing test: ', error);
    process.exit(2);
  });
