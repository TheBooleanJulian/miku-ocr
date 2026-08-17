# Integrating FreeLLMAPI (reference notes)

Working notes from wiring [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) into a
Telegram bot deployed on Zeabur, written up to reuse in other repos/projects. Not
FreeLLMAPI's own docs — this is "what we actually did and what broke."

## What it is

An OpenAI-compatible proxy that aggregates *free-tier* quota across ~29 LLM providers
(Google, Groq, Mistral, etc.) behind a single `/v1` endpoint. Key facts that shape how
you integrate it:

- **You still need your own provider API keys.** It doesn't grant free access to
  anything by itself — you add keys for whichever free-tier providers you want (e.g. a
  free Google AI Studio Gemini key) through its dashboard, and it routes/fails-over
  across them.
- **It does not proxy Anthropic/Claude.** If you want Claude specifically, this gives
  you nothing — Claude isn't a free-tier provider on it.
- **Not meant for production**, per the maintainers: "for personal experimentation and
  learning." Free tiers have no SLA.
- **Single-user, must not be exposed to the internet.** Binds to `127.0.0.1` in its own
  docker-compose by default. The dashboard manages your real provider keys with
  comparatively light auth.
- MIT licensed, actively maintained, healthy star count — reasonable trust signal
  despite being a solo-maintainer project.

## Deployment shape (Zeabur, but the pattern generalizes)

1. **Fork the repo** to your own GitHub account/org. Zeabur (and most PaaS git-deploy
   flows) only build from repos already connected to your account — there's usually no
   "deploy this arbitrary public Docker image/repo URL" CLI path. Grant the platform's
   GitHub App access to the new fork if it's scoped to "selected repositories."
2. **Deploy as its own service** in the same project as the app that will call it, so
   they share private networking. On Zeabur: `zeabur service deploy --repo-id <id>
   --branch-name main --template GIT --interactive=false`.
3. **Set `ENCRYPTION_KEY` before first boot.** The Dockerfile sets `NODE_ENV=production`,
   and in production the app hard-requires an explicit 64-char-hex `ENCRYPTION_KEY` (used
   for AES-256-GCM encryption of stored provider keys) or it exits immediately on boot.
   Outside production it silently auto-generates and persists a dev key — which is why
   this only bites you in a "real" deploy. Generate one with:
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   ```
   Set it as an env var on the service, *then* deploy/redeploy.
4. **Do not bind a public domain.** Leave it on the platform's private network only.
   On Zeabur this is automatic — services in the same project get an internal hostname
   (`<service>.zeabur.internal:8080`, also auto-injected into sibling services' env vars
   as `<SERVICE_NAME>_HOST`) without creating any domain.

## One-time dashboard setup (adding a provider key)

The dashboard needs a browser visit once, to create the admin account and add a
provider key. Since the service has no public domain by design, this is the one
deliberate, temporary exception:

1. Bind a short-lived, hard-to-guess generated domain to the service
   (`zeabur domain create ... --generated=true`).
2. Pull the **first-run setup code** from the container's runtime logs (it's printed on
   boot, only relevant when the dashboard is accessed from a browser that isn't "the
   machine running FreeLLMAPI" — which a remote PaaS deploy always is).
3. Visit the temp URL, create the account using that code, go to **Keys**, add a
   provider key (Gemini's free tier is the easy one — vision-capable, free, 2-minute
   signup at aistudio.google.com/apikey), copy the unified `freellmapi-...` bearer
   token from the header.
4. **Delete the temporary domain immediately after.** Don't leave it bound.

A CLI `port-forward` toggle exists (`zeabur service port-forward --enable`) but in
practice didn't produce an actual local tunnel for an HTTP-type service — it only
toggles a mode flag, no forwarded local port materializes. The temp-domain approach was
what actually worked.

## Calling it from application code

It's OpenAI-compatible, so point any OpenAI SDK at it instead of api.openai.com:

```python
from openai import OpenAI

client = OpenAI(
    api_key=FREELLMAPI_API_KEY,          # the unified "freellmapi-..." token
    base_url=FREELLMAPI_BASE_URL,        # e.g. http://<service>.zeabur.internal:8080/v1
)

response = client.chat.completions.create(
    model="auto",   # lets FreeLLMAPI's fallback chain pick a model; pin a specific
                     # model id instead if you need deterministic behavior
    max_tokens=4096,
    messages=[
        {"role": "system", "content": "..."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "..."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{b64_image}"},
                },
            ],
        },
    ],
)
text = response.choices[0].message.content
```

Env vars worth standardizing across repos:

| Variable | Required | Notes |
|---|---|---|
| `FREELLMAPI_API_KEY` | yes | unified bearer token from the dashboard |
| `FREELLMAPI_BASE_URL` | no | defaults to `http://localhost:3001/v1` for local dev; set to the internal service URL in prod |
| `FREELLMAPI_MODEL` | no | `auto`, or pin a specific model id |

## Gotcha: pin a recent `openai` SDK version

`openai==1.54.0` (and other older 1.5x pins) crashes on `OpenAI(...)` construction
against newer `httpx` releases:

```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

`httpx>=0.28` removed the `proxies` kwarg that older `openai` SDK versions still pass
through to `httpx.Client`. Pin `openai>=1.63` (or otherwise recent) to avoid this —
it's an SDK/httpx compatibility issue, unrelated to FreeLLMAPI itself, but it'll surface
immediately on first deploy since the client is normally constructed at import time.

## Security summary / why each choice was made

- Fork instead of running someone else's repo directly → your own audit trail, your
  own control over what gets deployed.
- `ENCRYPTION_KEY` set explicitly → provider keys stored encrypted at rest, key isn't
  silently auto-generated (and thus not silently lost / not protecting anything).
- No public domain, private networking only → respects the maintainer's own
  "must not be exposed to the internet" warning; the app-to-proxy hop never leaves the
  platform's internal network.
- Temporary domain for setup only, deleted immediately after → the one unavoidable
  exception, minimized to a single short-lived, randomly-named window.
