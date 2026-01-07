import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# Import database initialization
from db_setup import init_db

# ==================== AUTHENTICATION ====================
def authenticate(username, password):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, username, role, member_id FROM users WHERE username=? AND password=?", (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

# ==================== MEMBER MANAGEMENT ====================
def add_member(name, email, phone, address, gender, age, emergency_contact, blood_group, medical_conditions):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO members (name, email, phone, address, gender, age, emergency_contact, 
                     blood_group, medical_conditions, join_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (name, email, phone, address, gender, age, emergency_contact, blood_group, 
                   medical_conditions, datetime.now().date()))
        member_id = c.lastrowid
        conn.commit()
        conn.close()
        return True, "Member added successfully!", member_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already exists!", None

def get_all_members():
    conn = sqlite3.connect('gym_management.db')
    df = pd.read_sql_query("SELECT * FROM members ORDER BY id DESC", conn)
    conn.close()
    return df

def update_member(member_id, name, email, phone, address, gender, age, emergency_contact, blood_group, medical_conditions, status):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("""UPDATE members SET name=?, email=?, phone=?, address=?, gender=?, age=?, 
                 emergency_contact=?, blood_group=?, medical_conditions=?, status=?
                 WHERE id=?""", 
              (name, email, phone, address, gender, age, emergency_contact, blood_group, 
               medical_conditions, status, member_id))
    conn.commit()
    conn.close()

def delete_member(member_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        # Check if member has active subscriptions
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE member_id=? AND status='Active'", (member_id,))
        active_subs = c.fetchone()[0]
        
        if active_subs > 0:
            conn.close()
            return False, f"Cannot delete! Member has {active_subs} active subscription(s)."
        
        c.execute("DELETE FROM members WHERE id=?", (member_id,))
        conn.commit()
        conn.close()
        return True, "Member deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting member: {str(e)}"

def register_user(username, password, member_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role, member_id) VALUES (?, ?, ?, ?)",
                  (username, hashed_pw, "member", member_id))
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists!"

# ==================== PLAN MANAGEMENT ====================
def add_plan(plan_name, duration, price, features, description):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("INSERT INTO plans (plan_name, duration_months, price, features, description) VALUES (?, ?, ?, ?, ?)",
              (plan_name, duration, price, features, description))
    conn.commit()
    conn.close()

def get_all_plans():
    conn = sqlite3.connect('gym_management.db')
    df = pd.read_sql_query("SELECT * FROM plans WHERE is_active=1", conn)
    conn.close()
    return df

def delete_plan(plan_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        # Check if plan is being used in active subscriptions
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE plan_id=? AND status='Active'", (plan_id,))
        active_subs = c.fetchone()[0]
        
        if active_subs > 0:
            conn.close()
            return False, f"Cannot delete! {active_subs} active subscription(s) using this plan."
        
        c.execute("DELETE FROM plans WHERE id=?", (plan_id,))
        conn.commit()
        conn.close()
        return True, "Plan deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting plan: {str(e)}"

# ==================== SUBSCRIPTION MANAGEMENT ====================
def add_subscription(member_id, plan_id, start_date, payment_method):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("SELECT duration_months, price FROM plans WHERE id=?", (plan_id,))
    plan = c.fetchone()
    end_date = start_date + timedelta(days=plan[0] * 30)
    
    c.execute("""INSERT INTO subscriptions (member_id, plan_id, start_date, end_date)
                 VALUES (?, ?, ?, ?)""", (member_id, plan_id, start_date, end_date))
    sub_id = c.lastrowid
    
    c.execute("""INSERT INTO payments (member_id, subscription_id, amount, payment_date, payment_method, status)
                 VALUES (?, ?, ?, ?, ?, 'Completed')""", 
              (member_id, sub_id, plan[1], datetime.now().date(), payment_method))
    
    conn.commit()
    conn.close()
    return True, "Subscription created successfully!"

def get_all_subscriptions():
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT s.id, m.name, m.email, p.plan_name, s.start_date, s.end_date, s.status
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               ORDER BY s.start_date DESC"""
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def cancel_subscription(subscription_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE subscriptions SET status='Cancelled' WHERE id=?", (subscription_id,))
        conn.commit()
        conn.close()
        return True, "Subscription cancelled successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error cancelling subscription: {str(e)}"

# ==================== ATTENDANCE MANAGEMENT ====================
def mark_attendance(member_id, workout_type=None):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
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

def get_today_attendance():
    conn = sqlite3.connect('gym_management.db')
    today = datetime.now().date()
    query = """SELECT a.id, m.id as member_id, m.name, a.check_in, a.check_out, a.workout_type
               FROM attendance a
               JOIN members m ON a.member_id = m.id
               WHERE DATE(a.check_in) = ?
               ORDER BY a.check_in DESC"""
    df = pd.read_sql_query(query, conn, params=(today,))
    conn.close()
    return df

def delete_attendance(attendance_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM attendance WHERE id=?", (attendance_id,))
        conn.commit()
        conn.close()
        return True, "Attendance record deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting attendance: {str(e)}"

# ==================== TRAINER MANAGEMENT ====================
def add_trainer(name, email, phone, specialization, certifications, experience, hire_date, salary):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO trainers (name, email, phone, specialization, certifications, 
                     experience_years, hire_date, salary)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (name, email, phone, specialization, certifications, experience, hire_date, salary))
        conn.commit()
        conn.close()
        return True, "Trainer added successfully!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already exists!"

def get_all_trainers():
    conn = sqlite3.connect('gym_management.db')
    df = pd.read_sql_query("SELECT * FROM trainers WHERE status='Active'", conn)
    conn.close()
    return df

def delete_trainer(trainer_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM trainers WHERE id=?", (trainer_id,))
        conn.commit()
        conn.close()
        return True, "Trainer deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting trainer: {str(e)}"

# ==================== EQUIPMENT MANAGEMENT ====================
def add_equipment(name, category, purchase_date, price, condition):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("INSERT INTO equipment (name, category, purchase_date, purchase_price, condition) VALUES (?, ?, ?, ?, ?)",
              (name, category, purchase_date, price, condition))
    conn.commit()
    conn.close()

def get_all_equipment():
    conn = sqlite3.connect('gym_management.db')
    df = pd.read_sql_query("SELECT * FROM equipment ORDER BY id DESC", conn)
    conn.close()
    return df

def delete_equipment(equipment_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM equipment WHERE id=?", (equipment_id,))
        conn.commit()
        conn.close()
        return True, "Equipment deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting equipment: {str(e)}"

# ==================== ANNOUNCEMENTS ====================
def add_announcement(title, message, created_by):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    c.execute("INSERT INTO announcements (title, message, created_by) VALUES (?, ?, ?)",
              (title, message, created_by))
    conn.commit()
    conn.close()

def get_active_announcements():
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT title, message, created_at FROM announcements 
               WHERE is_active=1 ORDER BY created_at DESC LIMIT 5"""
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_announcement(announcement_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM announcements WHERE id=?", (announcement_id,))
        conn.commit()
        conn.close()
        return True, "Announcement deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting announcement: {str(e)}"

# ==================== FEEDBACK ====================
def get_all_feedback():
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT f.id, m.name, f.rating, f.message, f.created_at, f.response
               FROM feedback f
               JOIN members m ON f.member_id = m.id
               ORDER BY f.created_at DESC"""
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ==================== PAYMENTS ====================
def get_all_payments():
    conn = sqlite3.connect('gym_management.db')
    query = """SELECT p.id, m.name, p.amount, p.payment_date, p.payment_method, p.status
               FROM payments p
               JOIN members m ON p.member_id = m.id
               ORDER BY p.payment_date DESC"""
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_payment(payment_id):
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM payments WHERE id=?", (payment_id,))
        conn.commit()
        conn.close()
        return True, "Payment record deleted successfully!"
    except Exception as e:
        conn.close()
        return False, f"Error deleting payment: {str(e)}"

# ==================== DASHBOARD STATS ====================
def get_dashboard_stats():
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM members WHERE status='Active'")
    active_members = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status='Active' AND end_date >= DATE('now')")
    active_subs = c.fetchone()[0]
    
    today = datetime.now().date()
    c.execute("SELECT COUNT(*) FROM attendance WHERE DATE(check_in) = ?", (today,))
    today_attendance = c.fetchone()[0]
    
    c.execute("SELECT SUM(amount) FROM payments WHERE DATE(payment_date) = ?", (today,))
    today_revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM trainers WHERE status='Active'")
    active_trainers = c.fetchone()[0]
    
    c.execute("""SELECT COUNT(*) FROM subscriptions 
                 WHERE status='Active' AND end_date BETWEEN DATE('now') AND DATE('now', '+7 days')""")
    expiring_soon = c.fetchone()[0]
    
    conn.close()
    return {
        'active_members': active_members,
        'active_subs': active_subs,
        'today_attendance': today_attendance,
        'today_revenue': today_revenue,
        'active_trainers': active_trainers,
        'expiring_soon': expiring_soon
    }

# ==================== ADMIN PANEL ====================
def admin_panel():
    
    st.title("🏋️ Admin Dashboard")
    
    menu = st.sidebar.selectbox("Admin Menu", [
        "Dashboard", "Members", "Membership Plans", "Subscriptions",
        "Attendance", "Trainers", "Equipment", "Payments", 
        "Announcements", "Feedback", "Reports"
    ])
    
    if menu == "Dashboard":
        stats = get_dashboard_stats()
        st.subheader("📊 Overview")
        st.image(r".\assets\gym_banner.jpg", 
             caption="Gym Dashboard Overview 📊", 
             use_container_width=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Active Members", stats['active_members'], help="Total active gym members")
        col2.metric("Active Subscriptions", stats['active_subs'], help="Current active memberships")
        col3.metric("Active Trainers", stats['active_trainers'], help="Trainers currently employed")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Today's Attendance", stats['today_attendance'], help="Members checked in today")
        col2.metric("Today's Revenue", f"₹{stats['today_revenue']:.2f}", help="Revenue collected today")
        col3.metric("Expiring Soon", stats['expiring_soon'], delta="Next 7 days", help="Memberships expiring within 7 days")
        
        st.divider()
        
        st.subheader("📅 Today's Attendance")
        attendance_df = get_today_attendance()
        if not attendance_df.empty:
            st.dataframe(attendance_df, use_container_width=True, hide_index=True)
        else:
            st.info("No attendance records for today")
        
        st.divider()
        
        st.subheader("📢 Recent Announcements")
        announcements = get_active_announcements()
        if not announcements.empty:
            for _, ann in announcements.iterrows():
                with st.expander(f"📌 {ann['title']} - {ann['created_at'][:10]}"):
                    st.write(ann['message'])
        else:
            st.info("No announcements")
    
    elif menu == "Members":
        st.subheader("👥 Member Management")
        st.image(r".\assets\members.png",
             use_container_width=20)
        
        tab1, tab2, tab3, tab4 = st.tabs(["View Members", "Add Member", "Update Member", "Delete Member"])
        
        with tab1:
            members_df = get_all_members()
            if not members_df.empty:
                search = st.text_input("🔍 Search by name or email", "")
                if search:
                    members_df = members_df[
                        members_df['name'].str.contains(search, case=False) | 
                        members_df['email'].str.contains(search, case=False)
                    ]
                
                st.dataframe(members_df, use_container_width=True, hide_index=True)
                st.metric("Total Members", len(members_df))
            else:
                st.info("No members found")
        
        with tab2:
            with st.form("add_member_form"):
                st.write("### Basic Information")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Full Name*")
                    email = st.text_input("Email*")
                    phone = st.text_input("Phone*")
                    gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
                with col2:
                    age = st.number_input("Age*", min_value=1, max_value=120, value=25)
                    blood_group = st.selectbox("Blood Group", ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
                    emergency_contact = st.text_input("Emergency Contact")
                
                st.write("### Additional Information")
                address = st.text_area("Address")
                medical_conditions = st.text_area("Medical Conditions/Allergies")
                
                st.divider()
                st.write("### Create User Account (Optional)")
                create_account = st.checkbox("Create login account for member")
                username = password = None
                if create_account:
                    col1, col2 = st.columns(2)
                    username = col1.text_input("Username*")
                    password = col2.text_input("Password*", type="password")
                
                submitted = st.form_submit_button("➕ Add Member", type="primary")
                
                if submitted:
                    if name and email and phone:
                        success, message, member_id = add_member(name, email, phone, address, gender, age, 
                                                                 emergency_contact, blood_group, medical_conditions)
                        if success:
                            st.success(message)
                            if create_account and username and password:
                                acc_success, acc_message = register_user(username, password, member_id)
                                if acc_success:
                                    st.success(f"✅ User account created! Username: {username}")
                                else:
                                    st.warning(acc_message)
                            st.balloons()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill all required fields!")
        
        with tab3:
            members_df = get_all_members()
            if not members_df.empty:
                member_id = st.selectbox("Select Member to Update", 
                                        options=members_df['id'].tolist(),
                                        format_func=lambda x: f"{x} - {members_df[members_df['id']==x]['name'].values[0]}")
                
                member = members_df[members_df['id'] == member_id].iloc[0]
                
                with st.form("update_member_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Name", value=member['name'])
                        email = st.text_input("Email", value=member['email'])
                        phone = st.text_input("Phone", value=member['phone'])
                        gender = st.selectbox("Gender", ["Male", "Female", "Other"], 
                                            index=["Male", "Female", "Other"].index(member['gender']))
                        status = st.selectbox("Status", ["Active", "Inactive"], 
                                            index=["Active", "Inactive"].index(member['status']))
                    with col2:
                        age = st.number_input("Age", value=int(member['age']))
                        emergency_contact = st.text_input("Emergency Contact", value=member['emergency_contact'] or "")
                        blood_group = st.text_input("Blood Group", value=member['blood_group'] or "")
                    
                    address = st.text_area("Address", value=member['address'] or "")
                    medical_conditions = st.text_area("Medical Conditions", value=member['medical_conditions'] or "")
                    
                    update_btn = st.form_submit_button("✏️ Update Member", type="primary")
                    
                    if update_btn:
                        update_member(member_id, name, email, phone, address, gender, age, 
                                    emergency_contact, blood_group, medical_conditions, status)
                        st.success("Member updated successfully!")
                        st.rerun()
            else:
                st.warning("No members to update")
        
        with tab4:
            members_df = get_all_members()
            if not members_df.empty:
                member_to_delete = st.selectbox(
                    "Select Member to Delete",
                    options=members_df['id'].tolist(),
                    format_func=lambda x: f"{x} - {members_df[members_df['id']==x]['name'].values[0]} ({members_df[members_df['id']==x]['email'].values[0]})"
                )
                
                selected_member = members_df[members_df['id'] == member_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete: **{selected_member['name']}**")
                st.write(f"Email: {selected_member['email']} | Phone: {selected_member['phone']}")
                st.write(f"Join Date: {selected_member['join_date']} | Status: {selected_member['status']}")
                
                confirm = st.checkbox("I confirm I want to delete this member")
                
                if st.button("🗑️ Delete Member", type="secondary", disabled=not confirm):
                    success, message = delete_member(member_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No members available to delete")
    
    elif menu == "Membership Plans":
        st.subheader("📋 Membership Plans")
        
        tab1, tab2, tab3 = st.tabs(["View Plans", "Add Plan", "Delete Plan"])
        
        with tab1:
            plans_df = get_all_plans()
            if not plans_df.empty:
                for _, plan in plans_df.iterrows():
                    with st.expander(f"💳 {plan['plan_name']} - ₹{plan['price']} ({plan['duration_months']} months)"):
                        col1, col2 = st.columns(2)
                        col1.write(f"**Description:** {plan['description']}")
                        col2.write(f"**Features:** {plan['features']}")
            else:
                st.info("No plans found")
        
        with tab2:
            with st.form("add_plan_form"):
                plan_name = st.text_input("Plan Name*", placeholder="e.g., Premium Plan")
                col1, col2 = st.columns(2)
                duration = col1.number_input("Duration (months)*", min_value=1, max_value=24, value=1)
                price = col2.number_input("Price (₹)*", min_value=0.0, value=1000.0)
                features = st.text_area("Features (comma separated)", placeholder="Gym access, Personal trainer, Diet plan")
                description = st.text_area("Description", placeholder="Detailed plan description")
                
                if st.form_submit_button("➕ Add Plan", type="primary"):
                    if plan_name and duration and price:
                        add_plan(plan_name, duration, price, features, description)
                        st.success("Plan added successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill all required fields!")
        
        with tab3:
            plans_df = get_all_plans()
            if not plans_df.empty:
                plan_to_delete = st.selectbox(
                    "Select Plan to Delete",
                    options=plans_df['id'].tolist(),
                    format_func=lambda x: f"{plans_df[plans_df['id']==x]['plan_name'].values[0]} - ₹{plans_df[plans_df['id']==x]['price'].values[0]}"
                )
                
                selected_plan = plans_df[plans_df['id'] == plan_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete: **{selected_plan['plan_name']}**")
                st.write(f"Price: ₹{selected_plan['price']} | Duration: {selected_plan['duration_months']} months")
                st.write(f"Features: {selected_plan['features']}")
                
                confirm = st.checkbox("I confirm I want to delete this plan")
                
                if st.button("🗑️ Delete Plan", type="secondary", disabled=not confirm):
                    success, message = delete_plan(plan_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No plans available to delete")
    
    elif menu == "Subscriptions":
        st.subheader("💳 Subscription Management")
        
        tab1, tab2, tab3 = st.tabs(["View Subscriptions", "New Subscription", "Cancel Subscription"])
        
        with tab1:
            subs_df = get_all_subscriptions()
            if not subs_df.empty:
                col1, col2 = st.columns(2)
                status_filter = col1.selectbox("Filter by Status", ["All", "Active", "Inactive", "Cancelled"])
                
                if status_filter != "All":
                    subs_df = subs_df[subs_df['status'] == status_filter]
                
                st.dataframe(subs_df, use_container_width=True, hide_index=True)
                st.metric("Total Subscriptions", len(subs_df))
            else:
                st.info("No subscriptions found")
        
        with tab2:
            members_df = get_all_members()
            plans_df = get_all_plans()
            
            if not members_df.empty and not plans_df.empty:
                with st.form("add_subscription_form"):
                    member_id = st.selectbox("Select Member*", 
                                            options=members_df['id'].tolist(),
                                            format_func=lambda x: f"{x} - {members_df[members_df['id']==x]['name'].values[0]} ({members_df[members_df['id']==x]['email'].values[0]})")
                    
                    plan_id = st.selectbox("Select Plan*",
                                          options=plans_df['id'].tolist(),
                                          format_func=lambda x: f"{plans_df[plans_df['id']==x]['plan_name'].values[0]} - ₹{plans_df[plans_df['id']==x]['price'].values[0]} ({plans_df[plans_df['id']==x]['duration_months'].values[0]} months)")
                    
                    col1, col2 = st.columns(2)
                    start_date = col1.date_input("Start Date*", value=datetime.now())
                    payment_method = col2.selectbox("Payment Method*", ["Cash", "Card", "UPI", "Net Banking", "Cheque"])
                    
                    if st.form_submit_button("✅ Create Subscription", type="primary"):
                        success, message = add_subscription(member_id, plan_id, start_date, payment_method)
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
            else:
                st.warning("⚠️ Please add members and plans first!")
        
        with tab3:
            subs_df = get_all_subscriptions()
            active_subs = subs_df[subs_df['status'] == 'Active']
            
            if not active_subs.empty:
                sub_to_cancel = st.selectbox(
                    "Select Subscription to Cancel",
                    options=active_subs['id'].tolist(),
                    format_func=lambda x: f"ID: {x} - {active_subs[active_subs['id']==x]['name'].values[0]} ({active_subs[active_subs['id']==x]['plan_name'].values[0]})"
                )
                
                selected_sub = active_subs[active_subs['id'] == sub_to_cancel].iloc[0]
                
                st.warning(f"⚠️ Cancel subscription for: **{selected_sub['name']}**")
                st.write(f"Plan: {selected_sub['plan_name']} | End Date: {selected_sub['end_date']}")
                
                confirm = st.checkbox("I confirm I want to cancel this subscription")
                
                if st.button("🚫 Cancel Subscription", type="secondary", disabled=not confirm):
                    success, message = cancel_subscription(sub_to_cancel)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No active subscriptions to cancel")
    
    elif menu == "Attendance":
        st.subheader("✅ Attendance Management")
        
        tab1, tab2, tab3 = st.tabs(["Today's Attendance", "Mark Attendance", "Delete Attendance"])
        
        with tab1:
            attendance_df = get_today_attendance()
            if not attendance_df.empty:
                st.dataframe(attendance_df, use_container_width=True, hide_index=True)
                
                st.divider()
                st.subheader("Mark Checkout")
                member_id = st.number_input("Member ID for Checkout", min_value=1, step=1)
                if st.button("🚪 Mark Checkout", type="primary"):
                    success, message = checkout_attendance(member_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No attendance records for today")
        
        with tab2:
            members_df = get_all_members()
            if not members_df.empty:
                member_id = st.selectbox("Select Member",
                                        options=members_df['id'].tolist(),
                                        format_func=lambda x: f"{x} - {members_df[members_df['id']==x]['name'].values[0]}")
                
                workout_type = st.selectbox("Workout Type", ["Cardio", "Strength", "Yoga", "CrossFit", "Mixed", "Other"])
                
                if st.button("✅ Mark Check-In", type="primary", use_container_width=True):
                    success, message = mark_attendance(member_id, workout_type)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning("No members found!")
        
        with tab3:
            conn = sqlite3.connect('gym_management.db')
            query = """SELECT a.id, m.name, a.check_in, a.check_out, a.workout_type, a.duration_minutes
                       FROM attendance a
                       JOIN members m ON a.member_id = m.id
                       ORDER BY a.check_in DESC
                       LIMIT 50"""
            attendance_df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not attendance_df.empty:
                attendance_to_delete = st.selectbox(
                    "Select Attendance Record to Delete",
                    options=attendance_df['id'].tolist(),
                    format_func=lambda x: f"ID: {x} - {attendance_df[attendance_df['id']==x]['name'].values[0]} ({attendance_df[attendance_df['id']==x]['check_in'].values[0]})"
                )
                
                selected_attendance = attendance_df[attendance_df['id'] == attendance_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete attendance record for: **{selected_attendance['name']}**")
                st.write(f"Check-in: {selected_attendance['check_in']} | Workout: {selected_attendance['workout_type']}")
                
                confirm = st.checkbox("I confirm I want to delete this attendance record")
                
                if st.button("🗑️ Delete Attendance", type="secondary", disabled=not confirm):
                    success, message = delete_attendance(attendance_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No attendance records to delete")
    
    elif menu == "Trainers":
        st.subheader("🏃 Trainer Management")
        
        tab1, tab2, tab3 = st.tabs(["View Trainers", "Add Trainer", "Delete Trainer"])
        
        with tab1:
            trainers_df = get_all_trainers()
            if not trainers_df.empty:
                st.dataframe(trainers_df, use_container_width=True, hide_index=True)
                st.metric("Total Active Trainers", len(trainers_df))
            else:
                st.info("No trainers found")
        
        with tab2:
            with st.form("add_trainer_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Name*")
                    email = st.text_input("Email*")
                    phone = st.text_input("Phone*")
                    specialization = st.text_input("Specialization", placeholder="e.g., Yoga, CrossFit")
                with col2:
                    certifications = st.text_area("Certifications", placeholder="List certifications")
                    experience = st.number_input("Experience (years)", min_value=0, value=0)
                    hire_date = st.date_input("Hire Date*", value=datetime.now())
                    salary = st.number_input("Monthly Salary (₹)*", min_value=0.0, value=20000.0)
                
                if st.form_submit_button("➕ Add Trainer", type="primary"):
                    if name and email and phone:
                        success, message = add_trainer(name, email, phone, specialization, certifications, 
                                                      experience, hire_date, salary)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill all required fields!")
        
        with tab3:
            trainers_df = get_all_trainers()
            if not trainers_df.empty:
                trainer_to_delete = st.selectbox(
                    "Select Trainer to Delete",
                    options=trainers_df['id'].tolist(),
                    format_func=lambda x: f"{trainers_df[trainers_df['id']==x]['name'].values[0]} - {trainers_df[trainers_df['id']==x]['specialization'].values[0]}"
                )
                
                selected_trainer = trainers_df[trainers_df['id'] == trainer_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete: **{selected_trainer['name']}**")
                st.write(f"Email: {selected_trainer['email']} | Phone: {selected_trainer['phone']}")
                st.write(f"Specialization: {selected_trainer['specialization']} | Experience: {selected_trainer['experience_years']} years")
                
                confirm = st.checkbox("I confirm I want to delete this trainer")
                
                if st.button("🗑️ Delete Trainer", type="secondary", disabled=not confirm):
                    success, message = delete_trainer(trainer_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No trainers available to delete")
    
    elif menu == "Equipment":
        st.subheader("🏋️ Equipment Management")
        
        tab1, tab2, tab3 = st.tabs(["View Equipment", "Add Equipment", "Delete Equipment"])
        
        with tab1:
            equipment_df = get_all_equipment()
            if not equipment_df.empty:
                st.dataframe(equipment_df, use_container_width=True, hide_index=True)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Equipment", len(equipment_df))
                total_value = equipment_df['purchase_price'].sum()
                col2.metric("Total Investment", f"₹{total_value:.2f}")
            else:
                st.info("No equipment found")
        
        with tab2:
            with st.form("add_equipment_form"):
                col1, col2 = st.columns(2)
                name = col1.text_input("Equipment Name*")
                category = col1.selectbox("Category", ["Cardio", "Strength", "Free Weights", "Accessories", "Other"])
                purchase_date = col2.date_input("Purchase Date", value=datetime.now())
                price = col2.number_input("Purchase Price (₹)", min_value=0.0, value=0.0)
                condition = st.selectbox("Condition", ["Excellent", "Good", "Fair", "Needs Repair"])
                
                if st.form_submit_button("➕ Add Equipment", type="primary"):
                    if name:
                        add_equipment(name, category, purchase_date, price, condition)
                        st.success("Equipment added successfully!")
                        st.rerun()
                    else:
                        st.error("Please enter equipment name!")
        
        with tab3:
            equipment_df = get_all_equipment()
            if not equipment_df.empty:
                equip_to_delete = st.selectbox(
                    "Select Equipment to Delete",
                    options=equipment_df['id'].tolist(),
                    format_func=lambda x: f"{equipment_df[equipment_df['id']==x]['name'].values[0]} - {equipment_df[equipment_df['id']==x]['category'].values[0]}"
                )
                
                selected_equip = equipment_df[equipment_df['id'] == equip_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete: **{selected_equip['name']}**")
                st.write(f"Category: {selected_equip['category']} | Condition: {selected_equip['condition']}")
                st.write(f"Purchase Price: ₹{selected_equip['purchase_price']:.2f} | Purchase Date: {selected_equip['purchase_date']}")
                
                confirm = st.checkbox("I confirm I want to delete this equipment")
                
                if st.button("🗑️ Delete Equipment", type="secondary", disabled=not confirm):
                    success, message = delete_equipment(equip_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No equipment available to delete")
    
    elif menu == "Payments":
        st.subheader("💰 Payment Records")
        
        tab1, tab2 = st.tabs(["View Payments", "Delete Payment"])
        
        with tab1:
            payments_df = get_all_payments()
            if not payments_df.empty:
                col1, col2 = st.columns(2)
                start_date = col1.date_input("From Date", value=datetime.now() - timedelta(days=30))
                end_date = col2.date_input("To Date", value=datetime.now())
                
                payments_df['payment_date'] = pd.to_datetime(payments_df['payment_date'])
                filtered_df = payments_df[
                    (payments_df['payment_date'].dt.date >= start_date) & 
                    (payments_df['payment_date'].dt.date <= end_date)
                ]
                
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                
                col1, col2, col3 = st.columns(3)
                total_revenue = filtered_df['amount'].sum()
                col1.metric("Total Revenue", f"₹{total_revenue:.2f}")
                col2.metric("Total Transactions", len(filtered_df))
                avg_payment = filtered_df['amount'].mean()
                col3.metric("Average Payment", f"₹{avg_payment:.2f}")
            else:
                st.info("No payment records found")
        
        with tab2:
            payments_df = get_all_payments()
            if not payments_df.empty:
                payment_to_delete = st.selectbox(
                    "Select Payment to Delete",
                    options=payments_df['id'].tolist(),
                    format_func=lambda x: f"ID: {x} - {payments_df[payments_df['id']==x]['name'].values[0]} - ₹{payments_df[payments_df['id']==x]['amount'].values[0]} ({payments_df[payments_df['id']==x]['payment_date'].values[0]})"
                )
                
                selected_payment = payments_df[payments_df['id'] == payment_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete payment record:")
                st.write(f"Member: **{selected_payment['name']}**")
                st.write(f"Amount: ₹{selected_payment['amount']:.2f} | Date: {selected_payment['payment_date']}")
                st.write(f"Method: {selected_payment['payment_method']} | Status: {selected_payment['status']}")
                
                confirm = st.checkbox("I confirm I want to delete this payment record")
                
                if st.button("🗑️ Delete Payment", type="secondary", disabled=not confirm):
                    success, message = delete_payment(payment_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No payments available to delete")
    
    elif menu == "Announcements":
        st.subheader("📢 Announcements")
        
        tab1, tab2, tab3 = st.tabs(["View Announcements", "Create Announcement", "Delete Announcement"])
        
        with tab1:
            conn = sqlite3.connect('gym_management.db')
            query = "SELECT * FROM announcements ORDER BY created_at DESC"
            announcements_df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not announcements_df.empty:
                st.dataframe(announcements_df, use_container_width=True, hide_index=True)
            else:
                st.info("No announcements")
        
        with tab2:
            with st.form("add_announcement_form"):
                title = st.text_input("Title*", placeholder="Announcement title")
                message = st.text_area("Message*", height=150, placeholder="Announcement details")
                
                if st.form_submit_button("📢 Create Announcement", type="primary"):
                    if title and message:
                        add_announcement(title, message, st.session_state.user_id)
                        st.success("Announcement created!")
                        st.rerun()
                    else:
                        st.error("Please fill all fields!")
        
        with tab3:
            conn = sqlite3.connect('gym_management.db')
            query = "SELECT * FROM announcements ORDER BY created_at DESC"
            announcements_df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not announcements_df.empty:
                ann_to_delete = st.selectbox(
                    "Select Announcement to Delete",
                    options=announcements_df['id'].tolist(),
                    format_func=lambda x: f"{announcements_df[announcements_df['id']==x]['title'].values[0]} ({announcements_df[announcements_df['id']==x]['created_at'].values[0][:10]})"
                )
                
                selected_ann = announcements_df[announcements_df['id'] == ann_to_delete].iloc[0]
                
                st.warning(f"⚠️ You are about to delete: **{selected_ann['title']}**")
                st.write(f"Created: {selected_ann['created_at']}")
                with st.expander("View Message"):
                    st.write(selected_ann['message'])
                
                confirm = st.checkbox("I confirm I want to delete this announcement")
                
                if st.button("🗑️ Delete Announcement", type="secondary", disabled=not confirm):
                    success, message = delete_announcement(ann_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("No announcements to delete")
    
    elif menu == "Feedback":
        st.subheader("💬 Member Feedback")
        
        feedback_df = get_all_feedback()
        if not feedback_df.empty:
            st.dataframe(feedback_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            avg_rating = feedback_df['rating'].mean()
            col1.metric("Average Rating", f"{avg_rating:.1f}/5 ⭐")
            col2.metric("Total Feedback", len(feedback_df))
        else:
            st.info("No feedback received yet")
    
    elif menu == "Reports":
        st.subheader("📈 Reports & Analytics")
        
        report_type = st.selectbox("Select Report", [
            "Revenue Analysis", "Membership Growth", "Attendance Trends", 
            "Expiring Subscriptions"
        ])
        
        if report_type == "Revenue Analysis":
            conn = sqlite3.connect('gym_management.db')
            query = """SELECT strftime('%Y-%m', payment_date) as month, 
                              SUM(amount) as revenue, COUNT(*) as transactions
                       FROM payments
                       GROUP BY month
                       ORDER BY month DESC
                       LIMIT 12"""
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                st.bar_chart(df.set_index('month')['revenue'])
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        elif report_type == "Membership Growth":
            conn = sqlite3.connect('gym_management.db')
            query = """SELECT strftime('%Y-%m', join_date) as month, 
                              COUNT(*) as new_members
                       FROM members
                       GROUP BY month
                       ORDER BY month DESC
                       LIMIT 12"""
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                st.line_chart(df.set_index('month'))
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        elif report_type == "Attendance Trends":
            conn = sqlite3.connect('gym_management.db')
            query = """SELECT DATE(check_in) as date, COUNT(*) as attendance
                       FROM attendance
                       WHERE DATE(check_in) >= DATE('now', '-30 days')
                       GROUP BY date
                       ORDER BY date"""
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                st.area_chart(df.set_index('date'))
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        elif report_type == "Expiring Subscriptions":
            conn = sqlite3.connect('gym_management.db')
            query = """SELECT m.id, m.name, m.email, m.phone, s.end_date, p.plan_name
                       FROM subscriptions s
                       JOIN members m ON s.member_id = m.id
                       JOIN plans p ON s.plan_id = p.id
                       WHERE s.status = 'Active' 
                       AND s.end_date BETWEEN DATE('now') AND DATE('now', '+30 days')
                       ORDER BY s.end_date"""
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                st.warning(f"⚠️ {len(df)} subscriptions expiring in next 30 days!")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.success("✅ No subscriptions expiring soon")

def main():
    st.set_page_config(page_title="Admin Panel - Gym Management", page_icon="🏋️", layout="wide")
    
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🏋️ Admin Panel Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("🔐 Administrator Access")
            
            username = st.text_input("Username", placeholder="Enter admin username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            
            if st.button("Login", type="primary", use_container_width=True):
                user = authenticate(username, password)
                if user and user[2] == "admin":
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or not an admin account!")
            
            st.info("**Default:** Username: `admin` | Password: `admin123`")
        
        return
    
    st.sidebar.title(f"Welcome, {st.session_state.username}! 👋")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    admin_panel()

if __name__ == "__main__":
    main()