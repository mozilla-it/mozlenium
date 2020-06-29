//demo check

require('mozlenium')();

var assert = require('assert');
var url = 'https://www.google.com'

console.log("starting check");

$browser.get(url).then(function(){
    assert.ok($browser.waitForAndFindElement($driver.By.id("viewport"), 6000), "Doesn't seem like things are working properly");
    console.log("well that went great");
})

