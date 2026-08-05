# Tab Capability: browserAuth
Collects user-provided credentials for a validated login form and fills them into this tab without returning the values to the caller. Include `submit` only when the page requires an explicit submission action. Omit it for forms that auto-submit during credential entry.

## Secure Browser Authentication

Read this guidance before beginning sign-in. `browserAuth.request(...)` is the
secure sign-in handoff: use it when the user must choose a sign-in method or
provide credentials. It can offer the available sign-in methods and collect
user-provided credentials directly in a secure ChatGPT form. Browser-client
validates, fills, and submits those values without returning them to you.

### Non-Negotiable Rules

- Never ask the user to paste passwords, one-time codes, auth codes, security
  answers, or other secret sign-in values into chat.
- Never enter, read, inspect, log, print, or reconstruct credential values with
  Playwright, vision, tool output, or any other model-visible surface.
- Never emit a legacy `<browser_auth_request>` block or use a legacy form-fill
  path.
- CAPTCHAs are outside `browserAuth`. Never use this capability for one; follow
  the CAPTCHA guidance in the main Browser skill.
- Never include secrets, cookies, full URLs, query strings, JavaScript,
  DOM snippets, or other page content in a browser-auth request. Browser-client
  supplies the request message and derives credential-field labels from the
  verified form; do not provide either. Sign-in option labels must describe only
  methods actually visible on the current page.
- If `browserAuth` returns `unavailable`, stop the login attempt. Politely say
  that this browser cannot help the user log in to the site; do not explain
  why. Include a safe verified public link where they can sign in in their own
  browser, if one exists, and offer help with anything that does not require
  signing in. For this refusal, do not add login steps unless the user
  explicitly asks how to sign in themselves. Never tell the user to sign in and
  come back; signing in in their browser does not sign in this browser. Do not
  fall back to chat or direct credential entry.
- If login blocks only part of a broader task, keep and return any useful public
  work already completed.

### Authentication Lifecycle

1. Before the first authentication interaction, retain the target site's origin
   or a canonical signed-in URL for later verification, for example with
   `var targetOrigin = new URL(await tab.url()).origin`.
2. Inspect the visible page. List only methods the
   page actually offers, such as phone or SMS OTP, email or Gmail OTP, Google
   sign-in, username and password, passkey, or device approval. If exactly one
   method is available, tell the user which method the website offers and
   proceed without asking them to choose. If multiple methods are available,
   call `browserAuth.request(...)` with a separate, clearly labeled option for
   each visible method and wait for the user to choose. Include `options` only
   when the user must choose between two or more visible sign-in methods. Set
   each option's `label` to just the short visible method, such as "Google",
   "mobile number", or "email and password". The secure sign-in UI formats these
   methods consistently for the user. Use the same secure request to collect any
   already-visible credential fields required by the selected method. Never ask
   for credentials through chat or another tool.
   Describe a saved-account method with the visible account name, email, or
   provider when the page identifies it; never describe it only as "Password for
   saved account." Do not infer account details that are not visible or rank or
   choose a method for the user.
3. Follow the selected method through the visible page. Use
   `browserAuth.request(...)` for sign-in method choices and whenever the
   chosen method requires user-provided credentials.
   Repeat the choice step at each new authentication or recovery decision
   point. If the selected method fails, report the website-surfaced error and
   ask which visible alternative to use. Do not switch methods without the
   user's choice.
4. After every authentication transition, call
   `nodeRepl.write(await tab.dom_cua.get_visible_dom())` to inspect the rendered
   interactive structure across nested and cross-origin frames. Check for a
   CAPTCHA, error, next authentication step, or success. If the inspection
   appears incomplete, use a frame-aware inspection and interaction path; do not
   continue, assume success, or dismiss an overlay.
5. When authentication appears complete, verify the target site with fresh
   visible evidence. Treat a closed auth popup, blank page, spinner, missing tab,
   stale tab, or timeout as an unknown result, not a failed login and not proof
   of success.
6. If the target page fails to load after authentication, immediately create a
   new agent tab and navigate it to the retained target origin or canonical
   signed-in URL:

   ```js
   var verificationTab = await browser.tabs.new();
   await verificationTab.goto(targetOrigin);
   nodeRepl.write(await verificationTab.dom_cua.get_visible_dom());
   ```

   Inspect that fresh page. Authentication may already have succeeded and its
   cookies may be available even when the original tab or popup is stuck. Make
   this fresh-tab check the first recovery action; do not poll the stale tab,
   enumerate tabs, or reconnect first.
7. Report success only when the fresh target-domain page shows a positive
   signed-in signal. If the fresh page shows a login or verification screen,
   continue the authentication workflow from that page. If browser access still
   fails, report the state as unknown; never ask the user to check or operate
   this browser.

### Prepare A Credential Request

1. Inspect the live sign-in form with the cheapest targeted browser-side check
   that identifies the currently visible credential fields and submit behavior,
   such as visible-DOM inspection or narrowly scoped locator checks. Inspect
   what has already rendered; do not wait for page-load completion or repeatedly
   request full DOM snapshots.
2. Include only credential inputs that are visible and enabled on the current
   page. Issue exactly one request at a time for the current sign-in page. For
   multi-step sign-in, inspect the new page and make a separate request after
   each navigation.
3. Choose stable selectors that each resolve to exactly one field. Prefer
   semantic attributes such as `name`, `type`, and `autocomplete`. Avoid
   random-looking generated IDs when a stable semantic selector is available.
   Do not infer attributes that were not inspected. If the sign-in form is
   inside an iframe, create the selector with `tab.playwright.frameLocator(...)`
   and pass the resulting locator object to `browserAuth.request(...)`.
4. Set each field's `type` to its actual non-empty HTML input type. For
   example, a phone input may be `tel`, and a one-time code input is commonly
   `text` with `autocomplete: "one-time-code"`.
   Pass the inspected `autocomplete` value when the page exposes one.
5. Use only the current canonical origin, with scheme, host, and port but no
   path, query, or fragment. Set `expires_at` to a short-lived ISO timestamp no
   more than five minutes in the future.
6. Omit `submit` when filling the credential fields causes the form to
   auto-submit. Otherwise, use `click` only for a stable selector that resolves
   to exactly one visible enabled submit control distinct from the credential
   fields. If Enter on the final credential field submits the form, including
   when the submit button is disabled until input is present, use `press_enter`
   with that exact field selector instead of a broad or generic button selector.

If a visible textbox may be inside a component or shadow root, inspect its
`id`, `name`, and `type` attributes through a browser-side role locator, then
verify the resulting exact CSS selector with browser-side Playwright locator
count, visibility, and enabled checks. An accessible name reported by a role
locator is not proof that an `aria-label` attribute exists. Never infer an
`aria-label` selector; use one only when the inspected attribute is actually
present. Do not treat `document.querySelectorAll(...)` returning zero as
authoritative for a shadow-root textbox.

Use only the existing browser-side surface for sign-in inspection. Do not run
shell commands, standalone or local Playwright, package installs, browser
runtime installs, or reconnect attempts to inspect the site. Use scoped
temporary variables or fresh names for browser-side checks; do not redeclare
persistent top-level `const` or `let` bindings.

Browser-client is the source of truth for whether the request is safe to show
to the user. After a targeted inspection, call `browserAuth.request(...)` with
the best candidate selectors without repeatedly re-verifying them or stopping
merely because model-side proof is incomplete. If it returns `locator_invalid`,
re-inspect and correct the request instead of guessing or treating model-side
checks as authoritative.

If the targeted inspection itself fails, make at most one additional
browser-side tool call: a lighter targeted check against already rendered
state. If it still cannot identify candidate selectors for every required
visible enabled field, stop immediately and report the blockage. Do not issue
further browser-side navigation, DOM, locator, reconnect, shell, or
runtime-install calls for that sign-in attempt.

### Request Credentials

Get the advertised capability and issue a request containing only non-secret
metadata and selectors:

```js
var browserAuth = await tab.capabilities.get("browserAuth");
var browserAuthUrl = await tab.url();
if (!browserAuthUrl) {
  throw new Error("Cannot determine the current tab URL for browser auth.");
}

var usernameField = tab.playwright.locator('input[name="email"]');
var passwordField = tab.playwright.locator('input[type="password"]');
var submitButton = tab.playwright.locator('button[type="submit"]');

var browserAuthResult = await browserAuth.request({
  origin: new URL(browserAuthUrl).origin,
  expires_at: new Date(Date.now() + 2 * 60_000).toISOString(),
  fields: [
    {
      id: "username",
      type: "email",
      autocomplete: "username",
      required: true,
      selector: usernameField,
    },
    {
      id: "password",
      type: "password",
      autocomplete: "current-password",
      required: true,
      selector: passwordField,
    },
  ],
  submit: {
    selector: submitButton,
    action: "click",
  },
});
nodeRepl.write(browserAuthResult);
```

The example selectors are illustrative. Always inspect the current page and use
selectors that match its actual fields. For an iframe form, build the field
locator with `tab.playwright.frameLocator("iframe#auth").locator(...)` and pass
that locator object as `selector`. Omit `submit` when the form auto-submits
during credential entry.

### Request A Sign-In Method

When a sign-in page exposes multiple methods and a credential field is already
visible, offer the methods and securely collect the selected method's credentials
in one request:

```js
var browserAuth = await tab.capabilities.get("browserAuth");
var browserAuthUrl = await tab.url();
var emailField = tab.playwright.locator('input[name="email"]');
var googleButton = tab.playwright.locator('button[data-provider="google"]');
var emailSubmit = tab.playwright.locator('button[type="submit"]');

var browserAuthResult = await browserAuth.request({
  origin: new URL(browserAuthUrl).origin,
  expires_at: new Date(Date.now() + 2 * 60_000).toISOString(),
  fields: [
    {
      id: "email",
      type: "email",
      autocomplete: "username",
      required: true,
      selector: emailField,
    },
  ],
  options: [
    {
      id: "google",
      label: "Google",
      selector: googleButton,
    },
    {
      id: "email",
      label: "email",
      field_ids: ["email"],
    },
  ],
  submit: { selector: emailSubmit, action: "click" },
});
nodeRepl.write(browserAuthResult);
```

If the page exposes two or more sign-in method buttons and no credential
fields, use `fields: []` and give each option the locator for its visible
button. Browser-client clicks the selected button and returns its non-secret
`selected_option` identifier. If the choice reveals a new credential form,
inspect it and make a separate secure request. Option selectors, like
credential selectors, must resolve to exactly one visible, enabled element in
the same page and frame.

### Handle The Credential Request Result

- `submitted` means the selected sign-in button was clicked or credential entry
  completed and any configured submit action ran; it does not prove that
  sign-in succeeded. When options were offered, `selected_option` identifies
  the user's non-secret choice. Resume the Authentication Lifecycle at its
  transition-inspection step.
- `locator_invalid`, `page_changed`, or `origin_changed` means the saved request
  is stale or unsafe. If authentication still blocks the task, re-inspect the
  current page and issue a corrected fresh request.
- `expired` means the request timed out. Re-inspect before issuing a fresh
  request.
- `declined` with `reason: "user_took_over"` means the user took manual control
  of the cloud browser; their actions and final authentication state are
  unknown. Inspect the final page state with fresh visible DOM, then continue the
  Authentication Lifecycle from its transition-inspection step. Do not inspect
  or act on any intermediate state from the manual sign-in.
- `declined` without that reason or `cancelled` means the user chose not to
  continue. Respect that choice and do not retry unless the user asks.
- `unavailable` must never trigger a fallback to chat or direct credential
  entry. Follow the refusal guidance above.
- `submission_failed` must never trigger a fallback to chat or direct credential
  entry. Inspect the current page for a non-secret website error and report it
  only if the website visibly shows it. Otherwise, follow the refusal guidance
  above.
- The result never contains credential values. Never try to print or
  reconstruct them.

## API Reference
```ts
const capability = await tab.capabilities.get("browserAuth");

type BrowserAuthRequestOptions = Omit<BrowserAuthHandoffOptions, "fields" | "options" | "submit"> & { fields: Array<BrowserAuthRequestField>; options?: Array<BrowserAuthRequestOption>; submit?: BrowserAuthRequestSubmit };

type BrowserAuthHandoffOptions = z.infer<typeof BrowserAuthHandoffOptionsSchema>;

type BrowserAuthRequestField = Omit<BrowserAuthField, "selector"> & { selector: BrowserAuthSelector };

type BrowserAuthRequestOption = Omit<BrowserAuthOption, "selector"> & { selector?: BrowserAuthSelector };

type BrowserAuthRequestSubmit = Omit<BrowserAuthSubmit, "selector"> & { selector: BrowserAuthSelector };

type BrowserAuthField = z.infer<typeof BrowserAuthFieldSchema>;

type BrowserAuthSelector = string | PlaywrightLocator;

type BrowserAuthOption = z.infer<typeof BrowserAuthOptionSchema>;

type BrowserAuthSubmit = z.infer<typeof BrowserAuthSubmitSchema>;

interface BrowserAuthTabCapability {
  request(options: BrowserAuthRequestOptions): Promise<{ reason?: "user_took_over"; selected_option?: string; status: "submitted" | "declined" | "cancelled" | "unavailable" | "expired" | "origin_changed" | "page_changed" | "locator_invalid" | "submission_failed" }>; // Request user-provided credentials for a validated login form. When `submit` is omitted, a `submitted` result means the credential fields were filled successfully; inspect the resulting page to confirm that the form auto-submitted and sign-in advanced.
}
```
