const MozleniumLogger = require('./mozlenium-logger');
const logger = new MozleniumLogger();
const KEY_PREFIX = '-';
const getArgs = (key) => {
  const fileArguments = process.argv.slice(2);
  for (let i = 0, len = fileArguments.length; i < len; i += 1) {
    if (fileArguments[i].startsWith(KEY_PREFIX)) {
      if (
        i + 1 < len &&
        fileArguments[i] === `${KEY_PREFIX}${key}` &&
        !fileArguments[i + 1].startsWith(KEY_PREFIX)
      ) {
        return fileArguments[i + 1];
      }
    }
  }
  logger.error(`found no key: ${key}`);
  return null;
};
module.exports = getArgs;
