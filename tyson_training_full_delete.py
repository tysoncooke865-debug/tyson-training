import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime

# ============================================================
# TYSON TRAINING - DYNAMIC BLUE VERSION WITH DELETE FEATURE
# ============================================================

APP_TITLE = "Tyson Training"
LOG_FILE = Path("workout_log.csv")
BODYWEIGHT_FILE = Path("bodyweight_log.csv")
CARDIO_FILE = Path("cardio_log.csv")

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


# ------------------------------
# Helpers
# ------------------------------
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


def load_log():
    df = load_csv(LOG_FILE, ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"])

    # Compatibility with older versions that saved "set_number"
    if "set" not in df.columns and "set_number" in df.columns:
        df = df.rename(columns={"set_number": "set"})
    if "set" not in df.columns:
        df["set"] = 0

    return df


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
        if reps >= 5:
            return f"Try {weight + 2.5:.1f} kg next top set"
        return f"Repeat {weight:.1f} kg and beat reps"

    if exercise == "Paused Barbell Bench Press":
        if reps >= 8:
            return f"Try {weight + 2.5:.1f} kg"
        return f"Repeat {weight:.1f} kg with a clean pause"

    if reps >= 15:
        return f"Try {weight + 2.5:.1f} kg if form was clean"

    return f"Repeat {weight:.1f} kg and beat reps"


def save_workout(rows):
    df = load_log()
    pd.concat([df, pd.DataFrame(rows)], ignore_index=True).to_csv(LOG_FILE, index=False)


def normalise_workout_log(df):
    if "set" not in df.columns and "set_number" in df.columns:
        df = df.rename(columns={"set_number": "set"})
    if "set" not in df.columns:
        df["set"] = 0
    return df


# ------------------------------
# Page setup
# ------------------------------
st.set_page_config(page_title=APP_TITLE, layout="centered")

st.markdown("""
<style>
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 920px;
}

/* Dynamic blue background */
.stApp {
    background:
        radial-gradient(circle at 15% 15%, rgba(56,189,248,0.35), transparent 28%),
        radial-gradient(circle at 85% 30%, rgba(37,99,235,0.30), transparent 32%),
        radial-gradient(circle at 50% 90%, rgba(14,165,233,0.20), transparent 35%),
        linear-gradient(135deg, #020617, #071426, #020617);
    background-size: 180% 180%;
    animation: blueShift 12s ease infinite;
}

@keyframes blueShift {
    0% { background-position: 0% 30%; }
    50% { background-position: 100% 70%; }
    100% { background-position: 0% 30%; }
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #082f49, #020617);
}

/* Sidebar radio buttons */
div[role="radiogroup"] label {
    background: rgba(14,165,233,0.10);
    border: 1px solid rgba(56,189,248,0.25);
    border-radius: 14px;
    padding: 8px 12px;
    margin-bottom: 8px;
    transition: .2s ease;
}

div[role="radiogroup"] label:hover {
    background: rgba(56,189,248,0.25);
    box-shadow: 0 0 14px rgba(56,189,248,.35);
}

div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, #0284c7, #38bdf8);
    border: 1px solid #7dd3fc;
    box-shadow: 0 0 18px rgba(56,189,248,.55);
}

/* Glowing header */
.nw-hero {
    padding: 24px;
    border-radius: 24px;
    margin: 8px 0 24px 0;
    background:
        linear-gradient(135deg, rgba(7,20,38,0.98) 0%, rgba(15,39,68,0.98) 55%, rgba(6,17,31,0.98) 100%);
    border: 1px solid rgba(56, 189, 248, 0.55);
    box-shadow:
        0 0 18px rgba(56, 189, 248, 0.22),
        inset 0 0 18px rgba(56, 189, 248, 0.07);
    position: relative;
    overflow: hidden;
    animation: heroGlow 3.2s ease-in-out infinite;
}

@keyframes heroGlow {
    0%, 100% {
        box-shadow:
            0 0 18px rgba(56, 189, 248, 0.22),
            inset 0 0 18px rgba(56, 189, 248, 0.07);
        border-color: rgba(56, 189, 248, 0.45);
    }
    50% {
        box-shadow:
            0 0 34px rgba(56, 189, 248, 0.42),
            inset 0 0 24px rgba(56, 189, 248, 0.12);
        border-color: rgba(125, 211, 252, 0.75);
    }
}

.nw-hero-title {
    font-size: 32px;
    font-weight: 900;
    color: #e0f2fe;
    letter-spacing: -0.7px;
    text-shadow:
        0 0 8px rgba(125, 211, 252, 0.65),
        0 0 18px rgba(14, 165, 233, 0.45);
    animation: titlePulse 2.6s ease-in-out infinite;
}

@keyframes titlePulse {
    0%, 100% {
        opacity: 0.92;
        text-shadow:
            0 0 8px rgba(125, 211, 252, 0.55),
            0 0 18px rgba(14, 165, 233, 0.35);
    }
    50% {
        opacity: 1;
        text-shadow:
            0 0 12px rgba(186, 230, 253, 0.95),
            0 0 28px rgba(14, 165, 233, 0.75);
    }
}

.nw-hero-sub {
    margin-top: 5px;
    color: #bae6fd;
    font-weight: 750;
    font-size: 15px;
}

.nw-badge {
    display: inline-block;
    margin-top: 14px;
    padding: 8px 13px;
    border-radius: 999px;
    color: #e0f2fe;
    background: rgba(14, 165, 233, 0.18);
    border: 1px solid rgba(56, 189, 248, 0.42);
    font-size: 13px;
    font-weight: 850;
    box-shadow: 0 0 12px rgba(56,189,248,.14);
}

/* Exercise cards */
.nw-exercise-card {
    padding: 12px 13px;
    border-radius: 15px;
    background: linear-gradient(135deg, rgba(15,23,42,.68), rgba(7,20,38,.62));
    border: 1px solid rgba(56, 189, 248, 0.23);
    margin-bottom: 12px;
    box-shadow: 0 0 14px rgba(56,189,248,.08);
    animation: cardGlow 4s ease-in-out infinite;
}

@keyframes cardGlow {
    0%, 100% {
        box-shadow: 0 0 12px rgba(56,189,248,.08);
        border-color: rgba(56,189,248,.22);
    }
    50% {
        box-shadow: 0 0 20px rgba(56,189,248,.16);
        border-color: rgba(56,189,248,.36);
    }
}

.nw-card-title {
    font-weight: 900;
    color: #e0f2fe;
    font-size: 17px;
    margin-bottom: 4px;
}

.nw-small {
    color: #7dd3fc;
    font-weight: 750;
    font-size: 13px;
}

.nw-note {
    padding: 12px;
    border-radius: 14px;
    background: rgba(14, 165, 233, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.25);
    margin: 8px 0 12px 0;
}

/* Buttons */
.stButton button {
    background: linear-gradient(90deg, #0369a1, #0ea5e9, #38bdf8) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 900 !important;
    box-shadow: 0 0 15px rgba(56,189,248,.35);
    transition: .2s ease;
}

.stButton button:hover {
    transform: scale(1.02);
    box-shadow: 0 0 26px rgba(56,189,248,.75);
}

/* Metrics */
div[data-testid="stMetric"] {
    background: rgba(15,23,42,.65);
    border: 1px solid rgba(56,189,248,.20);
    padding: 12px;
    border-radius: 14px;
    box-shadow: 0 0 12px rgba(56,189,248,.08);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="nw-hero">
    <div class="nw-hero-title">⚡Training Tracker</div>
    <div class="nw-hero-sub">PPPPLA tracker - Tyson COOKE </div>
    <span class="nw-badge">Bench Strength • V-Taper • Delts • Ascend</span>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Menu", ["Today", "Cardio", "Progress", "Bodyweight", "Delete Data", "Routine"])

df = load_log()


# ------------------------------
# Today page
# ------------------------------
if page == "Today":
    st.header("Today’s Workout")

    workout = st.selectbox("Workout", list(ROUTINE.keys()))
    workout_date = st.date_input("Date", value=date.today())

    if workout == "Rest":
        st.info("Rest day. Walk, stretch, eat protein, sleep.")
    else:
        total_sets = sum(ex[1] for ex in ROUTINE[workout])
        st.caption(f"Target volume: {total_sets} working sets")

        rows = []

        for exercise, sets, reps_target in ROUTINE[workout]:
            with st.expander(f"⚡ {exercise}", expanded=True):
                st.markdown(
                    f"""
                    <div class="nw-exercise-card">
                        <div class="nw-card-title">{exercise}</div>
                        <div class="nw-small">{sets} sets × {reps_target}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if exercise == "Barbell Bench Press (Strength)":
                    st.markdown("""
<div class="nw-note">
<b>Strength bench:</b> heavy top set of 3-5 reps, then 3 back-off sets of 5-8 reps. Rest 3-5 minutes.
</div>
""", unsafe_allow_html=True)

                if exercise == "Paused Barbell Bench Press":
                    st.markdown("""
<div class="nw-note">
<b>Paused bench:</b> lighter bench with a 1-2 second dead stop on the chest. No bounce.
</div>
""", unsafe_allow_html=True)

                last = get_last_sets(df, exercise)
                if last is not None:
                    last_text = ", ".join(
                        f"{float(r.weight):g}kg × {int(r.reps)}"
                        for r in last.itertuples()
                    )
                    st.caption(f"Last session: {last_text}")

                st.caption(f"Suggestion: {suggest_weight(df, exercise)}")

                for set_no in range(1, sets + 1):
                    col1, col2 = st.columns(2)
                    with col1:
                        weight = st.number_input(
                            f"{exercise} set {set_no} kg",
                            min_value=0.0,
                            step=2.5,
                            key=f"{workout}-{exercise}-{set_no}-w",
                            placeholder="kg",
                        )
                    with col2:
                        reps = st.number_input(
                            f"{exercise} set {set_no} reps",
                            min_value=0,
                            step=1,
                            key=f"{workout}-{exercise}-{set_no}-r",
                            placeholder="reps",
                        )

                    if weight > 0 and reps > 0:
                        rows.append({
                            "date": str(workout_date),
                            "workout": workout,
                            "exercise": exercise,
                            "set": set_no,
                            "weight": weight,
                            "reps": reps,
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                        })

        if st.button("Save Workout", type="primary"):
            if rows:
                save_workout(rows)
                st.success("Workout saved.")
                st.balloons()
                st.rerun()
            else:
                st.warning("Enter at least one set first.")


# ------------------------------
# Cardio page
# ------------------------------
elif page == "Cardio":
    st.header("Cardio Tracker")

    cardio = load_csv(
        CARDIO_FILE,
        ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"]
    )

    c_date = st.date_input("Date", value=date.today())
    c_type = st.selectbox(
        "Type",
        ["Treadmill incline walk", "Outdoor walk", "Run", "Bike", "Stairmaster", "Boxing", "Other"]
    )

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
            row = pd.DataFrame([{
                "date": str(c_date),
                "type": c_type,
                "minutes": minutes,
                "distance_km": distance,
                "incline": incline,
                "speed": speed,
                "calories": calories,
                "notes": notes,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }])
            pd.concat([cardio, row], ignore_index=True).to_csv(CARDIO_FILE, index=False)
            st.success("Cardio saved.")
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


# ------------------------------
# Progress page
# ------------------------------
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

        sort_cols = ["date", "set"] if "set" in ex.columns else ["date"]
        st.dataframe(ex.sort_values(sort_cols, ascending=False), use_container_width=True)


# ------------------------------
# Bodyweight page
# ------------------------------
elif page == "Bodyweight":
    st.header("Bodyweight")

    bw_df = load_csv(BODYWEIGHT_FILE, ["date", "bodyweight", "timestamp"])

    bw_date = st.date_input("Date", value=date.today())
    bw = st.number_input("Bodyweight kg", min_value=0.0, step=0.1)

    if st.button("Save Bodyweight", type="primary"):
        if bw > 0:
            row = pd.DataFrame([{
                "date": str(bw_date),
                "bodyweight": bw,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }])
            pd.concat([bw_df, row], ignore_index=True).to_csv(BODYWEIGHT_FILE, index=False)
            st.success("Bodyweight saved.")
            st.rerun()

    if not bw_df.empty:
        bw_df["bodyweight"] = pd.to_numeric(bw_df["bodyweight"], errors="coerce").fillna(0)
        st.metric("Latest bodyweight", f"{bw_df.iloc[-1]['bodyweight']:.1f} kg")
        st.line_chart(bw_df, x="date", y="bodyweight")
        st.dataframe(bw_df.sort_values("date", ascending=False), use_container_width=True)


# ------------------------------
# Delete Data page
# ------------------------------
elif page == "Delete Data":
    st.header("Delete Logged Data")
    st.warning("Use this to remove accidental entries. This permanently edits the CSV file.")

    log_type = st.selectbox("Choose log", ["Workout", "Cardio", "Bodyweight"])

    if log_type == "Workout":
        path = LOG_FILE
        columns = ["date", "workout", "exercise", "set", "weight", "reps", "timestamp"]
    elif log_type == "Cardio":
        path = CARDIO_FILE
        columns = ["date", "type", "minutes", "distance_km", "incline", "speed", "calories", "notes", "timestamp"]
    else:
        path = BODYWEIGHT_FILE
        columns = ["date", "bodyweight", "timestamp"]

    data = load_csv(path, columns)

    if log_type == "Workout":
        data = normalise_workout_log(data)

    if data.empty:
        st.info(f"No {log_type.lower()} data found.")
    else:
        data = data.reset_index(drop=True)
        data.insert(0, "delete_id", data.index)

        dates = ["All"] + sorted(data["date"].dropna().astype(str).unique().tolist(), reverse=True)
        selected_date = st.selectbox("Filter by date", dates)

        if selected_date == "All":
            shown = data.copy()
        else:
            shown = data[data["date"].astype(str) == selected_date].copy()

        if log_type == "Workout" and not shown.empty and "exercise" in shown.columns:
            exercises = ["All"] + sorted(shown["exercise"].dropna().astype(str).unique().tolist())
            selected_exercise = st.selectbox("Filter by exercise", exercises)
            if selected_exercise != "All":
                shown = shown[shown["exercise"].astype(str) == selected_exercise].copy()

        st.dataframe(shown, use_container_width=True)
        st.caption("Use the delete_id from the first column.")

        delete_ids_text = st.text_input(
            "Enter delete_id numbers to delete",
            placeholder="Example: 0, 4, 7"
        )

        if st.button("Delete Selected Rows", type="primary"):
            if not delete_ids_text.strip():
                st.warning("Enter at least one delete_id.")
            else:
                try:
                    ids_to_delete = [int(x.strip()) for x in delete_ids_text.split(",") if x.strip()]
                    original = load_csv(path, columns).reset_index(drop=True)

                    if log_type == "Workout":
                        original = normalise_workout_log(original)

                    valid_ids = [i for i in ids_to_delete if 0 <= i < len(original)]

                    if not valid_ids:
                        st.warning("No valid delete_id numbers found.")
                    else:
                        updated = original.drop(index=valid_ids).reset_index(drop=True)
                        updated.to_csv(path, index=False)
                        st.success(f"Deleted {len(valid_ids)} row(s) from {log_type.lower()} log.")
                        st.rerun()

                except ValueError:
                    st.error("Use numbers separated by commas only. Example: 0, 4, 7")

        st.divider()
        st.subheader("Danger Zone")

        confirm_text = f"DELETE {log_type.upper()}"
        confirm = st.text_input(f"Type {confirm_text} to clear all {log_type.lower()} data")

        if st.button(f"Clear All {log_type} Data"):
            if confirm == confirm_text:
                pd.DataFrame(columns=columns).to_csv(path, index=False)
                st.success(f"All {log_type.lower()} data cleared.")
                st.rerun()
            else:
                st.error(f"Confirmation did not match. Type: {confirm_text}")


# ------------------------------
# Routine page
# ------------------------------
elif page == "Routine":
    st.header("PPPPLA Routine")

    st.info(
        "Strength bench = heavy top set + back-off sets. "
        "Paused bench = lighter controlled bench with a 1-2 second pause on the chest."
    )

    for day_num, (workout, exercises) in enumerate(ROUTINE.items(), start=1):
        st.subheader(f"Day {day_num}: {workout}")
        if workout == "Rest":
            st.write("Rest / walking / mobility")
        else:
            for exercise, sets, reps in exercises:
                st.write(f"**{exercise}** — {sets} sets × {reps}")
