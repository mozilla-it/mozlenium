/**
 * Class: MozleniumLogger
 * This class's job is to provide an interface for logging well formatted logs
 */
class MozleniumLogger {
  static ERROR_PREFIX = '[ERROR]: ';
  static TELEMETRY_PREFIX = 'TELEMETRY';
  static LOG_PREFIX = '[MESSAGE]: ';
  static STATUS_PREFIX = '[STATUSMSG]: ';
  static SUCCESS_PREFIX = '[SUCCESS]: ';
  constructor() {
    this.logger = console;
  }
  error(message, errorObj = null) {
    if (errorObj !== null) {
      this.logger.log(`${MozleniumLogger.ERROR_PREFIX}${message}`, errorObj);
    } else {
      this.logger.log(`${MozleniumLogger.ERROR_PREFIX}${message}`);
    }
  }
  logTelemetry(key, message) {
    this.logger.log(`[${MozleniumLogger.TELEMETRY_PREFIX}|${key}]: `, message);
  }
  log(message) {
    this.logger.log(`${MozleniumLogger.LOG_PREFIX}${message}`);
  }
  success(message) {
    this.logger.log(`${MozleniumLogger.SUCCESS_PREFIX}${message}`);
  }
  status(message) {
    this.logger.log(`${MozleniumLogger.STATUS_PREFIX}${message}`);
  }
}

module.exports = MozleniumLogger;
