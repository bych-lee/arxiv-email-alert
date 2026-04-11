## What it does

- searches arXiv by:
  - title / abstract keywords
  - recent submission date range
- sorts results in reverse chronological order
- sends one email digest with multiple papers
- runs automatically with GitHub Actions

<p align="center">
  <img src="fig_what.png" alt="What it does figure" width="700"><br>
  <em>Figure 1. End image.</em>
</p>

## How it works

<p align="center">
  <img src="fig_how.png" alt="How it works fig" width="700"><br>
  <em>Figure 2. Sequence diagram.</em>
</p>

## How to use

### 1. Fork this repository

### 2. Add repository variable

Go to:

`Settings -> Secrets and variables -> Actions -> Variables`

Create this variable:

- `CONFIG_YAML`

Example:

```yaml
query:
  include_keywords:
    - "gaussian"
    - "quantum"

  exclude_keywords: []

  categories: []

search:
  days_back: 7
  max_results: 10
```

### 3. Add repository secrets

Go to:

`Settings -> Secrets and variables -> Actions -> Secrets`

Create these secrets:

- `SENDER_EMAIL`
- `RECEIVER_EMAIL`
- `GMAIL_APP_PASSWORD`
