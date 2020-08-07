// EXAMPLE copied script

//air.mozilla.org - anonymous page
var assert = require('assert');
$browser.get('https://air.mozilla.org/').then(function () {
  // Check the H1 title matches expected output
  return $browser
    .waitForAndFindElement($driver.By.css('h1'), 1000)
    .then(function (element) {
      return element.getText().then(function (text) {
        assert.equal(
          'Upcoming Section',
          text,
          'Page H1 title did not match "' + text + '"',
        );
      });
    });
});
