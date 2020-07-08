//pad.mozilla.org
async function runner($browser, $driver, $secure) {
  return $browser
    .get('https://pad.mozilla.org')
    .then(function () {
      return $browser.waitForAndFindElement(
        $driver.By.xpath('//*[@id="field-email"]'),
        10000,
      );
    })
    .then(function () {
      return $browser
        .findElement($driver.By.xpath('//*[@id="field-email"]'))
        .sendKeys('moc-sso-monitoring@mozilla.com');
    })
    .then(function () {
      return $browser
        .findElement($driver.By.xpath('//*[@id="enter-initial"]'))
        .click();
    })
    .then(function () {
      return $browser.waitForAndFindElement(
        $driver.By.xpath('//*[@id="field-password"]'),
        10000,
      );
    })
    .then(function () {
      return $browser
        .findElement($driver.By.xpath('//*[@id="field-password"]'))
        .sendKeys($secure.SSO_LDAP_PASSWORD);
    })
    .then(function () {
      return $browser
        .findElement($driver.By.xpath('//*[@id="authorise-ldap-credentials"]'))
        .click();
    })
    .then(function () {
      return $browser.wait(function () {
        return $browser.getTitle().then(function (title) {
          return title === 'Etherpad';
        });
      }, 10000);
    });
}
module.exports = runner;
