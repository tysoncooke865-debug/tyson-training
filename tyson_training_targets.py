import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime, timedelta
import os
import base64
import json
import math

APP_TITLE = "Tyson Training"
LOG_FILE = Path("workout_log.csv")
BODYWEIGHT_FILE = Path("bodyweight_log.csv")
CARDIO_FILE = Path("cardio_log.csv")
BODYFAT_FILE = Path("bodyfat_log.csv")
TARGETS_FILE = Path("targets.csv")
PROFILE_FILE = Path("profile.csv")
ACHIEVEMENT_FILE = Path("achievements.csv")

ROUTINE = {
    "Push 1 - Strength": [
        ("Barbell Bench Press (Strength)", 4, "Top set 3-5 + 3 back-off sets 5-8"),
        ("Dumbbell Flat Bench Press", 3, "8-12"),
        ("Pec Deck Machine Fly", 3, "10-15"),
        ("Cable Lateral Raise", 4, "12-20"),
        ("Cable Triceps Pushdown", 4, "10-15"),
        ("Decline Push-Up", 2, "AMRAP"),
    ],
    "Pull 1 - Back Thickness": [
        ("Chest-Supported Machine Row", 4, "6-10"),
        ("Lat Pulldown", 4, "8-12"),
        ("Chest-Supported Dumbbell Row", 3, "8-12"),
        ("Reverse Pec Deck (Rear Delt Fly)", 4, "15-25"),
        ("EZ-Bar Curl", 4, "8-12"),
        ("Dumbbell Biceps Curl", 3, "10-15"),
    ],
    "Push 2 - Hypertrophy": [
        ("Paused Barbell Bench Press", 3, "5-8"),
        ("Dumbbell Flat Bench Press", 3, "8-12"),
        ("Pec Deck Machine Fly", 4, "12-20"),
        ("Dumbbell Lateral Raise", 5, "15-25"),
        ("Cable Lateral Raise", 3, "15-25"),
        ("Cable Triceps Pushdown", 4, "12-20"),
    ],
    "Pull 2 - Width / V-Taper": [
        ("Lat Pulldown", 4, "10-15"),
        ("Cable Lat Pullover (Straight-Arm Pulldown)", 4, "12-20"),
        ("Chest-Supported Machine Row", 3, "8-12"),
        ("Face Pull", 3, "15-25"),
        ("Reverse Pec Deck (Rear Delt Fly)", 3, "15-25"),
        ("EZ-Bar Curl", 3, "10-15"),
    ],
    "Legs": [
        ("Barbell Back Squat", 3, "5-8"),
        ("Hack Squat Machine", 4, "8-12"),
        ("Seated/Lying Leg Curl", 4, "10-15"),
        ("Leg Extension", 4, "12-20"),
        ("Seated Calf Raise", 5, "10-20"),
        ("Hip Adduction Machine", 3, "12-20"),
    ],
    "Aesthetics": [
        ("Cable Lateral Raise", 5, "15-25"),
        ("Cable Lat Pullover (Straight-Arm Pulldown)", 3, "12-20"),
        ("Pec Deck Machine Fly", 4, "12-20"),
        ("Reverse Pec Deck (Rear Delt Fly)", 4, "15-25"),
        ("Dumbbell Biceps Curl", 3, "10-15"),
        ("Cable Triceps Pushdown", 3, "10-15"),
        ("Machine Ab Crunch", 3, "10-20"),
        ("Lying Leg Raise", 3, "12-20"),
        ("Weighted Sit-Up", 2, "10-15"),
    ],
    "Rest": [],
}

MUSCLE_MAP = {
    "Barbell Bench Press (Strength)": "Chest",
    "Paused Barbell Bench Press": "Chest",
    "Dumbbell Flat Bench Press": "Chest",
    "Pec Deck Machine Fly": "Chest",
    "Decline Push-Up": "Chest",
    "Cable Lateral Raise": "Delts",
    "Dumbbell Lateral Raise": "Delts",
    "Reverse Pec Deck (Rear Delt Fly)": "Rear Delts",
    "Face Pull": "Rear Delts",
    "Cable Triceps Pushdown": "Triceps",
    "Lat Pulldown": "Back",
    "Cable Lat Pullover (Straight-Arm Pulldown)": "Back",
    "Chest-Supported Machine Row": "Back",
    "Chest-Supported Dumbbell Row": "Back",
    "EZ-Bar Curl": "Biceps",
    "Dumbbell Biceps Curl": "Biceps",
    "Barbell Back Squat": "Legs",
    "Hack Squat Machine": "Legs",
    "Seated/Lying Leg Curl": "Legs",
    "Leg Extension": "Legs",
    "Seated Calf Raise": "Calves",
    "Hip Adduction Machine": "Legs",
    "Machine Ab Crunch": "Abs",
    "Lying Leg Raise": "Abs",
    "Weighted Sit-Up": "Abs",
}

ACHIEVEMENTS = {
    # App / logging
    "first_set": ("⚡ First Signal", "Logged your first set."),
    "first_workout": ("🦇 Patrol Started", "Logged 10 total sets."),
    "hundred_sets": ("🔥 100 Set Streak", "Logged 100 total working sets."),
    "five_hundred_sets": ("⚔️ 500 Set Veteran", "Logged 500 total working sets."),
    "thousand_sets": ("👑 1000 Set Machine", "Logged 1000 total working sets."),

    # Consistency
    "three_day_streak": ("🔥 3 Day Streak", "Logged workouts on 3 different days."),
    "seven_day_streak": ("⚡ 7 Day Streak", "Logged workouts on 7 different days."),
    "fourteen_day_streak": ("🦾 14 Day Discipline", "Logged workouts on 14 different days."),
    "thirty_day_streak": ("🗿 30 Day Weapon", "Logged workouts on 30 different days."),
    "full_ppppla_week": ("💎 Full PPPPLA Week", "Logged all 6 training days at least once."),

    # Bench milestones
    "bench_60": ("🏋️ 1 Plate Bench", "Logged a 60kg+ bench press."),
    "bench_80": ("⚡ 80kg Bench", "Logged an 80kg+ bench press."),
    "bench_90": ("💪 90kg Bench Signal", "Logged 90kg or more on bench."),
    "bench_100": ("🏆 100kg Bench Club", "Logged a 100kg+ bench press."),
    "bench_110": ("🦾 110kg Bench", "Logged a 110kg+ bench press."),
    "bench_120": ("👑 120kg Bench", "Logged a 120kg+ bench press."),
    "bench_100_est": ("🏆 100kg Bench Quest", "Estimated 1RM reached 100kg."),
    "bench_120_est": ("👑 120kg Bench Quest", "Estimated 1RM reached 120kg."),
    "bench_bw": ("⚖️ Bodyweight Bench", "Estimated bench 1RM reached bodyweight."),
    "bench_1_25_bw": ("🦇 1.25× BW Bench", "Estimated bench 1RM reached 1.25× bodyweight."),
    "bench_1_5_bw": ("☀️ 1.5× BW Bench", "Estimated bench 1RM reached 1.5× bodyweight."),

    # Squat milestones
    "squat_100": ("🦵 100kg Squat", "Logged a 100kg+ squat."),
    "squat_140": ("⚔️ 2 Plate Squat", "Logged a 140kg+ squat."),
    "squat_160": ("🦾 160kg Squat", "Logged a 160kg+ squat."),
    "squat_180": ("🗿 180kg Squat", "Logged a 180kg+ squat."),
    "squat_200": ("👑 200kg Squat", "Logged a 200kg+ squat."),
    "squat_1_5_bw": ("⚖️ 1.5× BW Squat", "Estimated squat 1RM reached 1.5× bodyweight."),
    "squat_2_bw": ("☀️ 2× BW Squat", "Estimated squat 1RM reached 2× bodyweight."),

    # Bodyweight / bulking / cutting
    "first_bw_log": ("⚖️ Scale Online", "Logged bodyweight for the first time."),
    "bw_75": ("🏃 75kg Checkpoint", "Logged bodyweight at or below 75kg."),
    "bw_80": ("🦾 80kg Frame", "Logged bodyweight at or above 80kg."),
    "bw_85": ("🗿 85kg Bulk Mode", "Logged bodyweight at or above 85kg."),
    "bulk_2kg": ("📈 Lean Bulk Started", "Gained 2kg from your lowest logged bodyweight."),
    "bulk_5kg": ("🦾 5kg Bulk Arc", "Gained 5kg from your lowest logged bodyweight."),
    "cut_2kg": ("✂️ Cut Started", "Dropped 2kg from your highest logged bodyweight."),
    "cut_5kg": ("🔥 5kg Cut Arc", "Dropped 5kg from your highest logged bodyweight."),

    # Body fat
    "first_bf_log": ("📸 Body Fat Scan", "Saved your first body fat estimate."),
    "bf_under_15": ("💎 Under 15%", "Body fat estimate reached under 15%."),
    "bf_under_13": ("🦇 Under 13%", "Body fat estimate reached under 13%."),
    "bf_under_12": ("⚡ Under 12%", "Body fat estimate reached under 12%."),
    "bf_under_10": ("☀️ 10% Club", "Body fat estimate reached 10% or lower."),
    "bf_target_hit": ("🎯 Body Fat Target Hit", "Reached your saved body fat target."),

    # Cardio
    "first_cardio": ("🫀 Engine Started", "Logged your first cardio session."),
    "cardio_100": ("🫀 Engine Built", "Logged 100 total cardio minutes."),
    "cardio_300": ("🏃 300 Minute Engine", "Logged 300 total cardio minutes."),
    "cardio_1000": ("⚡ 1000 Minute Engine", "Logged 1000 total cardio minutes."),
    "cardio_5k_total": ("🛣️ 5km Total", "Logged 5km total cardio distance."),
    "cardio_25k_total": ("🛣️ 25km Total", "Logged 25km total cardio distance."),
    "cardio_100k_total": ("🌏 100km Total", "Logged 100km total cardio distance."),
    "boxing_logged": ("🥊 Sparring Logged", "Logged a boxing cardio session."),

    # Muscle group volume
    "chest_50": ("🛡️ 50 Chest Sets", "Logged 50 chest sets."),
    "chest_150": ("🛡️ Chest Built", "Logged 150 chest sets."),
    "back_50": ("🪽 50 Back Sets", "Logged 50 back sets."),
    "back_150": ("🪽 V-Taper Built", "Logged 150 back sets."),
    "delts_50": ("🪽 Wing Build", "Logged 50 delt/rear-delt sets."),
    "delts_150": ("💎 Capped Delts", "Logged 150 delt/rear-delt sets."),
    "arms_100": ("💪 Arm Arc", "Logged 100 biceps/triceps sets."),
    "legs_100": ("🦵 Leg Foundation", "Logged 100 leg/calf sets."),
    "abs_50": ("腹 Core Signal", "Logged 50 ab sets."),

    # Rank milestones
    "aesthetic_tier": ("💎 Aesthetic Tier", "Reached level 40."),
    "elite_physique": ("⚡ Elite Physique", "Reached level 60."),
    "chad_lite": ("🗿 Chad-Lite", "Reached level 75."),
    "chad": ("👑 Chad", "Reached level 90."),
    "true_adam": ("☀️ True Adam", "Reached level 100."),
}

def load_csv(path, columns):
    if path.exists():
        try:
            df = pd.read_csv(path)
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)


def normalise_workout_log(df):
    if "set" not in df.columns and "set_number" in df.columns:
        df = df.rename(columns={"set_number": "set"})
    for col in ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]:
        if col not in df.columns:
            df[col] = ""
    return df


def load_log():
    return normalise_workout_log(load_csv(LOG_FILE, ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]))


def load_achievements():
    return load_csv(ACHIEVEMENT_FILE, ["achievement_id", "name", "description", "date_unlocked"])


def save_achievement(achievement_id):
    ach = load_achievements()
    if achievement_id in ach["achievement_id"].astype(str).tolist():
        return False
    name, desc = ACHIEVEMENTS[achievement_id]
    new = pd.DataFrame([{
        "achievement_id": achievement_id,
        "name": name,
        "description": desc,
        "date_unlocked": datetime.now().isoformat(timespec="seconds"),
    }])
    pd.concat([ach, new], ignore_index=True).to_csv(ACHIEVEMENT_FILE, index=False)
    return True


def estimated_1rm(weight, reps):
    return weight * (1 + reps / 30) if reps > 0 else 0


def get_last_sets(df, exercise):
    if df.empty or "exercise" not in df.columns:
        return None
    previous = df[df["exercise"] == exercise]
    if previous.empty:
        return None
    last_date = previous["date"].max()
    return previous[previous["date"] == last_date]


def get_previous_best_1rm(df, exercise, exclude_date=None, exclude_set=None):
    if df.empty:
        return 0
    ex = df[df["exercise"] == exercise].copy()
    if exclude_date is not None and exclude_set is not None:
        ex["set"] = pd.to_numeric(ex["set"], errors="coerce").fillna(0).astype(int)
        ex = ex[~((ex["date"].astype(str) == str(exclude_date)) & (ex["set"] == int(exclude_set)))]
    if ex.empty:
        return 0
    ex["weight"] = pd.to_numeric(ex["weight"], errors="coerce").fillna(0)
    ex["reps"] = pd.to_numeric(ex["reps"], errors="coerce").fillna(0)
    ex["estimated_1rm"] = ex.apply(lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])), axis=1)
    return float(ex["estimated_1rm"].max())


def suggest_weight(df, exercise):
    last = get_last_sets(df, exercise)
    if last is None or last.empty:
        return "No previous data yet"
    last = last.copy()
    last["weight"] = pd.to_numeric(last["weight"], errors="coerce").fillna(0)
    last["reps"] = pd.to_numeric(last["reps"], errors="coerce").fillna(0)
    best = last.sort_values(["weight", "reps"], ascending=False).iloc[0]
    weight = float(best["weight"])
    reps = int(best["reps"])
    if exercise == "Barbell Bench Press (Strength)":
        return f"Try {weight + 2.5:.1f} kg next top set" if reps >= 5 else f"Repeat {weight:.1f} kg and beat reps"
    if exercise == "Paused Barbell Bench Press":
        return f"Try {weight + 2.5:.1f} kg" if reps >= 8 else f"Repeat {weight:.1f} kg with a clean pause"
    return f"Try {weight + 2.5:.1f} kg if form was clean" if reps >= 15 else f"Repeat {weight:.1f} kg and beat reps"


def completed_sets_for_day(df, workout_date, workout):
    if df.empty:
        return 0
    df = normalise_workout_log(df)
    today = df[(df["date"].astype(str) == str(workout_date)) & (df["workout"].astype(str) == str(workout))]
    if today.empty:
        return 0
    today["weight"] = pd.to_numeric(today["weight"], errors="coerce").fillna(0)
    today["reps"] = pd.to_numeric(today["reps"], errors="coerce").fillna(0)
    return len(today[(today["weight"] > 0) & (today["reps"] > 0)])


def save_set_auto(workout_date, workout, exercise, set_no, weight, reps):
    if weight <= 0 or reps <= 0:
        return False, False, 0, 0

    df_before = load_log()
    previous_best = get_previous_best_1rm(df_before, exercise, exclude_date=workout_date, exclude_set=set_no)
    current_1rm = estimated_1rm(float(weight), int(reps))
    is_pr = current_1rm > previous_best and previous_best > 0

    df = normalise_workout_log(df_before)
    df["date"] = df["date"].astype(str)
    df["workout"] = df["workout"].astype(str)
    df["exercise"] = df["exercise"].astype(str)
    df["set"] = pd.to_numeric(df["set"], errors="coerce").fillna(0).astype(int)

    mask = (
        (df["date"] == str(workout_date)) &
        (df["workout"] == str(workout)) &
        (df["exercise"] == str(exercise)) &
        (df["set"] == int(set_no))
    )

    new_row = {
        "date": str(workout_date),
        "workout": workout,
        "exercise": exercise,
        "set": int(set_no),
        "weight": float(weight),
        "reps": int(reps),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    if mask.any():
        old = df.loc[mask].iloc[-1]
        try:
            same_weight = float(old["weight"]) == float(weight)
            same_reps = int(float(old["reps"])) == int(reps)
        except Exception:
            same_weight = False
            same_reps = False
        if same_weight and same_reps:
            return False, False, current_1rm, previous_best
        df = df.loc[~mask].copy()

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)
    check_achievements()
    return True, is_pr, current_1rm, previous_best




def load_targets():
    return load_csv(
        TARGETS_FILE,
        ["target_type", "name", "target_value", "unit", "created_at", "notes"]
    )


def get_target(target_type, name):
    df = load_targets()
    if df.empty:
        return None
    matches = df[
        (df["target_type"].astype(str) == str(target_type)) &
        (df["name"].astype(str) == str(name))
    ]
    if matches.empty:
        return None
    try:
        return float(matches.iloc[-1]["target_value"])
    except Exception:
        return None


def load_profile():
    return load_csv(
        PROFILE_FILE,
        ["height_cm", "bodyweight_kg", "bench_e1rm", "squat_e1rm", "training_years", "physique_score", "leanness_score", "base_level", "created_at"]
    )


def save_profile(height_cm, bodyweight_kg, bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score):
    base_level = calculate_starting_level(bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score)
    df = pd.DataFrame([{
        "height_cm": height_cm,
        "bodyweight_kg": bodyweight_kg,
        "bench_e1rm": bench_e1rm,
        "squat_e1rm": squat_e1rm,
        "training_years": training_years,
        "physique_score": physique_score,
        "leanness_score": leanness_score,
        "base_level": base_level,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }])
    df.to_csv(PROFILE_FILE, index=False)
    return base_level


def get_base_level():
    profile = load_profile()
    if profile.empty:
        return 1
    try:
        return int(float(profile.iloc[-1]["base_level"]))
    except Exception:
        return 1


def calculate_starting_level(bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score):
    level = 1

    # Bench strength points
    if bench_e1rm >= 120:
        level += 28
    elif bench_e1rm >= 100:
        level += 22
    elif bench_e1rm >= 90:
        level += 18
    elif bench_e1rm >= 80:
        level += 14
    elif bench_e1rm >= 60:
        level += 8

    # Squat strength points
    if squat_e1rm >= 180:
        level += 18
    elif squat_e1rm >= 140:
        level += 14
    elif squat_e1rm >= 100:
        level += 9

    # Training age
    if training_years >= 5:
        level += 16
    elif training_years >= 3:
        level += 12
    elif training_years >= 1:
        level += 7

    # Physique/leanness self-ratings
    level += int(physique_score)
    level += int(leanness_score)

    return max(1, min(int(level), 100))


def rank_name(level):
    level = int(level)
    if level >= 100:
        return "☀️ True Adam"
    if level >= 90:
        return "👑 Chad"
    if level >= 75:
        return "🗿 Chad-Lite"
    if level >= 60:
        return "⚡ Elite Physique"
    if level >= 40:
        return "💎 Aesthetic Tier"
    if level >= 25:
        return "🦾 Athlete"
    if level >= 10:
        return "⚔️ Trainee"
    return "🌱 Rookie"




def current_exercise_best_1rm(exercise_name):
    df = load_log()

    if df.empty:
        return 0

    df = normalise_workout_log(df)
    ex = df[df["exercise"] == exercise_name].copy()

    if ex.empty:
        return 0

    ex["weight"] = pd.to_numeric(ex["weight"], errors="coerce").fillna(0)
    ex["reps"] = pd.to_numeric(ex["reps"], errors="coerce").fillna(0)

    ex["estimated_1rm"] = ex.apply(
        lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])),
        axis=1,
    )

    return float(ex["estimated_1rm"].max())



def latest_bodyweight_value():
    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])
    if bw_df.empty:
        return None
    bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
    valid = bw_df[bw_df["bodyweight"] > 0]
    if valid.empty:
        return None
    return float(valid.iloc[-1]["bodyweight"])


def latest_bodyfat_mid():
    bf_df = load_bodyfat_log()
    if bf_df.empty:
        return None
    bf_df["bf_mid"] = pd.to_numeric(bf_df["bf_mid"], errors="coerce").fillna(0)
    valid = bf_df[bf_df["bf_mid"] > 0]
    if valid.empty:
        return None
    return float(valid.iloc[-1]["bf_mid"])


def render_target_bar(title, current, target, unit, lower_is_better=False):
    if current is None or target is None:
        st.info(f"{title}: Set a target to begin.")
        return

    if lower_is_better:
        progress = 100 if current <= target else (target / current) * 100
    else:
        progress = (current / target) * 100 if target else 0

    progress = max(0, min(progress, 100))

    st.markdown(
        f"""
        <div class="mission-card">
            <div class="mission-title">{title}</div>
            <div class="progress-track">
                <div class="progress-fill" style="--progress:{progress}%;"></div>
            </div>
            <div class="progress-label">{current:.1f}{unit} / {target:.1f}{unit} ({progress:.0f}%)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workout_summary(df):
    df = normalise_workout_log(df.copy())
    if df.empty:
        return {
            "total_sets": 0, "total_reps": 0, "best_bench_1rm": 0, "latest_bw": 0,
            "xp": 0, "level": get_base_level(), "rank": rank_name(get_base_level()), "base_level": get_base_level(),
            "xp_into_level": 0, "xp_needed": 500
        }
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0)
    df["reps"] = pd.to_numeric(df["reps"], errors="coerce").fillna(0)
    total_sets = len(df[(df["weight"] > 0) & (df["reps"] > 0)])
    total_reps = int(df["reps"].sum())

    bench = df[df["exercise"] == "Barbell Bench Press (Strength)"].copy()
    if not bench.empty:
        bench["estimated_1rm"] = bench.apply(lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])), axis=1)
        best_bench_1rm = float(bench["estimated_1rm"].max())
    else:
        best_bench_1rm = 0

    cardio = load_csv(CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"])
    cardio["minutes"] = pd.to_numeric(cardio.get("minutes", 0), errors="coerce").fillna(0)
    cardio_minutes = float(cardio["minutes"].sum()) if not cardio.empty else 0

    xp = int(total_sets * 10 + cardio_minutes * 2)
    base_level = get_base_level()
    earned_levels = xp // 500
    level = max(1, min(base_level + earned_levels, 100))
    xp_into_level = xp % 500

    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])
    latest_bw = 0
    if not bw_df.empty:
        bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
        latest_bw = float(bw_df.iloc[-1]["bodyweight"])

    return {
        "total_sets": total_sets, "total_reps": total_reps, "best_bench_1rm": best_bench_1rm,
        "latest_bw": latest_bw, "xp": xp, "level": level, "rank": rank_name(level), "base_level": base_level,
        "xp_into_level": xp_into_level, "xp_needed": 500
    }


def muscle_heat_map(df):
    df = normalise_workout_log(df.copy())
    if df.empty:
        return pd.DataFrame(columns=["muscle", "sets"])
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0)
    df["reps"] = pd.to_numeric(df["reps"], errors="coerce").fillna(0)
    df = df[(df["weight"] > 0) & (df["reps"] > 0)]
    df["muscle"] = df["exercise"].map(MUSCLE_MAP).fillna("Other")
    return df.groupby("muscle", as_index=False).size().rename(columns={"size": "sets"}).sort_values("sets", ascending=False)



def unique_training_days(df):
    if df.empty or "date" not in df.columns:
        return 0
    return df["date"].dropna().astype(str).nunique()


def logged_all_ppppla_days(df):
    if df.empty or "workout" not in df.columns:
        return False
    required = {
        "Push 1 - Strength",
        "Pull 1 - Back Thickness",
        "Push 2 - Hypertrophy",
        "Pull 2 - Width / V-Taper",
        "Legs",
        "Aesthetics",
    }
    logged = set(df["workout"].dropna().astype(str).unique())
    return required.issubset(logged)


def get_bodyweight_stats():
    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])
    if bw_df.empty:
        return {"latest": None, "min": None, "max": None, "count": 0}
    bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
    valid = bw_df[bw_df["bodyweight"] > 0]
    if valid.empty:
        return {"latest": None, "min": None, "max": None, "count": 0}
    return {
        "latest": float(valid.iloc[-1]["bodyweight"]),
        "min": float(valid["bodyweight"].min()),
        "max": float(valid["bodyweight"].max()),
        "count": len(valid),
    }






def save_bodyfat_estimate(row):
    """
    Saves one body fat estimate row to bodyfat_log.csv.
    """
    df = load_bodyfat_log()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(BODYFAT_FILE, index=False)


def bodyfat_outputs(weight_kg, bf_percent, target_bf=10.0):
    """
    Returns fat mass, lean mass, target weight, and fat to lose.
    Safe against missing/invalid values.
    """
    try:
        weight_kg = float(weight_kg)
        bf_percent = float(bf_percent)
        target_bf = float(target_bf)

        if weight_kg <= 0 or bf_percent <= 0 or target_bf <= 0 or target_bf >= 100:
            return None, None, None, None

        fat_mass = weight_kg * (bf_percent / 100)
        lean_mass = weight_kg - fat_mass
        target_weight = lean_mass / (1 - target_bf / 100)
        fat_to_lose = max(weight_kg - target_weight, 0)

        return fat_mass, lean_mass, target_weight, fat_to_lose

    except Exception:
        return None, None, None, None


def safe_kg(value):
    if value is None:
        return "No data"
    try:
        return f"{float(value):.1f}kg"
    except Exception:
        return "No data"


def encode_image_for_openai(uploaded_file):
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def run_ai_bodyfat_estimate(front_photo, back_photo, height_cm, weight_kg, waist_cm, neck_cm, lighting, pump_status, time_of_day, model_name):
    """
    AI photo-based body fat estimate.
    Requires OPENAI_API_KEY in Streamlit secrets or environment variables.
    Waist/neck are optional and ignored unless > 0.
    """
    try:
        from openai import OpenAI
    except Exception as e:
        return None, f"OpenAI package not installed. Add 'openai' to requirements.txt. Error: {e}"

    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        api_key = None

    api_key = api_key or os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None, "Missing OPENAI_API_KEY. Add it to Streamlit Cloud secrets or your environment variables."

    if front_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."

    client = OpenAI(api_key=api_key)

    user_text = f"""
You are estimating male body fat percentage from physique photos for a fitness tracking app.

This is not medical advice. Give a realistic range, not false precision.

User stats:
- Height: {height_cm} cm
- Bodyweight: {weight_kg} kg
- Waist: {waist_cm if waist_cm and waist_cm > 0 else "Not provided"}
- Neck: {neck_cm if neck_cm and neck_cm > 0 else "Not provided"}
- Lighting: {lighting}
- Pump status: {pump_status}
- Time of day: {time_of_day}

Important:
- Do NOT use waist or neck unless actually provided.
- If waist/neck say "Not provided", base the estimate on photos, height, weight, lighting, pump, and time only.
- Be conservative if lighting/pump is flattering.
- Return ONLY valid JSON.

JSON schema:
{{
  "bf_low": number,
  "bf_high": number,
  "bf_mid": number,
  "confidence": "low" | "medium" | "high",
  "notes": "short practical explanation",
  "fat_storage": "short note",
  "ten_percent_notes": "short note"
}}
"""

    content = [{"type": "input_text", "text": user_text}]

    if front_photo is not None:
        content.append({"type": "input_image", "image_url": encode_image_for_openai(front_photo)})
    if back_photo is not None:
        content.append({"type": "input_image", "image_url": encode_image_for_openai(back_photo)})

    try:
        response = client.responses.create(
            model=model_name,
            input=[{"role": "user", "content": content}],
        )

        text = getattr(response, "output_text", None)
        if not text:
            text = str(response)

        text_clean = text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text_clean)

        for key in ["bf_low", "bf_high", "bf_mid", "confidence", "notes"]:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"

        return data, None

    except Exception as e:
        return None, f"AI estimate failed: {e}"



def load_bodyfat_log():
    return load_csv(
        BODYFAT_FILE,
        [
            "date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm",
            "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"
        ]
    )


def get_bodyfat_stats():
    bf_df = load_bodyfat_log()
    if bf_df.empty:
        return {"latest": None, "min": None, "count": 0}
    bf_df["bf_mid"] = pd.to_numeric(bf_df["bf_mid"], errors="coerce").fillna(0)
    valid = bf_df[bf_df["bf_mid"] > 0]
    if valid.empty:
        return {"latest": None, "min": None, "count": 0}
    return {
        "latest": float(valid.iloc[-1]["bf_mid"]),
        "min": float(valid["bf_mid"].min()),
        "count": len(valid),
    }


def get_cardio_stats():
    cardio = load_csv(CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"])
    if cardio.empty:
        return {"minutes": 0, "distance": 0, "count": 0, "types": set()}
    cardio["minutes"] = pd.to_numeric(cardio.get("minutes", 0), errors="coerce").fillna(0)
    cardio["distance_km"] = pd.to_numeric(cardio.get("distance_km", 0), errors="coerce").fillna(0)
    return {
        "minutes": float(cardio["minutes"].sum()),
        "distance": float(cardio["distance_km"].sum()),
        "count": len(cardio),
        "types": set(cardio.get("type", pd.Series(dtype=str)).dropna().astype(str).tolist()),
    }


def muscle_sets_count(heat, names):
    if heat.empty:
        return 0
    return int(heat[heat["muscle"].isin(names)]["sets"].sum())


def check_achievements():
    df = load_log()
    summary = workout_summary(df)
    heat = muscle_heat_map(df)
    bw = get_bodyweight_stats()
    bf = get_bodyfat_stats()
    cardio = get_cardio_stats()

    unlocked = []

    def unlock(key):
        if key in ACHIEVEMENTS and save_achievement(key):
            unlocked.append(ACHIEVEMENTS[key][0])

    # Basic logging
    if summary["total_sets"] >= 1: unlock("first_set")
    if summary["total_sets"] >= 10: unlock("first_workout")
    if summary["total_sets"] >= 100: unlock("hundred_sets")
    if summary["total_sets"] >= 500: unlock("five_hundred_sets")
    if summary["total_sets"] >= 1000: unlock("thousand_sets")

    # Consistency
    days = unique_training_days(df)
    if days >= 3: unlock("three_day_streak")
    if days >= 7: unlock("seven_day_streak")
    if days >= 14: unlock("fourteen_day_streak")
    if days >= 30: unlock("thirty_day_streak")
    if logged_all_ppppla_days(df): unlock("full_ppppla_week")

    # Strength - bench
    if summary["best_bench_1rm"] >= 100: unlock("bench_100_est")
    if summary["best_bench_1rm"] >= 120: unlock("bench_120_est")

    if bw["latest"]:
        if summary["best_bench_1rm"] >= bw["latest"]: unlock("bench_bw")
        if summary["best_bench_1rm"] >= bw["latest"] * 1.25: unlock("bench_1_25_bw")
        if summary["best_bench_1rm"] >= bw["latest"] * 1.5: unlock("bench_1_5_bw")

    bench = df[df["exercise"] == "Barbell Bench Press (Strength)"].copy() if not df.empty else pd.DataFrame()
    if not bench.empty:
        bench["weight"] = pd.to_numeric(bench["weight"], errors="coerce").fillna(0)
        max_bench = bench["weight"].max()
        if max_bench >= 60: unlock("bench_60")
        if max_bench >= 80: unlock("bench_80")
        if max_bench >= 90: unlock("bench_90")
        if max_bench >= 100: unlock("bench_100")
        if max_bench >= 110: unlock("bench_110")
        if max_bench >= 120: unlock("bench_120")

    # Strength - squat
    squat = df[df["exercise"] == "Barbell Back Squat"].copy() if not df.empty else pd.DataFrame()
    squat_e1rm = 0
    if not squat.empty:
        squat["weight"] = pd.to_numeric(squat["weight"], errors="coerce").fillna(0)
        squat["reps"] = pd.to_numeric(squat["reps"], errors="coerce").fillna(0)
        squat["estimated_1rm"] = squat.apply(lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])), axis=1)
        squat_e1rm = float(squat["estimated_1rm"].max())
        max_squat = squat["weight"].max()
        if max_squat >= 100: unlock("squat_100")
        if max_squat >= 140: unlock("squat_140")
        if max_squat >= 160: unlock("squat_160")
        if max_squat >= 180: unlock("squat_180")
        if max_squat >= 200: unlock("squat_200")

    if bw["latest"] and squat_e1rm:
        if squat_e1rm >= bw["latest"] * 1.5: unlock("squat_1_5_bw")
        if squat_e1rm >= bw["latest"] * 2: unlock("squat_2_bw")

    # Bodyweight / cut / bulk
    if bw["count"] >= 1: unlock("first_bw_log")
    if bw["latest"] and bw["latest"] <= 75: unlock("bw_75")
    if bw["latest"] and bw["latest"] >= 80: unlock("bw_80")
    if bw["latest"] and bw["latest"] >= 85: unlock("bw_85")
    if bw["min"] is not None and bw["latest"] is not None:
        if bw["latest"] - bw["min"] >= 2: unlock("bulk_2kg")
        if bw["latest"] - bw["min"] >= 5: unlock("bulk_5kg")
    if bw["max"] is not None and bw["latest"] is not None:
        if bw["max"] - bw["latest"] >= 2: unlock("cut_2kg")
        if bw["max"] - bw["latest"] >= 5: unlock("cut_5kg")

    # Body fat
    if bf["count"] >= 1: unlock("first_bf_log")
    if bf["latest"] and bf["latest"] < 15: unlock("bf_under_15")
    if bf["latest"] and bf["latest"] < 13: unlock("bf_under_13")
    if bf["latest"] and bf["latest"] < 12: unlock("bf_under_12")
    if bf["latest"] and bf["latest"] <= 10: unlock("bf_under_10")
    bf_target = get_target("Body Fat", "Body Fat %")
    if bf["latest"] and bf_target and bf["latest"] <= bf_target:
        unlock("bf_target_hit")

    # Cardio
    if cardio["count"] >= 1: unlock("first_cardio")
    if cardio["minutes"] >= 100: unlock("cardio_100")
    if cardio["minutes"] >= 300: unlock("cardio_300")
    if cardio["minutes"] >= 1000: unlock("cardio_1000")
    if cardio["distance"] >= 5: unlock("cardio_5k_total")
    if cardio["distance"] >= 25: unlock("cardio_25k_total")
    if cardio["distance"] >= 100: unlock("cardio_100k_total")
    if "Boxing" in cardio["types"]: unlock("boxing_logged")

    # Muscle heat map / volume
    if muscle_sets_count(heat, ["Chest"]) >= 50: unlock("chest_50")
    if muscle_sets_count(heat, ["Chest"]) >= 150: unlock("chest_150")
    if muscle_sets_count(heat, ["Back"]) >= 50: unlock("back_50")
    if muscle_sets_count(heat, ["Back"]) >= 150: unlock("back_150")
    delt_sets = muscle_sets_count(heat, ["Delts", "Rear Delts"])
    if delt_sets >= 50: unlock("delts_50")
    if delt_sets >= 150: unlock("delts_150")
    if muscle_sets_count(heat, ["Biceps", "Triceps"]) >= 100: unlock("arms_100")
    if muscle_sets_count(heat, ["Legs", "Calves"]) >= 100: unlock("legs_100")
    if muscle_sets_count(heat, ["Abs"]) >= 50: unlock("abs_50")

    # Rank achievements
    if summary["level"] >= 40: unlock("aesthetic_tier")
    if summary["level"] >= 60: unlock("elite_physique")
    if summary["level"] >= 75: unlock("chad_lite")
    if summary["level"] >= 90: unlock("chad")
    if summary["level"] >= 100: unlock("true_adam")

    return unlocked


st.set_page_config(page_title=APP_TITLE, layout="centered")

st.markdown("""
<style>
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 980px; }
.stApp {
    background:
        radial-gradient(circle at 15% 15%, rgba(56,189,248,0.35), transparent 28%),
        radial-gradient(circle at 85% 30%, rgba(37,99,235,0.30), transparent 32%),
        radial-gradient(circle at 50% 90%, rgba(14,165,233,0.20), transparent 35%),
        linear-gradient(135deg, #020617, #071426, #020617);
    background-size: 180% 180%;
    animation: blueShift 12s ease infinite;
}
@keyframes blueShift { 0% { background-position: 0% 30%; } 50% { background-position: 100% 70%; } 100% { background-position: 0% 30%; } }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #020617, #082f49, #020617); }
div[role="radiogroup"] label {
    background: rgba(14,165,233,0.10); border: 1px solid rgba(56,189,248,0.25);
    border-radius: 14px; padding: 8px 12px; margin-bottom: 8px; transition: .2s ease;
}
div[role="radiogroup"] label:hover { background: rgba(56,189,248,0.25); box-shadow: 0 0 14px rgba(56,189,248,.35); }
.nw-hero {
    padding: 24px; border-radius: 24px; margin: 8px 0 24px 0;
    background: linear-gradient(135deg, rgba(7,20,38,0.98) 0%, rgba(15,39,68,0.98) 55%, rgba(6,17,31,0.98) 100%);
    border: 1px solid rgba(56, 189, 248, 0.55);
    box-shadow: 0 0 18px rgba(56, 189, 248, 0.22), inset 0 0 18px rgba(56, 189, 248, 0.07);
    animation: heroDropIn 1.1s cubic-bezier(.18,.89,.32,1.28), heroGlow 3.2s ease-in-out infinite;
}
@keyframes heroDropIn { 0% { opacity: 0; transform: translateY(-35px) scale(.94); filter: blur(10px); } 60% { opacity: 1; transform: translateY(6px) scale(1.015); filter: blur(0); } 100% { transform: translateY(0) scale(1); } }
@keyframes heroGlow { 0%, 100% { box-shadow: 0 0 18px rgba(56,189,248,.22), inset 0 0 18px rgba(56,189,248,.07); } 50% { box-shadow: 0 0 34px rgba(56,189,248,.42), inset 0 0 24px rgba(56,189,248,.12); } }
.nw-hero-title { font-size: 32px; font-weight: 900; color: #e0f2fe; letter-spacing: -0.7px; text-shadow: 0 0 12px rgba(186,230,253,.95), 0 0 28px rgba(14,165,233,.75); }
.nw-hero-sub { margin-top: 5px; color: #bae6fd; font-weight: 750; font-size: 15px; }
.nw-badge { display: inline-block; margin-top: 14px; padding: 8px 13px; border-radius: 999px; color: #e0f2fe; background: rgba(14, 165, 233, 0.18); border: 1px solid rgba(56, 189, 248, 0.42); font-size: 13px; font-weight: 850; }
.nw-scanline { height: 3px; width: 100%; margin-top: 16px; border-radius: 999px; background: linear-gradient(90deg, transparent, #38bdf8, #e0f2fe, #38bdf8, transparent); background-size: 220% 100%; animation: scanMove 2.2s linear infinite; box-shadow: 0 0 14px rgba(56,189,248,.8); }
@keyframes scanMove { from { background-position: 220% 0; } to { background-position: -220% 0; } }
.page-transition { padding: 10px 14px; margin: -5px 0 16px 0; border-radius: 14px; color: #e0f2fe; font-weight: 900; background: rgba(14,165,233,.14); border: 1px solid rgba(56,189,248,.28); animation: pageSlideIn .55s ease-out; }
@keyframes pageSlideIn { from { opacity: 0; transform: translateX(-18px); filter: blur(5px); } to { opacity: 1; transform: translateX(0); filter: blur(0); } }
.nw-exercise-card, .dashboard-card {
    padding: 14px; border-radius: 16px; background: linear-gradient(135deg, rgba(15,23,42,.72), rgba(7,20,38,.64));
    border: 1px solid rgba(56, 189, 248, 0.25); margin-bottom: 12px; box-shadow: 0 0 14px rgba(56,189,248,.08);
    transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease; animation: cardGlow 4s ease-in-out infinite;
}
.nw-exercise-card:hover, .dashboard-card:hover { transform: translateY(-5px) scale(1.01); border-color: rgba(224,242,254,.65); box-shadow: 0 0 34px rgba(56,189,248,.45), inset 0 0 18px rgba(56,189,248,.12); }
@keyframes cardGlow { 0%, 100% { box-shadow: 0 0 12px rgba(56,189,248,.08); } 50% { box-shadow: 0 0 20px rgba(56,189,248,.16); } }
.nw-card-title { font-weight: 900; color: #e0f2fe; font-size: 17px; margin-bottom: 4px; }
.nw-small { color: #7dd3fc; font-weight: 750; font-size: 13px; }
.nw-note { padding: 12px; border-radius: 14px; background: rgba(14, 165, 233, 0.12); border: 1px solid rgba(56, 189, 248, 0.25); margin: 8px 0 12px 0; }
.mission-card { padding: 16px; border-radius: 18px; margin: 0 0 18px 0; background: linear-gradient(135deg, rgba(15,23,42,.78), rgba(7,20,38,.75)); border: 1px solid rgba(56,189,248,.34); box-shadow: 0 0 18px rgba(56,189,248,.12); animation: missionEnter .65s ease-out; }
@keyframes missionEnter { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
.mission-title { font-size: 15px; color: #bae6fd; font-weight: 900; margin-bottom: 8px; }
.progress-track { height: 16px; border-radius: 999px; overflow: hidden; background: rgba(15,23,42,.95); border: 1px solid rgba(56,189,248,.30); }
.progress-fill { height: 100%; width: var(--progress); border-radius: 999px; background: linear-gradient(90deg, #0284c7, #38bdf8, #e0f2fe); background-size: 200% 100%; animation: progressGlow 1.8s linear infinite, fillGrow .7s ease-out; box-shadow: 0 0 16px rgba(56,189,248,.8); }
@keyframes progressGlow { from { background-position: 0% 0; } to { background-position: 200% 0; } }
@keyframes fillGrow { from { width: 0%; } to { width: var(--progress); } }
.progress-label { margin-top: 8px; color: #7dd3fc; font-weight: 800; font-size: 13px; }
.save-banner, .achievement-banner, .pr-banner {
    padding: 16px; margin: 0 0 18px 0; border-radius: 18px;
    background: linear-gradient(90deg, rgba(3,105,161,.92), rgba(14,165,233,.88), rgba(56,189,248,.92));
    border: 1px solid rgba(224,242,254,.65); box-shadow: 0 0 30px rgba(56,189,248,.55);
    animation: savePop 2.2s ease-out forwards;
}
.pr-banner { background: linear-gradient(90deg, rgba(88,28,135,.95), rgba(14,165,233,.92), rgba(250,204,21,.85)); }
.achievement-banner { background: linear-gradient(90deg, rgba(8,47,73,.95), rgba(2,132,199,.92), rgba(16,185,129,.88)); }
.save-banner-title { color: white; font-size: 19px; font-weight: 950; }
.save-banner-sub { color: #e0f2fe; font-size: 13px; font-weight: 800; }
@keyframes savePop { 0% { opacity: 0; transform: translateY(-18px) scale(.95); filter: blur(8px); } 18% { opacity: 1; transform: translateY(0) scale(1.02); filter: blur(0); } 100% { opacity: .95; transform: translateY(0) scale(1); } }
.heat-row { margin: 8px 0 12px 0; }
.heat-label { color: #e0f2fe; font-weight: 850; font-size: 14px; margin-bottom: 4px; }
.stButton button { background: linear-gradient(90deg, #0369a1, #0ea5e9, #38bdf8) !important; color: white !important; border: none !important; border-radius: 14px !important; font-weight: 900 !important; box-shadow: 0 0 15px rgba(56,189,248,.35); transition: .2s ease; }
.stButton button:hover { transform: scale(1.02); box-shadow: 0 0 26px rgba(56,189,248,.75); }
div[data-testid="stMetric"] { background: rgba(15,23,42,.65); border: 1px solid rgba(56,189,248,.20); padding: 12px; border-radius: 14px; box-shadow: 0 0 12px rgba(56,189,248,.08); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="nw-hero">
    <div class="nw-hero-title">⚡ Tyson Training</div>
    <div class="nw-hero-sub">Nightwing-inspired PPPPLA tracker</div>
    <span class="nw-badge">Bench Strength • V-Taper • Delts • Cardio • XP System</span>
    <div class="nw-scanline"></div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Menu", ["Home", "Profile", "Today", "Cardio", "Progress", "Goals", "Achievements", "Body Fat", "Bodyweight", "Delete Data", "Routine"])
st.markdown(f'<div class="page-transition">⚡ {page} module loaded</div>', unsafe_allow_html=True)

for key in ["just_saved_message", "pr_message", "achievement_message"]:
    if key not in st.session_state:
        st.session_state[key] = ""

if st.session_state.just_saved_message:
    st.markdown(f"""<div class="save-banner"><div class="save-banner-title">⚡ {st.session_state.just_saved_message}</div><div class="save-banner-sub">Training log synced • progression updated</div></div>""", unsafe_allow_html=True)
    st.session_state.just_saved_message = ""

if st.session_state.pr_message:
    st.markdown(f"""<div class="pr-banner"><div class="save-banner-title">🏆 {st.session_state.pr_message}</div><div class="save-banner-sub">New performance record detected</div></div>""", unsafe_allow_html=True)
    st.session_state.pr_message = ""

if st.session_state.achievement_message:
    st.markdown(f"""<div class="achievement-banner"><div class="save-banner-title">🎖 ACHIEVEMENT UNLOCKED</div><div class="save-banner-sub">{st.session_state.achievement_message}</div></div>""", unsafe_allow_html=True)
    st.session_state.achievement_message = ""

df = load_log()

# Unlock any achievements already earned from existing data/profile.
check_achievements()

if page == "Home":
    st.header("Command Centre")
    summary = workout_summary(df)
    xp_percent = min((summary["xp_into_level"] / summary["xp_needed"]) * 100, 100)
    bench_percent = min((summary["best_bench_1rm"] / 100) * 100, 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("Level", f"{summary['level']}")
    c2.metric("Rank", summary.get("rank", rank_name(summary["level"])))
    c3.metric("Total Sets", f"{summary['total_sets']}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Bodyweight", f"{summary['latest_bw']:.1f} kg" if summary["latest_bw"] else "No data")
    c5.metric("Best Bench e1RM", f"{summary['best_bench_1rm']:.1f} kg")
    c6.metric("Total Reps", f"{summary['total_reps']}")

    bf_log = load_bodyfat_log()
    if not bf_log.empty:
        bf_log["bf_mid"] = pd.to_numeric(bf_log["bf_mid"], errors="coerce").fillna(0)
        latest_bf = float(bf_log.iloc[-1]["bf_mid"])
        st.metric("Latest BF Estimate", f"{latest_bf:.1f}%")

    st.markdown(f"""
    <div class="mission-card">
        <div class="mission-title">LEVEL {summary['level']} — {summary.get('rank', rank_name(summary['level']))}</div>
        <div class="progress-track"><div class="progress-fill" style="--progress: {xp_percent:.1f}%;"></div></div>
        <div class="progress-label">Base level {summary.get('base_level', 1)} • {summary['xp_into_level']}/{summary['xp_needed']} XP to next level</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="mission-card">
        <div class="mission-title">100KG BENCH QUEST</div>
        <div class="progress-track"><div class="progress-fill" style="--progress: {bench_percent:.1f}%;"></div></div>
        <div class="progress-label">{summary['best_bench_1rm']:.1f}kg estimated / 100kg — {bench_percent:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Active Targets")

    bf_target = get_target("Body Fat", "Body Fat %")
    bw_target = get_target("Bodyweight", "Bodyweight")
    bench_target = get_target("1RM", "Barbell Bench Press (Strength)")
    squat_target = get_target("1RM", "Barbell Back Squat")

    render_target_bar("BODY FAT TARGET", latest_bodyfat_mid(), bf_target, "%", lower_is_better=True)
    render_target_bar("BODYWEIGHT TARGET", latest_bodyweight_value(), bw_target, "kg", lower_is_better=False)
    render_target_bar("BENCH 1RM TARGET", current_exercise_best_1rm("Barbell Bench Press (Strength)"), bench_target, "kg", lower_is_better=False)
    render_target_bar("SQUAT 1RM TARGET", current_exercise_best_1rm("Barbell Back Squat"), squat_target, "kg", lower_is_better=False)

    st.subheader("Muscle Heat Map")
    heat = muscle_heat_map(df)
    if heat.empty:
        st.info("No muscle volume logged yet.")
    else:
        max_sets = max(int(heat["sets"].max()), 1)
        for _, row in heat.iterrows():
            pct = min((int(row["sets"]) / max_sets) * 100, 100)
            st.markdown(f"""
            <div class="heat-row">
                <div class="heat-label">{row['muscle']} — {int(row['sets'])} sets</div>
                <div class="progress-track"><div class="progress-fill" style="--progress: {pct:.1f}%;"></div></div>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("Recent Achievements")
    ach = load_achievements()
    if ach.empty:
        st.info("No achievements unlocked yet. Open the Achievements tab to check requirements.")
    else:
        st.metric("Achievements", f"{len(ach)}/{len(ACHIEVEMENTS)}")
        for _, row in ach.sort_values("date_unlocked", ascending=False).head(5).iterrows():
            st.markdown(f"""<div class="dashboard-card"><div class="nw-card-title">{row['name']}</div><div class="nw-small">{row['description']}</div></div>""", unsafe_allow_html=True)
        st.caption("Open the Achievements tab to view all locked/unlocked achievements.")



elif page == "Profile":
    st.header("Athlete Profile")
    st.info("Set your starting level from your current real-world stats, so you don't start at Level 1.")

    profile = load_profile()
    latest = profile.iloc[-1].to_dict() if not profile.empty else {}

    c1, c2 = st.columns(2)
    with c1:
        height_cm = st.number_input("Height cm", min_value=100.0, max_value=230.0, step=0.5, value=float(latest.get("height_cm", 183.5) or 183.5))
        bodyweight_kg = st.number_input("Bodyweight kg", min_value=30.0, max_value=200.0, step=0.1, value=float(latest.get("bodyweight_kg", latest_bodyweight_value() or 76.0) or 76.0))
        bench_e1rm = st.number_input("Current bench estimated 1RM kg", min_value=0.0, max_value=250.0, step=2.5, value=float(latest.get("bench_e1rm", current_exercise_best_1rm("Barbell Bench Press (Strength)") or 96.0) or 96.0))
    with c2:
        squat_e1rm = st.number_input("Current squat estimated 1RM kg", min_value=0.0, max_value=350.0, step=2.5, value=float(latest.get("squat_e1rm", current_exercise_best_1rm("Barbell Back Squat") or 140.0) or 140.0))
        training_years = st.number_input("Training years", min_value=0.0, max_value=30.0, step=0.5, value=float(latest.get("training_years", 3.0) or 3.0))
        physique_score = st.slider("Physique score", 0, 15, int(float(latest.get("physique_score", 10) or 10)), help="0 beginner, 10 clearly trained, 15 very aesthetic")
        leanness_score = st.slider("Leanness score", 0, 15, int(float(latest.get("leanness_score", 10) or 10)), help="0 soft, 10 lean/visible abs, 15 very lean")

    preview_level = calculate_starting_level(bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score)
    st.metric("Calculated Starting Level", f"Level {preview_level} — {rank_name(preview_level)}")

    if st.button("Save Athlete Profile", type="primary"):
        level = save_profile(height_cm, bodyweight_kg, bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score)
        check_achievements()
        st.session_state.just_saved_message = f"PROFILE SAVED — LEVEL {level}"
        st.rerun()

    st.subheader("Rank System")
    st.write("🌱 Level 1-9: Rookie")
    st.write("⚔️ Level 10-24: Trainee")
    st.write("🦾 Level 25-39: Athlete")
    st.write("💎 Level 40-59: Aesthetic Tier")
    st.write("⚡ Level 60-74: Elite Physique")
    st.write("🗿 Level 75-89: Chad-Lite")
    st.write("👑 Level 90-99: Chad")
    st.write("☀️ Level 100: True Adam")



elif page == "Today":
    st.header("Today’s Workout")
    workout = st.selectbox("Workout", list(ROUTINE.keys()))
    workout_date = st.date_input("Date", value=date.today())

    if workout == "Rest":
        st.info("Rest day. Walk, stretch, eat protein, sleep.")
    else:
        total_sets = sum(ex[1] for ex in ROUTINE[workout])
        completed_sets = completed_sets_for_day(load_log(), workout_date, workout)
        percent = 0 if total_sets == 0 else min((completed_sets / total_sets) * 100, 100)
        st.caption(f"Target volume: {total_sets} working sets")
        st.markdown(f"""<div class="mission-card"><div class="mission-title">MISSION PROGRESS</div><div class="progress-track"><div class="progress-fill" style="--progress: {percent:.1f}%;"></div></div><div class="progress-label">{completed_sets}/{total_sets} sets complete — {percent:.1f}%</div></div>""", unsafe_allow_html=True)

        for exercise, sets, reps_target in ROUTINE[workout]:
            with st.expander(f"⚡ {exercise}", expanded=True):
                st.markdown(f"""<div class="nw-exercise-card"><div class="nw-card-title">{exercise}</div><div class="nw-small">{sets} sets × {reps_target}</div></div>""", unsafe_allow_html=True)

                if exercise == "Barbell Bench Press (Strength)":
                    st.markdown("""<div class="nw-note"><b>Strength bench:</b> heavy top set of 3-5 reps, then 3 back-off sets of 5-8 reps. Rest 3-5 minutes.</div>""", unsafe_allow_html=True)
                if exercise == "Paused Barbell Bench Press":
                    st.markdown("""<div class="nw-note"><b>Paused bench:</b> lighter bench with a 1-2 second dead stop on the chest. No bounce.</div>""", unsafe_allow_html=True)

                last = get_last_sets(load_log(), exercise)
                if last is not None:
                    last_text = ", ".join(f"{float(r.weight):g}kg × {int(r.reps)}" for r in last.itertuples())
                    st.caption(f"Last session: {last_text}")
                st.caption(f"Suggestion: {suggest_weight(load_log(), exercise)}")

                for set_no in range(1, sets + 1):
                    col1, col2 = st.columns(2)
                    with col1:
                        weight = st.number_input(f"{exercise} set {set_no} kg", min_value=0.0, step=2.5, key=f"{workout}-{exercise}-{set_no}-w", placeholder="kg")
                    with col2:
                        reps = st.number_input(f"{exercise} set {set_no} reps", min_value=0, step=1, key=f"{workout}-{exercise}-{set_no}-r", placeholder="reps")

                    if weight > 0 and reps > 0:
                        changed, is_pr, current_1rm, previous_best = save_set_auto(workout_date, workout, exercise, set_no, weight, reps)
                        if changed:
                            st.session_state.just_saved_message = f"{exercise} SET {set_no} AUTO-SAVED"
                            if is_pr:
                                st.session_state.pr_message = f"{exercise}: {current_1rm:.1f}kg e1RM"
                            unlocked = check_achievements()
                            if unlocked:
                                st.session_state.achievement_message = " • ".join(unlocked)
                            st.rerun()

        st.caption("Sets auto-save once both weight and reps are entered. Edit the number to overwrite that set.")


elif page == "Cardio":
    st.header("Cardio Tracker")
    cardio = load_csv(CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"])
    c_date = st.date_input("Date", value=date.today())
    c_type = st.selectbox("Type", ["Treadmill incline walk", "Outdoor walk", "Run", "Bike", "Stairmaster", "Boxing", "Other"])
    col1, col2 = st.columns(2)
    with col1:
        minutes = st.number_input("Minutes", min_value=0.0, step=5.0)
        distance = st.number_input("Distance km", min_value=0.0, step=0.1)
        incline = st.number_input("Incline %", min_value=0.0, step=0.5)
    with col2:
        speed = st.number_input("Speed km/h", min_value=0.0, step=0.1)
        calories = st.number_input("Calories", min_value=0.0, step=10.0)
    notes = st.text_input("Notes", placeholder="Example: 12% incline, 4.6km/h, post-pull")

    if st.button("Save Cardio", type="primary"):
        if minutes > 0:
            row = pd.DataFrame([{"date": str(c_date), "type": c_type, "minutes": minutes, "distance_km": distance, "incline": incline, "speed": speed, "calories": calories, "notes": notes, "timestamp": datetime.now().isoformat(timespec="seconds")}])
            pd.concat([cardio, row], ignore_index=True).to_csv(CARDIO_FILE, index=False)
            unlocked = check_achievements()
            st.session_state.just_saved_message = "CARDIO SAVED — ENGINE UPDATED"
            if unlocked:
                st.session_state.achievement_message = " • ".join(unlocked)
            st.rerun()
        else:
            st.warning("Enter minutes first.")

    if not cardio.empty:
        cardio["minutes"] = pd.to_numeric(cardio["minutes"], errors="coerce").fillna(0)
        cardio["distance_km"] = pd.to_numeric(cardio["distance_km"], errors="coerce").fillna(0)
        cardio["calories"] = pd.to_numeric(cardio["calories"], errors="coerce").fillna(0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total minutes", f"{cardio['minutes'].sum():.0f}")
        c2.metric("Total km", f"{cardio['distance_km'].sum():.1f}")
        c3.metric("Calories", f"{cardio['calories'].sum():.0f}")
        daily = cardio.groupby("date", as_index=False)["minutes"].sum()
        st.line_chart(daily, x="date", y="minutes")
        st.dataframe(cardio.sort_values("date", ascending=False), use_container_width=True)


elif page == "Progress":
    st.header("Progress")
    if df.empty:
        st.info("No workouts logged yet.")
    else:
        exercise = st.selectbox("Exercise", sorted(df["exercise"].dropna().unique()))
        ex = df[df["exercise"] == exercise].copy()
        ex = normalise_workout_log(ex)
        ex["weight"] = pd.to_numeric(ex["weight"], errors="coerce").fillna(0)
        ex["reps"] = pd.to_numeric(ex["reps"], errors="coerce").fillna(0)
        ex["estimated_1rm"] = ex.apply(lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])), axis=1)
        c1, c2 = st.columns(2)
        c1.metric("Best weight", f"{ex['weight'].max():g} kg")
        c2.metric("Best estimated 1RM", f"{ex['estimated_1rm'].max():.1f} kg")
        daily = ex.groupby("date", as_index=False)["estimated_1rm"].max()
        st.line_chart(daily, x="date", y="estimated_1rm")
        target = get_target("1RM", exercise)
        if target:
            render_target_bar(f"{exercise.upper()} 1RM TARGET", float(ex["estimated_1rm"].max()), target, "kg", lower_is_better=False)
        st.dataframe(ex.sort_values(["date", "set"], ascending=False), use_container_width=True)




elif page == "Goals":
    st.header("Targets")
    st.info("Set body composition and strength targets. These will show on the Home dashboard and update as you log data.")

    st.subheader("Set Body Targets")
    c1, c2 = st.columns(2)
    with c1:
        bf_target = st.number_input("Body fat % target", min_value=3.0, max_value=30.0, step=0.5, value=float(get_target("Body Fat", "Body Fat %") or 10.0))
        if st.button("Save Body Fat Target", type="primary"):
            save_or_update_target("Body Fat", "Body Fat %", bf_target, "%", "Target body fat percentage")
            st.session_state.just_saved_message = "BODY FAT TARGET SAVED"
            st.rerun()
    with c2:
        bw_default = get_target("Bodyweight", "Bodyweight") or latest_bodyweight_value() or 76.0
        bw_target = st.number_input("Bodyweight target kg", min_value=30.0, max_value=200.0, step=0.1, value=float(bw_default))
        if st.button("Save Bodyweight Target", type="primary"):
            save_or_update_target("Bodyweight", "Bodyweight", bw_target, "kg", "Target scale weight")
            st.session_state.just_saved_message = "BODYWEIGHT TARGET SAVED"
            st.rerun()

    st.subheader("Set 1RM Targets")
    all_exercises = sorted({exercise for workout in ROUTINE.values() for exercise, _, _ in workout})
    default_exercise = "Barbell Bench Press (Strength)" if "Barbell Bench Press (Strength)" in all_exercises else all_exercises[0]
    exercise_target = st.selectbox("Exercise", all_exercises, index=all_exercises.index(default_exercise))

    current_best = current_exercise_best_1rm(exercise_target)
    existing_target = get_target("1RM", exercise_target)
    sensible_default = existing_target or (100.0 if exercise_target == "Barbell Bench Press (Strength)" else max(current_best + 10, 50))

    c3, c4 = st.columns(2)
    with c3:
        st.metric("Current estimated 1RM", f"{current_best:.1f}kg" if current_best else "No data")
    with c4:
        target_1rm = st.number_input("Target estimated 1RM kg", min_value=1.0, max_value=400.0, step=2.5, value=float(sensible_default))

    if st.button("Save 1RM Target", type="primary"):
        save_or_update_target("1RM", exercise_target, target_1rm, "kg", "Target estimated one rep max")
        st.session_state.just_saved_message = f"{exercise_target} TARGET SAVED"
        st.rerun()

    st.subheader("Target Progress")
    render_target_bar("BODY FAT TARGET", latest_bodyfat_mid(), get_target("Body Fat", "Body Fat %"), "%", lower_is_better=True)
    render_target_bar("BODYWEIGHT TARGET", latest_bodyweight_value(), get_target("Bodyweight", "Bodyweight"), "kg", lower_is_better=False)

    targets = load_targets()
    one_rm_targets = targets[targets["target_type"].astype(str) == "1RM"] if not targets.empty else pd.DataFrame()
    if not one_rm_targets.empty:
        for _, row in one_rm_targets.iterrows():
            name = str(row["name"])
            target = float(row["target_value"])
            render_target_bar(f"{name.upper()} TARGET", current_exercise_best_1rm(name), target, "kg", lower_is_better=False)

    st.subheader("Saved Targets")
    targets = load_targets()
    if targets.empty:
        st.info("No targets saved yet.")
    else:
        st.dataframe(targets, use_container_width=True)




elif page == "Achievements":
    st.header("Achievements")
    st.info("Achievements auto-unlock from your existing logs, bodyweight, body fat, cardio, targets, and profile level.")

    unlocked = check_achievements()
    if unlocked:
        st.session_state.achievement_message = " • ".join(unlocked)
        st.rerun()

    ach = load_achievements()
    unlocked_ids = set(ach["achievement_id"].astype(str).tolist()) if not ach.empty else set()

    st.metric("Unlocked", f"{len(unlocked_ids)}/{len(ACHIEVEMENTS)}")

    categories = {
        "Strength": ["bench", "squat"],
        "Cut/Bulk/Body": ["bw", "bulk", "cut", "bf", "body"],
        "Cardio": ["cardio", "boxing"],
        "Consistency": ["streak", "ppppla", "workout", "set"],
        "Muscle Volume": ["chest", "back", "delts", "arms", "legs", "abs"],
        "Rank": ["aesthetic", "elite", "chad", "adam"],
        "All": [""],
    }

    category = st.selectbox("Category", list(categories.keys()))
    filters = categories[category]

    for achievement_id, (name, desc) in ACHIEVEMENTS.items():
        if category != "All" and not any(f in achievement_id for f in filters):
            continue

        unlocked_status = achievement_id in unlocked_ids
        status = "✅ UNLOCKED" if unlocked_status else "🔒 LOCKED"
        css_opacity = "1" if unlocked_status else ".45"

        st.markdown(
            f"""
            <div class="dashboard-card" style="opacity:{css_opacity};">
                <div class="nw-card-title">{name} — {status}</div>
                <div class="nw-small">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


elif page == "Body Fat":
    st.header("Body Fat Estimator")
    st.info("Use this as a trend tool, not an exact medical measurement. For best results, use the same lighting, pose, and time of day each check.")

    mode = st.radio("Estimate method", ["Measurement estimate", "AI photo estimate", "Combined estimate"], horizontal=True)

    latest_bw = 0.0
    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])
    if not bw_df.empty:
        bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
        latest_bw = float(bw_df.iloc[-1]["bodyweight"])

    col1, col2 = st.columns(2)
    with col1:
        estimate_date = st.date_input("Date", value=date.today(), key="bf_date")
        weight_kg = st.number_input("Bodyweight kg", min_value=0.0, step=0.1, value=float(latest_bw) if latest_bw else 76.0)
        height_cm = st.number_input("Height cm", min_value=100.0, max_value=230.0, step=0.5, value=183.5)
    with col2:
        waist_cm = st.number_input("Waist at navel cm (optional for AI)", min_value=0.0, step=0.5, value=0.0)
        neck_cm = st.number_input("Neck cm (optional for AI)", min_value=0.0, step=0.5, value=0.0)
        target_bf = st.number_input("Target BF%", min_value=5.0, max_value=25.0, step=0.5, value=10.0)

    navy_bf = None
    ai_data = None

    if mode in ["Measurement estimate", "Combined estimate"]:
        st.subheader("Measurement Estimate")

        if waist_cm <= 0 or neck_cm <= 0:
            navy_bf = None
            st.warning("Enter waist and neck measurements to use the measurement estimate. AI photo mode does not require them.")
        else:
            navy_bf = navy_body_fat_male(height_cm, waist_cm, neck_cm)

        if navy_bf is None and waist_cm > 0 and neck_cm > 0:
            st.warning("Enter valid waist/neck/height values. Waist must be larger than neck.")
        else:
            bf_low = max(navy_bf - 1.0, 3)
            bf_high = navy_bf + 1.0
            fat_mass, lean_mass, target_weight, fat_to_lose = bodyfat_outputs(weight_kg, navy_bf, target_bf)

            c1, c2, c3 = st.columns(3)
            c1.metric("Estimated BF%", f"{navy_bf:.1f}%")
            c2.metric("Lean Mass", f"{lean_mass:.1f}kg")
            c3.metric(f"{target_bf:.1f}% Target", f"{target_weight:.1f}kg")

            st.markdown(
                f"""
                <div class="mission-card">
                    <div class="mission-title">BODY FAT RANGE</div>
                    <div class="progress-track">
                        <div class="progress-fill" style="--progress: {min(navy_bf * 4, 100):.1f}%;"></div>
                    </div>
                    <div class="progress-label">Measurement range: {bf_low:.1f}% - {bf_high:.1f}% • Fat to lose to {target_bf:.1f}%: {safe_kg(fat_to_lose)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Save Measurement Estimate", type="primary"):
                save_bodyfat_estimate({
                    "date": str(estimate_date),
                    "method": "Measurement",
                    "bodyweight": weight_kg,
                    "height_cm": height_cm,
                    "waist_cm": waist_cm,
                    "neck_cm": neck_cm,
                    "bf_low": round(bf_low, 2),
                    "bf_high": round(bf_high, 2),
                    "bf_mid": round(navy_bf, 2),
                    "confidence": "medium",
                    "notes": f"US Navy-style measurement estimate. Target {target_bf}% weight: {target_weight:.1f}kg.",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                })
                st.session_state.just_saved_message = "BODY FAT ESTIMATE SAVED"
                st.rerun()

    if mode in ["AI photo estimate", "Combined estimate"]:
        st.subheader("AI Photo Estimate")
        st.caption("Requires OpenAI API key. Upload front/back physique photos. Waist/neck are optional and ignored unless you enter them.")

        c1, c2 = st.columns(2)
        with c1:
            front_photo = st.file_uploader("Front photo", type=["jpg", "jpeg", "png", "webp"], key="front_photo")
        with c2:
            back_photo = st.file_uploader("Back photo", type=["jpg", "jpeg", "png", "webp"], key="back_photo")

        c3, c4, c5 = st.columns(3)
        with c3:
            lighting = st.selectbox("Lighting", ["Normal", "Harsh/good gym lighting", "Dim", "Outdoor", "Unknown"])
        with c4:
            pump_status = st.selectbox("Pump", ["No pump", "Light pump", "Full pump", "Unknown"])
        with c5:
            time_of_day = st.selectbox("Time", ["Morning", "Afternoon", "Night", "Unknown"])

        model_name = st.text_input("OpenAI model", value="gpt-5.1", help="Use a vision-capable model available to your API account.")

        if st.button("Run AI Photo Estimate", type="primary"):
            with st.spinner("Analysing physique photos..."):
                ai_data, err = run_ai_bodyfat_estimate(
                    front_photo, back_photo, height_cm, weight_kg, waist_cm, neck_cm, lighting, pump_status, time_of_day, model_name
                )

            if err:
                st.error(err)
            else:
                st.session_state["last_ai_bf"] = ai_data
                st.session_state.just_saved_message = "AI BODY FAT ESTIMATE COMPLETE"
                st.rerun()

        ai_data = st.session_state.get("last_ai_bf", None)
        if ai_data:
            bf_low = float(ai_data["bf_low"])
            bf_high = float(ai_data["bf_high"])
            bf_mid = float(ai_data["bf_mid"])
            fat_mass, lean_mass, target_weight, fat_to_lose = bodyfat_outputs(weight_kg, bf_mid, target_bf)

            c1, c2, c3 = st.columns(3)
            c1.metric("AI BF Range", f"{bf_low:.1f}-{bf_high:.1f}%")
            c2.metric("AI Midpoint", f"{bf_mid:.1f}%")
            c3.metric("Confidence", str(ai_data.get("confidence", "unknown")).title())

            if waist_cm > 0 and neck_cm > 0:
                st.caption(f"Measurement data supplied: waist {waist_cm:.1f}cm, neck {neck_cm:.1f}cm")
            else:
                st.caption("Measurement data: not supplied — AI estimate used photos + height/weight only.")

            st.markdown(
                f"""
                <div class="mission-card">
                    <div class="mission-title">AI PHOTO BODY FAT ESTIMATE</div>
                    <div class="progress-track">
                        <div class="progress-fill" style="--progress: {min(bf_mid * 4, 100):.1f}%;"></div>
                    </div>
                    <div class="progress-label">{bf_low:.1f}% - {bf_high:.1f}% • Target {target_bf:.1f}% weight: {safe_kg(target_weight)} • Fat to lose: {safe_kg(fat_to_lose)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write(f"**Notes:** {ai_data.get('notes', '')}")
            if ai_data.get("fat_storage"):
                st.write(f"**Fat storage:** {ai_data.get('fat_storage')}")
            if ai_data.get("ten_percent_notes"):
                st.write(f"**10% notes:** {ai_data.get('ten_percent_notes')}")

            if st.button("Save AI Estimate", type="primary"):
                save_bodyfat_estimate({
                    "date": str(estimate_date),
                    "method": "AI Photo",
                    "bodyweight": weight_kg,
                    "height_cm": height_cm,
                    "waist_cm": waist_cm,
                    "neck_cm": neck_cm,
                    "bf_low": round(bf_low, 2),
                    "bf_high": round(bf_high, 2),
                    "bf_mid": round(bf_mid, 2),
                    "confidence": ai_data.get("confidence", ""),
                    "notes": ai_data.get("notes", ""),
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                })
                st.session_state.just_saved_message = "AI BODY FAT ESTIMATE SAVED"
                st.rerun()

    if mode == "Combined estimate":
        ai_data = st.session_state.get("last_ai_bf", None)
        if navy_bf is None:
            st.caption("Combined estimate needs waist and neck measurements plus an AI estimate.")
        if navy_bf is not None and ai_data:
            ai_mid = float(ai_data["bf_mid"])
            combined_mid = (navy_bf + ai_mid) / 2
            combined_low = min(navy_bf - 1, float(ai_data["bf_low"]))
            combined_high = max(navy_bf + 1, float(ai_data["bf_high"]))
            fat_mass, lean_mass, target_weight, fat_to_lose = bodyfat_outputs(weight_kg, combined_mid, target_bf)

            st.subheader("Combined Estimate")
            c1, c2, c3 = st.columns(3)
            c1.metric("Combined Range", f"{combined_low:.1f}-{combined_high:.1f}%")
            c2.metric("Combined Mid", f"{combined_mid:.1f}%")
            c3.metric(f"{target_bf:.1f}% Target", f"{target_weight:.1f}kg")

            if st.button("Save Combined Estimate", type="primary"):
                save_bodyfat_estimate({
                    "date": str(estimate_date),
                    "method": "Combined",
                    "bodyweight": weight_kg,
                    "height_cm": height_cm,
                    "waist_cm": waist_cm,
                    "neck_cm": neck_cm,
                    "bf_low": round(combined_low, 2),
                    "bf_high": round(combined_high, 2),
                    "bf_mid": round(combined_mid, 2),
                    "confidence": "medium",
                    "notes": f"Combined measurement + AI estimate. Target {target_bf}% weight: {target_weight:.1f}kg.",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                })
                st.session_state.just_saved_message = "COMBINED BODY FAT ESTIMATE SAVED"
                st.rerun()

    st.subheader("Body Fat Target")
    render_target_bar("BODY FAT TARGET", latest_bodyfat_mid(), get_target("Body Fat", "Body Fat %"), "%", lower_is_better=True)

    st.subheader("Body Fat History")
    bf_log = load_bodyfat_log()
    if bf_log.empty:
        st.info("No body fat estimates saved yet.")
    else:
        bf_log["bf_mid"] = pd.to_numeric(bf_log["bf_mid"], errors="coerce").fillna(0)
        st.line_chart(bf_log, x="date", y="bf_mid")
        st.dataframe(bf_log.sort_values("date", ascending=False), use_container_width=True)



elif page == "Bodyweight":
    st.header("Bodyweight")
    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])
    bw_date = st.date_input("Date", value=date.today())
    bw = st.number_input("Bodyweight kg", min_value=0.0, step=0.1)
    if st.button("Save Bodyweight", type="primary"):
        if bw > 0:
            row = pd.DataFrame([{"date": str(bw_date), "bodyweight": bw, "timestamp": datetime.now().isoformat(timespec="seconds")}])
            pd.concat([bw_df, row], ignore_index=True).to_csv(BODYWEIGHT_FILE, index=False)
            st.session_state.just_saved_message = "BODYWEIGHT SAVED — STATS UPDATED"
            st.rerun()
    if not bw_df.empty:
        bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
        st.metric("Latest bodyweight", f"{bw_df.iloc[-1]['bodyweight']:.1f} kg")
        st.line_chart(bw_df, x="date", y="bodyweight")
        st.dataframe(bw_df.sort_values("date", ascending=False), use_container_width=True)


elif page == "Delete Data":
    st.header("Delete Logged Data")
    st.warning("Use this to remove accidental entries. This permanently edits the CSV file.")
    log_type = st.selectbox("Choose log", ["Workout", "Cardio", "Body Fat", "Bodyweight", "Targets", "Profile", "Achievements"])
    if log_type == "Workout":
        path, columns = LOG_FILE, ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]
    elif log_type == "Cardio":
        path, columns = CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"]
    elif log_type == "Body Fat":
        path, columns = BODYFAT_FILE, ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm", "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"]
    elif log_type == "Bodyweight":
        path, columns = BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"]
    elif log_type == "Targets":
        path, columns = TARGETS_FILE, ["target_type", "name", "target_value", "unit", "created_at", "notes"]
    elif log_type == "Profile":
        path, columns = PROFILE_FILE, ["height_cm", "bodyweight_kg", "bench_e1rm", "squat_e1rm", "training_years", "physique_score", "leanness_score", "base_level", "created_at"]
    else:
        path, columns = ACHIEVEMENT_FILE, ["achievement_id", "name", "description", "date_unlocked"]

    data = load_csv(path, columns)
    if log_type == "Workout":
        data = normalise_workout_log(data)

    if data.empty:
        st.info(f"No {log_type.lower()} data found.")
    else:
        data = data.reset_index(drop=True)
        data.insert(0, "delete_id", data.index)
        st.dataframe(data, use_container_width=True)
        delete_ids_text = st.text_input("Enter delete_id numbers to delete", placeholder="Example: 0, 4, 7")
        if st.button("Delete Selected Rows", type="primary"):
            if delete_ids_text.strip():
                try:
                    ids_to_delete = [int(x.strip()) for x in delete_ids_text.split(",") if x.strip()]
                    original = load_csv(path, columns).reset_index(drop=True)
                    if log_type == "Workout":
                        original = normalise_workout_log(original)
                    valid_ids = [i for i in ids_to_delete if 0 <= i < len(original)]
                    updated = original.drop(index=valid_ids).reset_index(drop=True)
                    updated.to_csv(path, index=False)
                    st.session_state.just_saved_message = f"DELETED {len(valid_ids)} ROW(S)"
                    st.rerun()
                except ValueError:
                    st.error("Use numbers separated by commas only.")
        st.divider()
        confirm_text = f"DELETE {log_type.upper()}"
        confirm = st.text_input(f"Type {confirm_text} to clear all {log_type.lower()} data")
        if st.button(f"Clear All {log_type} Data"):
            if confirm == confirm_text:
                pd.DataFrame(columns=columns).to_csv(path, index=False)
                st.session_state.just_saved_message = f"ALL {log_type.upper()} DATA CLEARED"
                st.rerun()
            else:
                st.error(f"Confirmation did not match. Type: {confirm_text}")


elif page == "Routine":
    st.header("PPPPLA Routine")
    st.info("Strength bench = heavy top set + back-off sets. Paused bench = lighter controlled bench with a 1-2 second pause on the chest.")
    for day_num, (workout, exercises) in enumerate(ROUTINE.items(), start=1):
        st.subheader(f"Day {day_num}: {workout}")
        if workout == "Rest":
            st.write("Rest / walking / mobility")
        else:
            for exercise, sets, reps in exercises:
                st.write(f"**{exercise}** — {sets} sets × {reps}")
