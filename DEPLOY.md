# Hosted demo checklist

Deploy from this repository on Streamlit Community Cloud. Saved answers are the default, so the demo runs with no API key. `requirements.txt` pins `streamlit==1.66.1` and `anthropic==2.4.0`, the versions that start the app locally.

## Secrets

1. Open the app in the Streamlit Community Cloud dashboard.
2. Open Settings, then Secrets.
3. For the saved-answer demo, leave secrets empty.
4. For a Live AI rehearsal, add the key as TOML and save:

```toml
ANTHROPIC_API_KEY = "the key"
```

5. The key stays in the hosting secrets. Do not commit it.
6. Reboot the app so it reads the new secret.

Live AI reads that secret first, then `ANTHROPIC_API_KEY` in the environment. With no key, the top strip says Saved AI answers. With a key, turn Live AI on from Settings in the sidebar. The strip then says Live AI, and a question with no saved answer calls the model.

## Spend limit

Live calls stop at three caps:

- 20 calls in one demo database
- 20 calls in one Explore visit
- 300 calls per day on the server

The daily count is kept in `/tmp/harbor-knowledge-live-cap.json`. When a cap is reached, the app uses a saved answer when one exists and shows "Live call limit reached. A saved answer is used when one exists."

Rehearse on saved answers. Turn Live AI on only to show a question that has no saved answer. A reboot clears `/tmp` and starts the daily count over.

## Reboot

1. Open the app in the Streamlit Community Cloud dashboard.
2. Open the app menu (the three dots) and choose Reboot.
3. Wait until the app shows step 0, Today's problem, and the chip says Saved AI answers.

Reboot the morning of the demo if a rehearsal used up the live-call cap, or if the app is showing an error.

## If the app is asleep

Community Cloud sleeps an idle app. The first open wakes it, and that wake takes longer than a later refresh.

1. Open the hosted link several minutes before the demo.
2. Wait until step 0 is on screen and the sidebar lists the story. Leave that tab open.
3. If the page stays on the Streamlit loading screen, reboot from the dashboard and open the link again.
4. If the link still will not load when the call starts, play the backup recording.

## Web app on Render

The web app is a second way to open the same demo. Render runs one service. That service is the API, and it also serves the website when a front-end build is present. The Streamlit app in the sections above stays available as the fallback for the Friday presentation.

Saved answers work with no key. Leave the key empty unless you are rehearsing a question that has no saved answer.

### Create the service

1. Sign in to [Render](https://render.com).
2. Choose New, then Blueprint, and connect this GitHub repository. Render reads `render.yaml` and creates a free web service named `harbor-knowledge`.
3. If Blueprint is not what you see, choose New, then Web Service, connect the same repository, and set the runtime to Docker. Leave the plan on Free. The Dockerfile in the repository is the build.
4. Wait until the first deploy is live. The service URL is on the Render dashboard.

### Set the key

1. Open the service in Render.
2. Open Environment.
3. Add `ANTHROPIC_API_KEY` only if you want Live AI. Paste the key into the value field and save. Render keeps it as a secret. Do not put the key in the repository, in a chat, or in a screenshot.
4. For the saved-answer demo, leave that variable empty.
5. Render redeploys when you save the variable. Wait until the deploy is live.

### Set a spend limit

The service in `render.yaml` is on the Free plan. A free web service sleeps when nobody is using it. It does not bill for that sleep.

If someone later changes the plan to a paid instance, Render can charge the account. Before the presentation week, open Billing in the Render dashboard and set a monthly spend limit. Keep this service on Free.

The app also stops live model calls on its own:

- 20 calls in one demo database
- 20 calls in one Explore visit
- 300 calls per day on the server

When a cap is reached, a saved answer is used when one exists.

### Wake a sleeping free instance

A free Render service sleeps after a stretch with no visitors. The first open wakes it, and that wake is slower than a later refresh. Do this before anyone is waiting on the call.

1. Open the service URL several minutes before the presentation.
2. Wait until a page is on screen. Leave that tab open.
3. If the tab stays on a Render sleep or loading page, wait a minute and refresh once.
4. If it still will not load when the call starts, use the Streamlit app from the top of this document. Open that hosted link, wait for step 0, and present from there. The backup recording is the last fallback if Streamlit will not load either.
