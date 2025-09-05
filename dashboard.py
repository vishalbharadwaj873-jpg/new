import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---- Simple dropout predictor ----
def predict_dropout(attendance, avg_grade, lms_activity, financial_aid):
    score = 0
    if attendance < 60: score += 0.4
    if avg_grade < 60: score += 0.3
    if lms_activity < 5: score += 0.2
    if financial_aid == 0: score += 0.1

    if score >= 0.7:
        return "High", score
    elif score >= 0.4:
        return "Medium", score
    else:
        return "Low", score

# ---- Load users ----
def load_users():
    return pd.read_csv("students.csv")

def save_users(df):
    df.to_csv("students.csv", index=False)

df_users = load_users()

# ---- Session State ----
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# ---- Login Page ----
if not st.session_state.logged_in:
    st.title("🔐 Login to Dropout Predictor")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = df_users[(df_users["username"] == username) &
                        (df_users["password"] == password)]
        if not user.empty:
            st.session_state.logged_in = True
            st.session_state.current_user = user.iloc[0].to_dict()
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---- After Login ----
else:
    user = st.session_state.current_user
    role = user["role"]

    # Sidebar Menu
    st.sidebar.title("📌 Navigation")
    menu_options = ["Home"]
    if role == "student":
        menu_options += ["My Risk Report"]
    elif role == "teacher":
        menu_options += ["Student Data", "Visualizations", "Update Student Data"]
    menu_options += ["Change Password"]  # ✅ Added for both

    choice = st.sidebar.radio("Go to", menu_options)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()

    # ---- Home Page ----
    if choice == "Home":
        st.title("🎓 Dropout Prediction & Counseling System")
        st.subheader(f"Welcome {user['full_name']} ({user['username']})")
        st.write(
            """
            This system helps identify students at risk of dropping out based on
            academic and activity data.  
            - **Students** can view their personal risk level and recommendations.  
            - **Admins** can monitor, update student data, analyze trends, and support at-risk learners.  
            """
        )

    # ---- Student Dashboard ----
    elif choice == "My Risk Report" and role == "student":
        st.title("📊 My Dropout Risk Report")

        attendance = user["attendance"]
        avg_grade = user["avg_grade"]
        lms_activity = user["lms_activity"]
        financial_aid = user["financial_aid"]

        risk, score = predict_dropout(attendance, avg_grade, lms_activity, financial_aid)

        st.metric("Attendance (%)", attendance)
        st.metric("Average Grade (%)", avg_grade)
        st.metric("LMS Activity", lms_activity)
        st.metric("Financial Aid", "Yes" if financial_aid == 1 else "No")

        if risk == "High":
            st.markdown(f"### 🔴 Predicted Dropout Risk: **{risk}**")
        elif risk == "Medium":
            st.markdown(f"### 🟠 Predicted Dropout Risk: **{risk}**")
        else:
            st.markdown(f"### 🟢 Predicted Dropout Risk: **{risk}**")

        st.progress(int(score * 100))

    # ---- Admin Dashboard ----
    elif choice == "Student Data" and role == "teacher":
        st.title("📋 Student Data Overview")

        # Search box
        search_query = st.text_input("🔍 Search by Student ID, Username, or Full Name")
        filtered_df = df_users[df_users["role"] == "student"]

        if search_query.strip():
            filtered_df = filtered_df[
                filtered_df["student_id"].astype(str).str.contains(search_query, case=False) |
                filtered_df["username"].str.contains(search_query, case=False) |
                filtered_df["full_name"].str.contains(search_query, case=False)
            ]

        results = []
        for _, row in filtered_df.iterrows():
            risk, score = predict_dropout(row["attendance"], row["avg_grade"],
                                          row["lms_activity"], row["financial_aid"])
            results.append({
                "student_id": row["student_id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "attendance": row["attendance"],
                "avg_grade": row["avg_grade"],
                "lms_activity": row["lms_activity"],
                "financial_aid": "Yes" if row["financial_aid"] == 1 else "No",
                "risk": risk,
                "score": round(score, 2)
            })

        res_df = pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)

        def highlight_risk(val):
            if val == "High":
                return "color: red; font-weight: bold;"
            elif val == "Medium":
                return "color: orange; font-weight: bold;"
            else:
                return "color: green; font-weight: bold;"

        st.dataframe(res_df.style.applymap(highlight_risk, subset=["risk"]),
                     use_container_width=True, hide_index=True)

    elif choice == "Visualizations" and role == "teacher":
        st.title("📊 Data Visualizations")

        results = []
        for _, row in df_users[df_users["role"] == "student"].iterrows():
            risk, score = predict_dropout(row["attendance"], row["avg_grade"],
                                          row["lms_activity"], row["financial_aid"])
            results.append({
                "attendance": row["attendance"],
                "avg_grade": row["avg_grade"],
                "risk": risk
            })
        res_df = pd.DataFrame(results)

        # Risk distribution pie chart
        st.subheader("Risk Distribution")
        fig, ax = plt.subplots()
        risk_counts = res_df["risk"].value_counts()
        ax.pie(risk_counts, labels=risk_counts.index, autopct="%1.1f%%",
               colors=["red", "orange", "green"])
        st.pyplot(fig)

        # Scatter plot
        st.subheader("Attendance vs Grades")
        fig2, ax2 = plt.subplots()
        color_map = {"High": "red", "Medium": "orange", "Low": "green"}
        for risk_cat, group in res_df.groupby("risk"):
            ax2.scatter(group["attendance"], group["avg_grade"],
                        label=risk_cat, color=color_map[risk_cat])
        ax2.set_xlabel("Attendance (%)")
        ax2.set_ylabel("Average Grade (%)")
        ax2.set_title("Attendance vs Grades (by Risk Level)")
        ax2.legend()
        st.pyplot(fig2)

    elif choice == "Update Student Data" and role == "teacher":
        st.title("✏️ Update Student Data")

        # Search + select student
        search_query = st.text_input("🔍 Search Student by ID, Username, or Full Name")
        student_list = df_users[df_users["role"] == "student"]

        if search_query.strip():
            student_list = student_list[
                student_list["student_id"].astype(str).str.contains(search_query, case=False) |
                student_list["username"].str.contains(search_query, case=False) |
                student_list["full_name"].str.contains(search_query, case=False)
            ]

        if not student_list.empty:
            student_choice = st.selectbox(
                "Select a student",
                student_list.apply(lambda x: f"{x['student_id']} - {x['full_name']} ({x['username']})", axis=1)
            )

            if student_choice:
                student_id = int(student_choice.split(" - ")[0])
                student_row = df_users[df_users["student_id"] == student_id].iloc[0]

                attendance = st.slider("Attendance (%)", 0, 100, int(student_row["attendance"]))
                avg_grade = st.slider("Average Grade (%)", 0, 100, int(student_row["avg_grade"]))
                lms_activity = st.slider("LMS Activity (logins)", 0, 20, int(student_row["lms_activity"]))
                financial_aid = st.selectbox("Financial Aid", [0, 1], index=int(student_row["financial_aid"]))

                if st.button("💾 Save Changes"):
                    df_users.loc[df_users["student_id"] == student_id,
                                 ["attendance", "avg_grade", "lms_activity", "financial_aid"]] = [
                                     attendance, avg_grade, lms_activity, financial_aid
                                 ]
                    save_users(df_users)
                    st.success("Student data updated successfully ✅")
        else:
            st.warning("⚠️ No students found for the given search.")

    # ---- Change Password ----
    elif choice == "Change Password":
        st.title("🔑 Change Password")

        current_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")

        if st.button("Update Password"):
            if current_pw != user["password"]:
                st.error("❌ Current password is incorrect.")
            elif new_pw != confirm_pw:
                st.error("❌ New passwords do not match.")
            elif len(new_pw) < 5:
                st.warning("⚠️ Password should be at least 5 characters.")
            else:
                df_users.loc[df_users["username"] == user["username"], "password"] = new_pw
                save_users(df_users)
                st.session_state.current_user["password"] = new_pw
                st.success("✅ Password updated successfully!")
