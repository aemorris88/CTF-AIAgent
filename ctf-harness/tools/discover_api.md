# Discovering your platform's API (2 minutes)

Your site is a single-page app, so the challenges and login are served by a JSON
API behind the scenes. This recipe captures the exact calls so you can fill in
`config.yaml -> platform:`. You only do this once.

## Steps

1. Open your CTF site in Chrome (or any browser).
2. Open **DevTools** (`F12` or `Cmd+Opt+I`) and click the **Network** tab.
3. Check **Preserve log**, and set the filter to **Fetch/XHR**.
4. **Log in** on the site normally. Watch the Network panel.
5. Click around to the **challenges / dashboard** view so the list loads.
6. (Optional) **Submit any flag** on one challenge, even a wrong one.

## What to copy out

For each of the three calls below, click the request in the Network panel and
read the **Headers** and **Response** tabs.

### 1. Login  ->  `platform.auth`
- Request URL path  ............  `auth.login_path`
- Request payload field names ..  `auth.username_field`, `auth.password_field`
- In the Response, where is the token? ..  `auth.token_json_path`
  (e.g. response `{"token": "ey..."}` -> `token`;  `{"data":{"jwt":"..."}}` -> `data.jwt`)
- On later requests, which header carries it? ..  `auth.auth_header` + `auth.auth_header_prefix`
  (look at a *subsequent* request's Request Headers, e.g. `Authorization: Bearer ey...`)
- If you see **no** token and instead a `Set-Cookie` on login, set `auth.mode: cookie`.

### 2. Challenge list  ->  `platform.challenges`
- Request URL path  ............  `challenges.list_path`
- In the Response, look at one challenge object and map its keys into
  `challenges.field_map` (left = our name, right = the key your API uses):
  `id, name, category, description, value, files, connection_info`.
  If a field doesn't exist, leave the mapping pointing at a key that isn't there —
  it just comes back empty, which is fine.
- If attachment URLs are relative (e.g. `/files/ch1.zip`), set `challenges.files_base_url`.

### 3. Flag submission  ->  `platform.submit`
- Request URL path  ............  `submit.submit_path`
- Payload field names  ........  `submit.challenge_id_field`, `submit.flag_field`
- In the Response, what marks success? ..  `submit.success_json_path` + `submit.success_value`
  (e.g. `{"status":"correct"}` -> path `status`, value `correct`)
- If there's no submit endpoint at all, set `submit.mode: regex` and the harness
  will instead count a run solved when the agent prints a string matching
  `flag.regex`.

## Can't find it?
Paste the three requests (URL + payload + a sample response) back to me and I'll
fill the config in for you. Redact your real password and any auth token first.
