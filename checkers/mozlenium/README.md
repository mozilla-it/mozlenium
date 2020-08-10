# mozlenium

## Setup CLI

To set up the cli, go find the desired selenium js script to test. A working example is in the `/examples/demo-check.js` file here. Create a new file for testing, then run the following command line.

## Run CLI

Install package:

```
npm run mozlenium:install --browser [browser]
```

Run browser with single test

```

npm run mozlenium:execute --ldap_pw=[ldap_pw] --browser [firefox|chrome] --from_file=[testfile] --to_file=[filetogenerate]
```

## Arguments

| Argument  | Description                                                    | Default                      |
| --------- | -------------------------------------------------------------- | ---------------------------- |
| ldap_pw   | Password for ldap accounts                                     | none                         |
| browser   | firefox \| chrome                                              | firefox                      |
| from_file | file that mozlenium will transform to selenium runnable test   | ../../examples/demo-check.js |
| to_file   | file that mozlenium will create and mozlenium will run against | /check.js                    |
