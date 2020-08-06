# mozlenium

## Setup CLI

To set up the cli, go find the desired selenium js script to test. A working example is in the `./test.js` file here. Paste the code you want
into that file, then run the following command line.

## Run CLI

This cli can be run with several options

Run browser with single test with installation

```
npm run [chrome|firefox]:install:test --ldap_pw=[ldap_pw]
```

Run the same browser single text with no installation

```
npm run [chrome|firefox]:run --ldap_pw=[ldap_pw]
eg: npm run firefox:run --ldap_pw=123...456
```
