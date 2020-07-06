require('mozlenium')();

$browser.wait(function() {
  return $browser.executeScript("return document.readyState").then(function(result) {
    return result === "complete";
  });
}).then(_ => {
  //console.log("browser ready.");
  var stime = Date.now();
  require('check')();
  if($result) {
    $result.then(_ => {
      var etime = Date.now();
      //console.log("done.");
      console.log("TELEMETRY: total_time", etime-stime)
    });
  }
});

