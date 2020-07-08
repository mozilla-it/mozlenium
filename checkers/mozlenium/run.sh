rm -rf node_modules
npm install
if [ $1 = "chrome" ]; then
  npm run install-chrome-dependencies
else
  npm run install-firefox-dependencies
fi

SSO_LDAP_PASSWORD=$SSO_LDAP_PASSWORD node ./wrapper.js $1
