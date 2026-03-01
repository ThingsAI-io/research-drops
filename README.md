# ResearchDrops

Automated daily research digest — fetches papers from RSS feeds, filters out based on topics of interest.

A GitHub Actions workflow runs every weekday: a Python script pulls entries from arXiv and Microsoft Research, then a [Copilot CLI](https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line) agent applies two skills — **research-filter** and **research-digest** — to separate signal from noise and publish a digest as a GitHub Discussion.

---

## How It Works

```
RSS Feeds → fetch.py → /tmp/research-monitor/feeds/ → Copilot Agent → output.json → GitHub Discussion
```

1. **Fetch** — `fetch.py` reads `conf/feeds.yml` and downloads all RSS/Atom feeds. Entries are written as individual Markdown files (YAML frontmatter + body) with a `titles.jsonl` index per feed.

2. **Filter** — The Copilot CLI agent loads `skills/research-filter/SKILL.md` and applies a two-phase filter: broad title scan, then strict abstract review using positive/negative signals from `conf/topics.yml`. Default: exclude.

3. **Format** — Surviving entries are tiered (High / Medium / Low) and formatted into a Markdown digest using `skills/research-digest/SKILL.md` and its FOR_EACH template.

4. **Publish** — The agent writes `output.json`. The workflow creates a GitHub Discussion with the formatted digest.

---

## Setup

### Prerequisites

- A GitHub repository (public or private)
- GitHub Copilot access (for the Copilot CLI agent step)

### 1. Create a GitHub Personal Access Token (Copilot)

The Copilot CLI agent authenticates via the `COPILOT_GITHUB_TOKEN` environment variable. Follow the [Copilot CLI authentication docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli#authenticating-with-environment-variables):

1. Go to **[Fine-grained personal access tokens](https://github.com/settings/personal-access-tokens/new)**
2. Under **Permissions**, click **Add permissions** and select **Copilot Requests**
3. Click **Generate token**
4. Copy the token

### 2. Create a Discussions token (optional)

The workflow publishes digests as GitHub Discussions. This requires a separate token with Discussions write access. If not set, the workflow runs normally but skips publishing.

1. Go to **[Fine-grained personal access tokens](https://github.com/settings/personal-access-tokens/new)**
2. Set **Repository access** to your ResearchDrops repo
3. Under **Repository permissions**, set **Discussions → Read and write**
4. Click **Generate token**
5. Copy the token

### 3. Add repository secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value | Required |
|---|---|---|
| `COPILOT_GITHUB_TOKEN` | The Copilot token from step 1 | Yes |
| `DISCUSSIONS_WRITE_TOKEN` | The Discussions token from step 2 | No |

### 4. Enable Discussions

1. Go to **Settings → General → Features**
2. Check **Discussions**
3. Make sure a **"General"** category exists (it's created by default)

### 5. Run it

The workflow runs automatically every weekday at 6 AM PST (arXiv doesn't update on weekends). To trigger it manually:

1. Go to **Actions → Daily Research Monitor → Run workflow**
2. Optionally override the model (default: `claude-sonnet-4.6`)
3. Check the job summary for the digest, or look in **Discussions**

---

## Customizing

### Adding feeds

Edit `conf/feeds.yml`. Each entry has:

```yaml
- id: my-feed
  name: "Human-readable name"
  url: "https://example.com/rss"
  description: "What this feed covers"
  format: rss          # rss or atom
  update_frequency: daily
```

### Changing topics

Edit `conf/topics.yml`. Each topic has:

```yaml
- id: my-topic
  name: "Topic Name"
  description: "What this topic cares about"
  keywords:
    - relevant-keyword
  positive_signals:
    - "Framings that make a paper worth surfacing"
  negative_signals:
    - "Look-alike traps to exclude"
```

The skills read these at runtime — no code changes needed.
