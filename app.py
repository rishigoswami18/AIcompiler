import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from database import get_connection, init_db, seed_admin
from auth import authenticate, register_user, is_logged_in, current_user, logout, hash_password

st.set_page_config(page_title="CRM System", page_icon="💼", layout="wide")

# ── Custom CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%); }
[data-testid="stSidebar"] { background: rgba(15,12,41,0.95); border-right: 1px solid rgba(99,102,241,0.2); }
div[data-testid="stMetric"] { background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.2); border-radius: 12px; padding: 16px; }
div[data-testid="stMetric"] label { color: #a5b4fc !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #e0e7ff !important; font-weight: 700; }
.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; border-radius: 8px; padding: 8px 24px; font-weight: 600; transition: all 0.3s; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(99,102,241,0.4); }
h1, h2, h3 { color: #e0e7ff !important; }
.stDataFrame { border-radius: 12px; overflow: hidden; }
div[data-testid="stForm"] { background: rgba(30,27,75,0.6); border: 1px solid rgba(99,102,241,0.2); border-radius: 16px; padding: 24px; backdrop-filter: blur(10px); }
.stSelectbox label, .stTextInput label, .stTextArea label, .stDateInput label, .stNumberInput label { color: #c7d2fe !important; }
.login-box { max-width: 420px; margin: 80px auto; background: rgba(30,27,75,0.7); border: 1px solid rgba(99,102,241,0.3); border-radius: 20px; padding: 40px; backdrop-filter: blur(20px); }
</style>
""", unsafe_allow_html=True)

DEAL_STAGES = ["lead","qualified","proposal","negotiation","closed_won","closed_lost"]
CONTACT_STATUSES = ["active","inactive","lead","customer"]
ACTIVITY_TYPES = ["call","email","meeting","task","note"]

# ── LOGIN / REGISTER ──
def show_login():
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        st.markdown("## 💼 CRM System")
        st.markdown("##### Sign in to your account")
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="admin@crm.com")
                pwd = st.text_input("Password", type="password", placeholder="admin123")
                if st.form_submit_button("Sign In", use_container_width=True):
                    user = authenticate(email, pwd)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        with tab2:
            with st.form("register_form"):
                fn = st.text_input("First Name")
                ln = st.text_input("Last Name")
                em = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    ok, msg = register_user(fn, ln, em, pw)
                    if ok:
                        st.success(msg + " Please login.")
                    else:
                        st.error(msg)

# ── SIDEBAR ──
def show_sidebar():
    u = current_user()
    with st.sidebar:
        st.markdown(f"### 💼 CRM")
        st.markdown(f"👤 **{u['first_name']} {u['last_name']}**")
        st.caption(f"Role: {u['role'].upper()}")
        st.divider()
        page = st.radio("Navigation", ["📊 Dashboard","👥 Contacts","🏢 Companies","💰 Deals","📅 Activities","⚙️ Settings"], label_visibility="collapsed")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
    return page

# ── DASHBOARD ──
def show_dashboard():
    st.markdown("## 📊 Dashboard")
    conn = get_connection()
    tc = conn.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"]
    td = conn.execute("SELECT COUNT(*) c FROM deals").fetchone()["c"]
    tr = conn.execute("SELECT COALESCE(SUM(value),0) c FROM deals WHERE stage='closed_won'").fetchone()["c"]
    ta = conn.execute("SELECT COUNT(*) c FROM activities WHERE is_completed=0").fetchone()["c"]
    tco = conn.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"]

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Contacts", tc)
    c2.metric("Total Deals", td)
    c3.metric("Revenue", f"${tr:,.0f}")
    c4.metric("Open Tasks", ta)
    c5.metric("Companies", tco)

    col1, col2 = st.columns(2)
    with col1:
        stages = conn.execute("SELECT stage, COUNT(*) cnt, COALESCE(SUM(value),0) val FROM deals GROUP BY stage").fetchall()
        if stages:
            df = pd.DataFrame([dict(r) for r in stages])
            fig = px.funnel(df, x="cnt", y="stage", color="stage", title="Deal Pipeline",
                          color_discrete_sequence=px.colors.sequential.Purp)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#c7d2fe", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No deals yet.")

    with col2:
        deals = conn.execute("SELECT stage, COALESCE(SUM(value),0) val FROM deals GROUP BY stage").fetchall()
        if deals:
            df = pd.DataFrame([dict(r) for r in deals])
            fig = px.pie(df, values="val", names="stage", title="Revenue by Stage", hole=0.4,
                        color_discrete_sequence=px.colors.sequential.Plasma)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#c7d2fe")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📋 Recent Activities")
    acts = conn.execute("SELECT a.*, c.first_name || ' ' || c.last_name as contact_name FROM activities a LEFT JOIN contacts c ON a.contact_id=c.id ORDER BY a.created_at DESC LIMIT 10").fetchall()
    if acts:
        df = pd.DataFrame([dict(r) for r in acts])
        st.dataframe(df[["type","subject","contact_name","due_date","is_completed"]], use_container_width=True, hide_index=True)
    else:
        st.info("No activities yet.")
    conn.close()

# ── CONTACTS ──
def show_contacts():
    st.markdown("## 👥 Contacts")
    conn = get_connection()
    col1, col2, col3 = st.columns([2,2,1])
    search = col1.text_input("🔍 Search", placeholder="Name or email...", label_visibility="collapsed")
    status_f = col2.selectbox("Filter Status", ["All"] + CONTACT_STATUSES, label_visibility="collapsed")
    if col3.button("➕ Add Contact", use_container_width=True):
        st.session_state.show_contact_form = True

    if st.session_state.get("show_contact_form"):
        companies = conn.execute("SELECT id, name FROM companies").fetchall()
        comp_map = {r["name"]: r["id"] for r in companies}
        with st.form("add_contact"):
            st.markdown("#### New Contact")
            ac1, ac2 = st.columns(2)
            fn = ac1.text_input("First Name")
            ln = ac2.text_input("Last Name")
            ac3, ac4 = st.columns(2)
            em = ac3.text_input("Email")
            ph = ac4.text_input("Phone")
            ac5, ac6 = st.columns(2)
            src = ac5.text_input("Source", placeholder="Web, Referral...")
            stat = ac6.selectbox("Status", CONTACT_STATUSES)
            comp = st.selectbox("Company", ["None"] + list(comp_map.keys()))
            if st.form_submit_button("Save Contact", use_container_width=True):
                cid = comp_map.get(comp)
                conn.execute("INSERT INTO contacts (first_name,last_name,email,phone,company_id,status,source,owner_id) VALUES (?,?,?,?,?,?,?,?)",
                           (fn,ln,em,ph,cid,stat,src,current_user()["id"]))
                conn.commit()
                st.session_state.show_contact_form = False
                st.rerun()

    q = "SELECT c.*, co.name as company_name FROM contacts c LEFT JOIN companies co ON c.company_id=co.id WHERE 1=1"
    params = []
    if search:
        q += " AND (c.first_name LIKE ? OR c.last_name LIKE ? OR c.email LIKE ?)"
        params += [f"%{search}%"]*3
    if status_f != "All":
        q += " AND c.status=?"
        params.append(status_f)
    q += " ORDER BY c.created_at DESC"
    rows = conn.execute(q, params).fetchall()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        display_cols = ["id","first_name","last_name","email","phone","status","company_name","source","created_at"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], use_container_width=True, hide_index=True)

        st.markdown("#### Manage Contact")
        mc1, mc2 = st.columns([1,3])
        del_id = mc1.number_input("Contact ID to delete", min_value=1, step=1)
        if mc2.button("🗑️ Delete Contact"):
            conn.execute("DELETE FROM contacts WHERE id=?", (del_id,))
            conn.commit()
            st.rerun()
    else:
        st.info("No contacts found.")
    conn.close()

# ── COMPANIES ──
def show_companies():
    st.markdown("## 🏢 Companies")
    conn = get_connection()
    col1, col2 = st.columns([3,1])
    search = col1.text_input("🔍 Search companies", placeholder="Name or industry...", label_visibility="collapsed")
    if col2.button("➕ Add Company", use_container_width=True):
        st.session_state.show_company_form = True

    if st.session_state.get("show_company_form"):
        with st.form("add_company"):
            st.markdown("#### New Company")
            cc1, cc2 = st.columns(2)
            name = cc1.text_input("Company Name")
            industry = cc2.text_input("Industry")
            cc3, cc4 = st.columns(2)
            website = cc3.text_input("Website")
            phone = cc4.text_input("Phone")
            address = st.text_input("Address")
            cc5, cc6 = st.columns(2)
            city = cc5.text_input("City")
            country = cc6.text_input("Country")
            if st.form_submit_button("Save Company", use_container_width=True):
                conn.execute("INSERT INTO companies (name,industry,website,phone,address,city,country,created_by) VALUES (?,?,?,?,?,?,?,?)",
                           (name,industry,website,phone,address,city,country,current_user()["id"]))
                conn.commit()
                st.session_state.show_company_form = False
                st.rerun()

    q = "SELECT * FROM companies WHERE 1=1"
    params = []
    if search:
        q += " AND (name LIKE ? OR industry LIKE ?)"
        params += [f"%{search}%"]*2
    q += " ORDER BY created_at DESC"
    rows = conn.execute(q, params).fetchall()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df[["id","name","industry","website","phone","city","country","created_at"]], use_container_width=True, hide_index=True)
        mc1, mc2 = st.columns([1,3])
        del_id = mc1.number_input("Company ID to delete", min_value=1, step=1)
        if mc2.button("🗑️ Delete Company"):
            conn.execute("UPDATE contacts SET company_id=NULL WHERE company_id=?", (del_id,))
            conn.execute("UPDATE deals SET company_id=NULL WHERE company_id=?", (del_id,))
            conn.execute("DELETE FROM companies WHERE id=?", (del_id,))
            conn.commit()
            st.rerun()
    else:
        st.info("No companies found.")
    conn.close()

# ── DEALS ──
def show_deals():
    st.markdown("## 💰 Deals")
    conn = get_connection()
    col1, col2, col3 = st.columns([2,2,1])
    search = col1.text_input("🔍 Search deals", placeholder="Title...", label_visibility="collapsed")
    stage_f = col2.selectbox("Filter Stage", ["All"] + DEAL_STAGES, label_visibility="collapsed")
    if col3.button("➕ Add Deal", use_container_width=True):
        st.session_state.show_deal_form = True

    if st.session_state.get("show_deal_form"):
        contacts = conn.execute("SELECT id, first_name||' '||last_name as name FROM contacts").fetchall()
        companies = conn.execute("SELECT id, name FROM companies").fetchall()
        ct_map = {r["name"]: r["id"] for r in contacts}
        co_map = {r["name"]: r["id"] for r in companies}
        with st.form("add_deal"):
            st.markdown("#### New Deal")
            dc1, dc2 = st.columns(2)
            title = dc1.text_input("Title")
            value = dc2.number_input("Value ($)", min_value=0.0, step=100.0)
            dc3, dc4 = st.columns(2)
            stage = dc3.selectbox("Stage", DEAL_STAGES)
            ecd = dc4.date_input("Expected Close Date")
            contact = st.selectbox("Contact", ["None"] + list(ct_map.keys()))
            company = st.selectbox("Company", ["None"] + list(co_map.keys()))
            desc = st.text_area("Description")
            if st.form_submit_button("Save Deal", use_container_width=True):
                conn.execute("INSERT INTO deals (title,value,stage,contact_id,company_id,owner_id,expected_close_date,description) VALUES (?,?,?,?,?,?,?,?)",
                           (title,value,stage,ct_map.get(contact),co_map.get(company),current_user()["id"],str(ecd),desc))
                conn.commit()
                st.session_state.show_deal_form = False
                st.rerun()

    # Kanban view
    st.markdown("### Pipeline View")
    kanban_cols = st.columns(len(DEAL_STAGES))
    for i, stage in enumerate(DEAL_STAGES):
        with kanban_cols[i]:
            label = stage.replace("_"," ").title()
            deals_in = conn.execute("SELECT * FROM deals WHERE stage=? ORDER BY value DESC", (stage,)).fetchall()
            total = sum(d["value"] for d in deals_in)
            st.markdown(f"**{label}**")
            st.caption(f"{len(deals_in)} deals · ${total:,.0f}")
            for d in deals_in:
                st.markdown(f"""<div style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.2);border-radius:8px;padding:10px;margin:6px 0;">
                <b style="color:#e0e7ff">{d['title']}</b><br><span style="color:#a5b4fc">${d['value']:,.0f}</span></div>""", unsafe_allow_html=True)

    # Table view
    st.markdown("### 📋 Table View")
    q = "SELECT d.*, c.first_name||' '||c.last_name as contact_name, co.name as company_name FROM deals d LEFT JOIN contacts c ON d.contact_id=c.id LEFT JOIN companies co ON d.company_id=co.id WHERE 1=1"
    params = []
    if search:
        q += " AND d.title LIKE ?"
        params.append(f"%{search}%")
    if stage_f != "All":
        q += " AND d.stage=?"
        params.append(stage_f)
    q += " ORDER BY d.created_at DESC"
    rows = conn.execute(q, params).fetchall()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df[["id","title","value","stage","contact_name","company_name","expected_close_date"]], use_container_width=True, hide_index=True)
    conn.close()

# ── ACTIVITIES ──
def show_activities():
    st.markdown("## 📅 Activities")
    conn = get_connection()
    col1, col2 = st.columns([3,1])
    type_f = col1.selectbox("Filter Type", ["All"] + ACTIVITY_TYPES, label_visibility="collapsed")
    if col2.button("➕ Add Activity", use_container_width=True):
        st.session_state.show_act_form = True

    if st.session_state.get("show_act_form"):
        contacts = conn.execute("SELECT id, first_name||' '||last_name as name FROM contacts").fetchall()
        deals = conn.execute("SELECT id, title FROM deals").fetchall()
        ct_map = {r["name"]: r["id"] for r in contacts}
        dl_map = {r["title"]: r["id"] for r in deals}
        with st.form("add_activity"):
            st.markdown("#### New Activity")
            ac1, ac2 = st.columns(2)
            atype = ac1.selectbox("Type", ACTIVITY_TYPES)
            subject = ac2.text_input("Subject")
            desc = st.text_area("Description")
            ac3, ac4 = st.columns(2)
            contact = ac3.selectbox("Contact", ["None"] + list(ct_map.keys()))
            deal = ac4.selectbox("Deal", ["None"] + list(dl_map.keys()))
            due = st.date_input("Due Date")
            if st.form_submit_button("Save Activity", use_container_width=True):
                conn.execute("INSERT INTO activities (type,subject,description,contact_id,deal_id,owner_id,due_date) VALUES (?,?,?,?,?,?,?)",
                           (atype,subject,desc,ct_map.get(contact),dl_map.get(deal),current_user()["id"],str(due)))
                conn.commit()
                st.session_state.show_act_form = False
                st.rerun()

    q = "SELECT a.*, c.first_name||' '||c.last_name as contact_name FROM activities a LEFT JOIN contacts c ON a.contact_id=c.id WHERE 1=1"
    params = []
    if type_f != "All":
        q += " AND a.type=?"
        params.append(type_f)
    q += " ORDER BY a.due_date ASC"
    rows = conn.execute(q, params).fetchall()
    if rows:
        for r in rows:
            d = dict(r)
            icon = {"call":"📞","email":"📧","meeting":"🤝","task":"✅","note":"📝"}.get(d["type"],"📌")
            done = "✓" if d["is_completed"] else "○"
            color = "rgba(34,197,94,0.2)" if d["is_completed"] else "rgba(99,102,241,0.1)"
            st.markdown(f"""<div style="background:{color};border:1px solid rgba(99,102,241,0.2);border-radius:10px;padding:12px;margin:6px 0;display:flex;align-items:center;gap:12px;">
            <span style="font-size:24px">{icon}</span>
            <div><b style="color:#e0e7ff">{done} {d['subject']}</b><br>
            <span style="color:#a5b4fc">{d['type'].title()} · {d.get('contact_name','—')} · Due: {d.get('due_date','—')}</span></div></div>""", unsafe_allow_html=True)

        st.markdown("#### Mark Complete / Delete")
        mc1, mc2, mc3 = st.columns(3)
        aid = mc1.number_input("Activity ID", min_value=1, step=1)
        if mc2.button("✅ Complete"):
            conn.execute("UPDATE activities SET is_completed=1, updated_at=? WHERE id=?", (datetime.now().isoformat(), aid))
            conn.commit(); st.rerun()
        if mc3.button("🗑️ Delete"):
            conn.execute("DELETE FROM activities WHERE id=?", (aid,))
            conn.commit(); st.rerun()
    else:
        st.info("No activities found.")
    conn.close()

# ── SETTINGS ──
def show_settings():
    st.markdown("## ⚙️ Settings")
    conn = get_connection()
    u = current_user()

    tab1, tab2 = st.tabs(["👤 Profile", "👥 User Management" if u["role"]=="admin" else "🔒 Change Password"])

    with tab1:
        with st.form("profile"):
            fn = st.text_input("First Name", value=u["first_name"])
            ln = st.text_input("Last Name", value=u["last_name"])
            em = st.text_input("Email", value=u["email"])
            st.divider()
            st.markdown("**Change Password**")
            cp = st.text_input("Current Password", type="password")
            np_ = st.text_input("New Password", type="password")
            if st.form_submit_button("Save Changes", use_container_width=True):
                conn.execute("UPDATE users SET first_name=?, last_name=?, email=?, updated_at=? WHERE id=?",
                           (fn, ln, em, datetime.now().isoformat(), u["id"]))
                if cp and np_:
                    from auth import verify_password
                    row = conn.execute("SELECT password_hash FROM users WHERE id=?", (u["id"],)).fetchone()
                    if verify_password(cp, row["password_hash"]):
                        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(np_), u["id"]))
                        st.success("Password updated!")
                    else:
                        st.error("Current password incorrect")
                conn.commit()
                st.session_state.user = dict(conn.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone())
                st.success("Profile updated!")

    with tab2:
        if u["role"] == "admin":
            users = conn.execute("SELECT id, first_name, last_name, email, role, is_active, created_at FROM users ORDER BY id").fetchall()
            df = pd.DataFrame([dict(r) for r in users])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            with st.form("change_pw"):
                cp2 = st.text_input("Current Password", type="password")
                np2 = st.text_input("New Password", type="password")
                if st.form_submit_button("Update Password"):
                    from auth import verify_password
                    row = conn.execute("SELECT password_hash FROM users WHERE id=?", (u["id"],)).fetchone()
                    if verify_password(cp2, row["password_hash"]):
                        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(np2), u["id"]))
                        conn.commit()
                        st.success("Password updated!")
                    else:
                        st.error("Wrong current password")
    conn.close()

# ── MAIN ──
def main():
    if not is_logged_in():
        show_login()
        return

    page = show_sidebar()
    if "Dashboard" in page:
        show_dashboard()
    elif "Contacts" in page:
        show_contacts()
    elif "Companies" in page:
        show_companies()
    elif "Deals" in page:
        show_deals()
    elif "Activities" in page:
        show_activities()
    elif "Settings" in page:
        show_settings()

if __name__ == "__main__":
    main()
