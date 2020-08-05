if [[ ! "$2" ]]; then
  echo "No file specified"
  exit 2
fi

node ./process-test.js $2

SSO_LDAP_PASSWORD=$SSO_LDAP_PASSWORD node ./wrapper.js $1