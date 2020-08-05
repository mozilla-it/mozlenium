# mozlenium

## Run CLI

This cli can be run with several options

Run browser with single test with installation

```
npm run [chrome|firefox]:install:test --ldap_pw=[ldap_pw] --test=[test_name]
eg: npm run firefox:install:test --ldap_pw=123...456 --test=check-airmo-login
```

Run the same browser single text with no installation

```
npm run [chrome|firefox]:test --ldap_pw=[ldap_pw] --test=[test_name]
eg: npm run firefox:test --ldap_pw=123...456 --test=check-airmo-login
```
