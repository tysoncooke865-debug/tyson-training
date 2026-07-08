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
    "first_set": ("⚡ First Signal", "Logged your first set."),
    "first_workout": ("🦇 Patrol Started", "Logged 10 total sets."),
    "bench_90": ("💪 90kg Bench Signal", "Logged 90kg or more on bench."),
    "bench_100_est": ("🏆 100kg Bench Quest", "Estimated 1RM reached 100kg."),
    "hundred_sets": ("🔥 100 Set Streak", "Logged 100 total working sets."),
    "cardio_100": ("🫀 Engine Built", "Logged 100 total cardio minutes."),
    "delts_50": ("🪽 Wing Build", "Logged 50 delt/rear-delt sets."),
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


def workout_summary(df):
    df = normalise_workout_log(df.copy())
    if df.empty:
        return {
            "total_sets": 0, "total_reps": 0, "best_bench_1rm": 0, "latest_bw": 0,
            "xp": 0, "level": 1, "xp_into_level": 0, "xp_needed": 100
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
    level = max(1, xp // 500 + 1)
    xp_into_level = xp % 500

    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])
    latest_bw = 0
    if not bw_df.empty:
        bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
        latest_bw = float(bw_df.iloc[-1]["bodyweight"])

    return {
        "total_sets": total_sets, "total_reps": total_reps, "best_bench_1rm": best_bench_1rm,
        "latest_bw": latest_bw, "xp": xp, "level": level, "xp_into_level": xp_into_level,
        "xp_needed": 500
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


def check_achievements():
    df = load_log()
    summary = workout_summary(df)
    heat = muscle_heat_map(df)
    cardio = load_csv(CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"])
    cardio["minutes"] = pd.to_numeric(cardio.get("minutes", 0), errors="coerce").fillna(0)
    cardio_minutes = float(cardio["minutes"].sum()) if not cardio.empty else 0

    unlocked = []
    if summary["total_sets"] >= 1 and save_achievement("first_set"):
        unlocked.append(ACHIEVEMENTS["first_set"][0])
    if summary["total_sets"] >= 10 and save_achievement("first_workout"):
        unlocked.append(ACHIEVEMENTS["first_workout"][0])
    if summary["total_sets"] >= 100 and save_achievement("hundred_sets"):
        unlocked.append(ACHIEVEMENTS["hundred_sets"][0])
    if summary["best_bench_1rm"] >= 100 and save_achievement("bench_100_est"):
        unlocked.append(ACHIEVEMENTS["bench_100_est"][0])

    bench = df[df["exercise"] == "Barbell Bench Press (Strength)"].copy() if not df.empty else pd.DataFrame()
    if not bench.empty:
        bench["weight"] = pd.to_numeric(bench["weight"], errors="coerce").fillna(0)
        if bench["weight"].max() >= 90 and save_achievement("bench_90"):
            unlocked.append(ACHIEVEMENTS["bench_90"][0])

    if cardio_minutes >= 100 and save_achievement("cardio_100"):
        unlocked.append(ACHIEVEMENTS["cardio_100"][0])

    if not heat.empty:
        delt_sets = heat[heat["muscle"].isin(["Delts", "Rear Delts"])]["sets"].sum()
        if delt_sets >= 50 and save_achievement("delts_50"):
            unlocked.append(ACHIEVEMENTS["delts_50"][0])

    return unlocked



def navy_body_fat_male(height_cm, waist_cm, neck_cm):
    """US Navy male body fat estimate. Uses inches internally."""
    try:
        height_in = float(height_cm) / 2.54
        waist_in = float(waist_cm) / 2.54
        neck_in = float(neck_cm) / 2.54
        if height_in <= 0 or waist_in <= neck_in or neck_in <= 0:
            return None
        return 86.010 * math.log10(waist_in - neck_in) - 70.041 * math.log10(height_in) + 36.76
    except Exception:
        return None


def bodyfat_outputs(weight_kg, bf_percent, target_bf=10.0):
    try:
        weight_kg = float(weight_kg)
        bf_percent = float(bf_percent)
        fat_mass = weight_kg * (bf_percent / 100)
        lean_mass = weight_kg - fat_mass
        target_weight = lean_mass / (1 - target_bf / 100)
        fat_to_lose = max(weight_kg - target_weight, 0)
        return fat_mass, lean_mass, target_weight, fat_to_lose
    except Exception:
        return None, None, None, None


def load_bodyfat_log():
    return load_csv(
        BODYFAT_FILE,
        [
            "date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm",
            "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"
        ]
    )


def save_bodyfat_estimate(row):
    df = load_bodyfat_log()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(BODYFAT_FILE, index=False)


def encode_image_for_openai(uploaded_file):
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def run_ai_bodyfat_estimate(front_photo, back_photo, height_cm, weight_kg, lighting, pump_status, time_of_day, model_name):
    """
    Photo-based estimate using OpenAI Vision via the Responses API.
    Requires OPENAI_API_KEY in environment or Streamlit secrets.
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
        return None, "Missing OPENAI_API_KEY. Add it to Streamlit secrets or your environment variables."

    client = OpenAI(api_key=api_key)

    content = [
        {
            "type": "input_text",
            "text": f"""
You are estimating male body fat from physique photos for a fitness tracking app.
This is not medical advice. Give a realistic range, not a false-precision number.

User stats:
- Height: {height_cm} cm
- Bodyweight: {weight_kg} kg
- Lighting: {lighting}
- Pump status: {pump_status}
- Time of day: {time_of_day}

Return ONLY valid JSON with this exact schema:
{{
  "bf_low": number,
  "bf_high": number,
  "bf_mid": number,
  "confidence": "low" | "medium" | "high",
  "notes": "short practical explanation",
  "fat_storage": "short note",
  "ten_percent_notes": "short note"
}}

Rules:
- Use a range.
- Be conservative if lighting/pump is flattering.
- Mention if lower abs/lower back appear to be the main remaining storage only if visible.
- Do not identify the person.
"""
        }
    ]

    if front_photo is not None:
        content.append({"type": "input_image", "image_url": encode_image_for_openai(front_photo)})
    if back_photo is not None:
        content.append({"type": "input_image", "image_url": encode_image_for_openai(back_photo)})

    if front_photo is None and back_photo is None:
        return None, "Upload at least one physique photo."

    try:
        response = client.responses.create(
            model=model_name,
            input=[{"role": "user", "content": content}],
        )

        text = getattr(response, "output_text", None)
        if not text:
            text = str(response)

        # Clean possible code fences just in case.
        text_clean = text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text_clean)

        required = ["bf_low", "bf_high", "bf_mid", "confidence", "notes"]
        for key in required:
            if key not in data:
                return None, f"AI response missing key: {key}. Raw response: {text[:500]}"

        return data, None

    except Exception as e:
        return None, f"AI estimate failed: {e}"



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

page = st.sidebar.radio("Menu", ["Home", "Today", "Cardio", "Progress", "Body Fat", "Bodyweight", "Delete Data", "Routine"])
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

if page == "Home":
    st.header("Command Centre")
    summary = workout_summary(df)
    xp_percent = min((summary["xp_into_level"] / summary["xp_needed"]) * 100, 100)
    bench_percent = min((summary["best_bench_1rm"] / 100) * 100, 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("Level", f"{summary['level']}")
    c2.metric("XP", f"{summary['xp']}")
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
        <div class="mission-title">LEVEL {summary['level']} ATHLETE</div>
        <div class="progress-track"><div class="progress-fill" style="--progress: {xp_percent:.1f}%;"></div></div>
        <div class="progress-label">{summary['xp_into_level']}/{summary['xp_needed']} XP to next level</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="mission-card">
        <div class="mission-title">100KG BENCH QUEST</div>
        <div class="progress-track"><div class="progress-fill" style="--progress: {bench_percent:.1f}%;"></div></div>
        <div class="progress-label">{summary['best_bench_1rm']:.1f}kg estimated / 100kg — {bench_percent:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

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

    st.subheader("Achievements")
    ach = load_achievements()
    if ach.empty:
        st.info("No achievements unlocked yet.")
    else:
        for _, row in ach.sort_values("date_unlocked", ascending=False).iterrows():
            st.markdown(f"""<div class="dashboard-card"><div class="nw-card-title">{row['name']}</div><div class="nw-small">{row['description']}</div></div>""", unsafe_allow_html=True)


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
        st.dataframe(ex.sort_values(["date", "set"], ascending=False), use_container_width=True)



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
        waist_cm = st.number_input("Waist at navel cm", min_value=0.0, step=0.5, value=80.0)
        neck_cm = st.number_input("Neck cm", min_value=0.0, step=0.5, value=39.0)
        target_bf = st.number_input("Target BF%", min_value=5.0, max_value=25.0, step=0.5, value=10.0)

    navy_bf = None
    ai_data = None

    if mode in ["Measurement estimate", "Combined estimate"]:
        navy_bf = navy_body_fat_male(height_cm, waist_cm, neck_cm)

        st.subheader("Measurement Estimate")
        if navy_bf is None:
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
                    <div class="progress-label">Measurement range: {bf_low:.1f}% - {bf_high:.1f}% • Fat to lose to {target_bf:.1f}%: {fat_to_lose:.1f}kg</div>
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
        st.caption("Requires OpenAI API key. Upload front/back physique photos. Avoid extreme pump/lighting if you want a realistic estimate.")

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
                    front_photo, back_photo, height_cm, weight_kg, lighting, pump_status, time_of_day, model_name
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

            st.markdown(
                f"""
                <div class="mission-card">
                    <div class="mission-title">AI PHOTO BODY FAT ESTIMATE</div>
                    <div class="progress-track">
                        <div class="progress-fill" style="--progress: {min(bf_mid * 4, 100):.1f}%;"></div>
                    </div>
                    <div class="progress-label">{bf_low:.1f}% - {bf_high:.1f}% • Target {target_bf:.1f}% weight: {target_weight:.1f}kg • Fat to lose: {fat_to_lose:.1f}kg</div>
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
    log_type = st.selectbox("Choose log", ["Workout", "Cardio", "Body Fat", "Bodyweight", "Achievements"])
    if log_type == "Workout":
        path, columns = LOG_FILE, ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]
    elif log_type == "Cardio":
        path, columns = CARDIO_FILE, ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"]
    elif log_type == "Body Fat":
        path, columns = BODYFAT_FILE, ["date", "method", "bodyweight", "height_cm", "waist_cm", "neck_cm", "bf_low", "bf_high", "bf_mid", "confidence", "notes", "timestamp"]
    elif log_type == "Bodyweight":
        path, columns = BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"]
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
