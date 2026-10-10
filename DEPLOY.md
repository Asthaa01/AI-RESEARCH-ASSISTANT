# Deploying the AI Research Assistant on Streamlit Community Cloud

Files in this folder: app.py, ai_comparison.py, similarity.py, research_database.db,
requirements.txt, .gitignore, .streamlit/secrets.toml.example

## 1. Test locally
    pip install -r requirements.txt
    copy .streamlit\secrets.toml.example .streamlit\secrets.toml   (then edit it: add your key)
    streamlit run app.py

## 2. Push to GitHub
    git init
    git add .
    git commit -m "AI Research Assistant"
    git branch -M main
    git remote add origin https://github.com/<your-username>/<your-repo>.git
    git push -u origin main
Check on github.com that secrets.toml and any .csv files are NOT in the repo.

## 3. Deploy
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click "Create app" -> "Deploy a public app from GitHub".
3. Pick your repository, branch = main, Main file path = app.py.
4. Open "Advanced settings": choose Python 3.12 (or 3.13) and paste into Secrets:
       GEMINI_API_KEY = "your-real-key"
5. Click Deploy. The first build takes a few minutes.

## Updating later
Push a commit to GitHub - the app redeploys automatically.
Secrets can be edited any time under App -> Settings -> Secrets.
