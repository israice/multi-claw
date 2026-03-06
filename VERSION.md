# START
pip install pyrogram
python BACKEND\create_telegram_group_with_topics.py

pip install -r requirements.txt

docker compose --profile mini-claw --profile pico-claw up -d --build
docker compose up -d --build
docker compose down && python run.py compose

python run.py compose

# CLEAN
docker builder prune -f && python run.py compose

# RECOVERY
git log --oneline -n 5

Copy-Item .env $env:TEMP\.env.backup
git reset --hard 80f714fc
git clean -fd
Copy-Item $env:TEMP\.env.backup .env -Force
git push origin master --force
python run.py

# UPDATE
git add .
git commit -m "v0.0.1 - first commit 01.03.2026"
git push
python run.py


# DEV LOG
v0.0.1 - first commit 03.03.2026
v0.0.2 - added dashboard page and 2 active telegram bots tested
v0.0.3 - added screenshots and creating telegram group script
v0.0.4 - added docker support for ubuntu servers

