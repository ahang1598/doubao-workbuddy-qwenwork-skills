// Upload-local signer. Parity-tested against the existing CLI signer.
import crypto from "node:crypto";

function sha256Hex(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

function hmac(key, data) {
  return crypto.createHmac("sha256", key).update(data).digest();
}

function toShortDate(date) {
  const yyyy = String(date.getUTCFullYear());
  const mm = String(date.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(date.getUTCDate()).padStart(2, "0");
  return `${yyyy}${mm}${dd}`;
}

function toXDate(date) {
  const shortDate = toShortDate(date);
  const HH = String(date.getUTCHours()).padStart(2, "0");
  const MM = String(date.getUTCMinutes()).padStart(2, "0");
  const SS = String(date.getUTCSeconds()).padStart(2, "0");
  return `${shortDate}T${HH}${MM}${SS}Z`;
}

function encodeRFC3986(value) {
  return encodeURIComponent(String(value)).replace(/[!*'()]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
}

function canonicalizeQuery(searchParams) {
  const pairs = [];
  for (const [k, v] of searchParams.entries()) {
    pairs.push([k, v]);
  }
  pairs.sort((a, b) => {
    if (a[0] < b[0]) return -1;
    if (a[0] > b[0]) return 1;
    if (a[1] < b[1]) return -1;
    if (a[1] > b[1]) return 1;
    return 0;
  });
  return pairs.map(([k, v]) => `${encodeRFC3986(k)}=${encodeRFC3986(v)}`).join("&");
}

/**
 * Volcengine API signer for HMAC-SHA256 (similar to AWS v4).
 *
 * @param {object} opts
 * @param {'GET'|'POST'|'PUT'|'DELETE'} opts.method
 * @param {string} opts.url - full url including query
 * @param {Record<string,string>} [opts.headers]
 * @param {string} [opts.body]
 * @param {string} opts.accessKeyId
 * @param {string} opts.secretAccessKey
 * @param {string} [opts.sessionToken]
 * @param {string} [opts.region]
 * @param {string} [opts.service]
 * @param {Date} [opts.date] - for testing
 */
export function signVolcRequest(opts) {
  const {
    method,
    url,
    headers = {},
    body = "",
    accessKeyId,
    secretAccessKey,
    sessionToken,
    region = "cn-north-1",
    service = "livesaas",
    date = new Date(),
  } = opts || {};

  if (!url) {
    throw new Error("url is required");
  }

  const u = new URL(url);
  const host = u.host;
  const pathname = u.pathname || "/";

  const shortDate = toShortDate(date);
  const xDate = toXDate(date);

  const payloadHash = sha256Hex(body || "");
  const canonicalQuery = canonicalizeQuery(u.searchParams);

  const canonicalHeaders = {
    "content-type": (headers["Content-Type"] || headers["content-type"] || "application/json").toLowerCase(),
    host,
    "x-content-sha256": payloadHash,
    "x-date": xDate,
  };

  for (const [k, v] of Object.entries(headers)) {
    canonicalHeaders[String(k).toLowerCase()] = String(v);
  }
  if (sessionToken) {
    canonicalHeaders["x-security-token"] = String(sessionToken);
  }

  const signedHeaderKeys = Object.keys(canonicalHeaders).sort();
  const signedHeaders = signedHeaderKeys.join(";");
  const canonicalHeaderString = signedHeaderKeys.map((k) => `${k}:${canonicalHeaders[k].trim()}`).join("\n") + "\n";

  const canonicalRequest = [method, pathname, canonicalQuery, canonicalHeaderString, signedHeaders, payloadHash].join("\n");

  const credentialScope = `${shortDate}/${region}/${service}/request`;
  const stringToSign = ["HMAC-SHA256", xDate, credentialScope, sha256Hex(canonicalRequest)].join("\n");

  const kDate = hmac(secretAccessKey, shortDate);
  const kRegion = hmac(kDate, region);
  const kService = hmac(kRegion, service);
  const kSigning = hmac(kService, "request");
  const signature = crypto.createHmac("sha256", kSigning).update(stringToSign).digest("hex");

  const authorization = `HMAC-SHA256 Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;

  const out = {};
  for (const [k, v] of Object.entries(headers)) {
    const key = String(k);
    const lower = key.toLowerCase();
    if (
      lower === "authorization" ||
      lower === "content-type" ||
      lower === "host" ||
      lower === "x-date" ||
      lower === "x-expires" ||
      lower === "x-content-sha256" ||
      lower === "x-security-token"
    ) {
      continue;
    }
    out[key] = String(v);
  }
  Object.assign(out, {
    Authorization: authorization,
    "X-Date": xDate,
    "X-Expires": "900",
    "X-Content-Sha256": payloadHash,
    "Content-Type": canonicalHeaders["content-type"],
    Host: host,
  });
  if (sessionToken) {
    out["X-Security-Token"] = String(sessionToken);
  }
  return out;
}
