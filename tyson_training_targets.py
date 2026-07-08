import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime, timedelta
import os
import base64
import json
import math
from supabase import create_client
import zipfile
from io import BytesIO

APP_TITLE = "Tyson Training"
LOG_FILE = Path("workout_log.csv")
BODYWEIGHT_FILE = Path("bodyweight_log.csv")
CARDIO_FILE = Path("cardio_log.csv")
BODYFAT_FILE = Path("bodyfat_log.csv")
MEASUREMENTS_FILE = Path("measurements.csv")
PHYSIQUE_RATING_FILE = Path("physique_ratings.csv")
CUSTOM_PLAN_FILE = Path("custom_workout_plan.csv")
TARGETS_FILE = Path("targets.csv")
PROFILE_FILE = Path("profile.csv")
ACHIEVEMENT_FILE = Path("achievements.csv")

def get_supabase_client():
    try:
        url = st.secrets.get("SUPABASE_URL", None)
        key = st.secrets.get("SUPABASE_KEY", None)
    except Exception:
        url, key = None, None

    url = url or os.getenv("SUPABASE_URL")
    key = key or os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


def supabase_enabled():
    return get_supabase_client() is not None


SUPABASE_TABLE_SCHEMAS = {
    "workout_log": ["date", "workout", "exercise", "muscle", "set", "weight", "reps", "estimated_1rm", "volume", "notes", "timestamp"],
    "bodyweight_log": ["date", "bodyweight", "timestamp"],
    "cardio_log": ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"],
    "bodyfat_log": ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm", "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"],
    "measurements": ["date", "bodyweight", "wrist_cm", "forearm_cm", "bicep_cm", "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "calf_cm", "shoulders_cm", "neck_cm", "notes", "timestamp"],
    "physique_ratings": ["date", "physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary", "timestamp"],
    "custom_workout_plan": ["plan_name", "workout", "exercise", "sets", "reps", "muscle", "reason", "day_goal", "timestamp"],
    "achievements": ["achievement_id", "name", "description", "date_unlocked"],
    "targets": ["target_type", "name", "target_value", "unit", "created_at", "notes"],
    "profile": ["height_cm", "bodyweight_kg", "bench_e1rm", "squat_e1rm", "training_years", "physique_score", "leanness_score", "base_level", "created_at"],
}


def clean_supabase_value(v):
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:
            pass

    if isinstance(v, (pd.Timestamp, datetime, date)):
        return str(v)

    return v


def clean_supabase_row(row, table_name):
    allowed = SUPABASE_TABLE_SCHEMAS.get(table_name, list(row.keys()))
    clean = {}
    for k in allowed:
        if k not in row:
            continue
        clean[k] = clean_supabase_value(row.get(k))

    # jsonb columns: accept stringified JSON or Python lists
    if table_name == "physique_ratings":
        for key in ["weak_points", "improvements"]:
            if isinstance(clean.get(key), str):
                try:
                    clean[key] = json.loads(clean[key])
                except Exception:
                    # Keep string if it is not JSON; diagnostic will reveal if table rejects it
                    pass

    return clean


def sb_select(table_name):
    sb = get_supabase_client()
    if sb is None:
        return None, "Supabase not configured"

    try:
        res = sb.table(table_name).select("*").execute()
        return res.data or [], None
    except Exception as e:
        return None, str(e)


def sb_insert(table_name, row, show_error=False):
    sb = get_supabase_client()
    if sb is None:
        msg = "Supabase not configured. Check SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets."
        if show_error:
            st.error(msg)
        return False, msg

    clean = clean_supabase_row(row, table_name)

    try:
        res = sb.table(table_name).insert(clean).execute()
        if show_error:
            st.success(f"✅ Insert succeeded: {table_name}")
            try:
                st.json(res.data)
            except Exception:
                st.write(res)
        return True, None

    except Exception as e:
        msg = str(e)
        if show_error:
            st.error(f"❌ Insert failed: {table_name}")
            st.code(msg)
            st.write("Attempted row:")
            st.json(clean)
        return False, msg


def sb_delete_matching(table_name, filters):
    sb = get_supabase_client()
    if sb is None:
        return False, "Supabase not configured"

    try:
        query = sb.table(table_name).delete()
        for k, v in filters.items():
            query = query.eq(k, v)
        query.execute()
        return True, None
    except Exception as e:
        return False, str(e)


def sb_delete_all(table_name):
    sb = get_supabase_client()
    if sb is None:
        return False, "Supabase not configured"

    try:
        # Delete all rows while avoiding requiring an id column
        sb.table(table_name).delete().neq(SUPABASE_TABLE_SCHEMAS[table_name][0], "__never_match__").execute()
        return True, None
    except Exception as e:
        return False, str(e)


def df_from_supabase(table_name, fallback_path, columns):
    data, err = sb_select(table_name)
    if data is not None:
        df = pd.DataFrame(data)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df
    return load_csv(fallback_path, columns)


def save_csv_backup(path, columns, row=None, df=None):
    current = load_csv(path, columns)
    if df is not None:
        df.to_csv(path, index=False)
        return
    if row is not None:
        pd.concat([current, pd.DataFrame([row])], ignore_index=True).to_csv(path, index=False)


def store_supabase_result(table_name, ok, err):
    if ok:
        st.session_state["last_supabase_write"] = f"Saved to Supabase: {table_name}"
        st.session_state["last_supabase_error"] = ""
    else:
        st.session_state["last_supabase_error"] = f"{table_name} insert failed: {err}"



# -----------------------------
# SUPABASE CONFIG / CSV BACKUP
# -----------------------------
@st.cache_resource






def append_csv_backup(path, columns, row):
    df = load_csv(path, columns)
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(path, index=False)



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


EXERCISE_LIBRARY = {
    "Upper Chest": [
        "Incline Barbell Bench Press",
        "Incline Dumbbell Bench Press",
        "Low-to-High Cable Fly",
        "Incline Smith Machine Press",
        "Incline Machine Chest Press",
    ],
    "Mid Chest": [
        "Barbell Bench Press",
        "Dumbbell Flat Bench Press",
        "Machine Chest Press",
        "Pec Deck Machine Fly",
        "Cable Chest Fly",
        "Decline Push-Up",
    ],
    "Side Delts": [
        "Cable Lateral Raise",
        "Dumbbell Lateral Raise",
        "Machine Lateral Raise",
        "Lean-Away Cable Lateral Raise",
        "Behind-the-Back Cable Lateral Raise",
    ],
    "Rear Delts": [
        "Reverse Pec Deck (Rear Delt Fly)",
        "Cable Rear Delt Fly",
        "Face Pull",
        "Chest-Supported Rear Delt Row",
    ],
    "Back Width": [
        "Lat Pulldown",
        "Neutral-Grip Lat Pulldown",
        "Assisted Pull-Up",
        "Cable Lat Pullover (Straight-Arm Pulldown)",
        "Single-Arm Cable Lat Pulldown",
    ],
    "Back Thickness": [
        "Chest-Supported Machine Row",
        "Chest-Supported Dumbbell Row",
        "Seated Cable Row",
        "T-Bar Row",
        "Machine High Row",
    ],
    "Biceps": [
        "EZ-Bar Curl",
        "Dumbbell Biceps Curl",
        "Incline Dumbbell Curl",
        "Cable Curl",
        "Preacher Curl Machine",
        "Hammer Curl",
    ],
    "Triceps": [
        "Cable Triceps Pushdown",
        "Overhead Cable Triceps Extension",
        "Machine Dip",
        "Close-Grip Bench Press",
        "Single-Arm Cable Triceps Extension",
    ],
    "Quads": [
        "Barbell Back Squat",
        "Hack Squat Machine",
        "Leg Press",
        "Bulgarian Split Squat",
        "Leg Extension",
        "Smith Machine Squat",
    ],
    "Hamstrings": [
        "Seated/Lying Leg Curl",
        "Romanian Deadlift",
        "Seated Leg Curl",
        "Lying Leg Curl",
        "Back Extension",
    ],
    "Glutes/Adductors": [
        "Hip Adduction Machine",
        "Hip Abduction Machine",
        "Cable Kickback",
        "Hip Thrust Machine",
    ],
    "Calves": [
        "Seated Calf Raise",
        "Standing Calf Raise",
        "Leg Press Calf Raise",
    ],
    "Abs": [
        "Machine Ab Crunch",
        "Lying Leg Raise",
        "Hanging Knee Raise",
        "Cable Crunch",
        "Weighted Sit-Up",
        "Decline Sit-Up",
    ],
    "Forearms/Grip": [
        "Wrist Curl",
        "Reverse Curl",
        "Farmer Carry",
        "Cable Wrist Curl",
    ],
}

FALLBACK_AESTHETIC_PLAN = {
    "Push 1 - Strength Bias": [
        ("Barbell Bench Press", 4, "3-6"),
        ("Incline Dumbbell Bench Press", 3, "8-12"),
        ("Machine Chest Press", 3, "8-12"),
        ("Lean-Away Cable Lateral Raise", 4, "15-25"),
        ("Overhead Cable Triceps Extension", 3, "10-15"),
        ("Cable Triceps Pushdown", 3, "12-20"),
    ],
    "Pull 1 - Width Bias": [
        ("Neutral-Grip Lat Pulldown", 4, "8-12"),
        ("Single-Arm Cable Lat Pulldown", 3, "10-15"),
        ("Chest-Supported Machine Row", 3, "8-12"),
        ("Cable Rear Delt Fly", 4, "15-25"),
        ("Incline Dumbbell Curl", 3, "10-15"),
        ("Hammer Curl", 3, "10-15"),
    ],
    "Push 2 - Upper Chest / Delts": [
        ("Incline Smith Machine Press", 4, "6-10"),
        ("Low-to-High Cable Fly", 3, "12-20"),
        ("Machine Lateral Raise", 5, "12-25"),
        ("Behind-the-Back Cable Lateral Raise", 3, "15-25"),
        ("Machine Dip", 3, "8-12"),
        ("Single-Arm Cable Triceps Extension", 3, "12-20"),
    ],
    "Pull 2 - Thickness / Rear Delts": [
        ("T-Bar Row", 4, "6-10"),
        ("Machine High Row", 3, "8-12"),
        ("Cable Lat Pullover (Straight-Arm Pulldown)", 3, "12-20"),
        ("Reverse Pec Deck (Rear Delt Fly)", 4, "15-25"),
        ("Preacher Curl Machine", 3, "8-12"),
        ("Cable Curl", 3, "12-20"),
    ],
    "Legs": [
        ("Hack Squat Machine", 4, "6-10"),
        ("Romanian Deadlift", 3, "8-12"),
        ("Leg Press", 3, "10-15"),
        ("Leg Extension", 3, "12-20"),
        ("Seated Leg Curl", 3, "10-15"),
        ("Standing Calf Raise", 4, "10-20"),
    ],
    "Aesthetic Weakpoint Day": [
        ("Machine Lateral Raise", 5, "15-25"),
        ("Low-to-High Cable Fly", 4, "12-20"),
        ("Single-Arm Cable Lat Pulldown", 3, "12-15"),
        ("Cable Rear Delt Fly", 4, "15-25"),
        ("Cable Crunch", 3, "10-15"),
        ("Hanging Knee Raise", 3, "10-20"),
    ],
}

MUSCLE_MAP = {
    # Chest / pressing
    "Barbell Bench Press (Strength)": "Chest",
    "Barbell Bench Press": "Chest",
    "Paused Barbell Bench Press": "Chest",
    "Dumbbell Flat Bench Press": "Chest",
    "Machine Chest Press": "Chest",
    "Incline Barbell Bench Press": "Upper Chest",
    "Incline Dumbbell Bench Press": "Upper Chest",
    "Incline Smith Machine Press": "Upper Chest",
    "Incline Machine Chest Press": "Upper Chest",
    "Pec Deck Machine Fly": "Chest",
    "Cable Chest Fly": "Chest",
    "Low-to-High Cable Fly": "Upper Chest",
    "Decline Push-Up": "Chest",
    "Machine Dip": "Triceps",

    # Delts / shoulders
    "Cable Lateral Raise": "Side Delts",
    "Dumbbell Lateral Raise": "Side Delts",
    "Machine Lateral Raise": "Side Delts",
    "Lean-Away Cable Lateral Raise": "Side Delts",
    "Behind-the-Back Cable Lateral Raise": "Side Delts",
    "Reverse Pec Deck (Rear Delt Fly)": "Rear Delts",
    "Cable Rear Delt Fly": "Rear Delts",
    "Face Pull": "Rear Delts",
    "Chest-Supported Rear Delt Row": "Rear Delts",

    # Back
    "Lat Pulldown": "Back Width",
    "Neutral-Grip Lat Pulldown": "Back Width",
    "Assisted Pull-Up": "Back Width",
    "Cable Lat Pullover (Straight-Arm Pulldown)": "Back Width",
    "Single-Arm Cable Lat Pulldown": "Back Width",
    "Chest-Supported Machine Row": "Back Thickness",
    "Chest-Supported Dumbbell Row": "Back Thickness",
    "Seated Cable Row": "Back Thickness",
    "T-Bar Row": "Back Thickness",
    "Machine High Row": "Back Thickness",

    # Biceps / forearms
    "EZ-Bar Curl": "Biceps",
    "Dumbbell Biceps Curl": "Biceps",
    "Incline Dumbbell Curl": "Biceps",
    "Cable Curl": "Biceps",
    "Preacher Curl Machine": "Biceps",
    "Hammer Curl": "Biceps",
    "Reverse Curl": "Forearms",
    "Wrist Curl": "Forearms",
    "Cable Wrist Curl": "Forearms",
    "Farmer Carry": "Forearms",

    # Triceps
    "Cable Triceps Pushdown": "Triceps",
    "Overhead Cable Triceps Extension": "Triceps",
    "Close-Grip Bench Press": "Triceps",
    "Single-Arm Cable Triceps Extension": "Triceps",

    # Legs
    "Barbell Back Squat": "Quads",
    "Hack Squat Machine": "Quads",
    "Leg Press": "Quads",
    "Bulgarian Split Squat": "Quads",
    "Leg Extension": "Quads",
    "Smith Machine Squat": "Quads",
    "Seated/Lying Leg Curl": "Hamstrings",
    "Romanian Deadlift": "Hamstrings",
    "Seated Leg Curl": "Hamstrings",
    "Lying Leg Curl": "Hamstrings",
    "Back Extension": "Hamstrings",
    "Hip Adduction Machine": "Adductors",
    "Hip Abduction Machine": "Glutes",
    "Cable Kickback": "Glutes",
    "Hip Thrust Machine": "Glutes",
    "Seated Calf Raise": "Calves",
    "Standing Calf Raise": "Calves",
    "Leg Press Calf Raise": "Calves",

    # Abs
    "Machine Ab Crunch": "Abs",
    "Lying Leg Raise": "Abs",
    "Hanging Knee Raise": "Abs",
    "Cable Crunch": "Abs",
    "Weighted Sit-Up": "Abs",
    "Decline Sit-Up": "Abs",
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






def load_bodyweight_log():
    return df_from_supabase("bodyweight_log", BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])


def load_cardio_log():
    return df_from_supabase("cardio_log", CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"])


def save_bodyweight_row(row):
    ok, err = sb_insert("bodyweight_log", row)
    store_supabase_result("bodyweight_log", ok, err)
    save_csv_backup(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"], row=row)


def save_cardio_row(row):
    ok, err = sb_insert("cardio_log", row)
    store_supabase_result("cardio_log", ok, err)
    save_csv_backup(CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"], row=row)


def normalise_workout_log(df):
    if "set" not in df.columns and "set_number" in df.columns:
        df = df.rename(columns={"set_number": "set"})
    for col in ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]:
        if col not in df.columns:
            df[col] = ""
    return df


def load_log():
    columns = ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]
    return normalise_workout_log(df_from_supabase("workout_log", LOG_FILE, columns))



def load_achievements():
    return df_from_supabase("achievements", ACHIEVEMENT_FILE, ["achievement_id", "name", "description", "date_unlocked"])



def save_achievement(achievement_id):
    ach = load_achievements()
    if achievement_id in ach["achievement_id"].astype(str).tolist():
        return False
    name, desc = ACHIEVEMENTS[achievement_id]
    row = {
        "achievement_id": achievement_id,
        "name": name,
        "description": desc,
        "date_unlocked": datetime.now().isoformat(timespec="seconds"),
    }
    ok, err = sb_insert("achievements", row)
    store_supabase_result("achievements", ok, err)
    save_csv_backup(ACHIEVEMENT_FILE, ["achievement_id", "name", "description", "date_unlocked"], row=row)
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

    timestamp = datetime.now().isoformat(timespec="seconds")
    muscle = infer_muscle_group(exercise) if "infer_muscle_group" in globals() else MUSCLE_MAP.get(exercise, "Other")

    csv_row = {
        "date": str(workout_date),
        "workout": str(workout),
        "exercise": str(exercise),
        "set": int(set_no),
        "weight": float(weight),
        "reps": int(reps),
        "timestamp": timestamp,
    }

    supabase_row = {
        **csv_row,
        "muscle": str(muscle),
        "estimated_1rm": float(current_1rm),
        "volume": float(weight) * int(reps),
        "notes": "",
    }

    if mask.any():
        old = df.loc[mask].iloc[-1]
        try:
            same_weight = float(old["weight"]) == float(weight)
            same_reps = int(float(old["reps"])) == int(reps)
        except Exception:
            same_weight = False, False

        if same_weight and same_reps:
            return False, False, current_1rm, previous_best

        df = df.loc[~mask].copy()
        sb_delete_matching("workout_log", {
            "date": str(workout_date),
            "workout": str(workout),
            "exercise": str(exercise),
            "set": int(set_no),
        })

    df = pd.concat([df, pd.DataFrame([csv_row])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)

    ok, err = sb_insert("workout_log", supabase_row)
    store_supabase_result("workout_log", ok, err)

    check_achievements()
    return True, is_pr, current_1rm, previous_best



def load_targets():
    columns = ["target_type", "name", "target_value", "unit", "created_at", "notes"]
    return df_from_supabase("targets", TARGETS_FILE, columns)



def save_or_update_target(target_type, name, target_value, unit, notes=""):
    df = load_targets()
    if not df.empty:
        df["target_type"] = df["target_type"].astype(str)
        df["name"] = df["name"].astype(str)
        df = df.loc[~((df["target_type"] == str(target_type)) & (df["name"] == str(name)))].copy()

    row = {
        "target_type": target_type,
        "name": name,
        "target_value": float(target_value),
        "unit": unit,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": notes,
    }

    sb_delete_matching("targets", {"target_type": str(target_type), "name": str(name)})
    ok, err = sb_insert("targets", row)
    store_supabase_result("targets", ok, err)
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(TARGETS_FILE, index=False)



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
    columns = ["height_cm", "bodyweight_kg", "bench_e1rm", "squat_e1rm", "training_years", "physique_score", "leanness_score", "base_level", "created_at"]
    return df_from_supabase("profile", PROFILE_FILE, columns)



def save_profile(height_cm, bodyweight_kg, bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score):
    base_level = calculate_starting_level(bench_e1rm, squat_e1rm, training_years, physique_score, leanness_score)
    row = {
        "height_cm": height_cm,
        "bodyweight_kg": bodyweight_kg,
        "bench_e1rm": bench_e1rm,
        "squat_e1rm": squat_e1rm,
        "training_years": training_years,
        "physique_score": physique_score,
        "leanness_score": leanness_score,
        "base_level": base_level,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    ok, err = sb_insert("profile", row)
    store_supabase_result("profile", ok, err)
    pd.DataFrame([row]).to_csv(PROFILE_FILE, index=False)
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
    bw_df = load_bodyweight_log()
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

    cardio = load_cardio_log()
    cardio["minutes"] = pd.to_numeric(cardio.get("minutes", 0), errors="coerce").fillna(0)
    cardio_minutes = float(cardio["minutes"].sum()) if not cardio.empty else 0

    xp = int(total_sets * 10 + cardio_minutes * 2)
    base_level = get_base_level()
    earned_levels = xp // 500
    level = max(1, min(base_level + earned_levels, 100))
    xp_into_level = xp % 500

    bw_df = load_bodyweight_log()
    latest_bw = 0
    if not bw_df.empty:
        bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
        latest_bw = float(bw_df.iloc[-1]["bodyweight"])

    return {
        "total_sets": total_sets, "total_reps": total_reps, "best_bench_1rm": best_bench_1rm,
        "latest_bw": latest_bw, "xp": xp, "level": level, "rank": rank_name(level), "base_level": base_level,
        "xp_into_level": xp_into_level, "xp_needed": 500
    }


def infer_muscle_group(exercise):
    name = str(exercise).strip()
    if name in MUSCLE_MAP:
        return MUSCLE_MAP[name]

    lower = name.lower()

    if any(x in lower for x in ["incline", "upper chest", "low-to-high"]):
        if any(x in lower for x in ["press", "bench", "fly", "chest"]):
            return "Upper Chest"

    if any(x in lower for x in ["bench", "pec", "chest", "fly", "push-up", "push up"]):
        return "Chest"

    if any(x in lower for x in ["lateral raise", "side delt", "machine lateral", "lean-away"]):
        return "Side Delts"

    if any(x in lower for x in ["rear delt", "reverse pec", "face pull"]):
        return "Rear Delts"

    if any(x in lower for x in ["pulldown", "pull-up", "pull up", "lat pullover", "straight-arm", "straight arm", "lat"]):
        return "Back Width"

    if any(x in lower for x in ["row", "t-bar", "machine high row", "high row"]):
        return "Back Thickness"

    if any(x in lower for x in ["curl", "bicep", "preacher", "hammer"]):
        if any(x in lower for x in ["wrist", "reverse", "farmer"]):
            return "Forearms"
        return "Biceps"

    if any(x in lower for x in ["tricep", "pushdown", "overhead extension", "close-grip", "dip"]):
        return "Triceps"

    if any(x in lower for x in ["squat", "leg press", "leg extension", "quad", "bulgarian"]):
        return "Quads"

    if any(x in lower for x in ["leg curl", "hamstring", "romanian", "rdl", "back extension"]):
        return "Hamstrings"

    if "calf" in lower:
        return "Calves"

    if any(x in lower for x in ["adduction", "adductor"]):
        return "Adductors"

    if any(x in lower for x in ["abduction", "kickback", "hip thrust", "glute"]):
        return "Glutes"

    if any(x in lower for x in ["crunch", "sit-up", "sit up", "leg raise", "knee raise", "abs"]):
        return "Abs"

    return "Other"


def muscle_heat_map(df):
    df = normalise_workout_log(df.copy())
    if df.empty:
        return pd.DataFrame(columns=["muscle", "sets"])
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0)
    df["reps"] = pd.to_numeric(df["reps"], errors="coerce").fillna(0)
    df = df[(df["weight"] > 0) & (df["reps"] > 0)]
    if df.empty:
        return pd.DataFrame(columns=["muscle", "sets"])
    df["muscle"] = df["exercise"].apply(infer_muscle_group)
    return (
        df.groupby("muscle", as_index=False)
        .size()
        .rename(columns={"size": "sets"})
        .sort_values("sets", ascending=False)
    )

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
    bw_df = load_bodyweight_log()
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







def load_measurements():
    columns = ["date", "bodyweight", "wrist_cm", "forearm_cm", "bicep_cm", "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "calf_cm", "shoulders_cm", "neck_cm", "notes", "timestamp"]
    return df_from_supabase("measurements", MEASUREMENTS_FILE, columns)



def save_measurements(row):
    ok, err = sb_insert("measurements", row)
    store_supabase_result("measurements", ok, err)
    save_csv_backup(MEASUREMENTS_FILE, ["date", "bodyweight", "wrist_cm", "forearm_cm", "bicep_cm", "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "calf_cm", "shoulders_cm", "neck_cm", "notes", "timestamp"], row=row)



def latest_measurements():
    df = load_measurements()
    if df.empty:
        return {}
    return df.iloc[-1].to_dict()


def load_physique_ratings():
    columns = ["date", "physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary", "timestamp"]
    return df_from_supabase("physique_ratings", PHYSIQUE_RATING_FILE, columns)



def save_physique_rating(row):
    ok, err = sb_insert("physique_ratings", row)
    store_supabase_result("physique_ratings", ok, err)
    save_csv_backup(PHYSIQUE_RATING_FILE, ["date", "physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary", "timestamp"], row=row)



def encode_uploaded_image(uploaded_file):
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def run_ai_physique_rating(front_photo, side_photo, back_photo, stats, model_name):
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
        return None, "Missing OPENAI_API_KEY. Add it to Streamlit Cloud secrets."

    if front_photo is None and side_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."

    client = OpenAI(api_key=api_key)

    user_text = f"""
You are a physique coach rating a male physique for a fitness app.

Do not identify the person. This is not medical advice.
Give practical bodybuilding/aesthetic feedback.

Known stats/measurements:
{json.dumps(stats, indent=2)}

Return ONLY valid JSON with this exact schema:
{{
  "physique_score": number,
  "leanness_score": number,
  "symmetry_score": number,
  "muscularity_score": number,
  "confidence": "low" | "medium" | "high",
  "weak_points": ["short point", "short point", "short point"],
  "improvements": ["short actionable improvement", "short actionable improvement", "short actionable improvement"],
  "summary": "short honest summary",
  "training_priority": ["Chest", "Side delts", "Back width", "Arms", "Legs", "Abs"]
}}

Scoring:
- physique_score out of 15 = overall aesthetic development
- leanness_score out of 15 = leanness/definition
- symmetry_score out of 15 = balance/proportions
- muscularity_score out of 15 = muscle size/fullness
Be realistic and useful, not flattering.
"""

    content = [{"type": "input_text", "text": user_text}]

    if front_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(front_photo)})
    if side_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(side_photo)})
    if back_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(back_photo)})

    try:
        response = client.responses.create(
            model=model_name,
            input=[{"role": "user", "content": content}],
        )
        text = getattr(response, "output_text", None) or str(response)
        text_clean = text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text_clean)

        required = ["physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary"]
        for key in required:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"

        return data, None

    except Exception as e:
        return None, f"AI physique rating failed: {e}"



def run_ai_custom_plan_from_physique(rating, measurements, goals, model_name):
    """
    Uses AI to build a custom plan from the exercise library, not just reusing the default PPPPLA.
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
        return None, "Missing OPENAI_API_KEY. Add it to Streamlit Cloud secrets."

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an expert bodybuilding coach making a custom workout plan for an aesthetic-focused lifter.

The user currently runs PPPPLA, but DO NOT simply repeat the existing routine.
Choose the best exercises from the exercise library below to target the physique weak points.

Exercise library:
{json.dumps(EXERCISE_LIBRARY, indent=2)}

Physique rating/weak points:
{json.dumps(rating, indent=2)}

Measurements:
{json.dumps(measurements, indent=2)}

Goal:
{goals}

Requirements:
- Create a 6-day split using these day names:
  1. Push 1 - Strength Bias
  2. Pull 1 - Width Bias
  3. Push 2 - Hypertrophy Bias
  4. Pull 2 - Thickness Bias
  5. Legs
  6. Aesthetic Weakpoint Day
- Each day must have 5-8 exercises.
- Choose exercises from the library. You may include the user's favourite exercises if suitable, but the plan must be meaningfully different from the old PPPPLA.
- Prioritise weak points from the physique rating.
- Include sets, reps, and a short reason for each exercise.
- Keep bench press progression if chest/strength is relevant.
- Bias side delts, upper chest, lats, rear delts, abs, or whatever weak points the AI rating says.
- Return ONLY valid JSON.

JSON schema:
{{
  "plan_name": "string",
  "rationale": "short summary",
  "weekly_focus": ["focus 1", "focus 2", "focus 3"],
  "days": [
    {{
      "day": "Push 1 - Strength Bias",
      "goal": "short day goal",
      "exercises": [
        {{
          "exercise": "exercise name",
          "sets": number,
          "reps": "rep range string",
          "reason": "why selected"
        }}
      ]
    }}
  ]
}}
"""

    try:
        response = client.responses.create(
            model=model_name,
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        )
        text = getattr(response, "output_text", None) or str(response)
        text_clean = text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text_clean)

        if "days" not in data:
            return None, f"AI response missing 'days'. Raw: {text[:500]}"

        return data, None

    except Exception as e:
        return None, f"AI custom plan failed: {e}"


def save_ai_custom_plan(ai_plan):
    rows = []
    for day in ai_plan.get("days", []):
        for ex in day.get("exercises", []):
            exercise = ex.get("exercise", "")
            rows.append({
                "workout": day.get("day", ""),
                "exercise": exercise,
                "sets": ex.get("sets", ""),
                "reps": ex.get("reps", ""),
                "muscle": infer_muscle_group(exercise) if "infer_muscle_group" in globals() else "",
                "reason": ex.get("reason", ""),
                "day_goal": day.get("goal", ""),
                "plan_name": ai_plan.get("plan_name", "AI Custom Plan"),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })

    if not rows:
        return False

    sb_delete_all("custom_workout_plan")
    for row in rows:
        ok, err = sb_insert("custom_workout_plan", row)
        store_supabase_result("custom_workout_plan", ok, err)

    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)
    return True



def save_fallback_custom_plan(plan):
    rows = []
    for workout, exercises in plan.items():
        for exercise, sets, reps in exercises:
            rows.append({
                "workout": workout,
                "exercise": exercise,
                "sets": sets,
                "reps": reps,
                "muscle": infer_muscle_group(exercise) if "infer_muscle_group" in globals() else "",
                "reason": "Fallback weak-point aesthetic plan",
                "day_goal": "Aesthetic development",
                "plan_name": "Fallback Aesthetic Weakpoint Plan",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })

    sb_delete_all("custom_workout_plan")
    for row in rows:
        ok, err = sb_insert("custom_workout_plan", row)
        store_supabase_result("custom_workout_plan", ok, err)

    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)



def generate_custom_plan_from_data(weak_points=None, priorities=None, goal="Aesthetic / lean bulk"):
    weak_points = weak_points or []
    priorities = priorities or []

    priority_text = " ".join([str(x).lower() for x in weak_points + priorities])

    extra_side_delts = "delt" in priority_text or "shoulder" in priority_text or "width" in priority_text
    extra_chest = "chest" in priority_text or "pec" in priority_text
    extra_back = "back" in priority_text or "lat" in priority_text or "v-taper" in priority_text
    extra_arms = "arm" in priority_text or "bicep" in priority_text or "tricep" in priority_text
    extra_legs = "leg" in priority_text or "quad" in priority_text or "hamstring" in priority_text

    plan = {
        "Push 1 - Strength": [
            ("Barbell Bench Press (Strength)", 4, "Top set 3-5 + 3 back-off sets 5-8"),
            ("Dumbbell Flat Bench Press", 3 + int(extra_chest), "8-12"),
            ("Pec Deck Machine Fly", 3 + int(extra_chest), "10-15"),
            ("Cable Lateral Raise", 4 + int(extra_side_delts), "12-20"),
            ("Cable Triceps Pushdown", 4, "10-15"),
            ("Decline Push-Up", 2, "AMRAP"),
        ],
        "Pull 1 - Back Thickness": [
            ("Chest-Supported Machine Row", 4, "6-10"),
            ("Lat Pulldown", 4 + int(extra_back), "8-12"),
            ("Chest-Supported Dumbbell Row", 3, "8-12"),
            ("Reverse Pec Deck (Rear Delt Fly)", 4 + int(extra_side_delts), "15-25"),
            ("EZ-Bar Curl", 4 + int(extra_arms), "8-12"),
            ("Dumbbell Biceps Curl", 3, "10-15"),
        ],
        "Push 2 - Hypertrophy": [
            ("Paused Barbell Bench Press", 3, "5-8"),
            ("Dumbbell Flat Bench Press", 3 + int(extra_chest), "8-12"),
            ("Pec Deck Machine Fly", 4, "12-20"),
            ("Dumbbell Lateral Raise", 5 + int(extra_side_delts), "15-25"),
            ("Cable Lateral Raise", 3, "15-25"),
            ("Cable Triceps Pushdown", 4 + int(extra_arms), "12-20"),
        ],
        "Pull 2 - Width / V-Taper": [
            ("Lat Pulldown", 4 + int(extra_back), "10-15"),
            ("Cable Lat Pullover (Straight-Arm Pulldown)", 4 + int(extra_back), "12-20"),
            ("Chest-Supported Machine Row", 3, "8-12"),
            ("Face Pull", 3, "15-25"),
            ("Reverse Pec Deck (Rear Delt Fly)", 3, "15-25"),
            ("EZ-Bar Curl", 3 + int(extra_arms), "10-15"),
        ],
        "Legs": [
            ("Barbell Back Squat", 3, "5-8"),
            ("Hack Squat Machine", 4 + int(extra_legs), "8-12"),
            ("Seated/Lying Leg Curl", 4, "10-15"),
            ("Leg Extension", 4 + int(extra_legs), "12-20"),
            ("Seated Calf Raise", 5, "10-20"),
            ("Hip Adduction Machine", 3, "12-20"),
        ],
        "Aesthetics": [
            ("Cable Lateral Raise", 5 + int(extra_side_delts), "15-25"),
            ("Cable Lat Pullover (Straight-Arm Pulldown)", 3 + int(extra_back), "12-20"),
            ("Pec Deck Machine Fly", 4 + int(extra_chest), "12-20"),
            ("Reverse Pec Deck (Rear Delt Fly)", 4, "15-25"),
            ("Dumbbell Biceps Curl", 3 + int(extra_arms), "10-15"),
            ("Cable Triceps Pushdown", 3 + int(extra_arms), "10-15"),
            ("Machine Ab Crunch", 3, "10-20"),
            ("Lying Leg Raise", 3, "12-20"),
            ("Weighted Sit-Up", 2, "10-15"),
        ],
    }

    return plan


def save_custom_plan(plan):
    rows = []
    for workout, exercises in plan.items():
        for exercise, sets, reps in exercises:
            rows.append({
                "workout": workout,
                "exercise": exercise,
                "sets": sets,
                "reps": reps,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)


def load_custom_plan():
    columns = ["workout", "exercise", "sets", "reps", "reason", "day_goal", "plan_name", "timestamp"]
    return df_from_supabase("custom_workout_plan", CUSTOM_PLAN_FILE, columns)



def save_bodyfat_estimate(row):
    ok, err = sb_insert("bodyfat_log", row)
    store_supabase_result("bodyfat_log", ok, err)
    save_csv_backup(BODYFAT_FILE, ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm", "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"], row=row)



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





def navy_body_fat_male(height_cm, waist_cm, neck_cm):
    """US Navy male body fat estimate. Uses inches internally. Returns None for invalid inputs."""
    try:
        height_in = float(height_cm) / 2.54
        waist_in = float(waist_cm) / 2.54
        neck_in = float(neck_cm) / 2.54
        if height_in <= 0 or neck_in <= 0 or waist_in <= neck_in:
            return None
        return 86.010 * math.log10(waist_in - neck_in) - 70.041 * math.log10(height_in) + 36.76
    except Exception:
        return None

def load_bodyfat_log():
    columns = ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm", "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"]
    return df_from_supabase("bodyfat_log", BODYFAT_FILE, columns)



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
    cardio = load_cardio_log()
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
    if muscle_sets_count(heat, ["Chest", "Upper Chest"]) >= 50: unlock("chest_50")
    if muscle_sets_count(heat, ["Chest", "Upper Chest"]) >= 150: unlock("chest_150")
    if muscle_sets_count(heat, ["Back", "Back Width", "Back Thickness"]) >= 50: unlock("back_50")
    if muscle_sets_count(heat, ["Back", "Back Width", "Back Thickness"]) >= 150: unlock("back_150")
    delt_sets = muscle_sets_count(heat, ["Delts", "Side Delts", "Rear Delts"])
    if delt_sets >= 50: unlock("delts_50")
    if delt_sets >= 150: unlock("delts_150")
    if muscle_sets_count(heat, ["Biceps", "Triceps"]) >= 100: unlock("arms_100")
    if muscle_sets_count(heat, ["Legs", "Quads", "Hamstrings", "Glutes", "Adductors", "Calves"]) >= 100: unlock("legs_100")
    if muscle_sets_count(heat, ["Abs"]) >= 50: unlock("abs_50")

    # Rank achievements
    if summary["level"] >= 40: unlock("aesthetic_tier")
    if summary["level"] >= 60: unlock("elite_physique")
    if summary["level"] >= 75: unlock("chad_lite")
    if summary["level"] >= 90: unlock("chad")
    if summary["level"] >= 100: unlock("true_adam")

    return unlocked



# ============================================================
# FINAL MERGE-SAFE DEFINITIONS / DEBUG PATCH
# ============================================================

def load_bodyfat_log():
    return load_csv(
        BODYFAT_FILE,
        ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm",
         "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"],
    )


def save_bodyfat_estimate(row):
    df = load_bodyfat_log()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(BODYFAT_FILE, index=False)


def bodyfat_outputs(weight_kg, bf_percent, target_bf=10.0):
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


def load_targets():
    return load_csv(TARGETS_FILE, ["target_type", "name", "target_value", "unit", "created_at", "notes"])


def save_or_update_target(target_type, name, target_value, unit, notes=""):
    df = load_targets()
    if not df.empty:
        df["target_type"] = df["target_type"].astype(str)
        df["name"] = df["name"].astype(str)
        df = df.loc[~((df["target_type"] == str(target_type)) & (df["name"] == str(name)))].copy()
    new_row = {
        "target_type": target_type,
        "name": name,
        "target_value": float(target_value),
        "unit": unit,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": notes,
    }
    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(TARGETS_FILE, index=False)


def get_target(target_type, name):
    df = load_targets()
    if df.empty:
        return None
    matches = df[(df["target_type"].astype(str) == str(target_type)) & (df["name"].astype(str) == str(name))]
    if matches.empty:
        return None
    try:
        return float(matches.iloc[-1]["target_value"])
    except Exception:
        return None


def latest_bodyweight_value():
    bw_df = load_bodyweight_log()
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


def current_exercise_best_1rm(exercise_name):
    df = load_log()
    if df.empty:
        return 0
    df = normalise_workout_log(df)
    ex = df[df["exercise"].astype(str) == str(exercise_name)].copy()
    if ex.empty:
        return 0
    ex["weight"] = pd.to_numeric(ex["weight"], errors="coerce").fillna(0)
    ex["reps"] = pd.to_numeric(ex["reps"], errors="coerce").fillna(0)
    ex["estimated_1rm"] = ex.apply(lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])), axis=1)
    return float(ex["estimated_1rm"].max())


def render_target_bar(title, current, target, unit, lower_is_better=False):
    if current is None or target is None:
        st.info(f"{title}: Set a target to begin.")
        return
    try:
        current = float(current)
        target = float(target)
    except Exception:
        st.info(f"{title}: Waiting for valid target/data.")
        return
    if target <= 0:
        st.info(f"{title}: Target must be above 0.")
        return
    progress = 100 if (lower_is_better and current <= target) else ((target / current) * 100 if lower_is_better else (current / target) * 100)
    progress = max(0, min(progress, 100))
    st.markdown(
        f"""
        <div class="mission-card">
            <div class="mission-title">{title}</div>
            <div class="progress-track"><div class="progress-fill" style="--progress:{progress:.1f}%;"></div></div>
            <div class="progress-label">{current:.1f}{unit} / {target:.1f}{unit} ({progress:.0f}%)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def encode_image_for_openai(uploaded_file):
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def encode_uploaded_image(uploaded_file):
    return encode_image_for_openai(uploaded_file)


def _get_openai_client():
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
        return None, "Missing OPENAI_API_KEY. Add it to Streamlit Cloud secrets."
    return OpenAI(api_key=api_key), None


def run_ai_bodyfat_estimate(front_photo, back_photo, height_cm, weight_kg, waist_cm, neck_cm, lighting, pump_status, time_of_day, model_name):
    client, err = _get_openai_client()
    if err:
        return None, err
    if front_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."
    user_text = f"""
Estimate male body fat from physique photos for a fitness app. Return ONLY valid JSON.

Stats:
Height: {height_cm} cm
Bodyweight: {weight_kg} kg
Waist: {waist_cm if waist_cm and waist_cm > 0 else "Not provided"}
Neck: {neck_cm if neck_cm and neck_cm > 0 else "Not provided"}
Lighting: {lighting}
Pump: {pump_status}
Time: {time_of_day}

Do not use waist/neck unless provided. Be conservative with flattering lighting or pump.

Schema:
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
        response = client.responses.create(model=model_name, input=[{"role": "user", "content": content}])
        text = getattr(response, "output_text", None) or str(response)
        data = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        for key in ["bf_low", "bf_high", "bf_mid", "confidence", "notes"]:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"
        return data, None
    except Exception as e:
        return None, f"AI estimate failed: {e}"


def load_measurements():
    return load_csv(
        MEASUREMENTS_FILE,
        ["date", "bodyweight", "wrist_cm", "forearm_cm", "bicep_cm", "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "calf_cm", "shoulders_cm", "neck_cm", "notes", "timestamp"],
    )


def save_measurements(row):
    df = load_measurements()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(MEASUREMENTS_FILE, index=False)


def latest_measurements():
    df = load_measurements()
    if df.empty:
        return {}
    return df.iloc[-1].to_dict()


def load_physique_ratings():
    return load_csv(
        PHYSIQUE_RATING_FILE,
        ["date", "physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary", "timestamp"],
    )


def save_physique_rating(row):
    df = load_physique_ratings()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(PHYSIQUE_RATING_FILE, index=False)


def run_ai_physique_rating(front_photo, side_photo, back_photo, stats, model_name):
    client, err = _get_openai_client()
    if err:
        return None, err
    if front_photo is None and side_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."
    user_text = f"""
Rate this male physique for an aesthetic fitness app. Do not identify the person. Return ONLY valid JSON.

Stats:
{json.dumps(stats, indent=2)}

Schema:
{{
  "physique_score": number,
  "leanness_score": number,
  "symmetry_score": number,
  "muscularity_score": number,
  "confidence": "low" | "medium" | "high",
  "weak_points": ["short point", "short point", "short point"],
  "improvements": ["short actionable improvement", "short actionable improvement", "short actionable improvement"],
  "summary": "short honest summary",
  "training_priority": ["Chest", "Side delts", "Back width", "Arms", "Legs", "Abs"]
}}

Scores are out of 15. Be realistic, not flattering.
"""
    content = [{"type": "input_text", "text": user_text}]
    if front_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(front_photo)})
    if side_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(side_photo)})
    if back_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(back_photo)})
    try:
        response = client.responses.create(model=model_name, input=[{"role": "user", "content": content}])
        text = getattr(response, "output_text", None) or str(response)
        data = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        required = ["physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary"]
        for key in required:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"
        return data, None
    except Exception as e:
        return None, f"AI physique rating failed: {e}"


def load_custom_plan():
    return load_csv(CUSTOM_PLAN_FILE, ["workout", "exercise", "sets", "reps", "reason", "day_goal", "plan_name", "timestamp"])


def save_ai_custom_plan(ai_plan):
    rows = []
    for day in ai_plan.get("days", []):
        for ex in day.get("exercises", []):
            rows.append({
                "workout": day.get("day", ""),
                "exercise": ex.get("exercise", ""),
                "sets": ex.get("sets", ""),
                "reps": ex.get("reps", ""),
                "reason": ex.get("reason", ""),
                "day_goal": day.get("goal", ""),
                "plan_name": ai_plan.get("plan_name", "AI Custom Plan"),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
    if not rows:
        return False
    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)
    return True


def save_fallback_custom_plan(plan):
    rows = []
    for workout, exercises in plan.items():
        for exercise, sets, reps in exercises:
            rows.append({
                "workout": workout,
                "exercise": exercise,
                "sets": sets,
                "reps": reps,
                "reason": "Fallback weak-point aesthetic plan",
                "day_goal": "Aesthetic development",
                "plan_name": "Fallback Aesthetic Weakpoint Plan",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)


def run_ai_custom_plan_from_physique(rating, measurements, goals, model_name):
    client, err = _get_openai_client()
    if err:
        return None, err
    prompt = f"""
You are an expert bodybuilding coach making a custom workout plan for an aesthetic-focused lifter.

DO NOT simply repeat the user's current PPPPLA routine.
Choose the best exercises from this exercise library:
{json.dumps(EXERCISE_LIBRARY, indent=2)}

Physique rating:
{json.dumps(rating, indent=2)}

Measurements:
{json.dumps(measurements, indent=2)}

Goal:
{goals}

Create a 6-day split:
Push 1 - Strength Bias
Pull 1 - Width Bias
Push 2 - Hypertrophy Bias
Pull 2 - Thickness Bias
Legs
Aesthetic Weakpoint Day

Each day: 5-8 exercises. Include exercise, sets, reps, reason.
Return ONLY valid JSON:
{{
  "plan_name": "string",
  "rationale": "short summary",
  "weekly_focus": ["focus 1", "focus 2", "focus 3"],
  "days": [
    {{
      "day": "Push 1 - Strength Bias",
      "goal": "short day goal",
      "exercises": [
        {{"exercise": "exercise name", "sets": 3, "reps": "8-12", "reason": "why selected"}}
      ]
    }}
  ]
}}
"""
    try:
        response = client.responses.create(model=model_name, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}])
        text = getattr(response, "output_text", None) or str(response)
        data = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        if "days" not in data:
            return None, f"AI response missing 'days'. Raw: {text[:500]}"
        return data, None
    except Exception as e:
        return None, f"AI custom plan failed: {e}"


# ============================================================
# FINAL SAFETY HELPERS — DO NOT REMOVE
# ============================================================

def load_bodyfat_log():
    return load_csv(
        BODYFAT_FILE,
        [
            "date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm",
            "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"
        ],
    )


def save_bodyfat_estimate(row):
    df = load_bodyfat_log()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(BODYFAT_FILE, index=False)


def bodyfat_outputs(weight_kg, bf_percent, target_bf=10.0):
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


def load_targets():
    return load_csv(TARGETS_FILE, ["target_type", "name", "target_value", "unit", "created_at", "notes"])


def save_or_update_target(target_type, name, target_value, unit, notes=""):
    df = load_targets()
    if not df.empty:
        df["target_type"] = df["target_type"].astype(str)
        df["name"] = df["name"].astype(str)
        df = df.loc[~((df["target_type"] == str(target_type)) & (df["name"] == str(name)))].copy()

    new_row = {
        "target_type": target_type,
        "name": name,
        "target_value": float(target_value),
        "unit": unit,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": notes,
    }
    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(TARGETS_FILE, index=False)


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


def latest_bodyweight_value():
    bw_df = load_bodyweight_log()
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


def current_exercise_best_1rm(exercise_name):
    df = load_log()
    if df.empty:
        return 0
    df = normalise_workout_log(df)
    ex = df[df["exercise"].astype(str) == str(exercise_name)].copy()
    if ex.empty:
        return 0
    ex["weight"] = pd.to_numeric(ex["weight"], errors="coerce").fillna(0)
    ex["reps"] = pd.to_numeric(ex["reps"], errors="coerce").fillna(0)
    ex["estimated_1rm"] = ex.apply(
        lambda x: estimated_1rm(float(x["weight"]), int(x["reps"])),
        axis=1,
    )
    return float(ex["estimated_1rm"].max())


def render_target_bar(title, current, target, unit, lower_is_better=False):
    if current is None or target is None:
        st.info(f"{title}: Set a target to begin.")
        return

    try:
        current = float(current)
        target = float(target)
    except Exception:
        st.info(f"{title}: Waiting for valid target/data.")
        return

    if target <= 0:
        st.info(f"{title}: Target must be above 0.")
        return

    if lower_is_better:
        progress = 100 if current <= target else (target / current) * 100
    else:
        progress = (current / target) * 100

    progress = max(0, min(progress, 100))

    st.markdown(
        f"""
        <div class="mission-card">
            <div class="mission-title">{title}</div>
            <div class="progress-track">
                <div class="progress-fill" style="--progress:{progress:.1f}%;"></div>
            </div>
            <div class="progress-label">{current:.1f}{unit} / {target:.1f}{unit} ({progress:.0f}%)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def encode_image_for_openai(uploaded_file):
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def encode_uploaded_image(uploaded_file):
    return encode_image_for_openai(uploaded_file)


def _get_openai_client():
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
        return None, "Missing OPENAI_API_KEY. Add it to Streamlit Cloud secrets."

    return OpenAI(api_key=api_key), None


def run_ai_bodyfat_estimate(front_photo, back_photo, height_cm, weight_kg, waist_cm, neck_cm, lighting, pump_status, time_of_day, model_name):
    client, err = _get_openai_client()
    if err:
        return None, err
    if front_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."

    user_text = f"""
Estimate male body fat percentage from physique photos for a fitness tracking app.
Return ONLY valid JSON.

Stats:
- Height: {height_cm} cm
- Bodyweight: {weight_kg} kg
- Waist: {waist_cm if waist_cm and waist_cm > 0 else "Not provided"}
- Neck: {neck_cm if neck_cm and neck_cm > 0 else "Not provided"}
- Lighting: {lighting}
- Pump status: {pump_status}
- Time of day: {time_of_day}

Do not use waist or neck unless provided. Be conservative with flattering lighting or pump.

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
        response = client.responses.create(model=model_name, input=[{"role": "user", "content": content}])
        text = getattr(response, "output_text", None) or str(response)
        data = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        for key in ["bf_low", "bf_high", "bf_mid", "confidence", "notes"]:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"
        return data, None
    except Exception as e:
        return None, f"AI estimate failed: {e}"


def load_measurements():
    return load_csv(
        MEASUREMENTS_FILE,
        ["date", "bodyweight", "wrist_cm", "forearm_cm", "bicep_cm",
         "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "calf_cm",
         "shoulders_cm", "neck_cm", "notes", "timestamp"],
    )


def save_measurements(row):
    df = load_measurements()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(MEASUREMENTS_FILE, index=False)


def latest_measurements():
    df = load_measurements()
    if df.empty:
        return {}
    return df.iloc[-1].to_dict()


def load_physique_ratings():
    return load_csv(
        PHYSIQUE_RATING_FILE,
        ["date", "physique_score", "leanness_score", "symmetry_score",
         "muscularity_score", "confidence", "weak_points", "improvements",
         "summary", "timestamp"],
    )


def save_physique_rating(row):
    df = load_physique_ratings()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(PHYSIQUE_RATING_FILE, index=False)


def run_ai_physique_rating(front_photo, side_photo, back_photo, stats, model_name):
    client, err = _get_openai_client()
    if err:
        return None, err
    if front_photo is None and side_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."

    user_text = f"""
Rate this male physique for an aesthetic fitness app. Do not identify the person.
Return ONLY valid JSON.

Stats:
{json.dumps(stats, indent=2)}

JSON schema:
{{
  "physique_score": number,
  "leanness_score": number,
  "symmetry_score": number,
  "muscularity_score": number,
  "confidence": "low" | "medium" | "high",
  "weak_points": ["short point", "short point", "short point"],
  "improvements": ["short actionable improvement", "short actionable improvement", "short actionable improvement"],
  "summary": "short honest summary",
  "training_priority": ["Chest", "Side delts", "Back width", "Arms", "Legs", "Abs"]
}}

Scores are out of 15. Be realistic and useful.
"""

    content = [{"type": "input_text", "text": user_text}]
    if front_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(front_photo)})
    if side_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(side_photo)})
    if back_photo is not None:
        content.append({"type": "input_image", "image_url": encode_uploaded_image(back_photo)})

    try:
        response = client.responses.create(model=model_name, input=[{"role": "user", "content": content}])
        text = getattr(response, "output_text", None) or str(response)
        data = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        for key in ["physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary"]:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"
        return data, None
    except Exception as e:
        return None, f"AI physique rating failed: {e}"


def load_custom_plan():
    return load_csv(CUSTOM_PLAN_FILE, ["workout", "exercise", "sets", "reps", "reason", "day_goal", "plan_name", "timestamp"])


def save_ai_custom_plan(ai_plan):
    rows = []
    for day in ai_plan.get("days", []):
        for ex in day.get("exercises", []):
            rows.append({
                "workout": day.get("day", ""),
                "exercise": ex.get("exercise", ""),
                "sets": ex.get("sets", ""),
                "reps": ex.get("reps", ""),
                "reason": ex.get("reason", ""),
                "day_goal": day.get("goal", ""),
                "plan_name": ai_plan.get("plan_name", "AI Custom Plan"),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
    if not rows:
        return False
    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)
    return True


def save_fallback_custom_plan(plan):
    rows = []
    for workout, exercises in plan.items():
        for exercise, sets, reps in exercises:
            rows.append({
                "workout": workout,
                "exercise": exercise,
                "sets": sets,
                "reps": reps,
                "reason": "Fallback weak-point aesthetic plan",
                "day_goal": "Aesthetic development",
                "plan_name": "Fallback Aesthetic Weakpoint Plan",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
    pd.DataFrame(rows).to_csv(CUSTOM_PLAN_FILE, index=False)


def run_ai_custom_plan_from_physique(rating, measurements, goals, model_name):
    client, err = _get_openai_client()
    if err:
        return None, err

    prompt = f"""
You are an expert bodybuilding coach making a custom workout plan for an aesthetic-focused lifter.

DO NOT simply repeat the user's current PPPPLA routine.
Choose exercises from this exercise library:
{json.dumps(EXERCISE_LIBRARY, indent=2)}

Physique rating:
{json.dumps(rating, indent=2)}

Measurements:
{json.dumps(measurements, indent=2)}

Goal:
{goals}

Create a 6-day split:
Push 1 - Strength Bias
Pull 1 - Width Bias
Push 2 - Hypertrophy Bias
Pull 2 - Thickness Bias
Legs
Aesthetic Weakpoint Day

Each day: 5-8 exercises. Include exercise, sets, reps, reason.
Return ONLY valid JSON:
{{
  "plan_name": "string",
  "rationale": "short summary",
  "weekly_focus": ["focus 1", "focus 2", "focus 3"],
  "days": [
    {{
      "day": "Push 1 - Strength Bias",
      "goal": "short day goal",
      "exercises": [
        {{"exercise": "exercise name", "sets": 3, "reps": "8-12", "reason": "why selected"}}
      ]
    }}
  ]
}}
"""
    try:
        response = client.responses.create(model=model_name, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}])
        text = getattr(response, "output_text", None) or str(response)
        data = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        if "days" not in data:
            return None, f"AI response missing 'days'. Raw: {text[:500]}"
        return data, None
    except Exception as e:
        return None, f"AI custom plan failed: {e}"

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

page = st.sidebar.radio("Menu", ["Home", "Profile", "Physique", "Measurements", "Today", "Cardio", "Progress", "Goals", "Achievements", "Body Fat", "Bodyweight", "Data Manager", "Delete Data", "Routine"])
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




elif page == "Measurements":
    st.header("Body Measurements")
    st.info("Log measurements to track proportions and help the app generate better physique-focused training plans.")

    latest = latest_measurements()
    latest_bw = latest_bodyweight_value() or float(latest.get("bodyweight", 76.0) or 76.0)

    c1, c2 = st.columns(2)
    with c1:
        m_date = st.date_input("Date", value=date.today(), key="measure_date")
        bodyweight = st.number_input("Bodyweight kg", min_value=0.0, step=0.1, value=float(latest_bw or 76.0))
        wrist = st.number_input("Wrist cm", min_value=0.0, step=0.1, value=float(latest.get("wrist_cm", 0) or 0))
        forearm = st.number_input("Forearm cm", min_value=0.0, step=0.1, value=float(latest.get("forearm_cm", 0) or 0))
        bicep = st.number_input("Bicep cm", min_value=0.0, step=0.1, value=float(latest.get("bicep_cm", 0) or 0))
        chest = st.number_input("Chest cm", min_value=0.0, step=0.1, value=float(latest.get("chest_cm", 0) or 0))
    with c2:
        waist = st.number_input("Waist cm", min_value=0.0, step=0.1, value=float(latest.get("waist_cm", 0) or 0))
        hips = st.number_input("Hips cm", min_value=0.0, step=0.1, value=float(latest.get("hips_cm", 0) or 0))
        thigh = st.number_input("Thigh cm", min_value=0.0, step=0.1, value=float(latest.get("thigh_cm", 0) or 0))
        calf = st.number_input("Calf cm", min_value=0.0, step=0.1, value=float(latest.get("calf_cm", 0) or 0))
        shoulders = st.number_input("Shoulders cm", min_value=0.0, step=0.1, value=float(latest.get("shoulders_cm", 0) or 0))
        neck = st.number_input("Neck cm", min_value=0.0, step=0.1, value=float(latest.get("neck_cm", 0) or 0))

    notes = st.text_input("Notes", placeholder="Morning, no pump, relaxed, etc.")

    if st.button("Save Measurements", type="primary"):
        save_measurements({
            "date": str(m_date),
            "bodyweight": bodyweight,
            "wrist_cm": wrist,
            "forearm_cm": forearm,
            "bicep_cm": bicep,
            "chest_cm": chest,
            "waist_cm": waist,
            "hips_cm": hips,
            "thigh_cm": thigh,
            "calf_cm": calf,
            "shoulders_cm": shoulders,
            "neck_cm": neck,
            "notes": notes,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
        st.session_state.just_saved_message = "MEASUREMENTS SAVED"
        st.rerun()

    st.subheader("Measurement History")
    mlog = load_measurements()
    if mlog.empty:
        st.info("No measurements logged yet.")
    else:
        st.dataframe(mlog.sort_values("date", ascending=False), use_container_width=True)
        chart_cols = [c for c in ["bodyweight", "bicep_cm", "chest_cm", "waist_cm", "shoulders_cm"] if c in mlog.columns]
        if chart_cols:
            for col in chart_cols:
                mlog[col] = pd.to_numeric(mlog[col], errors="coerce").fillna(0)
            st.line_chart(mlog, x="date", y=chart_cols)


elif page == "Physique":
    st.header("AI Physique Rating")
    st.info("Upload physique photos to get a physique score, leanness score, weak points, and a custom workout plan suggestion.")

    latest_m = latest_measurements()
    latest_bf = latest_bodyfat_mid()
    latest_bw = latest_bodyweight_value()

    c1, c2, c3 = st.columns(3)
    with c1:
        front_photo = st.file_uploader("Front photo", type=["jpg", "jpeg", "png", "webp"], key="phys_front")
    with c2:
        side_photo = st.file_uploader("Side photo", type=["jpg", "jpeg", "png", "webp"], key="phys_side")
    with c3:
        back_photo = st.file_uploader("Back photo", type=["jpg", "jpeg", "png", "webp"], key="phys_back")

    model_name = st.text_input("OpenAI model", value="gpt-5.1", key="phys_model")

    stats = {
        "bodyweight_kg": latest_bw,
        "bodyfat_estimate": latest_bf,
        "measurements": latest_m,
        "bench_e1rm": current_exercise_best_1rm("Barbell Bench Press (Strength)"),
        "squat_e1rm": current_exercise_best_1rm("Barbell Back Squat"),
    }

    if st.button("Run AI Physique Rating", type="primary"):
        with st.spinner("Rating physique and analysing weak points..."):
            result, err = run_ai_physique_rating(front_photo, side_photo, back_photo, stats, model_name)
        if err:
            st.error(err)
        else:
            st.session_state["last_physique_rating"] = result
            st.session_state.just_saved_message = "PHYSIQUE RATING COMPLETE"
            st.rerun()

    rating = st.session_state.get("last_physique_rating", None)

    if rating:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Physique", f"{float(rating['physique_score']):.1f}/15")
        c2.metric("Leanness", f"{float(rating['leanness_score']):.1f}/15")
        c3.metric("Symmetry", f"{float(rating['symmetry_score']):.1f}/15")
        c4.metric("Muscularity", f"{float(rating['muscularity_score']):.1f}/15")

        st.write(f"**Confidence:** {str(rating.get('confidence', 'unknown')).title()}")
        st.write(f"**Summary:** {rating.get('summary', '')}")

        st.subheader("Weak Points")
        for point in rating.get("weak_points", []):
            st.write(f"- {point}")

        st.subheader("What To Improve")
        for point in rating.get("improvements", []):
            st.write(f"- {point}")

        if st.button("Save Physique Rating", type="primary"):
            save_physique_rating({
                "date": str(date.today()),
                "physique_score": rating.get("physique_score"),
                "leanness_score": rating.get("leanness_score"),
                "symmetry_score": rating.get("symmetry_score"),
                "muscularity_score": rating.get("muscularity_score"),
                "confidence": rating.get("confidence"),
                "weak_points": json.dumps(rating.get("weak_points", [])),
                "improvements": json.dumps(rating.get("improvements", [])),
                "summary": rating.get("summary"),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
            st.session_state.just_saved_message = "PHYSIQUE RATING SAVED"
            st.rerun()

        st.subheader("Generate Custom Workout Plan")
        goal = st.selectbox(
            "Goal",
            ["Aesthetic / lean bulk", "Cutting / maintain muscle", "Bench strength focus", "V-taper focus", "Arms/Delts specialization", "Upper chest specialization"]
        )

        st.caption("This uses the AI physique rating + measurements + a larger exercise library to build a weak-point plan. It will not simply copy your current PPPPLA.")

        if st.button("Generate AI Custom Plan From Physique Analysis", type="primary"):
            with st.spinner("AI is building a custom weak-point plan..."):
                ai_plan, err = run_ai_custom_plan_from_physique(
                    rating=rating,
                    measurements=latest_measurements(),
                    goals=goal,
                    model_name=model_name,
                )

            if err:
                st.warning(err)
                st.info("Using fallback weak-point aesthetic plan instead.")
                save_fallback_custom_plan(FALLBACK_AESTHETIC_PLAN)
                st.session_state.just_saved_message = "FALLBACK CUSTOM PLAN GENERATED"
                st.rerun()
            else:
                ok = save_ai_custom_plan(ai_plan)
                if ok:
                    st.session_state["last_ai_plan"] = ai_plan
                    st.session_state.just_saved_message = "AI CUSTOM WORKOUT PLAN GENERATED"
                    st.rerun()
                else:
                    st.error("AI returned a plan, but no exercises could be saved.")

        last_plan = st.session_state.get("last_ai_plan", None)
        if last_plan:
            st.subheader(last_plan.get("plan_name", "AI Custom Plan"))
            st.write(last_plan.get("rationale", ""))
            if last_plan.get("weekly_focus"):
                st.write("**Weekly focus:** " + ", ".join(last_plan.get("weekly_focus", [])))

    st.subheader("Saved Physique Ratings")
    ratings = load_physique_ratings()
    if ratings.empty:
        st.info("No physique ratings saved yet.")
    else:
        st.dataframe(ratings.sort_values("date", ascending=False), use_container_width=True)

    st.subheader("Current Custom Workout Plan")
    plan_df = load_custom_plan()
    if plan_df.empty:
        st.info("No custom plan generated yet.")
    else:
        st.dataframe(plan_df, use_container_width=True)



elif page == "Today":
    st.header("Today’s Workout")
    if st.session_state.get("last_supabase_error"):
        st.error(st.session_state.get("last_supabase_error"))

    workout_source = st.radio(
        "Workout plan",
        ["PPPPLA Split", "AI Custom Workout Plan"],
        horizontal=True,
    )

    custom_plan_df = load_custom_plan()

    if workout_source == "AI Custom Workout Plan":
        if custom_plan_df.empty:
            st.warning("No AI custom workout plan found yet. Go to Physique → Generate AI Custom Plan first.")
            active_routine = ROUTINE
            workout_source = "PPPPLA Split"
        else:
            active_routine = {}
            custom_plan_df["sets"] = pd.to_numeric(custom_plan_df["sets"], errors="coerce").fillna(0).astype(int)

            for workout_name in custom_plan_df["workout"].dropna().astype(str).unique():
                day_df = custom_plan_df[custom_plan_df["workout"].astype(str) == workout_name]
                active_routine[workout_name] = [
                    (
                        str(row["exercise"]),
                        int(row["sets"]) if int(row["sets"]) > 0 else 3,
                        str(row["reps"]),
                    )
                    for _, row in day_df.iterrows()
                ]

            plan_name = custom_plan_df["plan_name"].dropna().astype(str).iloc[-1] if "plan_name" in custom_plan_df.columns and not custom_plan_df["plan_name"].dropna().empty else "AI Custom Plan"
            st.success(f"Using: {plan_name}")
    else:
        active_routine = ROUTINE

    workout = st.selectbox("Workout", list(active_routine.keys()))
    workout_date = st.date_input("Date", value=date.today())

    if workout == "Rest":
        st.info("Rest day. Walk, stretch, eat protein, sleep.")
    else:
        total_sets = sum(ex[1] for ex in active_routine[workout])
        completed_sets = completed_sets_for_day(load_log(), workout_date, workout)
        percent = 0 if total_sets == 0 else min((completed_sets / total_sets) * 100, 100)
        st.caption(f"Target volume: {total_sets} working sets")
        st.markdown(f"""<div class="mission-card"><div class="mission-title">MISSION PROGRESS</div><div class="progress-track"><div class="progress-fill" style="--progress: {percent:.1f}%;"></div></div><div class="progress-label">{completed_sets}/{total_sets} sets complete — {percent:.1f}%</div></div>""", unsafe_allow_html=True)

        for exercise, sets, reps_target in active_routine[workout]:
            with st.expander(f"⚡ {exercise}", expanded=True):
                st.markdown(f"""<div class="nw-exercise-card"><div class="nw-card-title">{exercise}</div><div class="nw-small">{sets} sets × {reps_target}</div></div>""", unsafe_allow_html=True)

                if exercise in ["Barbell Bench Press (Strength)", "Barbell Bench Press"]:
                    st.markdown("""<div class="nw-note"><b>Strength bench:</b> heavy top set of 3-5 reps, then back-off work. Rest 3-5 minutes.</div>""", unsafe_allow_html=True)
                if exercise == "Paused Barbell Bench Press":
                    st.markdown("""<div class="nw-note"><b>Paused bench:</b> lighter bench with a 1-2 second dead stop on the chest. No bounce.</div>""", unsafe_allow_html=True)

                if workout_source == "AI Custom Workout Plan" and not custom_plan_df.empty and "reason" in custom_plan_df.columns:
                    reason_rows = custom_plan_df[
                        (custom_plan_df["workout"].astype(str) == str(workout)) &
                        (custom_plan_df["exercise"].astype(str) == str(exercise))
                    ]
                    if not reason_rows.empty:
                        reason = str(reason_rows.iloc[0].get("reason", ""))
                        if reason and reason.lower() != "nan":
                            st.caption(f"AI reason: {reason}")

                last = get_last_sets(load_log(), exercise)
                if last is not None:
                    last_text = ", ".join(f"{float(r.weight):g}kg × {int(r.reps)}" for r in last.itertuples())
                    st.caption(f"Last session: {last_text}")
                st.caption(f"Suggestion: {suggest_weight(load_log(), exercise)}")

                for set_no in range(1, sets + 1):
                    col1, col2 = st.columns(2)
                    with col1:
                        weight = st.number_input(f"{exercise} set {set_no} kg", min_value=0.0, step=2.5, key=f"{workout_source}-{workout}-{exercise}-{set_no}-w", placeholder="kg")
                    with col2:
                        reps = st.number_input(f"{exercise} set {set_no} reps", min_value=0, step=1, key=f"{workout_source}-{workout}-{exercise}-{set_no}-r", placeholder="reps")

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
    cardio = load_cardio_log()
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
    bw_df = load_bodyweight_log()
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
            c3.metric(f"{target_bf:.1f}% Target", f"{safe_kg(target_weight)}")

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
                    "notes": f"US Navy-style measurement estimate. Target {target_bf}% weight: {safe_kg(target_weight)}.",
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
            c3.metric(f"{target_bf:.1f}% Target", f"{safe_kg(target_weight)}")

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
                    "notes": f"Combined measurement + AI estimate. Target {target_bf}% weight: {safe_kg(target_weight)}.",
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
    bw_df = load_bodyweight_log()
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



elif page == "Data Manager":
    st.header("📂 Data Manager")
    st.info("Download backups of your workout data. Supabase is used first when connected, with CSV as backup.")

    st.subheader("Supabase Status")
    if supabase_enabled():
        st.success("Supabase connected — data loads/saves to cloud database first.")
    else:
        st.warning("Supabase not connected — using CSV files only.")

    csv_files = [
        "workout_log.csv",
        "bodyweight_log.csv",
        "bodyfat_log.csv",
        "measurements.csv",
        "physique_ratings.csv",
        "custom_workout_plan.csv",
        "targets.csv",
        "achievements.csv",
        "cardio_log.csv",
        "profile.csv",
    ]

    st.subheader("Supabase Diagnostics")
    if supabase_enabled():
        st.success("Supabase client configured.")
    else:
        st.error("Supabase client not configured. Check Streamlit Secrets.")

    if st.session_state.get("last_supabase_write"):
        st.success(st.session_state.get("last_supabase_write"))
    if st.session_state.get("last_supabase_error"):
        st.error(st.session_state.get("last_supabase_error"))

    sample_rows = {
        "workout_log": {"date": str(date.today()), "workout": "Supabase Test", "exercise": "Connection Test", "muscle": "Test", "set": 1, "weight": 1, "reps": 1, "estimated_1rm": 1, "volume": 1, "notes": "test insert", "timestamp": datetime.now().isoformat(timespec="seconds")},
        "bodyweight_log": {"date": str(date.today()), "bodyweight": 77.0, "timestamp": datetime.now().isoformat(timespec="seconds")},
        "cardio_log": {"date": str(date.today()), "type": "Test", "minutes": 1, "distance_km": 0.1, "incline": 0, "speed": 1, "calories": 1, "notes": "test insert", "timestamp": datetime.now().isoformat(timespec="seconds")},
        "bodyfat_log": {"date": str(date.today()), "method": "Test", "bodyweight": 77.0, "height_cm": 183.5, "waist_cm": 0, "neck_cm": 0, "bf_low": 12, "bf_high": 14, "bf_mid": 13, "confidence": "test", "notes": "test insert", "timestamp": datetime.now().isoformat(timespec="seconds")},
        "measurements": {"date": str(date.today()), "bodyweight": 77.0, "wrist_cm": 0, "forearm_cm": 0, "bicep_cm": 0, "chest_cm": 0, "waist_cm": 0, "hips_cm": 0, "thigh_cm": 0, "calf_cm": 0, "shoulders_cm": 0, "neck_cm": 0, "notes": "test insert", "timestamp": datetime.now().isoformat(timespec="seconds")},
        "physique_ratings": {"date": str(date.today()), "physique_score": 1, "leanness_score": 1, "symmetry_score": 1, "muscularity_score": 1, "confidence": "test", "weak_points": ["test"], "improvements": ["test"], "summary": "test insert", "timestamp": datetime.now().isoformat(timespec="seconds")},
        "custom_workout_plan": {"plan_name": "Test Plan", "workout": "Test Day", "exercise": "Test Exercise", "sets": 1, "reps": "1", "muscle": "Test", "reason": "test insert", "day_goal": "test", "timestamp": datetime.now().isoformat(timespec="seconds")},
        "achievements": {"achievement_id": "test_" + datetime.now().strftime("%H%M%S"), "name": "Test Achievement", "description": "test insert", "date_unlocked": datetime.now().isoformat(timespec="seconds")},
        "targets": {"target_type": "Test", "name": "Test Target " + datetime.now().strftime("%H%M%S"), "target_value": 1, "unit": "test", "created_at": datetime.now().isoformat(timespec="seconds"), "notes": "test insert"},
        "profile": {"height_cm": 183.5, "bodyweight_kg": 77.0, "bench_e1rm": 100, "squat_e1rm": 140, "training_years": 3, "physique_score": 10, "leanness_score": 10, "base_level": 42, "created_at": datetime.now().isoformat(timespec="seconds")},
    }

    selected_test_table = st.selectbox("Supabase table to test", list(sample_rows.keys()))

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Test Selected Table Insert", type="primary"):
            sb_insert(selected_test_table, sample_rows[selected_test_table], show_error=True)

    with col_b:
        if st.button("Read Selected Table Rows"):
            data, err = sb_select(selected_test_table)
            if err:
                st.error(err)
            else:
                st.write(f"Rows found in Supabase {selected_test_table}: {len(data)}")
                if data:
                    st.dataframe(pd.DataFrame(data).tail(10), use_container_width=True)

    if st.button("Run All Supabase Insert Tests"):
        results = []
        for table, row in sample_rows.items():
            ok, err = sb_insert(table, row)
            results.append({"table": table, "ok": ok, "error": err or ""})
        st.dataframe(pd.DataFrame(results), use_container_width=True)

    st.subheader("Detected Data Files")

    file_rows = []
    for file in csv_files:
        path = Path(file)
        if path.exists():
            try:
                size_kb = path.stat().st_size / 1024
                modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                file_rows.append({
                    "file": file,
                    "exists": "Yes",
                    "size_kb": round(size_kb, 2),
                    "last_modified": modified,
                })
            except Exception:
                file_rows.append({
                    "file": file,
                    "exists": "Yes",
                    "size_kb": "",
                    "last_modified": "",
                })
        else:
            file_rows.append({
                "file": file,
                "exists": "No",
                "size_kb": "",
                "last_modified": "",
            })

    st.dataframe(pd.DataFrame(file_rows), use_container_width=True)

    st.subheader("Download Individual CSV Files")

    any_file = False
    for file in csv_files:
        path = Path(file)
        if path.exists():
            any_file = True
            with open(path, "rb") as f:
                st.download_button(
                    label=f"⬇️ Download {file}",
                    data=f,
                    file_name=file,
                    mime="text/csv",
                    key=f"download_{file}",
                )

    if not any_file:
        st.warning("No CSV data files exist yet. Log a workout/cardio/bodyweight entry first, then come back here.")

    st.subheader("Full Backup ZIP")

    zip_buffer = BytesIO()
    files_added = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in csv_files:
            path = Path(file)
            if path.exists():
                zip_file.write(path, arcname=file)
                files_added += 1

        # include a small backup manifest
        manifest = pd.DataFrame(file_rows).to_csv(index=False)
        zip_file.writestr("backup_manifest.csv", manifest)
        files_added += 1

    zip_buffer.seek(0)

    st.download_button(
        label="🔥 Download Full Training Backup ZIP",
        data=zip_buffer,
        file_name=f"tyson_training_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        disabled=(files_added <= 1),
        key="download_full_backup_zip",
    )

    st.divider()

    st.subheader("Restore / Import CSV Files")
    st.warning("Importing a CSV with the same name will replace the existing server file. Download a backup first.")

    uploaded_files = st.file_uploader(
        "Upload CSV files to restore",
        type=["csv"],
        accept_multiple_files=True,
        help="Upload files like workout_log.csv, bodyfat_log.csv, achievements.csv, etc.",
    )

    allowed_files = set(csv_files)

    if uploaded_files:
        st.write("Files ready to import:")
        for uploaded in uploaded_files:
            if uploaded.name in allowed_files:
                st.write(f"✅ {uploaded.name}")
            else:
                st.write(f"⚠️ {uploaded.name} — ignored because it is not a recognised app data file.")

        confirm_restore = st.checkbox("I understand this will replace matching CSV files on the app server.")

        if st.button("Restore Uploaded CSV Files", type="primary"):
            if not confirm_restore:
                st.error("Tick the confirmation box first.")
            else:
                restored = []
                ignored = []
                for uploaded in uploaded_files:
                    if uploaded.name not in allowed_files:
                        ignored.append(uploaded.name)
                        continue
                    data = uploaded.getvalue()
                    Path(uploaded.name).write_bytes(data)
                    restored.append(uploaded.name)

                if restored:
                    st.success("Restored: " + ", ".join(restored))
                if ignored:
                    st.warning("Ignored: " + ", ".join(ignored))
                st.session_state.just_saved_message = "DATA RESTORE COMPLETE"
                st.rerun()

    st.divider()


    st.divider()
    st.subheader("CSV → Supabase Migration")
    st.caption("Use this once if you already have CSV data and want to push it into Supabase.")
    if st.button("Upload Existing CSV Backups to Supabase", type="secondary"):
        if not supabase_enabled():
            st.error("Supabase is not connected.")
        else:
            migration_map = {
                "workout_log.csv": "workout_log",
                "bodyweight_log.csv": "bodyweight_log",
                "bodyfat_log.csv": "bodyfat_log",
                "measurements.csv": "measurements",
                "physique_ratings.csv": "physique_ratings",
                "custom_workout_plan.csv": "custom_workout_plan",
                "targets.csv": "targets",
                "achievements.csv": "achievements",
                "cardio_log.csv": "cardio_log",
                "profile.csv": "profile",
            }
            migrated = []
            for file, table in migration_map.items():
                path = Path(file)
                if not path.exists():
                    continue
                try:
                    df_mig = pd.read_csv(path)
                    if df_mig.empty:
                        continue
                    records = df_mig.where(pd.notnull(df_mig), None).to_dict(orient="records")
                    get_supabase_client().table(table).insert(records).execute()
                    migrated.append(f"{file} → {table} ({len(records)} rows)")
                except Exception as e:
                    st.warning(f"Could not migrate {file}: {e}")
            if migrated:
                st.success("Migrated: " + " | ".join(migrated))
            else:
                st.info("No CSV rows found to migrate.")

    st.subheader("Quick Preview")
    preview_file = st.selectbox("Preview CSV", csv_files)
    preview_path = Path(preview_file)

    if preview_path.exists():
        try:
            preview_df = pd.read_csv(preview_path)
            st.caption(f"Showing last 50 rows from {preview_file}")
            st.dataframe(preview_df.tail(50), use_container_width=True)
        except Exception as e:
            st.error(f"Could not preview {preview_file}: {e}")
    else:
        st.info(f"{preview_file} does not exist yet.")


elif page == "Delete Data":
    st.header("Delete Logged Data")
    st.warning("Use this to remove accidental entries. This permanently edits the CSV file.")
    log_type = st.selectbox("Choose log", ["Workout", "Cardio", "Body Fat", "Bodyweight", "Measurements", "Physique Ratings", "Custom Plan", "Targets", "Profile", "Achievements"])
    if log_type == "Workout":
        path, columns = LOG_FILE, ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]
    elif log_type == "Cardio":
        path, columns = CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"]
    elif log_type == "Body Fat":
        path, columns = BODYFAT_FILE, ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm", "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"]
    elif log_type == "Bodyweight":
        path, columns = BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"]
    elif log_type == "Measurements":
        path, columns = MEASUREMENTS_FILE, ["date", "bodyweight", "wrist_cm", "forearm_cm", "bicep_cm", "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "calf_cm", "shoulders_cm", "neck_cm", "notes", "timestamp"]
    elif log_type == "Physique Ratings":
        path, columns = PHYSIQUE_RATING_FILE, ["date", "physique_score", "leanness_score", "symmetry_score", "muscularity_score", "confidence", "weak_points", "improvements", "summary", "timestamp"]
    elif log_type == "Custom Plan":
        path, columns = CUSTOM_PLAN_FILE, ["workout", "exercise", "sets", "reps", "reason", "day_goal", "plan_name", "timestamp"]
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
