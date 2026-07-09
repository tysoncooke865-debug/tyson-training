"""
Workout and mission logic target module.
"""

import pandas as pd

def completed_sets_for_day(df: pd.DataFrame, workout_date, workout: str) -> int:
    """Count actual completed sets, not completed exercises."""
    if df is None or df.empty:
        return 0

    today = df[
        (df["date"].astype(str) == str(workout_date)) &
        (df["workout"].astype(str) == str(workout))
    ].copy()

    if today.empty:
        return 0

    if "set_number" in today.columns and "set" not in today.columns:
        today = today.rename(columns={"set_number": "set"})

    for col in ["set", "weight", "reps"]:
        if col in today.columns:
            today[col] = pd.to_numeric(today[col], errors="coerce").fillna(0)

    today = today[(today["set"] > 0) & (today["weight"] > 0) & (today["reps"] > 0)]
    today = today.drop_duplicates(subset=["date", "workout", "exercise", "set"], keep="last")
    return int(len(today))
