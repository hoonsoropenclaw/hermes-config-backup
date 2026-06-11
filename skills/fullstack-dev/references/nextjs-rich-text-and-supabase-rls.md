# Next.js + Tiptap Rich Text + Supabase (RLS) — Pitfalls

**Use this when**: building a Next.js app with user-edited rich text (Tiptap / ProseMirror) and Supabase as the primary store, where users create content in their own browser and the server reads it back.

These are the failures that show up in production builds but pass type-checks. Load this reference when the build is green but the runtime does the wrong thing silently.

---

## 1. Never use `Buffer` in a `'use client'` component

**Symptom**: clicking a button in the browser does nothing. No console error. No network request. The `onClick` handler simply stops mid-execution.

**Root cause**:
```ts
// components/FilterPanel.tsx — 'use client' at the top
function encodeGroups(groups) {
  return Buffer.from(JSON.stringify({ groups })).toString('base64url');
  //     ^^^^^^ Buffer is a Node global. In the browser it's undefined.
  //     Accessing it throws → handler aborts → no router.push, no fetch, nothing.
}
```

`Buffer` exists in Node and Edge runtime but not in the browser bundle. The component compiles, the JSX renders, but the moment a click reaches that function, it throws and React silently swallows the throw (because the handler isn't wrapped in an error boundary that surfaces it).

**Fix — use the Web API**:
```ts
function encodeGroups(groups) {
  if (typeof window !== 'undefined' && typeof btoa === 'function') {
    const b64 = btoa(unescape(encodeURIComponent(JSON.stringify({ groups }))));
    return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  return Buffer.from(JSON.stringify({ groups })).toString('base64url');
}
```

**Detection**:
- Click handler feels dead → open browser devtools → Sources → "Pause on exceptions" → click again → it'll pause at `Buffer is not defined`.
- For the silent-swallow case, add `try { ... } catch (e) { console.error(e) }` around suspicious handlers, or throw into a `<ErrorBoundary>`.

**Heuristic**: any code in a `'use client'` file or that might be imported by one — `Buffer`, `process.env` (only `NEXT_PUBLIC_*` is safe), `fs`, `path`, `crypto` (Node), `__dirname`. Treat them as Node-only.

---

## 2. Tiptap 3 changed the import shape — `extension-color` is gone

**Symptom**: build fails with
> Module has no default export
> Did you mean FontSize?

**Root cause**: Tiptap v3 merged the standalone extension packages (`@tiptap/extension-color`, `@tiptap/extension-font-size`, `@tiptap/extension-font-family`) into `@tiptap/extension-text-style` as **named subpath exports**. Old tutorials and code generators still emit:
```ts
import Color from '@tiptap/extension-color';        // ❌ exists in v2, gone in v3
import FontSize from '@tiptap/extension-font-size'; // ❌ never existed as standalone
```

**Fix — correct v3 import**:
```ts
import { TextStyle, Color, FontSize } from '@tiptap/extension-text-style';
//                                                            ^^^^^^^^^^ one package, three named exports
```

Check installed version before importing:
```bash
cat node_modules/@tiptap/extension-text-style/package.json | grep version
# If < 3.0.0, the legacy imports still work.
```

**Bonus — the v3 chain commands** (FontSize, Color, etc.):
```ts
editor.chain().focus().setFontSize('20px').run();
editor.chain().focus().unsetFontSize().run();   // remove, not unsetMark('textStyle')
```

Using `setMark('textStyle', { fontSize: '20px' })` works but doesn't go through the FontSize extension's chain methods, so programmatic `unsetFontSize` won't find it.

---

## 3. sanitize-html for `dangerouslySetInnerHTML` of user content

**Symptom**: user pastes a Word document into a Tiptap editor, content includes inline styles, anchor tags, and `<o:p>` Microsoft tags. The page renders, but external users can now inject `<script>` because the content is round-tripped via `dangerouslySetInnerHTML`.

**Pattern**:
1. Save Tiptap's `editor.getHTML()` directly (Tiptap only emits its own allowed tags, so on the *write* side you're already safe).
2. On the *read* side (when displaying someone else's content in a server component), run through `sanitize-html` before passing to `dangerouslySetInnerHTML`. Defense in depth — Tiptap output is well-formed, but future schema changes, manual DB edits, or direct API calls shouldn't be able to escalate.

**Minimal allowlist**:
```ts
import sanitize from 'sanitize-html';

const ALLOWED = ['p', 'br', 'strong', 'em', 'u', 's', 'span', 'a', 'ul', 'ol', 'li'];

export function sanitizeHtml(dirty: string) {
  return sanitize(dirty, {
    allowedTags: ALLOWED,
    allowedAttributes: {
      a: ['href', 'target', 'rel', 'class'],
      span: ['style'],
      p: ['style'],
    },
    allowedStyles: {
      '*': {
        'color': [/^#[0-9a-fA-F]{3,8}$/],
        'font-size': [/^\d+(?:\.\d+)?(?:px|em|rem|%)$/],
        'font-weight': [/^(?:bold|normal|\d+)$/],
        'text-decoration': [/^(?:underline|line-through|none)$/],
      },
    },
    allowedSchemes: ['http', 'https', 'mailto', 'tel'],
    transformTags: {
      a: (_tag, attribs) => ({
        tagName: 'a',
        attribs: { ...attribs, target: '_blank', rel: 'noopener noreferrer' },
      }),
    },
  });
}
```

**Don't** rely on Tiptap's output being "safe" because it's structured — that's coupling your security model to a library version. Run sanitizer unconditionally.

Install both:
```bash
npm install sanitize-html
npm install --save-dev @types/sanitize-html
```

---

## 4. Supabase RLS for the "user manages own org's content" pattern

**Use case**: every announcement/tag is owned by a department; public visitors can read all of them, but only authenticated members of a department can create new tags or post announcements on behalf of their own department.

**Don't** rely on the Vercel/Next.js API layer to enforce this. The right boundary is the database, because:
- The anon key is intentionally exposed to the browser
- Direct API access (bypassing your Next.js) wouldn't be caught
- Auditors and security reviews look at the DB

**Pattern — two-key architecture**:
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — used in API routes and (if you ever query directly from the browser) the client. RLS-enforced.
- `SUPABASE_SERVICE_ROLE_KEY` — used in API routes that need to write on behalf of the user (e.g., creating a user, inserting a record using the user's identity but not their session). Bypasses RLS. **Never** `NEXT_PUBLIC_`.

In Vercel:
- `NEXT_PUBLIC_*` keys get all 3 targets (production / preview / development)
- Service-role keys: encrypted + all 3 targets, never `NEXT_PUBLIC_`

**Minimal RLS policy set**:
```sql
-- departments, tags, announcements: public read
CREATE POLICY "ann_read_public" ON announcements FOR SELECT USING (deleted_at IS NULL);
CREATE POLICY "tags_read_public" ON tags      FOR SELECT USING (is_active = TRUE);

-- users: NO select policy for anon → anon literally cannot read user rows
-- (only the server with service_role can)

-- writes: no policy → only service_role (server) can write
```

That gives you: public read for everyone, write only through your server-side API routes, which authenticate the user via your own auth (JWT) and then call the Supabase server client with service_role.

**For "only the publisher's department can edit their own announcements"**, add explicit INSERT/UPDATE policies with a USING clause that compares `publisher_dept = current_setting('app.current_dept')` — but this requires `SET LOCAL app.current_dept = ...` in the same transaction, which is its own pattern. For a school-bulletin-scale app with a small admin team, server-side checks (`if (a.publisher_dept !== me.dept) return 403`) in the API route are simpler and equally safe, because the API route already authenticates the user.

---

## 5. Lazy import for SDKs whose constructor validates env at load time

**Symptom**: serverless function 500s because the SDK (e.g. `@vercel/kv`) throws inside its module top-level code when `KV_REST_API_URL` is missing or points to a deleted resource.

**Pattern**:
```ts
let sdkPromise: Promise<SdkLike | null> | null = null;

export const HAS_SDK = !!(process.env.SDK_URL && process.env.SDK_TOKEN);

async function getSdk(): Promise<SdkLike | null> {
  if (!HAS_SDK) return null;
  if (!sdkPromise) {
    sdkPromise = import('sdk-name')
      .then(m => m.default as SdkLike)
      .catch(() => null);
  }
  return sdkPromise;
}

export async function sdkGet(key: string) {
  const sdk = await getSdk();
  if (!sdk) return null;
  return sdk.get(key);
}
```

Why this helps:
- Top-level `import { kv } from '@vercel/kv'` runs at module load. If the SDK constructor probes env or network on load, you're 500'd before any of your code runs.
- Lazy `await import(...)` only fires when a function actually needs the SDK. If your app boots in "no storage" mode, the SDK never instantiates.

This is also the correct pattern for optional features (e.g. `HAS_BLOB`, `HAS_SENTRY_DSN`) — feature-detect at runtime, not at module load.

---

## Quick diagnostic checklist when "build is green but prod is broken"

| Symptom | Likely cause | See |
|---|---|---|
| Button click does nothing, no console error | `Buffer`/Node API in client code | §1 |
| "Module has no default export" in Tiptap | Tiptap 3 subpath import shape | §2 |
| User-injected HTML in DB causes XSS | No `sanitize-html` on read | §3 |
| Service_role accidentally exposed | `NEXT_PUBLIC_` prefix on secret | §4 |
| Serverless 500s at startup | SDK loads env at module init | §5 |
