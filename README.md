# EVOFORGE Modular Project

## How to run locally

```bash
streamlit run app.py
```

## Deploy on Streamlit Cloud

Set the entry file to:

```text
app.py
```

## Structure

```text
app.py
evoforge/
  legacy/
    runtime.py      # current working app, preserved exactly
    runner.py       # runs runtime.py
  modules/
    config.py       # page labels/constants
    navigation.py   # route_to / route_button target module
    data.py         # Supabase/CSV target module
    workouts.py     # mission/workout logic target module
    avatar.py       # avatar/evolution target module
    ui.py           # reusable UI component target module
    pages.py        # future page render functions
avatar_assets/
requirements.txt
```

## Why this is Phase 1

The existing app is large and patch-heavy. This refactor safely gives it a real
multi-file project layout without breaking the current working runtime.

Next phase is to progressively move code out of `evoforge/legacy/runtime.py`
into `evoforge/modules/*`, starting with:
1. navigation
2. data/Supabase
3. workout logger
4. avatar
5. UI cards
6. page functions
