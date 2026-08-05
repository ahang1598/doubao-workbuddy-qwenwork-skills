# Authentication

## Choosing Authentication

Choose the authentication model that matches where the site will run.

- For sites used inside an OpenAI workspace, prefer the platform-provided
  authenticated-user headers when the site only needs to know the current OpenAI
  user.
- For routes that should only be visible after ChatGPT sign-in, use
  dispatch-owned SIWC from the default starter instead of adding app-owned auth.
- For sites that need public sign-in or external identity providers, do not
  scaffold an app-owned auth stack from a starter. Confirm the current platform
  auth path before implementation.
- Do not add a full auth stack when the workspace-authenticated user header is
  sufficient for the product.

Signed-in visitors receive both `oai-authenticated-user-id` and `oai-authenticated-user-email`. Private Sites require every visitor to sign in; public Sites may also have anonymous visitors, for whom neither header is present.

The user ID is stable for the same user on the same Site and different across Sites. Email and name are intended for display or contact purposes.

For SIWC-authenticated workspace sites, the dispatcher may also forward the
current user's non-empty SIWC `name` claim as
`oai-authenticated-user-full-name`. That value is percent-encoded UTF-8 and is
sent with an `oai-authenticated-user-full-name-encoding` header set to
`percent-encoded-utf-8`. Treat the full name as optional, decode it only when
the encoding header matches, and do not depend on name-split headers.

## Adding Authentication

Use this flow when the site needs sign-in-gated or identity-aware behavior.

1. Decide which auth model the product needs:
   - use dispatch-owned SIWC for browser routes that should only be visible
     after ChatGPT sign-in. This works whether the route needs the forwarded
     user information or only needs an authenticated viewer.
   - do not add SIWC just because a site is public or published. Add it only
     when the requested product has a concrete sign-in-gated surface.
   - use the workspace-authenticated user header directly only when no route
     needs to initiate sign-in.
   - keep authorization decisions in server-side code for every site.
   - do not add app-owned public sign-in or external OAuth from a starter;
     confirm the current platform auth path before implementation.
2. For dispatch-owned SIWC routes:
   - treat SIWC as authentication, not workspace authorization. A successful
     sign-in identifies a ChatGPT user but does not prove workspace membership.
     Use the Sites hosting platform's access policy controls for workspace-wide
     restrictions, or enforce an explicit server-side membership or allowlist
     check when a route must exclude non-members.
   - import the ready-to-use helpers from
     `templates/vinext-starter/app/chatgpt-auth.ts`.
   - use `getChatGPTUser()` for optional signed-in UI, such as rendering a
     "Sign in with ChatGPT" button for anonymous users and account details for
     signed-in users.
   - call `requireChatGPTUser(returnTo)` only in server-rendered browser page
     flows that should redirect to `/signin-with-chatgpt`.
   - do not implement app routes for `/signin-with-chatgpt`,
     `/signout-with-chatgpt`, or `/callback`; dispatch owns those paths.
   - keep `returnTo` to same-origin relative paths such as `/profile` or
     `/notes/123?tab=activity`.
   - mark protected pages `export const dynamic = "force-dynamic"` because
     they depend on per-request identity headers.
   - when a protected page needs path or query parameters in `returnTo`, compute
     `returnTo` in the page component and call `requireChatGPTUser` from a
     nested async server component. This avoids Vinext page-probe redirects
     before the real search params are available.
   - use `/signout-with-chatgpt?return_to=...` for browser sign-out links.
   - for API routes or server actions that require identity, check
     `getChatGPTUser()` server-side and reject missing identity instead of
     trusting client-side affordances.
3. For workspace-authenticated sites:
   - read `oai-authenticated-user-id` when a feature needs a stable user key.
   - read `oai-authenticated-user-email` for display or contact purposes.
   - read and decode `oai-authenticated-user-full-name` only when a display name
     improves the product, and always fall back to email because the full name
     header may be absent.
4. Add sign-in-gated product flows only where the site actually needs protected
   visibility or identity-aware behavior.

Common SIWC fits include pages or endpoints that should not be visible to
anonymous visitors, account/profile pages, user-specific dashboards,
saved/user-owned records, write actions that should be attributed to the current
ChatGPT user, and explicit "sign in to continue" flows. Do not use SIWC for
public landing pages, static content, read-only public data, or device-local UI
preferences.
