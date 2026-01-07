import sqlite3
import hashlib

def init_db():
    conn = sqlite3.connect('gym_management.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL,
                  member_id INTEGER,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (member_id) REFERENCES members(id))''')
    
    # Members table
    c.execute('''CREATE TABLE IF NOT EXISTS members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  phone TEXT NOT NULL,
                  address TEXT,
                  gender TEXT,
                  age INTEGER,
                  emergency_contact TEXT,
                  blood_group TEXT,
                  medical_conditions TEXT,
                  join_date DATE NOT NULL,
                  profile_photo BLOB,
                  status TEXT DEFAULT 'Active')''')
    
    # Membership plans table
    c.execute('''CREATE TABLE IF NOT EXISTS plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  plan_name TEXT NOT NULL,
                  duration_months INTEGER NOT NULL,
                  price REAL NOT NULL,
                  features TEXT,
                  description TEXT,
                  is_active INTEGER DEFAULT 1)''')
    
    # Check if features column exists, if not add it (for existing databases)
    c.execute("PRAGMA table_info(plans)")
    columns = [column[1] for column in c.fetchall()]
    if 'features' not in columns:
        c.execute("ALTER TABLE plans ADD COLUMN features TEXT")
    if 'is_active' not in columns:
        c.execute("ALTER TABLE plans ADD COLUMN is_active INTEGER DEFAULT 1")
    
    # Member subscriptions table
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id INTEGER NOT NULL,
                  plan_id INTEGER NOT NULL,
                  start_date DATE NOT NULL,
                  end_date DATE NOT NULL,
                  status TEXT DEFAULT 'Active',
                  auto_renew INTEGER DEFAULT 0,
                  FOREIGN KEY (member_id) REFERENCES members(id),
                  FOREIGN KEY (plan_id) REFERENCES plans(id))''')
    
    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id INTEGER NOT NULL,
                  subscription_id INTEGER,
                  amount REAL NOT NULL,
                  payment_date DATE NOT NULL,
                  payment_method TEXT NOT NULL,
                  transaction_id TEXT,
                  status TEXT DEFAULT 'Completed',
                  notes TEXT,
                  FOREIGN KEY (member_id) REFERENCES members(id),
                  FOREIGN KEY (subscription_id) REFERENCES subscriptions(id))''')
    
    # Attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id INTEGER NOT NULL,
                  check_in DATETIME NOT NULL,
                  check_out DATETIME,
                  workout_type TEXT,
                  duration_minutes INTEGER,
                  FOREIGN KEY (member_id) REFERENCES members(id))''')
    
    # Trainers table
    c.execute('''CREATE TABLE IF NOT EXISTS trainers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  phone TEXT NOT NULL,
                  specialization TEXT,
                  certifications TEXT,
                  experience_years INTEGER,
                  hire_date DATE NOT NULL,
                  salary REAL,
                  status TEXT DEFAULT 'Active')''')
    
    # Training sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS training_sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id INTEGER NOT NULL,
                  trainer_id INTEGER NOT NULL,
                  session_date DATETIME NOT NULL,
                  duration_minutes INTEGER,
                  session_type TEXT,
                  notes TEXT,
                  status TEXT DEFAULT 'Scheduled',
                  FOREIGN KEY (member_id) REFERENCES members(id),
                  FOREIGN KEY (trainer_id) REFERENCES trainers(id))''')
    
    # Equipment table
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  category TEXT,
                  purchase_date DATE,
                  purchase_price REAL,
                  condition TEXT DEFAULT 'Good',
                  maintenance_date DATE,
                  notes TEXT)''')
    
    # Announcements table
    c.execute('''CREATE TABLE IF NOT EXISTS announcements
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_by INTEGER,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  is_active INTEGER DEFAULT 1,
                  FOREIGN KEY (created_by) REFERENCES users(id))''')
    
    # Feedback table
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id INTEGER NOT NULL,
                  rating INTEGER,
                  message TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  response TEXT,
                  FOREIGN KEY (member_id) REFERENCES members(id))''')
    
    # Workout plans table
    c.execute('''CREATE TABLE IF NOT EXISTS workout_plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id INTEGER NOT NULL,
                  trainer_id INTEGER,
                  plan_name TEXT NOT NULL,
                  description TEXT,
                  exercises TEXT,
                  created_date DATE NOT NULL,
                  is_active INTEGER DEFAULT 1,
                  FOREIGN KEY (member_id) REFERENCES members(id),
                  FOREIGN KEY (trainer_id) REFERENCES trainers(id))''')
    
    # Create default admin if not exists
    try:
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", hashed_pw, "admin"))
    except sqlite3.IntegrityError:
        pass
    
    # Add sample plans if empty
    c.execute("SELECT COUNT(*) FROM plans")
    if c.fetchone()[0] == 0:
        sample_plans = [
            ("Basic Plan", 1, 1500.0, "Access to gym, Locker facility", "Perfect for beginners", 1),
            ("Premium Plan", 3, 4000.0, "Access to gym, Personal trainer, Diet plan, Locker", "Best value for money", 1),
            ("Elite Plan", 6, 7500.0, "All Premium features, Spa access, Supplement guidance", "Complete fitness solution", 1),
            ("Annual Plan", 12, 12000.0, "All Elite features, Free merchandise, Priority booking", "Save more with annual plan", 1)
        ]
        c.executemany("INSERT INTO plans (plan_name, duration_months, price, features, description, is_active) VALUES (?, ?, ?, ?, ?, ?)", sample_plans)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_db()