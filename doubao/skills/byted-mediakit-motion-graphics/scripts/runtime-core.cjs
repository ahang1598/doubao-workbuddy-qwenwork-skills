"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/constants.js
var require_constants = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/constants.js"(exports2, module2) {
    "use strict";
    var SEMVER_SPEC_VERSION = "2.0.0";
    var MAX_LENGTH = 256;
    var MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER || /* istanbul ignore next */
    9007199254740991;
    var MAX_SAFE_COMPONENT_LENGTH = 16;
    var MAX_SAFE_BUILD_LENGTH = MAX_LENGTH - 6;
    var RELEASE_TYPES = [
      "major",
      "premajor",
      "minor",
      "preminor",
      "patch",
      "prepatch",
      "prerelease"
    ];
    module2.exports = {
      MAX_LENGTH,
      MAX_SAFE_COMPONENT_LENGTH,
      MAX_SAFE_BUILD_LENGTH,
      MAX_SAFE_INTEGER,
      RELEASE_TYPES,
      SEMVER_SPEC_VERSION,
      FLAG_INCLUDE_PRERELEASE: 1,
      FLAG_LOOSE: 2
    };
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/debug.js
var require_debug = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/debug.js"(exports2, module2) {
    "use strict";
    var debug = typeof process === "object" && process.env && process.env.NODE_DEBUG && /\bsemver\b/i.test(process.env.NODE_DEBUG) ? (...args) => console.error("SEMVER", ...args) : () => {
    };
    module2.exports = debug;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/re.js
var require_re = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/re.js"(exports2, module2) {
    "use strict";
    var {
      MAX_SAFE_COMPONENT_LENGTH,
      MAX_SAFE_BUILD_LENGTH,
      MAX_LENGTH
    } = require_constants();
    var debug = require_debug();
    exports2 = module2.exports = {};
    var re = exports2.re = [];
    var safeRe = exports2.safeRe = [];
    var src = exports2.src = [];
    var safeSrc = exports2.safeSrc = [];
    var t = exports2.t = {};
    var R = 0;
    var LETTERDASHNUMBER = "[a-zA-Z0-9-]";
    var safeRegexReplacements = [
      ["\\s", 1],
      ["\\d", MAX_LENGTH],
      [LETTERDASHNUMBER, MAX_SAFE_BUILD_LENGTH]
    ];
    var makeSafeRegex = (value) => {
      for (const [token, max] of safeRegexReplacements) {
        value = value.split(`${token}*`).join(`${token}{0,${max}}`).split(`${token}+`).join(`${token}{1,${max}}`);
      }
      return value;
    };
    var createToken = (name, value, isGlobal) => {
      const safe = makeSafeRegex(value);
      const index = R++;
      debug(name, index, value);
      t[name] = index;
      src[index] = value;
      safeSrc[index] = safe;
      re[index] = new RegExp(value, isGlobal ? "g" : void 0);
      safeRe[index] = new RegExp(safe, isGlobal ? "g" : void 0);
    };
    createToken("NUMERICIDENTIFIER", "0|[1-9]\\d*");
    createToken("NUMERICIDENTIFIERLOOSE", "\\d+");
    createToken("NONNUMERICIDENTIFIER", `\\d*[a-zA-Z-]${LETTERDASHNUMBER}*`);
    createToken("MAINVERSION", `(${src[t.NUMERICIDENTIFIER]})\\.(${src[t.NUMERICIDENTIFIER]})\\.(${src[t.NUMERICIDENTIFIER]})`);
    createToken("MAINVERSIONLOOSE", `(${src[t.NUMERICIDENTIFIERLOOSE]})\\.(${src[t.NUMERICIDENTIFIERLOOSE]})\\.(${src[t.NUMERICIDENTIFIERLOOSE]})`);
    createToken("PRERELEASEIDENTIFIER", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIER]})`);
    createToken("PRERELEASEIDENTIFIERLOOSE", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIERLOOSE]})`);
    createToken("PRERELEASE", `(?:-(${src[t.PRERELEASEIDENTIFIER]}(?:\\.${src[t.PRERELEASEIDENTIFIER]})*))`);
    createToken("PRERELEASELOOSE", `(?:-?(${src[t.PRERELEASEIDENTIFIERLOOSE]}(?:\\.${src[t.PRERELEASEIDENTIFIERLOOSE]})*))`);
    createToken("BUILDIDENTIFIER", `${LETTERDASHNUMBER}+`);
    createToken("BUILD", `(?:\\+(${src[t.BUILDIDENTIFIER]}(?:\\.${src[t.BUILDIDENTIFIER]})*))`);
    createToken("FULLPLAIN", `v?${src[t.MAINVERSION]}${src[t.PRERELEASE]}?${src[t.BUILD]}?`);
    createToken("FULL", `^${src[t.FULLPLAIN]}$`);
    createToken("LOOSEPLAIN", `[v=\\s]*${src[t.MAINVERSIONLOOSE]}${src[t.PRERELEASELOOSE]}?${src[t.BUILD]}?`);
    createToken("LOOSE", `^${src[t.LOOSEPLAIN]}$`);
    createToken("GTLT", "((?:<|>)?=?)");
    createToken("XRANGEIDENTIFIERLOOSE", `${src[t.NUMERICIDENTIFIERLOOSE]}|x|X|\\*`);
    createToken("XRANGEIDENTIFIER", `${src[t.NUMERICIDENTIFIER]}|x|X|\\*`);
    createToken("XRANGEPLAIN", `[v=\\s]*(${src[t.XRANGEIDENTIFIER]})(?:\\.(${src[t.XRANGEIDENTIFIER]})(?:\\.(${src[t.XRANGEIDENTIFIER]})(?:${src[t.PRERELEASE]})?${src[t.BUILD]}?)?)?`);
    createToken("XRANGEPLAINLOOSE", `[v=\\s]*(${src[t.XRANGEIDENTIFIERLOOSE]})(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})(?:${src[t.PRERELEASELOOSE]})?${src[t.BUILD]}?)?)?`);
    createToken("XRANGE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAIN]}$`);
    createToken("XRANGELOOSE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAINLOOSE]}$`);
    createToken("COERCEPLAIN", `${"(^|[^\\d])(\\d{1,"}${MAX_SAFE_COMPONENT_LENGTH}})(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?`);
    createToken("COERCE", `${src[t.COERCEPLAIN]}(?:$|[^\\d])`);
    createToken("COERCEFULL", src[t.COERCEPLAIN] + `(?:${src[t.PRERELEASE]})?(?:${src[t.BUILD]})?(?:$|[^\\d])`);
    createToken("COERCERTL", src[t.COERCE], true);
    createToken("COERCERTLFULL", src[t.COERCEFULL], true);
    createToken("LONETILDE", "(?:~>?)");
    createToken("TILDETRIM", `(\\s*)${src[t.LONETILDE]}\\s+`, true);
    exports2.tildeTrimReplace = "$1~";
    createToken("TILDE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAIN]}$`);
    createToken("TILDELOOSE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAINLOOSE]}$`);
    createToken("LONECARET", "(?:\\^)");
    createToken("CARETTRIM", `(\\s*)${src[t.LONECARET]}\\s+`, true);
    exports2.caretTrimReplace = "$1^";
    createToken("CARET", `^${src[t.LONECARET]}${src[t.XRANGEPLAIN]}$`);
    createToken("CARETLOOSE", `^${src[t.LONECARET]}${src[t.XRANGEPLAINLOOSE]}$`);
    createToken("COMPARATORLOOSE", `^${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]})$|^$`);
    createToken("COMPARATOR", `^${src[t.GTLT]}\\s*(${src[t.FULLPLAIN]})$|^$`);
    createToken("COMPARATORTRIM", `(\\s*)${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]}|${src[t.XRANGEPLAIN]})`, true);
    exports2.comparatorTrimReplace = "$1$2$3";
    createToken("HYPHENRANGE", `^\\s*(${src[t.XRANGEPLAIN]})\\s+-\\s+(${src[t.XRANGEPLAIN]})\\s*$`);
    createToken("HYPHENRANGELOOSE", `^\\s*(${src[t.XRANGEPLAINLOOSE]})\\s+-\\s+(${src[t.XRANGEPLAINLOOSE]})\\s*$`);
    createToken("STAR", "(<|>)?=?\\s*\\*");
    createToken("GTE0", "^\\s*>=\\s*0\\.0\\.0\\s*$");
    createToken("GTE0PRE", "^\\s*>=\\s*0\\.0\\.0-0\\s*$");
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/parse-options.js
var require_parse_options = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/parse-options.js"(exports2, module2) {
    "use strict";
    var looseOption = Object.freeze({ loose: true });
    var emptyOpts = Object.freeze({});
    var parseOptions = (options) => {
      if (!options) {
        return emptyOpts;
      }
      if (typeof options !== "object") {
        return looseOption;
      }
      return options;
    };
    module2.exports = parseOptions;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/identifiers.js
var require_identifiers = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/identifiers.js"(exports2, module2) {
    "use strict";
    var numeric = /^[0-9]+$/;
    var compareIdentifiers = (a, b) => {
      if (typeof a === "number" && typeof b === "number") {
        return a === b ? 0 : a < b ? -1 : 1;
      }
      const anum = numeric.test(a);
      const bnum = numeric.test(b);
      if (anum && bnum) {
        a = +a;
        b = +b;
      }
      return a === b ? 0 : anum && !bnum ? -1 : bnum && !anum ? 1 : a < b ? -1 : 1;
    };
    var rcompareIdentifiers = (a, b) => compareIdentifiers(b, a);
    module2.exports = {
      compareIdentifiers,
      rcompareIdentifiers
    };
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/classes/semver.js
var require_semver = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/classes/semver.js"(exports2, module2) {
    "use strict";
    var debug = require_debug();
    var { MAX_LENGTH, MAX_SAFE_INTEGER } = require_constants();
    var { safeRe: re, t } = require_re();
    var parseOptions = require_parse_options();
    var { compareIdentifiers } = require_identifiers();
    var isPrereleaseIdentifier = (prerelease, identifier) => {
      const identifiers = identifier.split(".");
      if (identifiers.length > prerelease.length) {
        return false;
      }
      for (let i = 0; i < identifiers.length; i++) {
        if (compareIdentifiers(prerelease[i], identifiers[i]) !== 0) {
          return false;
        }
      }
      return true;
    };
    var SemVer = class _SemVer {
      constructor(version, options) {
        options = parseOptions(options);
        if (version instanceof _SemVer) {
          if (version.loose === !!options.loose && version.includePrerelease === !!options.includePrerelease) {
            return version;
          } else {
            version = version.version;
          }
        } else if (typeof version !== "string") {
          throw new TypeError(`Invalid version. Must be a string. Got type "${typeof version}".`);
        }
        if (version.length > MAX_LENGTH) {
          throw new TypeError(
            `version is longer than ${MAX_LENGTH} characters`
          );
        }
        debug("SemVer", version, options);
        this.options = options;
        this.loose = !!options.loose;
        this.includePrerelease = !!options.includePrerelease;
        const m = version.trim().match(options.loose ? re[t.LOOSE] : re[t.FULL]);
        if (!m) {
          throw new TypeError(`Invalid Version: ${version}`);
        }
        this.raw = version;
        this.major = +m[1];
        this.minor = +m[2];
        this.patch = +m[3];
        if (this.major > MAX_SAFE_INTEGER || this.major < 0) {
          throw new TypeError("Invalid major version");
        }
        if (this.minor > MAX_SAFE_INTEGER || this.minor < 0) {
          throw new TypeError("Invalid minor version");
        }
        if (this.patch > MAX_SAFE_INTEGER || this.patch < 0) {
          throw new TypeError("Invalid patch version");
        }
        if (!m[4]) {
          this.prerelease = [];
        } else {
          this.prerelease = m[4].split(".").map((id) => {
            if (/^[0-9]+$/.test(id)) {
              const num = +id;
              if (num >= 0 && num < MAX_SAFE_INTEGER) {
                return num;
              }
            }
            return id;
          });
        }
        this.build = m[5] ? m[5].split(".") : [];
        this.format();
      }
      format() {
        this.version = `${this.major}.${this.minor}.${this.patch}`;
        if (this.prerelease.length) {
          this.version += `-${this.prerelease.join(".")}`;
        }
        return this.version;
      }
      toString() {
        return this.version;
      }
      compare(other) {
        debug("SemVer.compare", this.version, this.options, other);
        if (!(other instanceof _SemVer)) {
          if (typeof other === "string" && other === this.version) {
            return 0;
          }
          other = new _SemVer(other, this.options);
        }
        if (other.version === this.version) {
          return 0;
        }
        return this.compareMain(other) || this.comparePre(other);
      }
      compareMain(other) {
        if (!(other instanceof _SemVer)) {
          other = new _SemVer(other, this.options);
        }
        if (this.major < other.major) {
          return -1;
        }
        if (this.major > other.major) {
          return 1;
        }
        if (this.minor < other.minor) {
          return -1;
        }
        if (this.minor > other.minor) {
          return 1;
        }
        if (this.patch < other.patch) {
          return -1;
        }
        if (this.patch > other.patch) {
          return 1;
        }
        return 0;
      }
      comparePre(other) {
        if (!(other instanceof _SemVer)) {
          other = new _SemVer(other, this.options);
        }
        if (this.prerelease.length && !other.prerelease.length) {
          return -1;
        } else if (!this.prerelease.length && other.prerelease.length) {
          return 1;
        } else if (!this.prerelease.length && !other.prerelease.length) {
          return 0;
        }
        let i = 0;
        do {
          const a = this.prerelease[i];
          const b = other.prerelease[i];
          debug("prerelease compare", i, a, b);
          if (a === void 0 && b === void 0) {
            return 0;
          } else if (b === void 0) {
            return 1;
          } else if (a === void 0) {
            return -1;
          } else if (a === b) {
            continue;
          } else {
            return compareIdentifiers(a, b);
          }
        } while (++i);
      }
      compareBuild(other) {
        if (!(other instanceof _SemVer)) {
          other = new _SemVer(other, this.options);
        }
        let i = 0;
        do {
          const a = this.build[i];
          const b = other.build[i];
          debug("build compare", i, a, b);
          if (a === void 0 && b === void 0) {
            return 0;
          } else if (b === void 0) {
            return 1;
          } else if (a === void 0) {
            return -1;
          } else if (a === b) {
            continue;
          } else {
            return compareIdentifiers(a, b);
          }
        } while (++i);
      }
      // preminor will bump the version up to the next minor release, and immediately
      // down to pre-release. premajor and prepatch work the same way.
      inc(release, identifier, identifierBase) {
        if (release.startsWith("pre")) {
          if (!identifier && identifierBase === false) {
            throw new Error("invalid increment argument: identifier is empty");
          }
          if (identifier) {
            const match = `-${identifier}`.match(this.options.loose ? re[t.PRERELEASELOOSE] : re[t.PRERELEASE]);
            if (!match || match[1] !== identifier) {
              throw new Error(`invalid identifier: ${identifier}`);
            }
          }
        }
        switch (release) {
          case "premajor":
            this.prerelease.length = 0;
            this.patch = 0;
            this.minor = 0;
            this.major++;
            this.inc("pre", identifier, identifierBase);
            break;
          case "preminor":
            this.prerelease.length = 0;
            this.patch = 0;
            this.minor++;
            this.inc("pre", identifier, identifierBase);
            break;
          case "prepatch":
            this.prerelease.length = 0;
            this.inc("patch", identifier, identifierBase);
            this.inc("pre", identifier, identifierBase);
            break;
          case "prerelease":
            if (this.prerelease.length === 0) {
              this.inc("patch", identifier, identifierBase);
            }
            this.inc("pre", identifier, identifierBase);
            break;
          case "release":
            if (this.prerelease.length === 0) {
              throw new Error(`version ${this.raw} is not a prerelease`);
            }
            this.prerelease.length = 0;
            break;
          case "major":
            if (this.minor !== 0 || this.patch !== 0 || this.prerelease.length === 0) {
              this.major++;
            }
            this.minor = 0;
            this.patch = 0;
            this.prerelease = [];
            break;
          case "minor":
            if (this.patch !== 0 || this.prerelease.length === 0) {
              this.minor++;
            }
            this.patch = 0;
            this.prerelease = [];
            break;
          case "patch":
            if (this.prerelease.length === 0) {
              this.patch++;
            }
            this.prerelease = [];
            break;
          case "pre": {
            const base = Number(identifierBase) ? 1 : 0;
            if (this.prerelease.length === 0) {
              this.prerelease = [base];
            } else {
              let i = this.prerelease.length;
              while (--i >= 0) {
                if (typeof this.prerelease[i] === "number") {
                  this.prerelease[i]++;
                  i = -2;
                }
              }
              if (i === -1) {
                if (identifier === this.prerelease.join(".") && identifierBase === false) {
                  throw new Error("invalid increment argument: identifier already exists");
                }
                this.prerelease.push(base);
              }
            }
            if (identifier) {
              let prerelease = [identifier, base];
              if (identifierBase === false) {
                prerelease = [identifier];
              }
              if (isPrereleaseIdentifier(this.prerelease, identifier)) {
                const prereleaseBase = this.prerelease[identifier.split(".").length];
                if (isNaN(prereleaseBase)) {
                  this.prerelease = prerelease;
                }
              } else {
                this.prerelease = prerelease;
              }
            }
            break;
          }
          default:
            throw new Error(`invalid increment argument: ${release}`);
        }
        this.raw = this.format();
        if (this.build.length) {
          this.raw += `+${this.build.join(".")}`;
        }
        return this;
      }
    };
    module2.exports = SemVer;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/parse.js
var require_parse = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/parse.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var parse = (version, options, throwErrors = false) => {
      if (version instanceof SemVer) {
        return version;
      }
      try {
        return new SemVer(version, options);
      } catch (er) {
        if (!throwErrors) {
          return null;
        }
        throw er;
      }
    };
    module2.exports = parse;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/valid.js
var require_valid = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/valid.js"(exports2, module2) {
    "use strict";
    var parse = require_parse();
    var valid = (version, options) => {
      const v = parse(version, options);
      return v ? v.version : null;
    };
    module2.exports = valid;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/clean.js
var require_clean = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/clean.js"(exports2, module2) {
    "use strict";
    var parse = require_parse();
    var clean = (version, options) => {
      const s = parse(version.trim().replace(/^[=v]+/, ""), options);
      return s ? s.version : null;
    };
    module2.exports = clean;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/inc.js
var require_inc = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/inc.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var inc = (version, release, options, identifier, identifierBase) => {
      if (typeof options === "string") {
        identifierBase = identifier;
        identifier = options;
        options = void 0;
      }
      try {
        return new SemVer(
          version instanceof SemVer ? version.version : version,
          options
        ).inc(release, identifier, identifierBase).version;
      } catch (er) {
        return null;
      }
    };
    module2.exports = inc;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/diff.js
var require_diff = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/diff.js"(exports2, module2) {
    "use strict";
    var parse = require_parse();
    var diff = (version1, version2) => {
      const v1 = parse(version1, null, true);
      const v2 = parse(version2, null, true);
      const comparison = v1.compare(v2);
      if (comparison === 0) {
        return null;
      }
      const v1Higher = comparison > 0;
      const highVersion = v1Higher ? v1 : v2;
      const lowVersion = v1Higher ? v2 : v1;
      const highHasPre = !!highVersion.prerelease.length;
      const lowHasPre = !!lowVersion.prerelease.length;
      if (lowHasPre && !highHasPre) {
        if (!lowVersion.patch && !lowVersion.minor) {
          return "major";
        }
        if (lowVersion.compareMain(highVersion) === 0) {
          if (lowVersion.minor && !lowVersion.patch) {
            return "minor";
          }
          return "patch";
        }
      }
      const prefix = highHasPre ? "pre" : "";
      if (v1.major !== v2.major) {
        return prefix + "major";
      }
      if (v1.minor !== v2.minor) {
        return prefix + "minor";
      }
      if (v1.patch !== v2.patch) {
        return prefix + "patch";
      }
      return "prerelease";
    };
    module2.exports = diff;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/major.js
var require_major = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/major.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var major = (a, loose) => new SemVer(a, loose).major;
    module2.exports = major;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/minor.js
var require_minor = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/minor.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var minor = (a, loose) => new SemVer(a, loose).minor;
    module2.exports = minor;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/patch.js
var require_patch = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/patch.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var patch = (a, loose) => new SemVer(a, loose).patch;
    module2.exports = patch;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/prerelease.js
var require_prerelease = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/prerelease.js"(exports2, module2) {
    "use strict";
    var parse = require_parse();
    var prerelease = (version, options) => {
      const parsed = parse(version, options);
      return parsed && parsed.prerelease.length ? parsed.prerelease : null;
    };
    module2.exports = prerelease;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/compare.js
var require_compare = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/compare.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var compare = (a, b, loose) => new SemVer(a, loose).compare(new SemVer(b, loose));
    module2.exports = compare;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/rcompare.js
var require_rcompare = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/rcompare.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var rcompare = (a, b, loose) => compare(b, a, loose);
    module2.exports = rcompare;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/compare-loose.js
var require_compare_loose = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/compare-loose.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var compareLoose = (a, b) => compare(a, b, true);
    module2.exports = compareLoose;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/compare-build.js
var require_compare_build = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/compare-build.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var compareBuild = (a, b, loose) => {
      const versionA = new SemVer(a, loose);
      const versionB = new SemVer(b, loose);
      return versionA.compare(versionB) || versionA.compareBuild(versionB);
    };
    module2.exports = compareBuild;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/sort.js
var require_sort = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/sort.js"(exports2, module2) {
    "use strict";
    var compareBuild = require_compare_build();
    var sort = (list, loose) => list.sort((a, b) => compareBuild(a, b, loose));
    module2.exports = sort;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/rsort.js
var require_rsort = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/rsort.js"(exports2, module2) {
    "use strict";
    var compareBuild = require_compare_build();
    var rsort = (list, loose) => list.sort((a, b) => compareBuild(b, a, loose));
    module2.exports = rsort;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/gt.js
var require_gt = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/gt.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var gt = (a, b, loose) => compare(a, b, loose) > 0;
    module2.exports = gt;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/lt.js
var require_lt = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/lt.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var lt = (a, b, loose) => compare(a, b, loose) < 0;
    module2.exports = lt;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/eq.js
var require_eq = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/eq.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var eq = (a, b, loose) => compare(a, b, loose) === 0;
    module2.exports = eq;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/neq.js
var require_neq = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/neq.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var neq = (a, b, loose) => compare(a, b, loose) !== 0;
    module2.exports = neq;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/gte.js
var require_gte = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/gte.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var gte = (a, b, loose) => compare(a, b, loose) >= 0;
    module2.exports = gte;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/lte.js
var require_lte = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/lte.js"(exports2, module2) {
    "use strict";
    var compare = require_compare();
    var lte = (a, b, loose) => compare(a, b, loose) <= 0;
    module2.exports = lte;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/cmp.js
var require_cmp = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/cmp.js"(exports2, module2) {
    "use strict";
    var eq = require_eq();
    var neq = require_neq();
    var gt = require_gt();
    var gte = require_gte();
    var lt = require_lt();
    var lte = require_lte();
    var cmp = (a, op, b, loose) => {
      switch (op) {
        case "===":
          if (typeof a === "object") {
            a = a.version;
          }
          if (typeof b === "object") {
            b = b.version;
          }
          return a === b;
        case "!==":
          if (typeof a === "object") {
            a = a.version;
          }
          if (typeof b === "object") {
            b = b.version;
          }
          return a !== b;
        case "":
        case "=":
        case "==":
          return eq(a, b, loose);
        case "!=":
          return neq(a, b, loose);
        case ">":
          return gt(a, b, loose);
        case ">=":
          return gte(a, b, loose);
        case "<":
          return lt(a, b, loose);
        case "<=":
          return lte(a, b, loose);
        default:
          throw new TypeError(`Invalid operator: ${op}`);
      }
    };
    module2.exports = cmp;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/coerce.js
var require_coerce = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/coerce.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var parse = require_parse();
    var { safeRe: re, t } = require_re();
    var coerce = (version, options) => {
      if (version instanceof SemVer) {
        return version;
      }
      if (typeof version === "number") {
        version = String(version);
      }
      if (typeof version !== "string") {
        return null;
      }
      options = options || {};
      let match = null;
      if (!options.rtl) {
        match = version.match(options.includePrerelease ? re[t.COERCEFULL] : re[t.COERCE]);
      } else {
        const coerceRtlRegex = options.includePrerelease ? re[t.COERCERTLFULL] : re[t.COERCERTL];
        let next;
        while ((next = coerceRtlRegex.exec(version)) && (!match || match.index + match[0].length !== version.length)) {
          if (!match || next.index + next[0].length !== match.index + match[0].length) {
            match = next;
          }
          coerceRtlRegex.lastIndex = next.index + next[1].length + next[2].length;
        }
        coerceRtlRegex.lastIndex = -1;
      }
      if (match === null) {
        return null;
      }
      const major = match[2];
      const minor = match[3] || "0";
      const patch = match[4] || "0";
      const prerelease = options.includePrerelease && match[5] ? `-${match[5]}` : "";
      const build = options.includePrerelease && match[6] ? `+${match[6]}` : "";
      return parse(`${major}.${minor}.${patch}${prerelease}${build}`, options);
    };
    module2.exports = coerce;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/truncate.js
var require_truncate = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/truncate.js"(exports2, module2) {
    "use strict";
    var parse = require_parse();
    var constants = require_constants();
    var SemVer = require_semver();
    var truncate = (version, truncation, options) => {
      if (!constants.RELEASE_TYPES.includes(truncation)) {
        return null;
      }
      const clonedVersion = cloneInputVersion(version, options);
      return clonedVersion && doTruncation(clonedVersion, truncation);
    };
    var cloneInputVersion = (version, options) => {
      const versionStringToParse = version instanceof SemVer ? version.version : version;
      return parse(versionStringToParse, options);
    };
    var doTruncation = (version, truncation) => {
      if (isPrerelease(truncation)) {
        return version.version;
      }
      version.prerelease = [];
      switch (truncation) {
        case "major":
          version.minor = 0;
          version.patch = 0;
          break;
        case "minor":
          version.patch = 0;
          break;
      }
      return version.format();
    };
    var isPrerelease = (type) => {
      return type.startsWith("pre");
    };
    module2.exports = truncate;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/lrucache.js
var require_lrucache = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/internal/lrucache.js"(exports2, module2) {
    "use strict";
    var LRUCache = class {
      constructor() {
        this.max = 1e3;
        this.map = /* @__PURE__ */ new Map();
      }
      get(key) {
        const value = this.map.get(key);
        if (value === void 0) {
          return void 0;
        } else {
          this.map.delete(key);
          this.map.set(key, value);
          return value;
        }
      }
      delete(key) {
        return this.map.delete(key);
      }
      set(key, value) {
        const deleted = this.delete(key);
        if (!deleted && value !== void 0) {
          if (this.map.size >= this.max) {
            const firstKey = this.map.keys().next().value;
            this.delete(firstKey);
          }
          this.map.set(key, value);
        }
        return this;
      }
    };
    module2.exports = LRUCache;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/classes/range.js
var require_range = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/classes/range.js"(exports2, module2) {
    "use strict";
    var SPACE_CHARACTERS = /\s+/g;
    var Range = class _Range {
      constructor(range, options) {
        options = parseOptions(options);
        if (range instanceof _Range) {
          if (range.loose === !!options.loose && range.includePrerelease === !!options.includePrerelease) {
            return range;
          } else {
            return new _Range(range.raw, options);
          }
        }
        if (range instanceof Comparator) {
          this.raw = range.value;
          this.set = [[range]];
          this.formatted = void 0;
          return this;
        }
        this.options = options;
        this.loose = !!options.loose;
        this.includePrerelease = !!options.includePrerelease;
        this.raw = range.trim().replace(SPACE_CHARACTERS, " ");
        this.set = this.raw.split("||").map((r) => this.parseRange(r.trim())).filter((c) => c.length);
        if (!this.set.length) {
          throw new TypeError(`Invalid SemVer Range: ${this.raw}`);
        }
        if (this.set.length > 1) {
          const first = this.set[0];
          this.set = this.set.filter((c) => !isNullSet(c[0]));
          if (this.set.length === 0) {
            this.set = [first];
          } else if (this.set.length > 1) {
            for (const c of this.set) {
              if (c.length === 1 && isAny(c[0])) {
                this.set = [c];
                break;
              }
            }
          }
        }
        this.formatted = void 0;
      }
      get range() {
        if (this.formatted === void 0) {
          this.formatted = "";
          for (let i = 0; i < this.set.length; i++) {
            if (i > 0) {
              this.formatted += "||";
            }
            const comps = this.set[i];
            for (let k = 0; k < comps.length; k++) {
              if (k > 0) {
                this.formatted += " ";
              }
              this.formatted += comps[k].toString().trim();
            }
          }
        }
        return this.formatted;
      }
      format() {
        return this.range;
      }
      toString() {
        return this.range;
      }
      parseRange(range) {
        range = range.replace(BUILDSTRIPRE, "");
        const memoOpts = (this.options.includePrerelease && FLAG_INCLUDE_PRERELEASE) | (this.options.loose && FLAG_LOOSE);
        const memoKey = memoOpts + ":" + range;
        const cached = cache.get(memoKey);
        if (cached) {
          return cached;
        }
        const loose = this.options.loose;
        const hr = loose ? re[t.HYPHENRANGELOOSE] : re[t.HYPHENRANGE];
        range = range.replace(hr, hyphenReplace(this.options.includePrerelease));
        debug("hyphen replace", range);
        range = range.replace(re[t.COMPARATORTRIM], comparatorTrimReplace);
        debug("comparator trim", range);
        range = range.replace(re[t.TILDETRIM], tildeTrimReplace);
        debug("tilde trim", range);
        range = range.replace(re[t.CARETTRIM], caretTrimReplace);
        debug("caret trim", range);
        let rangeList = range.split(" ").map((comp) => parseComparator(comp, this.options)).join(" ").split(/\s+/).map((comp) => replaceGTE0(comp, this.options));
        if (loose) {
          rangeList = rangeList.filter((comp) => {
            debug("loose invalid filter", comp, this.options);
            return !!comp.match(re[t.COMPARATORLOOSE]);
          });
        }
        debug("range list", rangeList);
        const rangeMap = /* @__PURE__ */ new Map();
        const comparators = rangeList.map((comp) => new Comparator(comp, this.options));
        for (const comp of comparators) {
          if (isNullSet(comp)) {
            return [comp];
          }
          rangeMap.set(comp.value, comp);
        }
        if (rangeMap.size > 1 && rangeMap.has("")) {
          rangeMap.delete("");
        }
        const result = [...rangeMap.values()];
        cache.set(memoKey, result);
        return result;
      }
      intersects(range, options) {
        if (!(range instanceof _Range)) {
          throw new TypeError("a Range is required");
        }
        return this.set.some((thisComparators) => {
          return isSatisfiable(thisComparators, options) && range.set.some((rangeComparators) => {
            return isSatisfiable(rangeComparators, options) && thisComparators.every((thisComparator) => {
              return rangeComparators.every((rangeComparator) => {
                return thisComparator.intersects(rangeComparator, options);
              });
            });
          });
        });
      }
      // if ANY of the sets match ALL of its comparators, then pass
      test(version) {
        if (!version) {
          return false;
        }
        if (typeof version === "string") {
          try {
            version = new SemVer(version, this.options);
          } catch (er) {
            return false;
          }
        }
        for (let i = 0; i < this.set.length; i++) {
          if (testSet(this.set[i], version, this.options)) {
            return true;
          }
        }
        return false;
      }
    };
    module2.exports = Range;
    var LRU = require_lrucache();
    var cache = new LRU();
    var parseOptions = require_parse_options();
    var Comparator = require_comparator();
    var debug = require_debug();
    var SemVer = require_semver();
    var {
      safeRe: re,
      src,
      t,
      comparatorTrimReplace,
      tildeTrimReplace,
      caretTrimReplace
    } = require_re();
    var { FLAG_INCLUDE_PRERELEASE, FLAG_LOOSE } = require_constants();
    var BUILDSTRIPRE = new RegExp(src[t.BUILD], "g");
    var isNullSet = (c) => c.value === "<0.0.0-0";
    var isAny = (c) => c.value === "";
    var isSatisfiable = (comparators, options) => {
      let result = true;
      const remainingComparators = comparators.slice();
      let testComparator = remainingComparators.pop();
      while (result && remainingComparators.length) {
        result = remainingComparators.every((otherComparator) => {
          return testComparator.intersects(otherComparator, options);
        });
        testComparator = remainingComparators.pop();
      }
      return result;
    };
    var parseComparator = (comp, options) => {
      comp = comp.replace(re[t.BUILD], "");
      debug("comp", comp, options);
      comp = replaceCarets(comp, options);
      debug("caret", comp);
      comp = replaceTildes(comp, options);
      debug("tildes", comp);
      comp = replaceXRanges(comp, options);
      debug("xrange", comp);
      comp = replaceStars(comp, options);
      debug("stars", comp);
      return comp;
    };
    var isX = (id) => !id || id.toLowerCase() === "x" || id === "*";
    var invalidXRangeOrder = (M, m, p) => isX(M) && !isX(m) || isX(m) && p && !isX(p);
    var replaceTildes = (comp, options) => {
      return comp.trim().split(/\s+/).map((c) => replaceTilde(c, options)).join(" ");
    };
    var replaceTilde = (comp, options) => {
      const r = options.loose ? re[t.TILDELOOSE] : re[t.TILDE];
      const z = options.includePrerelease ? "-0" : "";
      return comp.replace(r, (_, M, m, p, pr) => {
        debug("tilde", comp, _, M, m, p, pr);
        let ret;
        if (isX(M)) {
          ret = "";
        } else if (isX(m)) {
          ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`;
        } else if (isX(p)) {
          ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`;
        } else if (pr) {
          debug("replaceTilde pr", pr);
          ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
        } else {
          ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`;
        }
        debug("tilde return", ret);
        return ret;
      });
    };
    var replaceCarets = (comp, options) => {
      return comp.trim().split(/\s+/).map((c) => replaceCaret(c, options)).join(" ");
    };
    var replaceCaret = (comp, options) => {
      debug("caret", comp, options);
      const r = options.loose ? re[t.CARETLOOSE] : re[t.CARET];
      const z = options.includePrerelease ? "-0" : "";
      return comp.replace(r, (_, M, m, p, pr) => {
        debug("caret", comp, _, M, m, p, pr);
        let ret;
        if (isX(M)) {
          ret = "";
        } else if (isX(m)) {
          ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`;
        } else if (isX(p)) {
          if (M === "0") {
            ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`;
          } else {
            ret = `>=${M}.${m}.0${z} <${+M + 1}.0.0-0`;
          }
        } else if (pr) {
          debug("replaceCaret pr", pr);
          if (M === "0") {
            if (m === "0") {
              ret = `>=${M}.${m}.${p}-${pr} <${M}.${m}.${+p + 1}-0`;
            } else {
              ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
            }
          } else {
            ret = `>=${M}.${m}.${p}-${pr} <${+M + 1}.0.0-0`;
          }
        } else {
          debug("no pr");
          if (M === "0") {
            if (m === "0") {
              ret = `>=${M}.${m}.${p} <${M}.${m}.${+p + 1}-0`;
            } else {
              ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`;
            }
          } else {
            ret = `>=${M}.${m}.${p} <${+M + 1}.0.0-0`;
          }
        }
        debug("caret return", ret);
        return ret;
      });
    };
    var replaceXRanges = (comp, options) => {
      debug("replaceXRanges", comp, options);
      return comp.split(/\s+/).map((c) => replaceXRange(c, options)).join(" ");
    };
    var replaceXRange = (comp, options) => {
      comp = comp.trim();
      const r = options.loose ? re[t.XRANGELOOSE] : re[t.XRANGE];
      return comp.replace(r, (ret, gtlt, M, m, p, pr) => {
        debug("xRange", comp, ret, gtlt, M, m, p, pr);
        if (invalidXRangeOrder(M, m, p)) {
          return comp;
        }
        const xM = isX(M);
        const xm = xM || isX(m);
        const xp = xm || isX(p);
        const anyX = xp;
        if (gtlt === "=" && anyX) {
          gtlt = "";
        }
        pr = options.includePrerelease ? "-0" : "";
        if (xM) {
          if (gtlt === ">" || gtlt === "<") {
            ret = "<0.0.0-0";
          } else {
            ret = "*";
          }
        } else if (gtlt && anyX) {
          if (xm) {
            m = 0;
          }
          p = 0;
          if (gtlt === ">") {
            gtlt = ">=";
            if (xm) {
              M = +M + 1;
              m = 0;
              p = 0;
            } else {
              m = +m + 1;
              p = 0;
            }
          } else if (gtlt === "<=") {
            gtlt = "<";
            if (xm) {
              M = +M + 1;
            } else {
              m = +m + 1;
            }
          }
          if (gtlt === "<") {
            pr = "-0";
          }
          ret = `${gtlt + M}.${m}.${p}${pr}`;
        } else if (xm) {
          ret = `>=${M}.0.0${pr} <${+M + 1}.0.0-0`;
        } else if (xp) {
          ret = `>=${M}.${m}.0${pr} <${M}.${+m + 1}.0-0`;
        }
        debug("xRange return", ret);
        return ret;
      });
    };
    var replaceStars = (comp, options) => {
      debug("replaceStars", comp, options);
      return comp.trim().replace(re[t.STAR], "");
    };
    var replaceGTE0 = (comp, options) => {
      debug("replaceGTE0", comp, options);
      return comp.trim().replace(re[options.includePrerelease ? t.GTE0PRE : t.GTE0], "");
    };
    var hyphenReplace = (incPr) => ($0, from, fM, fm, fp, fpr, fb, to, tM, tm, tp, tpr) => {
      if (isX(fM)) {
        from = "";
      } else if (isX(fm)) {
        from = `>=${fM}.0.0${incPr ? "-0" : ""}`;
      } else if (isX(fp)) {
        from = `>=${fM}.${fm}.0${incPr ? "-0" : ""}`;
      } else if (fpr) {
        from = `>=${from}`;
      } else {
        from = `>=${from}${incPr ? "-0" : ""}`;
      }
      if (isX(tM)) {
        to = "";
      } else if (isX(tm)) {
        to = `<${+tM + 1}.0.0-0`;
      } else if (isX(tp)) {
        to = `<${tM}.${+tm + 1}.0-0`;
      } else if (tpr) {
        to = `<=${tM}.${tm}.${tp}-${tpr}`;
      } else if (incPr) {
        to = `<${tM}.${tm}.${+tp + 1}-0`;
      } else {
        to = `<=${to}`;
      }
      return `${from} ${to}`.trim();
    };
    var testSet = (set, version, options) => {
      for (let i = 0; i < set.length; i++) {
        if (!set[i].test(version)) {
          return false;
        }
      }
      if (version.prerelease.length && !options.includePrerelease) {
        for (let i = 0; i < set.length; i++) {
          debug(set[i].semver);
          if (set[i].semver === Comparator.ANY) {
            continue;
          }
          if (set[i].semver.prerelease.length > 0) {
            const allowed = set[i].semver;
            if (allowed.major === version.major && allowed.minor === version.minor && allowed.patch === version.patch) {
              return true;
            }
          }
        }
        return false;
      }
      return true;
    };
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/classes/comparator.js
var require_comparator = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/classes/comparator.js"(exports2, module2) {
    "use strict";
    var ANY = Symbol("SemVer ANY");
    var Comparator = class _Comparator {
      static get ANY() {
        return ANY;
      }
      constructor(comp, options) {
        options = parseOptions(options);
        if (comp instanceof _Comparator) {
          if (comp.loose === !!options.loose) {
            return comp;
          } else {
            comp = comp.value;
          }
        }
        comp = comp.trim().split(/\s+/).join(" ");
        debug("comparator", comp, options);
        this.options = options;
        this.loose = !!options.loose;
        this.parse(comp);
        if (this.semver === ANY) {
          this.value = "";
        } else {
          this.value = this.operator + this.semver.version;
        }
        debug("comp", this);
      }
      parse(comp) {
        const r = this.options.loose ? re[t.COMPARATORLOOSE] : re[t.COMPARATOR];
        const m = comp.match(r);
        if (!m) {
          throw new TypeError(`Invalid comparator: ${comp}`);
        }
        this.operator = m[1] !== void 0 ? m[1] : "";
        if (this.operator === "=") {
          this.operator = "";
        }
        if (!m[2]) {
          this.semver = ANY;
        } else {
          this.semver = new SemVer(m[2], this.options.loose);
        }
      }
      toString() {
        return this.value;
      }
      test(version) {
        debug("Comparator.test", version, this.options.loose);
        if (this.semver === ANY || version === ANY) {
          return true;
        }
        if (typeof version === "string") {
          try {
            version = new SemVer(version, this.options);
          } catch (er) {
            return false;
          }
        }
        return cmp(version, this.operator, this.semver, this.options);
      }
      intersects(comp, options) {
        if (!(comp instanceof _Comparator)) {
          throw new TypeError("a Comparator is required");
        }
        if (this.operator === "") {
          if (this.value === "") {
            return true;
          }
          return new Range(comp.value, options).test(this.value);
        } else if (comp.operator === "") {
          if (comp.value === "") {
            return true;
          }
          return new Range(this.value, options).test(comp.semver);
        }
        options = parseOptions(options);
        if (options.includePrerelease && (this.value === "<0.0.0-0" || comp.value === "<0.0.0-0")) {
          return false;
        }
        if (!options.includePrerelease && (this.value.startsWith("<0.0.0") || comp.value.startsWith("<0.0.0"))) {
          return false;
        }
        if (this.operator.startsWith(">") && comp.operator.startsWith(">")) {
          return true;
        }
        if (this.operator.startsWith("<") && comp.operator.startsWith("<")) {
          return true;
        }
        if (this.semver.version === comp.semver.version && this.operator.includes("=") && comp.operator.includes("=")) {
          return true;
        }
        if (cmp(this.semver, "<", comp.semver, options) && this.operator.startsWith(">") && comp.operator.startsWith("<")) {
          return true;
        }
        if (cmp(this.semver, ">", comp.semver, options) && this.operator.startsWith("<") && comp.operator.startsWith(">")) {
          return true;
        }
        return false;
      }
    };
    module2.exports = Comparator;
    var parseOptions = require_parse_options();
    var { safeRe: re, t } = require_re();
    var cmp = require_cmp();
    var debug = require_debug();
    var SemVer = require_semver();
    var Range = require_range();
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/satisfies.js
var require_satisfies = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/functions/satisfies.js"(exports2, module2) {
    "use strict";
    var Range = require_range();
    var satisfies = (version, range, options) => {
      try {
        range = new Range(range, options);
      } catch (er) {
        return false;
      }
      return range.test(version);
    };
    module2.exports = satisfies;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/to-comparators.js
var require_to_comparators = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/to-comparators.js"(exports2, module2) {
    "use strict";
    var Range = require_range();
    var toComparators = (range, options) => new Range(range, options).set.map((comp) => comp.map((c) => c.value).join(" ").trim().split(" "));
    module2.exports = toComparators;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/max-satisfying.js
var require_max_satisfying = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/max-satisfying.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var Range = require_range();
    var maxSatisfying = (versions, range, options) => {
      let max = null;
      let maxSV = null;
      let rangeObj = null;
      try {
        rangeObj = new Range(range, options);
      } catch (er) {
        return null;
      }
      versions.forEach((v) => {
        if (rangeObj.test(v)) {
          if (!max || maxSV.compare(v) === -1) {
            max = v;
            maxSV = new SemVer(max, options);
          }
        }
      });
      return max;
    };
    module2.exports = maxSatisfying;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/min-satisfying.js
var require_min_satisfying = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/min-satisfying.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var Range = require_range();
    var minSatisfying = (versions, range, options) => {
      let min = null;
      let minSV = null;
      let rangeObj = null;
      try {
        rangeObj = new Range(range, options);
      } catch (er) {
        return null;
      }
      versions.forEach((v) => {
        if (rangeObj.test(v)) {
          if (!min || minSV.compare(v) === 1) {
            min = v;
            minSV = new SemVer(min, options);
          }
        }
      });
      return min;
    };
    module2.exports = minSatisfying;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/min-version.js
var require_min_version = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/min-version.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var Range = require_range();
    var gt = require_gt();
    var minVersion = (range, loose) => {
      range = new Range(range, loose);
      let minver = new SemVer("0.0.0");
      if (range.test(minver)) {
        return minver;
      }
      minver = new SemVer("0.0.0-0");
      if (range.test(minver)) {
        return minver;
      }
      minver = null;
      for (let i = 0; i < range.set.length; ++i) {
        const comparators = range.set[i];
        let setMin = null;
        comparators.forEach((comparator) => {
          const compver = new SemVer(comparator.semver.version);
          switch (comparator.operator) {
            case ">":
              if (compver.prerelease.length === 0) {
                compver.patch++;
              } else {
                compver.prerelease.push(0);
              }
              compver.raw = compver.format();
            case "":
            case ">=":
              if (!setMin || gt(compver, setMin)) {
                setMin = compver;
              }
              break;
            case "<":
            case "<=":
              break;
            default:
              throw new Error(`Unexpected operation: ${comparator.operator}`);
          }
        });
        if (setMin && (!minver || gt(minver, setMin))) {
          minver = setMin;
        }
      }
      if (minver && range.test(minver)) {
        return minver;
      }
      return null;
    };
    module2.exports = minVersion;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/valid.js
var require_valid2 = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/valid.js"(exports2, module2) {
    "use strict";
    var Range = require_range();
    var validRange = (range, options) => {
      try {
        return new Range(range, options).range || "*";
      } catch (er) {
        return null;
      }
    };
    module2.exports = validRange;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/outside.js
var require_outside = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/outside.js"(exports2, module2) {
    "use strict";
    var SemVer = require_semver();
    var Comparator = require_comparator();
    var { ANY } = Comparator;
    var Range = require_range();
    var satisfies = require_satisfies();
    var gt = require_gt();
    var lt = require_lt();
    var lte = require_lte();
    var gte = require_gte();
    var outside = (version, range, hilo, options) => {
      version = new SemVer(version, options);
      range = new Range(range, options);
      let gtfn, ltefn, ltfn, comp, ecomp;
      switch (hilo) {
        case ">":
          gtfn = gt;
          ltefn = lte;
          ltfn = lt;
          comp = ">";
          ecomp = ">=";
          break;
        case "<":
          gtfn = lt;
          ltefn = gte;
          ltfn = gt;
          comp = "<";
          ecomp = "<=";
          break;
        default:
          throw new TypeError('Must provide a hilo val of "<" or ">"');
      }
      if (satisfies(version, range, options)) {
        return false;
      }
      for (let i = 0; i < range.set.length; ++i) {
        const comparators = range.set[i];
        let high = null;
        let low = null;
        comparators.forEach((comparator) => {
          if (comparator.semver === ANY) {
            comparator = new Comparator(">=0.0.0");
          }
          high = high || comparator;
          low = low || comparator;
          if (gtfn(comparator.semver, high.semver, options)) {
            high = comparator;
          } else if (ltfn(comparator.semver, low.semver, options)) {
            low = comparator;
          }
        });
        if (high.operator === comp || high.operator === ecomp) {
          return false;
        }
        if ((!low.operator || low.operator === comp) && ltefn(version, low.semver)) {
          return false;
        } else if (low.operator === ecomp && ltfn(version, low.semver)) {
          return false;
        }
      }
      return true;
    };
    module2.exports = outside;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/gtr.js
var require_gtr = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/gtr.js"(exports2, module2) {
    "use strict";
    var outside = require_outside();
    var gtr = (version, range, options) => outside(version, range, ">", options);
    module2.exports = gtr;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/ltr.js
var require_ltr = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/ltr.js"(exports2, module2) {
    "use strict";
    var outside = require_outside();
    var ltr = (version, range, options) => outside(version, range, "<", options);
    module2.exports = ltr;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/intersects.js
var require_intersects = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/intersects.js"(exports2, module2) {
    "use strict";
    var Range = require_range();
    var intersects = (r1, r2, options) => {
      r1 = new Range(r1, options);
      r2 = new Range(r2, options);
      return r1.intersects(r2, options);
    };
    module2.exports = intersects;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/simplify.js
var require_simplify = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/simplify.js"(exports2, module2) {
    "use strict";
    var satisfies = require_satisfies();
    var compare = require_compare();
    module2.exports = (versions, range, options) => {
      const set = [];
      let first = null;
      let prev = null;
      const v = versions.sort((a, b) => compare(a, b, options));
      for (const version of v) {
        const included = satisfies(version, range, options);
        if (included) {
          prev = version;
          if (!first) {
            first = version;
          }
        } else {
          if (prev) {
            set.push([first, prev]);
          }
          prev = null;
          first = null;
        }
      }
      if (first) {
        set.push([first, null]);
      }
      const ranges = [];
      for (const [min, max] of set) {
        if (min === max) {
          ranges.push(min);
        } else if (!max && min === v[0]) {
          ranges.push("*");
        } else if (!max) {
          ranges.push(`>=${min}`);
        } else if (min === v[0]) {
          ranges.push(`<=${max}`);
        } else {
          ranges.push(`${min} - ${max}`);
        }
      }
      const simplified = ranges.join(" || ");
      const original = typeof range.raw === "string" ? range.raw : String(range);
      return simplified.length < original.length ? simplified : range;
    };
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/subset.js
var require_subset = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/ranges/subset.js"(exports2, module2) {
    "use strict";
    var Range = require_range();
    var Comparator = require_comparator();
    var { ANY } = Comparator;
    var satisfies = require_satisfies();
    var compare = require_compare();
    var subset = (sub, dom, options = {}) => {
      if (sub === dom) {
        return true;
      }
      sub = new Range(sub, options);
      dom = new Range(dom, options);
      let sawNonNull = false;
      OUTER:
        for (const simpleSub of sub.set) {
          for (const simpleDom of dom.set) {
            const isSub = simpleSubset(simpleSub, simpleDom, options);
            sawNonNull = sawNonNull || isSub !== null;
            if (isSub) {
              continue OUTER;
            }
          }
          if (sawNonNull) {
            return false;
          }
        }
      return true;
    };
    var minimumVersionWithPreRelease = [new Comparator(">=0.0.0-0")];
    var minimumVersion = [new Comparator(">=0.0.0")];
    var simpleSubset = (sub, dom, options) => {
      if (sub === dom) {
        return true;
      }
      if (sub.length === 1 && sub[0].semver === ANY) {
        if (dom.length === 1 && dom[0].semver === ANY) {
          return true;
        } else if (options.includePrerelease) {
          sub = minimumVersionWithPreRelease;
        } else {
          sub = minimumVersion;
        }
      }
      if (dom.length === 1 && dom[0].semver === ANY) {
        if (options.includePrerelease) {
          return true;
        } else {
          dom = minimumVersion;
        }
      }
      const eqSet = /* @__PURE__ */ new Set();
      let gt, lt;
      for (const c of sub) {
        if (c.operator === ">" || c.operator === ">=") {
          gt = higherGT(gt, c, options);
        } else if (c.operator === "<" || c.operator === "<=") {
          lt = lowerLT(lt, c, options);
        } else {
          eqSet.add(c.semver);
        }
      }
      if (eqSet.size > 1) {
        return null;
      }
      let gtltComp;
      if (gt && lt) {
        gtltComp = compare(gt.semver, lt.semver, options);
        if (gtltComp > 0) {
          return null;
        } else if (gtltComp === 0 && (gt.operator !== ">=" || lt.operator !== "<=")) {
          return null;
        }
      }
      for (const eq of eqSet) {
        if (gt && !satisfies(eq, String(gt), options)) {
          return null;
        }
        if (lt && !satisfies(eq, String(lt), options)) {
          return null;
        }
        for (const c of dom) {
          if (!satisfies(eq, String(c), options)) {
            return false;
          }
        }
        return true;
      }
      let higher, lower;
      let hasDomLT, hasDomGT;
      let needDomLTPre = lt && !options.includePrerelease && lt.semver.prerelease.length ? lt.semver : false;
      let needDomGTPre = gt && !options.includePrerelease && gt.semver.prerelease.length ? gt.semver : false;
      if (needDomLTPre && needDomLTPre.prerelease.length === 1 && lt.operator === "<" && needDomLTPre.prerelease[0] === 0) {
        needDomLTPre = false;
      }
      for (const c of dom) {
        hasDomGT = hasDomGT || c.operator === ">" || c.operator === ">=";
        hasDomLT = hasDomLT || c.operator === "<" || c.operator === "<=";
        if (gt) {
          if (needDomGTPre) {
            if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomGTPre.major && c.semver.minor === needDomGTPre.minor && c.semver.patch === needDomGTPre.patch) {
              needDomGTPre = false;
            }
          }
          if (c.operator === ">" || c.operator === ">=") {
            higher = higherGT(gt, c, options);
            if (higher === c && higher !== gt) {
              return false;
            }
          } else if (gt.operator === ">=" && !c.test(gt.semver)) {
            return false;
          }
        }
        if (lt) {
          if (needDomLTPre) {
            if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomLTPre.major && c.semver.minor === needDomLTPre.minor && c.semver.patch === needDomLTPre.patch) {
              needDomLTPre = false;
            }
          }
          if (c.operator === "<" || c.operator === "<=") {
            lower = lowerLT(lt, c, options);
            if (lower === c && lower !== lt) {
              return false;
            }
          } else if (lt.operator === "<=" && !c.test(lt.semver)) {
            return false;
          }
        }
        if (!c.operator && (lt || gt) && gtltComp !== 0) {
          return false;
        }
      }
      if (gt && hasDomLT && !lt && gtltComp !== 0) {
        return false;
      }
      if (lt && hasDomGT && !gt && gtltComp !== 0) {
        return false;
      }
      if (needDomGTPre || needDomLTPre) {
        return false;
      }
      return true;
    };
    var higherGT = (a, b, options) => {
      if (!a) {
        return b;
      }
      const comp = compare(a.semver, b.semver, options);
      return comp > 0 ? a : comp < 0 ? b : b.operator === ">" && a.operator === ">=" ? b : a;
    };
    var lowerLT = (a, b, options) => {
      if (!a) {
        return b;
      }
      const comp = compare(a.semver, b.semver, options);
      return comp < 0 ? a : comp > 0 ? b : b.operator === "<" && a.operator === "<=" ? b : a;
    };
    module2.exports = subset;
  }
});

// node_modules/.pnpm/semver@7.8.5/node_modules/semver/index.js
var require_semver2 = __commonJS({
  "node_modules/.pnpm/semver@7.8.5/node_modules/semver/index.js"(exports2, module2) {
    "use strict";
    var internalRe = require_re();
    var constants = require_constants();
    var SemVer = require_semver();
    var identifiers = require_identifiers();
    var parse = require_parse();
    var valid = require_valid();
    var clean = require_clean();
    var inc = require_inc();
    var diff = require_diff();
    var major = require_major();
    var minor = require_minor();
    var patch = require_patch();
    var prerelease = require_prerelease();
    var compare = require_compare();
    var rcompare = require_rcompare();
    var compareLoose = require_compare_loose();
    var compareBuild = require_compare_build();
    var sort = require_sort();
    var rsort = require_rsort();
    var gt = require_gt();
    var lt = require_lt();
    var eq = require_eq();
    var neq = require_neq();
    var gte = require_gte();
    var lte = require_lte();
    var cmp = require_cmp();
    var coerce = require_coerce();
    var truncate = require_truncate();
    var Comparator = require_comparator();
    var Range = require_range();
    var satisfies = require_satisfies();
    var toComparators = require_to_comparators();
    var maxSatisfying = require_max_satisfying();
    var minSatisfying = require_min_satisfying();
    var minVersion = require_min_version();
    var validRange = require_valid2();
    var outside = require_outside();
    var gtr = require_gtr();
    var ltr = require_ltr();
    var intersects = require_intersects();
    var simplifyRange = require_simplify();
    var subset = require_subset();
    module2.exports = {
      parse,
      valid,
      clean,
      inc,
      diff,
      major,
      minor,
      patch,
      prerelease,
      compare,
      rcompare,
      compareLoose,
      compareBuild,
      sort,
      rsort,
      gt,
      lt,
      eq,
      neq,
      gte,
      lte,
      cmp,
      coerce,
      truncate,
      Comparator,
      Range,
      satisfies,
      toComparators,
      maxSatisfying,
      minSatisfying,
      minVersion,
      validRange,
      outside,
      gtr,
      ltr,
      intersects,
      simplifyRange,
      subset,
      SemVer,
      re: internalRe.re,
      src: internalRe.src,
      tokens: internalRe.t,
      SEMVER_SPEC_VERSION: constants.SEMVER_SPEC_VERSION,
      RELEASE_TYPES: constants.RELEASE_TYPES,
      compareIdentifiers: identifiers.compareIdentifiers,
      rcompareIdentifiers: identifiers.rcompareIdentifiers
    };
  }
});

// src/standalone.ts
var standalone_exports = {};
__export(standalone_exports, {
  createToolTelemetry: () => createToolTelemetry
});
module.exports = __toCommonJS(standalone_exports);

// src/cli-telemetry.ts
var import_node_async_hooks = require("node:async_hooks");

// src/invocation-user-agent.ts
var import_semver2 = __toESM(require_semver2());

// src/invocation-context.ts
var import_node_crypto = require("node:crypto");
var import_semver = __toESM(require_semver2());
var UNKNOWN_VALUE = "unknown";
var STABLE_NAME_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
var CALLER_NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
var MAJOR_MINOR_VERSION_PATTERN = /^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$/;
var MAX_NAME_LENGTH = 128;
var MAX_VERSION_LENGTH = 32;
var MAX_SKILL_ID_LENGTH = MAX_NAME_LENGTH + 1 + MAX_VERSION_LENGTH;
function hasNonEmptyValue(env, key) {
  return typeof env[key] === "string" && env[key].trim().length > 0;
}
function hasEnvKey(env, key) {
  return Object.prototype.hasOwnProperty.call(env, key);
}
function hasEnvKeyPrefix(env, prefix) {
  return Object.keys(env).some((key) => key.startsWith(prefix));
}
function hasAnyNonEmptyValue(env, keys) {
  return keys.some((key) => hasNonEmptyValue(env, key));
}
function hasTrimmedValueIgnoreCase(env, key, expected) {
  return env[key]?.trim().toLowerCase() === expected.toLowerCase();
}
function hasTrimmedValueContainingIgnoreCase(env, key, expected) {
  return env[key]?.trim().toLowerCase().includes(expected.toLowerCase()) === true;
}
function hasNonEmptyPrefix(env, prefix) {
  return Object.entries(env).some(
    ([key, value]) => key.startsWith(prefix) && typeof value === "string" && value.trim().length > 0
  );
}
function normalizeStableName(value) {
  if (!value || value.length > MAX_NAME_LENGTH)
    return void 0;
  return STABLE_NAME_PATTERN.test(value) ? value : void 0;
}
function normalizeAiAgentName(value) {
  const trimmedValue = value?.trim();
  if (!trimmedValue || trimmedValue.length > MAX_NAME_LENGTH)
    return void 0;
  return CALLER_NAME_PATTERN.test(trimmedValue) ? trimmedValue : void 0;
}
function normalizeSkillId(value) {
  if (!value || value.length > MAX_SKILL_ID_LENGTH)
    return {};
  const segments = value.split("/");
  if (segments.length > 2)
    return {};
  const name = normalizeStableName(segments[0]);
  if (!name)
    return {};
  const version = segments[1];
  return {
    name,
    version: version && version.length <= MAX_VERSION_LENGTH && (import_semver.default.valid(version) === version || MAJOR_MINOR_VERSION_PATTERN.test(version)) ? version : void 0
  };
}
function normalizeIdeClientName(value) {
  return normalizeStableName(value?.trim());
}
function detectOuterRuntime(env) {
  if (hasNonEmptyPrefix(env, "OPENCLAW_"))
    return "openclaw";
  if (hasNonEmptyPrefix(env, "ARKCLAW_") || hasTrimmedValueContainingIgnoreCase(env, "IDENTITY_NAME", "arkclaw")) {
    return "arkclaw";
  }
  if (hasNonEmptyPrefix(env, "HERMES_"))
    return "hermes";
  if (hasEnvKey(env, "COZE_CLAW_AGENT_ID"))
    return "coze-claw";
  return void 0;
}
function detectInnerAiClient(env) {
  if (hasTrimmedValueIgnoreCase(env, "AI_AGENT", "trae"))
    return "trae";
  const customAiAgent = normalizeAiAgentName(env.AI_AGENT);
  if (customAiAgent)
    return customAiAgent;
  if (hasEnvKeyPrefix(env, "DOUBAO_OFFICE_"))
    return "doubao-office";
  const hasClaudeCode = hasAnyNonEmptyValue(env, [
    "CLAUDECODE",
    "CLAUDE_CODE"
  ]);
  if (hasClaudeCode && hasNonEmptyValue(env, "CLAUDE_CODE_IS_COWORK")) {
    return "claude-cowork";
  }
  if (hasClaudeCode)
    return "claude-code";
  if (hasNonEmptyValue(env, "VELO_ENV"))
    return "velo";
  if (hasNonEmptyPrefix(env, "CODEX_"))
    return "codex";
  if (hasNonEmptyPrefix(env, "CURSOR_"))
    return "cursor";
  if (hasNonEmptyPrefix(env, "TRAE_") || hasNonEmptyValue(env, "COCO_PLUGIN_ROOT") || hasTrimmedValueIgnoreCase(env, "ICUBE_PRODUCT_BRAND_NAME", "trae")) {
    return "trae";
  }
  if (hasNonEmptyValue(env, "GEMINI_CLI"))
    return "gemini-cli";
  if (hasAnyNonEmptyValue(env, ["KIRO_SESSION_ID", "KIRO_AGENT_PATH"])) {
    return "kiro";
  }
  if (hasAnyNonEmptyValue(env, ["OPENCODE", "OPENCODE_CLIENT"])) {
    return "opencode";
  }
  if (hasNonEmptyValue(env, "ANTIGRAVITY_AGENT"))
    return "antigravity";
  if (hasAnyNonEmptyValue(env, [
    "COPILOT_CLI",
    "COPILOT_MODEL",
    "COPILOT_ALLOW_ALL"
  ])) {
    return "github-copilot";
  }
  if (hasNonEmptyValue(env, "CLINE_ACTIVE"))
    return "cline";
  if (hasNonEmptyValue(env, "AMP_CURRENT_THREAD_ID"))
    return "amp";
  if (env.PI_CODING_AGENT === "true")
    return "pi";
  if (hasNonEmptyValue(env, "REPL_ID"))
    return "replit";
  if (hasNonEmptyValue(env, "AUGMENT_AGENT"))
    return "augment";
  if (hasNonEmptyValue(env, "QWEN_CODE"))
    return "qwen-code";
  return hasNonEmptyValue(env, "COPILOT_GITHUB_TOKEN") ? "github-copilot" : void 0;
}
function resolveAiCaller(env) {
  const segments = [detectOuterRuntime(env), detectInnerAiClient(env)].filter(
    (value) => Boolean(value)
  );
  const caller = [...new Set(segments)].join(",");
  if (caller)
    return caller;
  return normalizeStableName(env.IDENTITY_NAME?.trim());
}
function resolveInvocationContext({
  cliName,
  cliVersion,
  env = process.env,
  stdinIsTTY = process.stdin.isTTY === true,
  stdoutIsTTY = process.stdout.isTTY === true
}) {
  const skill = normalizeSkillId(env.VE_SKILL_ID);
  const ideClientName = normalizeIdeClientName(env.IDE_CLIENT_NAME);
  const aiCaller = resolveAiCaller(env);
  let invocationType;
  let callerName = UNKNOWN_VALUE;
  if (skill.name) {
    invocationType = "skill";
    callerName = aiCaller ?? UNKNOWN_VALUE;
  } else if (ideClientName) {
    invocationType = "ide-plugin";
    callerName = ideClientName;
  } else if (aiCaller) {
    invocationType = "direct";
    callerName = aiCaller;
  } else if (stdinIsTTY && stdoutIsTTY) {
    invocationType = "manual";
  } else {
    invocationType = "unknown";
  }
  return Object.freeze({
    cli_name: cliName,
    cli_version: import_semver.default.valid(cliVersion) === cliVersion ? cliVersion : UNKNOWN_VALUE,
    // One immutable Base Context is shared by the completion event and every
    // first-party business request made by this CLI invocation.
    invocation_id: (0, import_node_crypto.randomUUID)(),
    invocation_type: invocationType,
    caller_name: callerName,
    skill_name: skill.name ?? UNKNOWN_VALUE,
    skill_version: skill.version ?? UNKNOWN_VALUE
  });
}

// src/invocation-context-store.ts
var invocationContext;
function initializeInvocationContext(context) {
  invocationContext ??= context;
  return invocationContext;
}
function getInvocationContext() {
  return invocationContext;
}
function initializeInvocation(options) {
  if (invocationContext)
    return invocationContext;
  return initializeInvocationContext(resolveInvocationContext(options));
}

// src/invocation-user-agent.ts
var MAX_USER_AGENT_LENGTH = 512;
var MAX_NAME_LENGTH2 = 128;
var MAX_VERSION_LENGTH2 = 32;
var MAX_CALLER_SEGMENTS = 2;
var PRODUCT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
var STABLE_NAME_PATTERN2 = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
var CALLER_NAME_PATTERN2 = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
var MAJOR_MINOR_VERSION_PATTERN2 = /^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$/;
var UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
var INVOCATION_TYPES = /* @__PURE__ */ new Set([
  "skill",
  "direct",
  "ide-plugin",
  "manual",
  "unknown"
]);
function isValidVersion(value) {
  return typeof value === "string" && value.length <= MAX_VERSION_LENGTH2 && import_semver2.default.valid(value) === value;
}
function isValidSkillVersion(value) {
  return typeof value === "string" && value.length <= MAX_VERSION_LENGTH2 && (import_semver2.default.valid(value) === value || MAJOR_MINOR_VERSION_PATTERN2.test(value));
}
function isValidStableName(value) {
  return typeof value === "string" && value.length <= MAX_NAME_LENGTH2 && STABLE_NAME_PATTERN2.test(value);
}
function isValidCallerName(value) {
  return typeof value === "string" && value.length <= MAX_NAME_LENGTH2 && CALLER_NAME_PATTERN2.test(value);
}
function isValidCallerChain(value) {
  if (typeof value !== "string")
    return false;
  const segments = value.split(",");
  return segments.length <= MAX_CALLER_SEGMENTS && segments.every(isValidCallerName);
}
function fitsUserAgentLimit(value) {
  return Buffer.byteLength(value, "ascii") <= MAX_USER_AGENT_LENGTH;
}
function composeUserAgent(requiredStart, invocationIdToken, callerToken, skillToken) {
  return [
    ...requiredStart,
    ...callerToken ? [callerToken] : [],
    ...skillToken ? [skillToken] : [],
    invocationIdToken
  ].join(" ");
}
function buildInvocationUserAgent(context) {
  if (!context || typeof context.cli_name !== "string" || !PRODUCT_PATTERN.test(context.cli_name) || !isValidVersion(context.cli_version) || typeof context.invocation_id !== "string" || !UUID_PATTERN.test(context.invocation_id) || !INVOCATION_TYPES.has(context.invocation_type)) {
    return void 0;
  }
  const requiredStart = [
    `${context.cli_name}/${context.cli_version}`,
    `invocation/${context.invocation_type}`
  ];
  const invocationIdToken = `invocation-id/${context.invocation_id}`;
  let callerToken;
  if (context.caller_name !== UNKNOWN_VALUE && isValidCallerChain(context.caller_name)) {
    callerToken = `caller/${context.caller_name.split(",").join("+")}`;
  }
  let skillToken;
  let skillTokenWithoutVersion;
  if (context.skill_name !== UNKNOWN_VALUE && isValidStableName(context.skill_name)) {
    skillTokenWithoutVersion = `skill/${context.skill_name}`;
    skillToken = skillTokenWithoutVersion;
    if (context.skill_version !== UNKNOWN_VALUE && isValidSkillVersion(context.skill_version)) {
      skillToken += `#${context.skill_version}`;
    }
  }
  let userAgent = composeUserAgent(
    requiredStart,
    invocationIdToken,
    callerToken,
    skillToken
  );
  if (fitsUserAgentLimit(userAgent))
    return userAgent;
  if (skillToken && skillToken !== skillTokenWithoutVersion) {
    skillToken = skillTokenWithoutVersion;
    userAgent = composeUserAgent(
      requiredStart,
      invocationIdToken,
      callerToken,
      skillToken
    );
    if (fitsUserAgentLimit(userAgent))
      return userAgent;
  }
  callerToken = void 0;
  userAgent = composeUserAgent(
    requiredStart,
    invocationIdToken,
    callerToken,
    skillToken
  );
  if (fitsUserAgentLimit(userAgent))
    return userAgent;
  skillToken = void 0;
  userAgent = composeUserAgent(
    requiredStart,
    invocationIdToken,
    callerToken,
    skillToken
  );
  return fitsUserAgentLimit(userAgent) ? userAgent : void 0;
}
function getInvocationUserAgent() {
  return buildInvocationUserAgent(getInvocationContext());
}

// src/safe-fields.ts
var MAX_KEY_LENGTH = 64;
var MAX_SCALAR_LENGTH = 255;
var MAX_RECORD_LENGTH = 1024;
var MAX_MEMBERS = 300;
var MASKED_VALUE = "*";
var SAFE_KEY_PATTERN = /^[A-Za-z][A-Za-z0-9_]*$/;
var BUILT_IN_SENSITIVE_KEY_PARTS = [
  "accountid",
  "accesskey",
  "authorization",
  "cookie",
  "credential",
  "password",
  "passwd",
  "privatekey",
  "secret",
  "token"
];
function codePointLength(value) {
  return Array.from(value).length;
}
function truncateCodePoints(value, maxLength) {
  const points = Array.from(value);
  if (points.length <= maxLength)
    return value;
  return `${points.slice(0, Math.max(0, maxLength - 1)).join("")}\u2026`;
}
function canonicalSensitiveKey(value) {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}
function isSensitiveKey(key, configured) {
  const canonical = canonicalSensitiveKey(key);
  return configured.has(canonical) || BUILT_IN_SENSITIVE_KEY_PARTS.some((part) => canonical.includes(part));
}
function normalizeScalar(value) {
  if (typeof value === "string") {
    const cleaned = value.replace(/[\u0000-\u001f\u007f]/g, " ");
    return truncateCodePoints(cleaned, MAX_SCALAR_LENGTH);
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : void 0;
  }
  return typeof value === "boolean" ? value : void 0;
}
function normalizeValue(value) {
  if (!Array.isArray(value))
    return normalizeScalar(value);
  const result = [];
  for (const item of value) {
    const normalized = normalizeScalar(item);
    if (normalized !== void 0)
      result.push(normalized);
  }
  return result.length > 0 ? result : void 0;
}
function normalizeRecord(input, configuredRedactions, maxMembers) {
  const values = {};
  let members = 0;
  for (const key of Object.keys(input ?? {}).sort()) {
    if (codePointLength(key) > MAX_KEY_LENGTH || !SAFE_KEY_PATTERN.test(key)) {
      continue;
    }
    const rawValue = input?.[key];
    if (rawValue == null)
      continue;
    const value = isSensitiveKey(key, configuredRedactions) ? MASKED_VALUE : normalizeValue(rawValue);
    if (value === void 0)
      continue;
    const valueMembers = Array.isArray(value) ? value.length + 1 : 1;
    if (members + valueMembers > maxMembers) {
      if (!Array.isArray(value))
        continue;
      const remainingElements = Math.max(0, maxMembers - members - 1);
      if (remainingElements === 0)
        continue;
      values[key] = value.slice(0, remainingElements);
      members += remainingElements + 1;
      continue;
    }
    values[key] = value;
    members += valueMembers;
  }
  return { values, members };
}
function serializeRecord(values) {
  const accepted = {};
  for (const key of Object.keys(values).sort()) {
    const value = values[key];
    let candidateValue = value;
    let candidate = JSON.stringify({ ...accepted, [key]: candidateValue });
    if (codePointLength(candidate) > MAX_RECORD_LENGTH && Array.isArray(value)) {
      const prefix = [];
      for (const item of value) {
        const next = [...prefix, item];
        candidate = JSON.stringify({ ...accepted, [key]: next });
        if (codePointLength(candidate) > MAX_RECORD_LENGTH)
          break;
        prefix.push(item);
      }
      if (prefix.length === 0)
        continue;
      candidateValue = prefix;
      candidate = JSON.stringify({ ...accepted, [key]: candidateValue });
    }
    if (codePointLength(candidate) <= MAX_RECORD_LENGTH) {
      accepted[key] = candidateValue;
    }
  }
  return Object.keys(accepted).length > 0 ? JSON.stringify(accepted) : void 0;
}
function serializeSafeFields(params, extra, sensitiveParamNames) {
  const sensitiveParams = new Set(
    sensitiveParamNames.map(canonicalSensitiveKey).filter(Boolean)
  );
  const normalizedParams = normalizeRecord(
    params,
    sensitiveParams,
    MAX_MEMBERS
  );
  const normalizedExtra = normalizeRecord(
    extra,
    // The caller-supplied list describes command params only. Extra keeps the
    // built-in secret safeguards but is not matched against that list.
    /* @__PURE__ */ new Set(),
    // Tea counts params and extra together, so extra receives only the member
    // budget not already consumed by automatically collected options.
    Math.max(0, MAX_MEMBERS - normalizedParams.members)
  );
  return {
    params: serializeRecord(normalizedParams.values),
    extra: serializeRecord(normalizedExtra.values)
  };
}
function limitErrorMessage(error) {
  const raw = error instanceof Error ? error.message : "";
  return truncateCodePoints(raw || "Unknown error", 500);
}

// src/tea-reporter.ts
var import_node_crypto2 = require("node:crypto");
var CN_TEA_ENDPOINT = "https://mcs.zijieapi.com/list";
var SG_TEA_ENDPOINT = "https://sgali-mcs.byteoversea.com/list";
var TEA_EVENT_NAME = "cli_command_executed";
var CN_PRODUCTION_APP_ID = 1045459;
var SG_PRODUCTION_APP_ID = 1047954;
var TEST_APP_ID = 1046114;
var REQUEST_TIMEOUT_MS = 1e3;
var MAX_ENVELOPE_BYTES = 1024 * 1024;
function createTeaReporter(debug = false, region = "cn") {
  const appId = debug ? TEST_APP_ID : region === "sg" ? SG_PRODUCTION_APP_ID : CN_PRODUCTION_APP_ID;
  const endpoint = region === "sg" ? SG_TEA_ENDPOINT : CN_TEA_ENDPOINT;
  const userUniqueId = (0, import_node_crypto2.randomUUID)();
  return {
    userUniqueId,
    async report(event) {
      const now = Date.now();
      const params = Object.fromEntries(
        Object.entries(event).filter(([, value]) => value != null)
      );
      const payload = [
        // Preserve Tea CLI's exact /list wire shape: params is intentionally
        // a JSON string nested inside the outer JSON envelope.
        {
          events: [
            {
              event: TEA_EVENT_NAME,
              params: JSON.stringify(params),
              local_time_ms: now
            }
          ],
          user: { user_unique_id: userUniqueId },
          local_time: Math.floor(now / 1e3),
          header: { app_id: appId },
          verbose: 1
        }
      ];
      const body = JSON.stringify(payload);
      if (Buffer.byteLength(body, "utf8") > MAX_ENVELOPE_BYTES) {
        return;
      }
      try {
        await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json; charset=UTF-8" },
          body,
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
        });
      } catch {
      }
    }
  };
}
var teaReporterContract = Object.freeze({
  cnEndpoint: CN_TEA_ENDPOINT,
  sgEndpoint: SG_TEA_ENDPOINT,
  eventName: TEA_EVENT_NAME,
  productionAppId: CN_PRODUCTION_APP_ID,
  sgProductionAppId: SG_PRODUCTION_APP_ID,
  testAppId: TEST_APP_ID,
  requestTimeoutMs: REQUEST_TIMEOUT_MS
});

// src/commander.ts
function commandOwners(actionCommand) {
  const owners = [];
  let command = actionCommand;
  while (command) {
    owners.push(command);
    command = command.parent;
  }
  return owners;
}
function canonicalCommand(actionCommand) {
  const names = [];
  let command = actionCommand;
  while (command) {
    names.push(command.name());
    command = command.parent;
  }
  const path3 = names.reverse();
  return path3.length > 0 ? path3.join(".") : void 0;
}
function explicitOption(owner, option) {
  const key = option.attributeName();
  return owner.getOptionValueSource(key) === "cli" ? { key, value: owner.getOptionValue(key) } : void 0;
}
function resolveOutputFormat(owners) {
  let hasOutputOption = false;
  let explicitJson;
  let explicitFormat;
  for (const owner of owners) {
    for (const option of owner.options) {
      const key = option.attributeName();
      if (key !== "json" && key !== "format")
        continue;
      hasOutputOption = true;
      if (owner.getOptionValueSource(key) !== "cli")
        continue;
      if (key === "json")
        explicitJson = owner.getOptionValue(key);
      if (key === "format")
        explicitFormat = owner.getOptionValue(key);
    }
  }
  if (explicitJson === true)
    return "json";
  if (typeof explicitFormat === "string") {
    const normalized = explicitFormat.trim().toLowerCase();
    return normalized === "json" || normalized === "human" ? normalized : void 0;
  }
  return hasOutputOption ? "human" : void 0;
}
function commandMetadata(actionCommand) {
  const command = canonicalCommand(actionCommand);
  if (!command)
    return void 0;
  const owners = commandOwners(actionCommand);
  const params = {};
  for (const owner of owners) {
    for (const option of owner.options) {
      const explicit = explicitOption(owner, option);
      if (!explicit)
        continue;
      if (explicit.key === "json" || explicit.key === "format")
        continue;
      params[explicit.key] = explicit.value;
    }
  }
  return {
    command,
    params: Object.keys(params).length > 0 ? params : void 0,
    outputFormat: resolveOutputFormat(owners)
  };
}
async function runCommand(controller, program, argv) {
  let actionStarted = false;
  program.hook("preAction", (_thisCommand, actionCommand) => {
    const metadata = commandMetadata(actionCommand);
    if (!metadata)
      return;
    controller.beginCommand(metadata);
    actionStarted = true;
  });
  try {
    const result = await program.parseAsync([...argv]);
    if (actionStarted)
      controller.finishCommandSuccess();
    return result;
  } catch (error) {
    if (actionStarted)
      await controller.finishCommandFailure(error);
    throw error;
  }
}

// src/script.ts
var import_node_path = __toESM(require("node:path"));
function canonicalOptionName(value) {
  const parts = value.split(/[-_]+/).filter(Boolean);
  if (parts.length === 0 || !/^[A-Za-z]/.test(parts[0]))
    return void 0;
  const key = parts.map(
    (part, index) => index === 0 ? `${part[0].toLowerCase()}${part.slice(1)}` : `${part[0].toUpperCase()}${part.slice(1)}`
  ).join("");
  return /^[A-Za-z][A-Za-z0-9_]*$/.test(key) ? key : void 0;
}
function addParam(params, key, value) {
  const current = params[key];
  if (current === void 0) {
    params[key] = value;
  } else if (Array.isArray(current)) {
    current.push(value);
  } else {
    params[key] = [current, value];
  }
}
function lastValue(value) {
  return Array.isArray(value) ? value[value.length - 1] : value;
}
function resolveOutputFormat2(params) {
  const json = lastValue(params.json);
  const format = lastValue(params.format);
  delete params.json;
  delete params.format;
  if (json === true)
    return "json";
  if (typeof format === "string") {
    const normalized = format.trim().toLowerCase();
    return normalized === "json" || normalized === "human" ? normalized : void 0;
  }
  return json === false ? "human" : void 0;
}
function parseScriptArguments(argv) {
  const params = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--")
      break;
    if (!token.startsWith("--") || token.length === 2)
      continue;
    const equalsIndex = token.indexOf("=");
    const rawOption = token.slice(2, equalsIndex < 0 ? void 0 : equalsIndex);
    if (equalsIndex < 0 && rawOption.startsWith("no-") && rawOption.length > 3) {
      const key2 = canonicalOptionName(rawOption.slice(3));
      if (key2)
        addParam(params, key2, false);
      continue;
    }
    const key = canonicalOptionName(rawOption);
    if (!key)
      continue;
    if (equalsIndex >= 0) {
      addParam(params, key, token.slice(equalsIndex + 1));
      continue;
    }
    const next = argv[index + 1];
    if (next !== void 0 && next !== "--" && !next.startsWith("--")) {
      addParam(params, key, next);
      index += 1;
    } else {
      addParam(params, key, true);
    }
  }
  const outputFormat = resolveOutputFormat2(params);
  return {
    params: Object.keys(params).length > 0 ? params : void 0,
    outputFormat
  };
}
function inferScriptCommand(argv) {
  const entry = argv[1]?.replace(/\\/g, "/") ?? "script";
  const basename = import_node_path.default.posix.basename(entry);
  const extension = import_node_path.default.posix.extname(basename);
  const stem = extension ? basename.slice(0, -extension.length) : basename;
  const normalized = stem.trim().toLowerCase().replace(/[^a-z0-9.-]+/g, "-").replace(/^-+|-+$/g, "");
  return normalized || "script";
}
function hasNonZeroExitCode(exitCode) {
  if (exitCode === void 0 || exitCode === null)
    return false;
  return Number(exitCode) !== 0;
}
async function runScriptCommand(controller, handler, options = {}) {
  const argv = options.argv ?? process.argv;
  const parsed = parseScriptArguments(argv);
  controller.beginCommand({
    command: options.command ?? inferScriptCommand(argv),
    ...parsed
  });
  try {
    const result = await handler();
    if (hasNonZeroExitCode(process.exitCode)) {
      await controller.finishCommandFailure(
        new Error(`Script completed with exit code ${process.exitCode}`)
      );
    } else {
      controller.finishCommandSuccess();
    }
    return result;
  } catch (error) {
    await controller.finishCommandFailure(error);
    throw error;
  }
}

// src/device-id.ts
var import_node_crypto3 = require("node:crypto");
var import_node_fs = require("node:fs");
var import_node_os = __toESM(require("node:os"));
var import_node_path2 = __toESM(require("node:path"));
var DEVICE_ID_FILE_NAME = "device-id";
var DIRECTORY_SEGMENT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
var UUID_PATTERN2 = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
var MAX_DEVICE_ID_FILE_BYTES = 128;
function nonEmpty(value) {
  const normalized = value?.trim();
  return normalized || void 0;
}
function normalizeDeviceIdDirectory(value) {
  if (typeof value !== "string")
    return void 0;
  const normalized = value.trim();
  return DIRECTORY_SEGMENT_PATTERN.test(normalized) ? normalized : void 0;
}
function resolveDeviceIdDirectory({
  cliName,
  env = process.env,
  homeDirectory = import_node_os.default.homedir(),
  platform = process.platform
}) {
  const directoryName = normalizeDeviceIdDirectory(cliName);
  if (!directoryName)
    return void 0;
  const home = nonEmpty(homeDirectory);
  if (platform === "win32") {
    const base2 = nonEmpty(env.LOCALAPPDATA) ?? nonEmpty(env.APPDATA);
    if (base2)
      return import_node_path2.default.join(base2, directoryName);
    return home ? import_node_path2.default.join(home, "AppData", "Local", directoryName) : void 0;
  }
  if (platform === "darwin") {
    return home ? import_node_path2.default.join(home, "Library", "Application Support", directoryName) : void 0;
  }
  const xdgConfigHome = nonEmpty(env.XDG_CONFIG_HOME);
  const base = xdgConfigHome && import_node_path2.default.isAbsolute(xdgConfigHome) ? xdgConfigHome : home ? import_node_path2.default.join(home, ".config") : void 0;
  return base ? import_node_path2.default.join(base, directoryName) : void 0;
}
function readDeviceId(filePath) {
  try {
    const stat = (0, import_node_fs.lstatSync)(filePath);
    if (!stat.isFile() || stat.size > MAX_DEVICE_ID_FILE_BYTES)
      return void 0;
    const value = (0, import_node_fs.readFileSync)(filePath, "utf8").trim().toLowerCase();
    return UUID_PATTERN2.test(value) ? value : void 0;
  } catch {
    return void 0;
  }
}
function getOrCreateDeviceId(configDirectory) {
  if (!configDirectory)
    return void 0;
  const filePath = import_node_path2.default.join(configDirectory, DEVICE_ID_FILE_NAME);
  const existing = readDeviceId(filePath);
  if (existing)
    return existing;
  try {
    (0, import_node_fs.mkdirSync)(configDirectory, { recursive: true, mode: 448 });
    const candidate = (0, import_node_crypto3.randomUUID)();
    const temporaryPath = import_node_path2.default.join(
      configDirectory,
      `.${DEVICE_ID_FILE_NAME}.${process.pid}.${(0, import_node_crypto3.randomUUID)()}.tmp`
    );
    try {
      (0, import_node_fs.writeFileSync)(temporaryPath, `${candidate}
`, {
        encoding: "utf8",
        flag: "wx",
        mode: 384
      });
      (0, import_node_fs.linkSync)(temporaryPath, filePath);
      return candidate;
    } finally {
      try {
        (0, import_node_fs.unlinkSync)(temporaryPath);
      } catch {
      }
    }
  } catch {
    return readDeviceId(filePath);
  }
}
var deviceIdContract = Object.freeze({
  fileName: DEVICE_ID_FILE_NAME
});

// src/cli-telemetry.ts
var COMMAND_PATTERN = /^[a-z0-9]+(?:[.-][a-z0-9]+)*$/;
var MAX_COMMAND_LENGTH = 128;
var MAX_ACCOUNT_ID_LENGTH = 128;
function commandResult(error) {
  return error instanceof Error && error.name === "AbortError" ? "cancelled" : "failure";
}
function isValidCommand(command) {
  return command.length <= MAX_COMMAND_LENGTH && COMMAND_PATTERN.test(command);
}
var ToolTelemetryController = class {
  constructor(config) {
    this.config = config;
    // AsyncLocalStorage lets addExtra() find the command that owns the current
    // async chain without requiring business code to pass command IDs around.
    this.storage = new import_node_async_hooks.AsyncLocalStorage();
    this.runnerStarted = false;
    this.invocationFinished = false;
    initializeInvocation({
      cliName: config.cliName,
      cliVersion: config.cliVersion
    });
    this.sensitiveParamNames = [...config.sensitiveParamNames ?? []];
  }
  run(program, argv) {
    return runCommand(this, program, argv);
  }
  runScript(handler, options = {}) {
    if (options.accountId !== void 0) {
      this.setAccountId(options.accountId);
    }
    return runScriptCommand(this, handler, options);
  }
  getUserAgent() {
    return getInvocationUserAgent();
  }
  addExtra(extra) {
    if (this.config.disabled === true)
      return;
    const command = this.storage.getStore();
    if (!command || command.finished) {
      return;
    }
    Object.assign(command.extra, extra);
  }
  setAccountId(accountId) {
    if (this.invocationFinished || typeof accountId !== "string")
      return;
    const normalized = accountId.trim();
    if (normalized.length === 0 || Array.from(normalized).length > MAX_ACCOUNT_ID_LENGTH || /[\u0000-\u001f\u007f]/.test(normalized)) {
      return;
    }
    this.accountId = normalized;
  }
  beginCommand(metadata) {
    const command = this.createCommand(metadata);
    this.activeCommand = command;
    this.storage.enterWith(command);
  }
  finishCommandSuccess() {
    const command = this.activeCommand;
    if (!command)
      return;
    void this.finishCommand(command, "success");
  }
  async finishCommandFailure(error) {
    const command = this.activeCommand;
    if (!command)
      return;
    await this.finishCommand(command, commandResult(error), error);
  }
  createCommand(metadata) {
    if (this.runnerStarted) {
      throw new Error("Telemetry instances can run only one top-level command");
    }
    this.runnerStarted = true;
    return {
      metadata,
      startedAt: performance.now(),
      extra: {},
      finished: false
    };
  }
  async finishCommand(command, result, error) {
    if (command.finished)
      return;
    command.finished = true;
    this.invocationFinished = true;
    if (this.activeCommand === command)
      this.activeCommand = void 0;
    if (this.config.disabled === true || !isValidCommand(command.metadata.command)) {
      return;
    }
    try {
      const context = getInvocationContext();
      if (!context)
        return;
      const safeFields = serializeSafeFields(
        command.metadata.params,
        command.extra,
        this.sensitiveParamNames
      );
      const deviceIdDirectory = resolveDeviceIdDirectory({
        cliName: this.config.deviceIdDirectory ?? this.config.cliName
      });
      const event = {
        cli_name: context.cli_name,
        cli_version: context.cli_version,
        invocation_id: context.invocation_id,
        device_id: deviceIdDirectory ? getOrCreateDeviceId(deviceIdDirectory) : void 0,
        command: command.metadata.command,
        params: safeFields.params,
        result,
        error_message: result === "failure" ? limitErrorMessage(error) : void 0,
        duration_ms: Math.max(
          0,
          Math.round(performance.now() - command.startedAt)
        ),
        output_format: command.metadata.outputFormat,
        node_major: process.versions.node.split(".")[0],
        os: process.platform,
        arch: process.arch,
        interaction_mode: command.metadata.interactionMode ?? (process.stdin.isTTY === true && process.stdout.isTTY === true ? "interactive" : "non-interactive"),
        invocation_type: context.invocation_type,
        caller_name: context.caller_name === UNKNOWN_VALUE ? void 0 : context.caller_name,
        skill_name: context.skill_name === UNKNOWN_VALUE ? void 0 : context.skill_name,
        skill_version: context.skill_version === UNKNOWN_VALUE ? void 0 : context.skill_version,
        account_id: this.accountId,
        extra: safeFields.extra
      };
      await this.getReporter().report(event);
    } catch {
    }
  }
  getReporter() {
    this.reporter ??= createTeaReporter(
      this.config.debug === true,
      this.config.region
    );
    return this.reporter;
  }
};
function createToolTelemetry(config) {
  return new ToolTelemetryController({
    cliName: config.toolName,
    cliVersion: config.toolVersion,
    deviceIdDirectory: config.deviceIdDirectory,
    region: config.region,
    disabled: config.disabled,
    debug: config.debug,
    sensitiveParamNames: config.sensitiveParamNames
  });
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  createToolTelemetry
});