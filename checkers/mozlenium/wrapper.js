const { $browser, $driver, $secure } = require('./mozlenium.js');
const runner = require('./check.js');

const runWrapper = async ($browser) => {
  try {
    await $browser.wait(() =>
      $browser
        .executeScript('return document.readyState')
        .then((result) => result === 'complete'),
    );
    const stime = Date.now();
    if (!runner) {
      throw new Error('Error loading runner');
    }
    const result = await runner($browser, $driver, $secure);
    const etime = Date.now();
    console.log('TELEMETRY: total_time', etime - stime);
    return etime - stime;
  } catch (error) {
    console.log('Error in runWrapper: ', error.message);
    throw new Error(error.message);
  }
};

runWrapper($browser)
  .then((runTime) => {
    console.log('Completed Wrapper!');
  })
  .catch((error) => {
    console.error('Wrapper runner failed: ', error.message);
    process.exit(2);
  });
