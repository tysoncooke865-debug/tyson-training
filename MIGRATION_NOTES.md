# Migration notes

This bundle is the safest modular version:

- Use `app.py` as the Streamlit entrypoint.
- The current working app is preserved in `evoforge/legacy/runtime.py`.
- New modular files are ready for progressive migration.
- This avoids another breakage from moving thousands of lines at once.

Recommended next migration order:

1. Move constants into `modules/config.py`.
2. Move routing helpers into `modules/navigation.py`.
3. Move Supabase + CSV helpers into `modules/data.py`.
4. Move workout logging and set counting into `modules/workouts.py`.
5. Move avatar logic into `modules/avatar.py`.
6. Move reusable UI components into `modules/ui.py`.
7. Finally split each page into `modules/pages.py`.
