import streamlit as st
import ollama
import sqlite3
import hashlib
import json

# --- Database Setup and User Management ---
def init_db():
    """
    Initializes the SQLite database and creates user, chat history, and health data tables.
    The user_health_data table stores health information for each user.
    """
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Create chat_history table with a foreign key to users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # New table for user health data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_health_data (
            user_id INTEGER PRIMARY KEY,
            data_json TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Registers a new user and initializes their health data."""
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    try:
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        user_id = cursor.lastrowid
        # Initialize an empty health data entry for the new user
        cursor.execute("INSERT INTO user_health_data (user_id, data_json) VALUES (?, ?)", (user_id, json.dumps({})))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("ชื่อผู้ใช้งานนี้มีอยู่แล้ว โปรดเลือกชื่ออื่น")
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticates a user."""
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return user[0]
    return None

def save_message(user_id, role, content):
    """Saves a message to the database for a specific user."""
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def load_messages(user_id):
    """Loads all messages for a specific user from the database."""
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id", (user_id,))
    messages = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
    conn.close()
    return messages

def save_health_data(user_id, health_data):
    """Saves user's health data to the database."""
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    data_json = json.dumps(health_data, ensure_ascii=False)
    cursor.execute("REPLACE INTO user_health_data (user_id, data_json) VALUES (?, ?)", (user_id, data_json))
    conn.commit()
    conn.close()

def load_health_data(user_id):
    """Loads user's health data from the database."""
    conn = sqlite3.connect('personal_health_ai.db')
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM user_health_data WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return json.loads(result[0])
    return {}

# --- Streamlit App UI Pages ---
def login_register_page():
    """Displays the login/register UI."""
    st.title("ยินดีต้อนรับสู่ AI สุขภาพส่วนตัว! 🩺")
    st.markdown("กรุณาเข้าสู่ระบบหรือลงทะเบียนเพื่อเริ่มต้นใช้งาน")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("เข้าสู่ระบบ")
        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้")
            password = st.text_input("รหัสผ่าน", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ")
            if submitted:
                user_id = authenticate_user(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.messages = load_messages(user_id)
                    st.session_state.health_data = load_health_data(user_id)
                    st.session_state.show_health_form = not bool(st.session_state.health_data)
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    with col2:
        st.subheader("ลงทะเบียน")
        with st.form("register_form"):
            new_username = st.text_input("ชื่อผู้ใช้ใหม่")
            new_password = st.text_input("รหัสผ่านใหม่", type="password")
            submitted = st.form_submit_button("ลงทะเบียน")
            if submitted:
                if new_username and new_password:
                    if register_user(new_username, new_password):
                        st.success("ลงทะเบียนสำเร็จ! โปรดเข้าสู่ระบบ")
                else:
                    st.error("กรุณาเลือกชื่อผู้ใช้และรหัสผ่าน")


def health_data_form_page():
    """Page to collect initial health data or allow updating."""
    st.title("กรอกข้อมูลสุขภาพของคุณ")
    st.markdown("เพื่อให้ AI สามารถให้คำแนะนำที่เหมาะสมยิ่งขึ้น กรุณากรอกข้อมูลด้านล่าง")

    current_data = st.session_state.health_data

    with st.form("health_form"):
        # Personal Information
        st.subheader("ข้อมูลส่วนตัว")
        col1, col2, col3 = st.columns(3)
        with col1:
            gender = st.selectbox(
                "เพศ:",
                ["เลือก", "ชาย", "หญิง", "อื่นๆ"],
                index=["เลือก", "ชาย", "หญิง", "อื่นๆ"].index(current_data.get("เพศ", "เลือก"))
            )
        with col2:
            age = st.number_input("อายุ:", min_value=1, max_value=120, value=current_data.get("อายุ", 25))
        with col3:
            height = st.number_input("ส่วนสูง (ซม.):", min_value=100, max_value=250, value=current_data.get("ส่วนสูง", 170))
            weight = st.number_input("น้ำหนัก (กก.):", min_value=30, max_value=300, value=current_data.get("น้ำหนัก", 65))

        # Lifestyle Information
        st.subheader("ข้อมูลไลฟ์สไตล์")
        col4, col5 = st.columns(2)
        with col4:
            activity_level = st.selectbox(
                "ระดับกิจกรรมในแต่ละวัน:",
                ["เลือก", "น้อยมาก (นั่งทำงาน)", "น้อย (เดินเล็กน้อย)", "ปานกลาง (ออกกำลังกาย 3-5 ครั้ง/สัปดาห์)", "มาก (ออกกำลังกายทุกวัน)"],
                index=["เลือก", "น้อยมาก (นั่งทำงาน)", "น้อย (เดินเล็กน้อย)", "ปานกลาง (ออกกำลังกาย 3-5 ครั้ง/สัปดาห์)", "มาก (ออกกำลังกายทุกวัน)"].index(current_data.get("ระดับกิจกรรม", "เลือก"))
            )
        with col5:
            dietary_preference = st.multiselect(
                "ข้อจำกัดหรือรูปแบบการทานอาหาร:",
                ["ทั่วไป", "มังสวิรัติ", "วีแกน", "คีโต", "อาหารคลีน", "แพ้อาหารทะเล", "แพ้นม", "อื่นๆ"],
                default=current_data.get("รูปแบบการทานอาหาร", [])
            )
        
        st.subheader("ประวัติทางการแพทย์ (ถ้ามี)")
        med_conditions = st.multiselect(
            "โรคประจำตัว:",
            ["ไม่มี", "โรคเบาหวาน", "ความดันโลหิตสูง", "โรคหัวใจ", "โรคไต", "โรคไขมันในเลือดสูง", "ภูมิแพ้", "อื่นๆ"],
            default=current_data.get("โรคประจำตัว", [])
        )
        medications = st.text_area(
            "ยาที่ใช้ประจำ:",
            value=current_data.get("ยาที่ใช้ประจำ", ""),
            placeholder="เช่น ยาความดัน, ยาลดน้ำตาลในเลือด"
        )
        allergies = st.text_area(
            "อาการแพ้ (อาหาร/ยา):",
            value=current_data.get("อาการแพ้", ""),
            placeholder="เช่น แพ้กุ้ง, แพ้ยาเพนิซิลลิน"
        )
        
        submitted = st.form_submit_button("บันทึกและไปที่หน้าแชท")
        
    if submitted:
        if "เลือก" in [gender, activity_level]:
            st.warning("กรุณาเลือก เพศ และ ระดับกิจกรรม")
        else:
            health_data = {
                "เพศ": gender,
                "อายุ": age,
                "ส่วนสูง": height,
                "น้ำหนัก": weight,
                "ระดับกิจกรรม": activity_level,
                "รูปแบบการทานอาหาร": dietary_preference,
                "โรคประจำตัว": med_conditions,
                "ยาที่ใช้ประจำ": medications,
                "อาการแพ้": allergies
            }
            save_health_data(st.session_state.user_id, health_data)
            st.session_state.health_data = health_data
            st.session_state.show_health_form = False
            st.rerun()

def chat_page():
    """Displays the main chatbot UI."""
    st.header(f"สวัสดี, คุณ{st.session_state.username}! 🤖")
    
    # Initialize necessary session state variables
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    if "current_response" not in st.session_state:
        st.session_state.current_response = ""

    # --- Sidebar Menu for Health Profile ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("ข้อมูลสุขภาพของคุณ")
    if st.sidebar.button("แก้ไขข้อมูลสุขภาพ"):
        st.session_state.show_health_form = True
        st.rerun()
    
    if st.session_state.health_data:
        st.sidebar.json(st.session_state.health_data)
    else:
        st.sidebar.info("คุณยังไม่มีข้อมูลสุขภาพ กรุณากดปุ่มเพื่อกรอก")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("ออกจากระบบ"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Chat Display Area ---
    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Generation Logic ---
    if st.session_state.is_generating:
        # This block runs when a response is being generated
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            stop_button_pressed = st.button("หยุดคิด", key="stop_gen")
            
            try:
                OLLAMA_MODEL = "gpt-oss:20b"
                response_stream = ollama.chat(
                    model=OLLAMA_MODEL, 
                    messages=st.session_state.ollama_messages, 
                    stream=True
                )
                
                for chunk in response_stream:
                    if stop_button_pressed:
                        break
                    st.session_state.current_response += chunk['message']['content']
                    message_placeholder.markdown(st.session_state.current_response + "▌")
                
                message_placeholder.markdown(st.session_state.current_response)

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
                st.error(f"โปรดตรวจสอบว่าได้ติดตั้งโมเดล '{OLLAMA_MODEL}' และรัน Ollama เรียบร้อยแล้ว")
            
            # After generation (success or fail), save and reset state
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_response})
            save_message(st.session_state.user_id, "assistant", st.session_state.current_response)
            
            # Reset the generation state
            st.session_state.is_generating = False
            st.session_state.current_response = ""
            st.rerun()

    # --- User Input Logic ---
    # This block runs only when not generating a response
    if not st.session_state.is_generating:
        if prompt := st.chat_input("มีอะไรให้ฉันช่วยเรื่องสุขภาพได้บ้าง?"):
            # Prepare messages and start generation
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_message(st.session_state.user_id, "user", prompt)
            
            # Build ollama messages
            user_health_profile = st.session_state.health_data
            system_prompt = (
    "คุณคือ AI ผู้ช่วยด้านสุขภาพและโภชนาการส่วนตัวที่เป็นมิตร โดยเฉพาะโรคเบาหวาน"
    "คุณควรให้คำแนะนำตามข้อมูลสุขภาพของผู้ใช้ด้านล่าง:\n\n"
    f"{json.dumps(user_health_profile, ensure_ascii=False, indent=2)}\n\n"
    "โปรดใช้ข้อมูลนี้ประกอบการตอบทุกครั้ง "
    "หากผู้ใช้ถามเรื่องที่เกี่ยวกับสุขภาพ อาหาร การออกกำลังกาย "
    "ให้คำแนะนำที่เหมาะสมกับข้อมูลด้านบน"
)
            ollama_messages = [
                {"role": "system", "content": system_prompt}
            ]
            ollama_messages.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])
            
            # Save ollama messages to session state for the next rerun
            st.session_state.ollama_messages = ollama_messages
            
            # Set the flag to start generation
            st.session_state.is_generating = True
            st.rerun()
        
# --- Main App Logic ---
st.set_page_config(page_title="Personalized Health AI", layout="wide")
init_db()

# Initialize session state flags for navigation
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_health_form" not in st.session_state:
    st.session_state.show_health_form = False

# Logic to switch between pages
if st.session_state.logged_in:
    if st.session_state.show_health_form:
        health_data_form_page()
    else:
        chat_page()
else:
    login_register_page()
