import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# Database helper functions
def get_member_by_id(member_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = c.fetchone()
    conn.close()
    return member

def get_member_dashboard_stats(member_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    
    # Current subscription
    c.execute("""SELECT p.plan_name, s.end_date, s.status
                 FROM subscriptions s
                 JOIN plans p ON s.plan_id = p.id
                 WHERE s.member_id = ? AND s.status = 'Active'
                 ORDER BY s.end_date DESC LIMIT 1""", (member_id,))
    subscription = c.fetchone()
    
    # Attendance count this month
    c.execute("""SELECT COUNT(*) FROM attendance 
                 WHERE member_id = ? AND strftime('%Y-%m', check_in) = strftime('%Y-%m', 'now')""", 
              (member_id,))
    monthly_attendance = c.fetchone()[0]
    
    # Total sessions
    c.execute("SELECT COUNT(*) FROM training_sessions WHERE member_id = ?", (member_id,))
    total_sessions = c.fetchone()[0]
    
    # Active workout plans
    c.execute("SELECT COUNT(*) FROM workout_plans WHERE member_id = ? AND is_active = 1", (member_id,))
    active_plans = c.fetchone()[0]
    
    conn.close()
    
    return {
        'subscription': subscription,
        'monthly_attendance': monthly_attendance,
        'total_sessions': total_sessions,
        'active_plans': active_plans
    }

def get_active_announcements():
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT title, message, created_at FROM announcements 
               WHERE is_active=1 ORDER BY created_at DESC LIMIT 5"""
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_member_subscriptions(member_id):
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT s.id, p.plan_name, s.start_date, s.end_date, s.status, p.price
               FROM subscriptions s
               JOIN plans p ON s.plan_id = p.id
               WHERE s.member_id = ?
               ORDER BY s.start_date DESC"""
    df = pd.read_sql_query(query, conn, params=(member_id,))
    conn.close()
    return df

def get_all_plans():
    conn = sqlite3.connect('gym_management.db')
    df = pd.read_sql_query("SELECT * FROM plans WHERE is_active=1", conn)
    conn.close()
    return df

def mark_attendance(member_id, workout_type=None):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    # Check if already checked in today
    today = datetime.now().date()
    c.execute("""SELECT id FROM attendance 
                 WHERE member_id=? AND DATE(check_in)=? AND check_out IS NULL""", 
              (member_id, today))
    existing = c.fetchone()
    
    if existing:
        conn.close()
        return False, "Already checked in today!"
    
    c.execute("INSERT INTO attendance (member_id, check_in, workout_type) VALUES (?, ?, ?)",
              (member_id, datetime.now(), workout_type))
    conn.commit()
    conn.close()
    return True, "Check-in successful!"

def checkout_attendance(member_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("""SELECT id, check_in FROM attendance 
                 WHERE member_id=? AND check_out IS NULL 
                 ORDER BY check_in DESC LIMIT 1""", (member_id,))
    attendance = c.fetchone()
    
    if not attendance:
        conn.close()
        return False, "No active check-in found!"
    
    check_in_time = datetime.strptime(attendance[1], "%Y-%m-%d %H:%M:%S.%f")
    duration = (datetime.now() - check_in_time).total_seconds() / 60
    
    c.execute("UPDATE attendance SET check_out=?, duration_minutes=? WHERE id=?",
              (datetime.now(), int(duration), attendance[0]))
    conn.commit()
    conn.close()
    return True, f"Check-out successful! Duration: {int(duration)} minutes"

def get_member_attendance(member_id, limit=30):
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT id, check_in, check_out, workout_type, duration_minutes
               FROM attendance
               WHERE member_id = ?
               ORDER BY check_in DESC
               LIMIT ?"""
    df = pd.read_sql_query(query, conn, params=(member_id, limit))
    conn.close()
    return df

def get_all_trainers():
    conn = sqlite3.connect('gym_management.db')
    df = pd.read_sql_query("SELECT * FROM trainers WHERE status='Active'", conn)
    conn.close()
    return df

def book_session(member_id, trainer_id, session_date, duration, session_type):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("""INSERT INTO training_sessions (member_id, trainer_id, session_date, duration_minutes, session_type)
                 VALUES (?, ?, ?, ?, ?)""",
              (member_id, trainer_id, session_date, duration, session_type))
    conn.commit()
    conn.close()
    return True, "Session booked successfully!"

def get_member_sessions(member_id):
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT ts.id, t.name as trainer, ts.session_date, ts.duration_minutes, 
                      ts.session_type, ts.status
               FROM training_sessions ts
               JOIN trainers t ON ts.trainer_id = t.id
               WHERE ts.member_id = ?
               ORDER BY ts.session_date DESC"""
    df = pd.read_sql_query(query, conn, params=(member_id,))
    conn.close()
    return df

def get_member_workout_plans(member_id):
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT wp.id, wp.plan_name, t.name as trainer, wp.description, 
                      wp.exercises, wp.created_date, wp.is_active
               FROM workout_plans wp
               LEFT JOIN trainers t ON wp.trainer_id = t.id
               WHERE wp.member_id = ?
               ORDER BY wp.created_date DESC"""
    df = pd.read_sql_query(query, conn, params=(member_id,))
    conn.close()
    return df

def get_member_payments(member_id):
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT p.id, p.amount, p.payment_date, p.payment_method, p.status, p.transaction_id
               FROM payments p
               WHERE p.member_id = ?
               ORDER BY p.payment_date DESC"""
    df = pd.read_sql_query(query, conn, params=(member_id,))
    conn.close()
    return df

def add_feedback(member_id, rating, message):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("INSERT INTO feedback (member_id, rating, message) VALUES (?, ?, ?)",
              (member_id, rating, message))
    conn.commit()
    conn.close()

def authenticate(username, password):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, username, role, member_id FROM users WHERE username=? AND password=?", (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

# ==================== USER PANEL ====================
def user_panel(member_id):
    st.title("👤 Member Portal")
    
    # Get member info
    member = get_member_by_id(member_id)
    if not member:
        st.error("Member not found!")
        return
    
    st.sidebar.success(f"Welcome, {member[1]}!")
    
    menu = st.sidebar.selectbox("Member Menu", [
        "Dashboard", "My Profile", "My Subscription", "Attendance", 
        "Book Training", "Workout Plans", "Payments", "Feedback","Contact"
    ])
    
    if menu == "Dashboard":
        st.subheader("📊 My Dashboard")
        
        stats = get_member_dashboard_stats(member_id)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("This Month Visits", stats['monthly_attendance'])
        col2.metric("Training Sessions", stats['total_sessions'])
        col3.metric("Active Plans", stats['active_plans'])
        
        if stats['subscription']:
            with st.container():
                st.subheader("🎫 Current Membership")
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Plan:** {stats['subscription'][0]}")
                col2.write(f"**Expires:** {stats['subscription'][1]}")
                col3.write(f"**Status:** {stats['subscription'][2]}")
                
                # Days remaining
                end_date = datetime.strptime(stats['subscription'][1], "%Y-%m-%d")
                days_left = (end_date - datetime.now()).days
                if days_left < 7:
                    st.warning(f"⚠️ Your membership expires in {days_left} days!")
                else:
                    st.info(f"✅ {days_left} days remaining")
        else:
            st.warning("⚠️ No active subscription. Please contact admin to renew your membership!")
        
        st.subheader("📢 Latest Announcements")
        announcements = get_active_announcements()
        if not announcements.empty:
            for _, ann in announcements.iterrows():
                with st.expander(f"📌 {ann['title']}"):
                    st.write(ann['message'])
                    st.caption(f"Posted on: {ann['created_at'][:10]}")
        else:
            st.info("No announcements available")
    
    elif menu == "My Profile":
        st.subheader("👤 My Profile")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("https://via.placeholder.com/150", caption="Profile Photo")
            st.info("📧 Contact admin to update your profile")
        
        with col2:
            st.write(f"**Name:** {member[1]}")
            st.write(f"**Email:** {member[2]}")
            st.write(f"**Phone:** {member[3]}")
            st.write(f"**Gender:** {member[5]}")
            st.write(f"**Age:** {member[6]}")
            st.write(f"**Blood Group:** {member[8] or 'N/A'}")
            st.write(f"**Member Since:** {member[10]}")
            st.write(f"**Status:** {'🟢 ' + member[12] if member[12] == 'Active' else '🔴 ' + member[12]}")
        
        st.subheader("📝 Additional Information")
        st.write(f"**Address:** {member[4] or 'N/A'}")
        st.write(f"**Emergency Contact:** {member[7] or 'N/A'}")
        
        if member[9]:
            st.warning(f"**Medical Conditions:** {member[9]}")
        else:
            st.success("**Medical Conditions:** None reported")
    
    elif menu == "My Subscription":
        st.subheader("💳 My Subscriptions")
        
        tab1, tab2 = st.tabs(["Current Subscriptions", "Available Plans"])
        
        with tab1:
            subs_df = get_member_subscriptions(member_id)
            if not subs_df.empty:
                st.dataframe(subs_df, use_container_width=True)
                
                # Show active subscription details
                active_sub = subs_df[subs_df['status'] == 'Active']
                if not active_sub.empty:
                    st.success(f"✅ Active Plan: {active_sub.iloc[0]['plan_name']}")
                    st.info(f"💰 Amount Paid: ₹{active_sub.iloc[0]['price']}")
            else:
                st.info("No subscriptions found. Contact admin to purchase a plan.")
        
        with tab2:
            st.subheader("🏋️ Available Membership Plans")
            plans_df = get_all_plans()
            if not plans_df.empty:
                for _, plan in plans_df.iterrows():
                    with st.expander(f"💳 {plan['plan_name']} - ₹{plan['price']}"):
                        st.write(f"**Duration:** {plan['duration_months']} months")
                        if plan['features']:
                            st.write(f"**Features:** {plan['features']}")
                        if plan['description']:
                            st.write(f"**Description:** {plan['description']}")
                        st.info("📞 Contact admin to subscribe to this plan")
            else:
                st.info("No plans available")
    
    elif menu == "Attendance":
        st.subheader("✅ My Attendance")
        
        tab1, tab2 = st.tabs(["Attendance History", "Mark Attendance"])
        
        with tab1:
            attendance_df = get_member_attendance(member_id)
            if not attendance_df.empty:
                st.dataframe(attendance_df, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Visits", len(attendance_df))
                
                # This month attendance
                conn = sqlite3.connect('gym_management.db')
                c = conn.cursor()
                c.execute("""SELECT COUNT(*) FROM attendance 
                            WHERE member_id = ? AND strftime('%Y-%m', check_in) = strftime('%Y-%m', 'now')""", 
                         (member_id,))
                monthly = c.fetchone()[0]
                conn.close()
                col2.metric("This Month", monthly)
                
                # Average duration
                avg_duration = attendance_df['duration_minutes'].mean()
                if pd.notna(avg_duration):
                    col3.metric("Avg. Duration", f"{int(avg_duration)} min")
            else:
                st.info("No attendance records. Start by checking in!")
        
        with tab2:
            st.write("### Quick Check-In/Out")
            
            # Check current status
            conn = sqlite3.connect('gym_management.db')
            c = conn.cursor()
            today = datetime.now().date()
            c.execute("""SELECT id, check_in FROM attendance 
                         WHERE member_id=? AND DATE(check_in)=? AND check_out IS NULL""", 
                      (member_id, today))
            active_checkin = c.fetchone()
            conn.close()
            
            if active_checkin:
                check_in_time = datetime.strptime(active_checkin[1], "%Y-%m-%d %H:%M:%S.%f")
                duration = (datetime.now() - check_in_time).total_seconds() / 60
                st.success(f"✅ You're checked in! Duration: {int(duration)} minutes")
            else:
                st.info("You're currently checked out")
            
            workout_type = st.selectbox("Workout Type", ["Cardio", "Strength", "Yoga", "CrossFit", "Mixed", "Other"])
            
            col1, col2 = st.columns(2)
            if col1.button("✅ Check In", use_container_width=True, type="primary"):
                success, message = mark_attendance(member_id, workout_type)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            
            if col2.button("🚪 Check Out", use_container_width=True):
                success, message = checkout_attendance(member_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    elif menu == "Book Training":
        st.subheader("🎯 Training Sessions")
        
        tab1, tab2 = st.tabs(["My Sessions", "Book New Session"])
        
        with tab1:
            sessions_df = get_member_sessions(member_id)
            if not sessions_df.empty:
                st.dataframe(sessions_df, use_container_width=True)
                st.metric("Total Sessions", len(sessions_df))
            else:
                st.info("No training sessions booked yet")
        
        with tab2:
            st.write("### Book a Training Session")
            trainers_df = get_all_trainers()
            if not trainers_df.empty:
                with st.form("book_session_form"):
                    trainer_id = st.selectbox("Select Trainer",
                                             options=trainers_df['id'].tolist(),
                                             format_func=lambda x: f"{trainers_df[trainers_df['id']==x]['name'].values[0]} - {trainers_df[trainers_df['id']==x]['specialization'].values[0]}")
                    
                    # Show trainer details
                    selected_trainer = trainers_df[trainers_df['id'] == trainer_id].iloc[0]
                    st.info(f"🏃 **{selected_trainer['name']}** | Specialization: {selected_trainer['specialization']} | Experience: {selected_trainer['experience_years']} years")
                    
                    session_date = st.date_input("Session Date", min_value=datetime.now().date())
                    session_time = st.time_input("Session Time", value=datetime.now().time())
                    duration = st.number_input("Duration (minutes)", min_value=30, max_value=180, value=60, step=15)
                    session_type = st.selectbox("Session Type", ["Personal Training", "Group Training", "Consultation", "Diet Planning"])
                    
                    if st.form_submit_button("📅 Book Session", type="primary"):
                        session_datetime = datetime.combine(session_date, session_time)
                        success, message = book_session(member_id, trainer_id, session_datetime, duration, session_type)
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
            else:
                st.warning("No trainers available at the moment")
    
    elif menu == "Workout Plans":
        st.subheader("💪 My Workout Plans")
        
        plans_df = get_member_workout_plans(member_id)
        if not plans_df.empty:
            for _, plan in plans_df.iterrows():
                status_emoji = "✅" if plan['is_active'] else "⏸️"
                status_text = "Active" if plan['is_active'] else "Inactive"
                
                with st.expander(f"{status_emoji} {plan['plan_name']} - By {plan['trainer'] or 'Self'} [{status_text}]"):
                    st.write(f"**Description:** {plan['description']}")
                    st.write(f"**Created Date:** {plan['created_date']}")
                    st.write("**Exercises:**")
                    st.text_area("Exercise Details", value=plan['exercises'], height=200, disabled=True, key=f"ex_{plan['id']}")
        else:
            st.info("No workout plans assigned yet. Book a training session to get personalized workout plans!")
    
    elif menu == "Payments":
        st.subheader("💰 My Payments")
        
        payments_df = get_member_payments(member_id)
        if not payments_df.empty:
            st.dataframe(payments_df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            total = payments_df['amount'].sum()
            col1.metric("Total Paid", f"₹{total:.2f}")
            col2.metric("Total Transactions", len(payments_df))
            
            # Payment history chart
            st.subheader("📊 Payment History")
            payments_df['payment_date'] = pd.to_datetime(payments_df['payment_date'])
            monthly_payments = payments_df.groupby(payments_df['payment_date'].dt.to_period('M'))['amount'].sum()
            st.bar_chart(monthly_payments)
        else:
            st.info("No payment records available")

    
    elif menu == "Contact":
        st.title("📩 Contact Us")
        st.write("We'd love to hear from you!")

        st.markdown("---")

        with st.form("contact_form"):
            name = st.text_input("👤 Full Name")
            email = st.text_input("📧 Email Address")
            subject = st.text_input("📝 Subject")
            message = st.text_area("💬 Message", height=150)

            submitted = st.form_submit_button("🚀 Send Message")

            if submitted:
                if name and email and message:
                    st.success("✅ Message sent successfully!")
                else:
                    st.error("❌ Please fill all required fields.")

        st.markdown("---")

        st.subheader("📌 Contact Details")
        st.write("📧 **Email:** support@progym.com")
        st.write("📞 **Phone:** +91 98765 43210")
        st.write("🌍 **Website:** www.progym.com")
        st.write("📍 **Location:** India")








    
    elif menu == "Feedback":
        st.subheader("💬 Share Your Feedback")
        
        st.write("We value your feedback! Help us improve our services.")
        
        with st.form("feedback_form"):
            rating = st.slider("Rate your overall experience", 1, 5, 5, help="1 = Poor, 5 = Excellent")
            
            # Show rating emoji
            rating_emojis = {1: "😞", 2: "😕", 3: "😐", 4: "😊", 5: "🤩"}
            st.write(f"### {rating_emojis[rating]} {rating}/5")
            
            message = st.text_area("Your feedback and suggestions", height=150, placeholder="Tell us about your experience...")
            
            if st.form_submit_button("Submit Feedback", type="primary"):
                if message:
                    add_feedback(member_id, rating, message)
                    st.success("✅ Thank you for your feedback! We appreciate your input.")
                    st.balloons()
                else:
                    st.error("Please enter your feedback before submitting")

def main():
    st.set_page_config(page_title="Member Portal - Gym Management", page_icon="👤", layout="wide")
    
    # Session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Login page
    if not st.session_state.logged_in:
        st.title("👤 Member Portal Login")
        st.write("### Welcome to Gym Management System")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.container():
                st.subheader("🔐 Login to your account")
                
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                if st.button("Login", type="primary", use_container_width=True):
                    user = authenticate(username, password)
                    if user and user[2] == "member":  # Check if role is member
                        st.session_state.logged_in = True
                        st.session_state.user_id = user[0]
                        st.session_state.username = user[1]
                        st.session_state.member_id = user[3]
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or not a member account!")
                
                st.divider()
                st.info("📞 Don't have an account? Contact gym admin to create your member account.")
        
        return
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Display user panel
    user_panel(st.session_state.member_id)

if __name__ == "__main__":
    main()