# marketing

Public marketing + sign-in site for verifi-dental. **Contains no PHI**, so this is
the piece that belongs on Vercel. Static HTML — no build step.

## Deploy to Vercel

1. In Vercel, **New Project → import `andrewgalli411-sudo/verifi-dental`**.
2. **Root Directory:** `marketing`. **Framework Preset:** Other. No build command; output is the folder itself.
3. Deploy. Add your custom domain (e.g. `www.verifidental.com`).

## Wire the "Sign in" button to the app

The app (which handles PHI) lives on AWS, not here. Set the sign-in target by
editing the one line in `index.html`:

```js
var APP_URL = "https://app.verifidental.com/login";
```

Until the AWS app is deployed, leave it as-is (the button stays inert).

## Why this is split from the app

Standard Vercel does not sign a HIPAA BAA (Enterprise only). This marketing site
has no patient data so it's fine here; the admin console, report views, API, and
database run in the BAA-covered AWS environment (see `../infra`).
