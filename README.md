# Oregon Trail (Web + Terminal)

This repo contains:
- `web/`: browser version of Oregon Trail v2 (static HTML/CSS/JS)
- `oregon_trail_v2.py`: terminal version
- `OregonTrailIOS/`: iOS prototype

## Run locally (web)

```bash
cd web
python3 -m http.server 8000
```

Open <http://localhost:8000>.

## Deploy to GitHub Pages

This repo includes a workflow at:
- `.github/workflows/deploy-pages.yml`

It deploys the `web/` directory to GitHub Pages on every push to `main`.

### One-time GitHub settings

1. Push this repo to GitHub.
2. In GitHub, open `Settings -> Pages`.
3. Under `Build and deployment`, set `Source` to `GitHub Actions`.
4. Push to `main` (or run the workflow manually from `Actions`).

After deployment, your site will be available at your GitHub Pages URL.
