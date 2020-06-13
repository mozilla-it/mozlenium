//demo check

require('mozlenium')();

var assert = require('assert');
var url = 'https://www.google.com'

console.log("starting check");

$browser.get(url);

console.log($secure.SECRETSTUFF);

console.log("well that went great");

