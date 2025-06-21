import streamlit as st
import pandas as pd
import datetime
import hashlib
import re
from supabase import create_client, Client

# Streamlit app
st.set_page_config(layout="wide", page_title="رفيقي")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    return create_client(st.secrets.supabase.url, st.secrets.supabase.key)


supabase: Client = init_supabase()

# Hash passwords
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Generate YYMMDDXX user IDs
def generate_user_id():
    now = datetime.datetime.now()
    date_part = now.strftime('%y%m%d')  # YYMMDD
    
    # Find the highest sequence number for today in Supabase
    res = supabase.table('users') \
        .select('id') \
        .ilike('id', f'{date_part}%') \
        .order('id', desc=True) \
        .limit(1) \
        .execute()
    
    if res.data:
        last_seq = int(res.data[0]['id'][-2:])
        new_seq = last_seq + 1
        if new_seq > 99:
            raise ValueError("Daily user limit exceeded (max 100 per day)")
    else:
        new_seq = 0  # Start with 00
    
    return f"{date_part}{new_seq:02d}"  # YYMMDDXX

# Username validation
def is_valid_username(username):
    pattern = r'^[a-z][a-z0-9]*$'
    return re.fullmatch(pattern, username) is not None

# User registration
def create_user(username, firstname, lastname, password, email):
    try:
        if not is_valid_username(username):
            st.error("اسم المستخدم غير صالح. يجب أن يبدأ بحرف صغير ويحتوي فقط على أحرف وأرقام (بدون مسافات).")
            return None
            
        user_id = generate_user_id()
        res = supabase.table('users').insert({
            'id': user_id,
            'username': username,
            'firstname': firstname,
            'lastname': lastname,
            'password': make_hashes(password),
            'email': email,
            'created_at': datetime.datetime.now().isoformat()
        }).execute()
        
        if res.data:
            return user_id
        return None
    except Exception as e:
        st.error(f"Error creating user: {str(e)}")
        return None

# User login
def login_user(username, password):
    res = supabase.table('users') \
        .select('*') \
        .eq('username', username) \
        .limit(1) \
        .execute()
    
    if res.data and check_hashes(password, res.data[0]['password']):
        return res.data[0]['id']
    return None

# Prayer tracking functions
def insert_record(user_id, data):
    record = {
        'user_id': user_id,
        'date': datetime.date.today().isoformat(),
        'fajr': data['fajr'],
        'duha': data['duha'],
        'morning_adhkar': data['morning_adhkar'],
        'dhuhr': data['dhuhr'],
        'asr': data['asr'],
        'evening_adhkar': data['evening_adhkar'],
        'maghrib': data['maghrib'],
        'isha': data['isha'],
        'shaf_watr': data['shaf_watr'],
        'quran_recitation': data['quran_recitation'],
        'quran_memorization': data['quran_memorization'],
        'quran_review': data['quran_review']
    }
    supabase.table('tracker').insert(record).execute()

def get_records(user_id):
    res = supabase.table('tracker') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('date', desc=True) \
        .execute()
    return pd.DataFrame(res.data)

# Arabic-English mapping and value sets
questions = {
    "الفجر": {"en": "fajr", "type": "salah"},
    "الضحى": {"en": "duha", "type": "duha"},
    "اذكار الصباح": {"en": "morning_adhkar", "type": "yes_no"},
    "الظهر": {"en": "dhuhr", "type": "salah"},
    "العصر": {"en": "asr", "type": "salah"},
    "اذكار المساء": {"en": "evening_adhkar", "type": "yes_no"},
    "المغرب": {"en": "maghrib", "type": "salah"},
    "العشاء": {"en": "isha", "type": "salah"},
    "الشفع والوتر": {"en": "shaf_watr", "type": "watr"},
    "تلاوة القرآن": {"en": "quran_recitation", "type": "yes_no"},
    "حفظ القرآن": {"en": "quran_memorization", "type": "yes_no"},
    "مراجعة القرآن": {"en": "quran_review", "type": "yes_no"}
}

salah_options = {
    1: "🕌 المسجد/جماعة",
    2: "🧎 فرد",
    3: "⏳ صلاة فائتة",
    4: "❌ لم أصلي"
}

yes_no_options = {
    1: "✔️ نعم",
    2: "❌ لا"
}

# # Streamlit app
# st.set_page_config(layout="wide", page_title="رفيقي")

# Authentication state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'register' not in st.session_state:
    st.session_state.register = False

# Authentication UI
if not st.session_state.user_id:
    if st.session_state.register:
        # Registration form
        st.markdown("<h1 style='text-align: center; color: #2E86C1;'>تسجيل مستخدم جديد</h1>", unsafe_allow_html=True)
        
        with st.form("register_form"):
            username = st.text_input("اسم المستخدم (يبدأ بحرف صغير، أرقام فقط)")
            email = st.text_input("البريد الإلكتروني")
            firstname = st.text_input("الاسم الاول")
            lastname = st.text_input("الاسم الاخير")
            password = st.text_input("كلمة المرور", type="password")
            confirm_password = st.text_input("تأكيد كلمة المرور", type="password")
            
            submitted = st.form_submit_button("تسجيل")
            
            if submitted:
                if password == confirm_password:
                    user_id = create_user(username, firstname, lastname, password, email)
                    if user_id:
                        st.success(f"تم التسجيل بنجاح! رقم عضويتك: {user_id}")
                        st.session_state.register = False
                else:
                    st.error("كلمات المرور غير متطابقة")
        
        if st.button("العودة لتسجيل الدخول"):
            st.session_state.register = False
    else:
        # Login form
        st.markdown("<h1 style='text-align: center; color: #2E86C1;'>تسجيل الدخول</h1>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            
            submitted = st.form_submit_button("دخول")
            
            if submitted:
                user_id = login_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
        
        if st.button("تسجيل مستخدم جديد"):
            st.session_state.register = True
else:
    # Main application
    st.markdown(f"<h1 style='text-align: center; color: #2E86C1;'>مرحباً {st.session_state.username}</h1>", unsafe_allow_html=True)
    
    # Logout button
    if st.button("تسجيل الخروج"):
        st.session_state.user_id = None
        st.rerun()
    
    # Prayer tracking form
    with st.form("daily_tracker"):
        responses = {}
        cols = st.columns(3)
        
        for i, (question_ar, question_data) in enumerate(questions.items()):
            with cols[i % 3]:
                q_type = question_data["type"]
                q_en = question_data["en"]
                
                if q_type == "salah":
                    responses[q_en] = st.radio(
                        question_ar,
                        options=salah_options.keys(),
                        format_func=lambda x: salah_options[x],
                        key=f"{q_en}_radio"
                    )
                    
                elif q_type == "duha":
                    responses[q_en] = st.slider(
                        f"{question_ar} (ركعات)",
                        min_value=0,
                        max_value=8,
                        value=0,
                        key=f"{q_en}_slider"
                    )
                    
                elif q_type == "watr":
                    responses[q_en] = st.slider(
                        f"{question_ar} (ركعات)",
                        min_value=0,
                        max_value=3,
                        value=0,
                        key=f"{q_en}_slider"
                    )
                    
                elif q_type == "yes_no":
                    responses[q_en] = st.radio(
                        question_ar,
                        options=yes_no_options.keys(),
                        format_func=lambda x: yes_no_options[x],
                        key=f"{q_en}_radio"
                    )
        
        submitted = st.form_submit_button("حفظ البيانات")
        
        if submitted:
            # Convert radio selections to text values before saving
            for q_en, value in responses.items():
                if questions[[k for k,v in questions.items() if v["en"] == q_en][0]]["type"] == "salah":
                    responses[q_en] = salah_options[value]
                elif questions[[k for k,v in questions.items() if v["en"] == q_en][0]]["type"] == "yes_no":
                    responses[q_en] = yes_no_options[value]
            
            insert_record(st.session_state.user_id, responses)
            st.success("تم حفظ البيانات بنجاح!")
    
    # Dashboard
    st.markdown("---")
    st.header("لوحة المتابعة")
    
    # Get user records
    df = get_records(st.session_state.user_id)
    
    if not df.empty:
        # Convert to proper datetime and sort
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False)
        
        # Date selector for viewing specific dates
        selected_date = st.selectbox(
            "اختر تاريخاً",
            df['date'].dt.date.unique(),
            index=0
        )
        
        # Display selected entry
        st.subheader("بيانات التاريخ المحدد")
        selected_data = df[df['date'].dt.date == selected_date].iloc[0]
        
        cols = st.columns(4)
        for i, (question_ar, question_data) in enumerate(questions.items()):
            with cols[i % 4]:
                q_en = question_data["en"]
                value = selected_data[q_en]
                if question_data["type"] in ["duha", "watr"]:
                    st.metric(question_ar, f"{value} ركعات")
                else:
                    st.metric(question_ar, value)
        
        # Display history chart
        st.subheader("التاريخ")
        
        # Convert to numeric for charting
        chart_df = df.copy()
        for col in chart_df.columns:
            if col not in ['id', 'user_id', 'date']:
                if col in ['duha', 'shaf_watr']:
                    # Keep numeric values for rakaat counts
                    chart_df[col] = chart_df[col].astype(float)
                else:
                    # Convert yes/no and salah to binary
                    chart_df[col] = chart_df[col].apply(
                        lambda x: 1 if 'نعم' in str(x) or 'المسجد' in str(x) else 0
                    )
        
        # Melt for better plotting
        melted_df = chart_df.melt(
            id_vars=['date'], 
            value_vars=[q['en'] for q in questions.values()],
            var_name='activity', 
            value_name='value'
        )
        
        # Show chart
        st.line_chart(melted_df, x='date', y='value', color='activity')
        
        # Show raw data
        st.subheader("البيانات الخام")
        st.dataframe(df.drop(columns=['id', 'user_id']))
    else:
        st.info("لا توجد بيانات مسجلة بعد.")
