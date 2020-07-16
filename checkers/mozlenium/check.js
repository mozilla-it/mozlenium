async function runner($browser, $driver, $secure) {
  //demo check
  var assert = require('assert');
  var url = 'https://duckduckgo.com'
  console.log("starting check");
  $browser.get(url).then(function(){
      assert.ok($browser.waitForAndFindElement($driver.By.id("content_homepage"), 30000), "Doesn't seem like things are working properly");
      console.log("well that went great");
  });
  console.log($secure.SECRETSTUFF);
}
module.exports = runner;