const fetch = require('fetch');
const yaml = require('js-yaml');
const fs = require('fs');
// Load config
require('dotenv').config();

// Get Content from YAML
const getJSFromYAML = (yaml) => {
  const parsed = yaml
    .filter(({ kind }) => kind === 'ConfigMap')
    .map(({ data }) => Object.values(data)[0]);
  if (!parsed.length) {
    return null;
  }
  return parsed[0];
};
if (process.argv.length < 3) {
  console.log('Missing filename');
  return;
}
const [, , filename] = process.argv;
const githubUrl = `${process.env.GITHUB_DOCUMENT_PATH}${filename}.yaml`;

// Fetch Yaml from Github
fetch.fetchUrl(
  githubUrl,
  {
    headers: {
      Authorization: `token ${process.env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github.v3.raw',
    },
  },
  (error, metadata, response) => {
    if (error) {
      console.log('found error: ', error);
      return;
    }
    const yamlDocs = yaml.safeLoadAll(response.toString());
    let data = getJSFromYAML(yamlDocs);
    data = data.replace(/[\^\n\r]\$browser\./, 'return $browser.');
    const checkContent = `async function runner($browser, $driver, $secure) { \n ${data} }\n\nmodule.exports = runner;`;

    // Create file with content pulled from github
    fs.writeFile('check.js', checkContent, function (err, file) {
      if (err) throw err;
      console.log('check.js file created');
    });
  },
);
