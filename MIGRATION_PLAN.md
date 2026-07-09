# Migration plan

## Phase 1 complete
- Project split into folders
- Current app preserved as `legacy/runtime.py`
- Safe `app.py` launcher created
- Modular target files created

## Phase 2
Move utilities:
1. constants to `core/config.py`
2. Supabase/CSV to `core/database.py`
3. workout functions to `systems/workouts.py`

## Phase 3
Move UI:
1. navigation to `ui/navigation.py`
2. cards/components to `ui/cards.py`

## Phase 4
Move pages:
1. Home
2. Missions
3. Evolution
4. Progress
5. Oracle
6. Engine
7. Quests
8. Data/Profile/Delete/Routine
