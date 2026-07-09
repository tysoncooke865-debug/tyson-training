# EVOFORGE Split Project

## Run

```bash
streamlit run app.py
```

## Deploy

Set Streamlit Cloud main file to:

```text
app.py
```

## Important

The working uploaded app is preserved at:

```text
legacy/runtime.py
```

The app launcher runs that file directly, so the deployment should behave like your current app.

The folders `core/`, `systems/`, `ui/`, and `pages/` are the clean split structure for future migration.

## Structure

```text
app.py
tyson_training_targets.py
legacy/runtime.py

core/
  config.py
  database.py

systems/
  workouts.py
  body.py
  achievements.py
  avatar.py

ui/
  navigation.py
  cards.py

pages/
  home.py
  missions.py
  evolution.py
  progress.py
  oracle.py
  engine.py
  quests.py
  data_manager.py

avatar_assets/
requirements.txt
```

## Next phase

Move one page at a time from `legacy/runtime.py` into the matching file in `pages/`.
Do not move everything at once.
