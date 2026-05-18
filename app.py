"""
JobMatcher — AI 智能投递管理工具 v1.7
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import plotly.express as px
import uuid
import re

# LLM（DeepSeek via Anthropic SDK）
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

# ── API 配置（Streamlit Cloud secrets → 环境变量 → 内置默认值）──
def get_llm_config():
    """获取LLM配置，优先级：st.secrets > 环境变量 > 默认值"""
    config = {"base_url": "", "api_key": "", "model": ""}
    for key in ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"]:
        # 1. Streamlit Cloud secrets
        try:
            val = st.secrets.get(key, "")
            if val:
                config[key.lower().replace("anthropic_", "")] = val
                continue
        except:
            pass
        # 2. 环境变量
        val = os.environ.get(key, "")
        if val:
            config[key.lower().replace("anthropic_", "")] = val
            continue
    # 3. 默认值（DeepSeek 兼容 Anthropic SDK）
    if not config.get("base_url"):
        config["base_url"] = "https://api.deepseek.com/anthropic"
    if not config.get("model"):
        config["model"] = "deepseek-v4-pro"
    return config


def get_anthropic_client():
    """获取配置好的 Anthropic 客户端"""
    if not HAS_ANTHROPIC:
        return None
    cfg = get_llm_config()
    if not cfg.get("api_key"):
        return None
    return Anthropic(base_url=cfg["base_url"], api_key=cfg["api_key"])

# ═══════════════════════════════════════
# 配置
# ═══════════════════════════════════════
st.set_page_config(page_title="JobMatcher", page_icon="🎯", layout="wide")

# ═══════════════════════════════════════
# 全局 UI 美化
# ═══════════════════════════════════════
st.markdown("""
<style>
/* ── 全局字体与底色 ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', 'Microsoft YaHei', 'PingFang SC', sans-serif;
    color: #1a1a2e;
}

/* ── 主背景微调 ── */
.stApp { background: linear-gradient(180deg, #f8f9fc 0%, #ffffff 100%); }

/* ── 侧边栏 ── */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8ecf1;
    box-shadow: 2px 0 12px rgba(0,0,0,0.04);
}
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 6px 12px;
    border-radius: 8px;
    transition: all 0.15s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: #f0f4ff;
}

/* ── 标题 ── */
h1 { font-weight: 700 !important; letter-spacing: -0.5px; }
h2 { font-weight: 600 !important; }
h3 { font-weight: 600 !important; }

/* ── 卡片容器 ── */
.card {
    background: #ffffff;
    border: 1px solid #e8ecf1;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 12px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
.card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }

/* ── 按钮 ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

/* ── 主要按钮 ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4F46E5, #6366F1) !important;
    border: none !important;
}

/* ── Metric 卡片 ── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e8ecf1;
    border-radius: 10px;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid #e8ecf1 !important;
    border-radius: 10px !important;
    margin: 8px 0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.02) !important;
}

/* ── Tab 标签 ── */
.stTabs [data-baseweb="tab"] {
    font-weight: 500;
    padding: 10px 20px !important;
    border-radius: 8px 8px 0 0 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #f0f4ff !important;
    color: #4F46E5 !important;
    border-bottom: 2px solid #4F46E5 !important;
}

/* ── 输入框 ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    border-radius: 8px !important;
    border: 1px solid #d1d5db !important;
}

/* ── 进度条 ── */
.stProgress > div > div {
    background: linear-gradient(90deg, #4F46E5, #6366F1) !important;
    border-radius: 4px;
}

/* ── 数据表格 ── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e8ecf1;
}

/* ── 状态徽章 ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 10pt;
    font-weight: 500;
}
.badge-active { background: #e0f2fe; color: #0369a1; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-danger { background: #fee2e2; color: #991b1b; }
.badge-muted { background: #f3f4f6; color: #6b7280; }

/* ── 分割线 ── */
hr { border-color: #e8ecf1 !important; }

/* ── 滚动条 ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
ACTIVE_PROFILE_FILE = os.path.join(DATA_DIR, "active_profile.json")
# 隐私：所有数据均按用户隔离，无共享存储

# 确保目录存在
for d in [DATA_DIR, PROFILES_DIR]:
    os.makedirs(d, exist_ok=True)

# ── 用户档案管理 ──

def get_active_profile():
    """获取当前活跃用户ID"""
    if os.path.exists(ACTIVE_PROFILE_FILE):
        with open(ACTIVE_PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("active", "default")
    return "default"

def set_active_profile(profile_id):
    """切换活跃用户"""
    with open(ACTIVE_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump({"active": profile_id}, f, ensure_ascii=False, indent=2)

def list_profiles():
    """列出所有用户档案"""
    if not os.path.exists(PROFILES_DIR):
        return []
    profiles = []
    for d in os.listdir(PROFILES_DIR):
        profile_dir = os.path.join(PROFILES_DIR, d)
        if os.path.isdir(profile_dir):
            info_file = os.path.join(profile_dir, "info.json")
            info = {}
            if os.path.exists(info_file):
                with open(info_file, "r", encoding="utf-8") as f:
                    info = json.load(f)
            profiles.append({
                "id": d,
                "name": info.get("name", d),
                "email": info.get("email", ""),
                "phone": info.get("phone", ""),
                "created_at": info.get("created_at", ""),
            })
    return profiles

def get_profile_path(profile_id):
    """获取指定用户的数据目录"""
    pdir = os.path.join(PROFILES_DIR, profile_id)
    os.makedirs(pdir, exist_ok=True)
    return pdir

def get_history_file(profile_id=None):
    if profile_id is None:
        profile_id = get_active_profile()
    return os.path.join(get_profile_path(profile_id), "application_history.json")

def get_exp_lib_file(profile_id=None):
    if profile_id is None:
        profile_id = get_active_profile()
    return os.path.join(get_profile_path(profile_id), "experience_library.json")

def hash_password(password):
    if HAS_BCRYPT:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return password  # 无bcrypt时明文

def verify_password(password, hashed):
    if HAS_BCRYPT and hashed and hashed != password:  # hashed != password 判断是否为hash
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except:
            return password == hashed
    return password == hashed

def create_profile(name, email="", phone="", password=""):
    """创建新用户档案"""
    pid = str(uuid.uuid4())[:8]
    pdir = get_profile_path(pid)
    info = {
        "name": name, "email": email, "phone": phone,
        "password": hash_password(password) if password else "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    with open(os.path.join(pdir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    # 初始化空的经历库
    default_lib = {"basic": {"name": name, "email": email, "phone": phone}, "education": [], "skills": [], "experiences": [], "certifications": [], "personal_projects": [], "resume_directions": {}, "interview_notes": ""}
    with open(os.path.join(pdir, "experience_library.json"), "w", encoding="utf-8") as f:
        json.dump(default_lib, f, ensure_ascii=False, indent=2)
    with open(os.path.join(pdir, "application_history.json"), "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)
    return pid

def verify_login(profile_id, password):
    """验证用户登录"""
    pdir = get_profile_path(profile_id)
    info_file = os.path.join(pdir, "info.json")
    if not os.path.exists(info_file):
        return False
    with open(info_file, "r", encoding="utf-8") as f:
        info = json.load(f)
    stored_pw = info.get("password", "")
    if not stored_pw:
        # 旧用户未设密码，首次登录时设置的密码即为密码
        info["password"] = hash_password(password)
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        return True
    return verify_password(password, stored_pw)

def migrate_legacy_data():
    """迁移旧版数据到 default 用户"""
    default_dir = get_profile_path("default")
    legacy_exp = os.path.join(os.path.dirname(DATA_DIR), "experience_library.json")
    legacy_hist = os.path.join(os.path.dirname(DATA_DIR), "application_history.json")

    if os.path.exists(legacy_exp) and not os.path.exists(os.path.join(default_dir, "experience_library.json")):
        import shutil
        shutil.copy(legacy_exp, os.path.join(default_dir, "experience_library.json"))
    if os.path.exists(legacy_hist) and not os.path.exists(os.path.join(default_dir, "application_history.json")):
        import shutil
        shutil.copy(legacy_hist, os.path.join(default_dir, "application_history.json"))
    info = {"name": "牟思雨", "email": "msy1994dut@163.com", "phone": "18504284554", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if not os.path.exists(os.path.join(default_dir, "info.json")):
        with open(os.path.join(default_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

# 种子数据：仅对指定用户加载真实经历库，其他用户生成模拟数据
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_experience_library.json")
DEVICE_SECRET = "msy2026"  # 只有URL带此密钥的设备才能加载真实数据

MOCK_EXPERIENCE_LIB = {
    "basic": {"name": "张明", "phone": "138****1234", "email": "demo@example.com"},
    "education": [
        {"time": "2019.09–2022.06", "school": "XX大学", "degree": "硕士", "major": "计算机科学与技术", "highlights": []},
        {"time": "2015.09–2019.06", "school": "YY大学", "degree": "本科", "major": "信息管理", "highlights": []},
    ],
    "skills": [
        {"name": "数据分析", "category": "tech", "level": "advanced"},
        {"name": "项目管理", "category": "methodology", "level": "intermediate"},
        {"name": "用户运营", "category": "domain", "level": "intermediate"},
        {"name": "SQL", "category": "tech", "level": "intermediate"},
        {"name": "Python", "category": "tech", "level": "beginner"},
        {"name": "跨部门沟通", "category": "methodology", "level": "advanced"},
        {"name": "产品运营", "category": "domain", "level": "intermediate"},
    ],
    "experiences": [
        {"id": "mock-1", "company": "某互联网科技公司", "role": "产品运营专员", "time": "2021.07–2024.03",
         "category": ["产品运营"], "summary": "负责用户增长与活动运营",
         "bullets": [
             {"text": "负责APP日活用户增长，通过A/B测试优化推送策略，DAU提升25%", "keywords": ["用户增长", "A/B测试"]},
             {"text": "策划并执行3场大型营销活动，累计参与用户超50万，ROI达1:3.5", "keywords": ["活动运营", "ROI"]},
             {"text": "搭建用户画像体系，实现精准推送，消息点击率从8%提升至15%", "keywords": ["用户画像", "精准推送"]},
         ]},
        {"id": "mock-2", "company": "某电商平台", "role": "运营实习生", "time": "2020.06–2020.09",
         "category": ["电商运营"], "summary": "协助商家运营与数据分析",
         "bullets": [
             {"text": "协助运营团队管理50+商家店铺，监控商品上下架与活动报名", "keywords": ["商家运营"]},
             {"text": "使用Excel和SQL完成周度销售数据报表，为运营决策提供数据支持", "keywords": ["数据分析", "SQL"]},
         ]},
    ],
    "certifications": ["PMP项目管理认证", "数据分析师认证"],
    "personal_projects": [],
    "resume_directions": {"产品运营": {"target_roles": ["产品运营"], "emphasize_skills": ["数据分析", "用户运营", "项目管理"], "primary_experiences": ["mock-1", "mock-2"], "summary_template": "3年产品运营经验，擅长数据驱动增长。"}},
    "interview_entries": [],
}

def is_owner_device():
    """检查当前设备是否是真实数据所有者"""
    # 1. session已授权
    if st.session_state.get("device_authorized"):
        return True
    # 2. URL含密钥
    if st.query_params.get("key", "") == DEVICE_SECRET:
        st.session_state["device_authorized"] = True
        return True
    return False

def init_user_data(profile_id):
    """初始化用户数据：真实设备加载种子数据，其他设备生成模拟数据"""
    user_dir = get_profile_path(profile_id)
    exp_file = os.path.join(user_dir, "experience_library.json")
    if not os.path.exists(exp_file):
        if is_owner_device() and os.path.exists(SEED_FILE):
            import shutil
            shutil.copy(SEED_FILE, exp_file)
        else:
            mock_data = json.loads(json.dumps(MOCK_EXPERIENCE_LIB))
            mock_data["basic"]["name"] = f"演示用户{profile_id[:4]}"
            with open(exp_file, "w", encoding="utf-8") as f:
                json.dump(mock_data, f, ensure_ascii=False, indent=2)
    hist_file = os.path.join(user_dir, "application_history.json")
    if not os.path.exists(hist_file):
        with open(hist_file, "w", encoding="utf-8") as f:
            json.dump([], f)
    info_file = os.path.join(user_dir, "info.json")
    if not os.path.exists(info_file):
        info = {"name": f"用户{profile_id[:6]}", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        if is_owner:
            info = {"name": "牟思雨", "email": "msy1994dut@163.com", "phone": "18504284554", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

migrate_legacy_data()

# 动态路径（基于活跃用户）
def _current_history_file():
    return get_history_file(get_active_profile())

def _current_exp_lib_file():
    return get_exp_lib_file(get_active_profile())

STATUS_FLOW = ["待投递", "已投递", "初筛", "一面", "二面", "终面", "offer", "已拒", "归档"]
STATUS_COLORS = {
    "待投递": "#90A4AE", "已投递": "#42A5F5", "初筛": "#AB47BC",
    "一面": "#FFA726", "二面": "#FF7043", "终面": "#EF5350",
    "offer": "#66BB6A", "已拒": "#BDBDBD", "归档": "#78909C",
}
DIRECTIONS = ["AI产品运营", "服务体验运营", "AI项目管理", "通用", "其他"]


# ═══════════════════════════════════════
# 数据层
# ═══════════════════════════════════════

def load_history():
    if st.session_state.get("is_guest"):
        return st.session_state.get("guest_history", [])
    fpath = _current_history_file()
    if not os.path.exists(fpath):
        return []
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(records):
    if st.session_state.get("is_guest"):
        st.session_state["guest_history"] = records
        return
    with open(_current_history_file(), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def load_experience_lib():
    if st.session_state.get("is_guest"):
        return st.session_state.get("guest_exp_lib", {})
    fpath = _current_exp_lib_file()
    if not os.path.exists(fpath):
        return {}
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════
# 投递记录 CRUD
# ═══════════════════════════════════════

def render_add_form():
    """新增投递记录表单"""
    st.subheader("➕ 新增投递记录")

    with st.form("add_application", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("公司名称 *", placeholder="如：美团")
            position = st.text_input("岗位名称 *", placeholder="如：大模型智能客服运营")
            city = st.selectbox("城市", ["上海", "北京", "沈阳", "杭州", "深圳", "广州", "成都", "其他"])
            direction = st.selectbox("求职方向", DIRECTIONS)
        with col2:
            salary = st.text_input("薪资范围", placeholder="如：20k-35k·16薪")
            platform = st.selectbox("投递渠道", ["Boss直聘", "猎聘", "脉脉", "官网", "内推", "其他"])
            contact = st.text_input("联系人/HR", placeholder="如有，填写联系人或HR名称")
            status = st.selectbox("当前状态", STATUS_FLOW, index=0)

        jd_text = st.text_area("岗位JD（可选，粘贴后可用于匹配分析）", height=120, placeholder="粘贴岗位描述...")
        notes = st.text_area("备注", height=60, placeholder="面试感受、跟进计划等...")

        submitted = st.form_submit_button("✅ 保存记录", type="primary", use_container_width=True)

        if submitted:
            if not company or not position:
                st.error("公司名称和岗位名称为必填项")
                return

            record = {
                "id": str(uuid.uuid4())[:8],
                "company": company.strip(),
                "position": position.strip(),
                "city": city,
                "direction": direction,
                "salary": salary.strip(),
                "platform": platform,
                "contact": contact.strip(),
                "status": status,
                "jd_text": jd_text.strip(),
                "notes": notes.strip(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "history": [{"status": status, "time": datetime.now().strftime("%Y-%m-%d %H:%M")}],
            }

            records = load_history()
            records.append(record)
            save_history(records)
            st.success(f"✅ 已保存：{company} - {position}")
            st.rerun()


def render_record_list(records):
    """投递记录列表 + 筛选"""
    if not records:
        st.info("📭 暂无投递记录，点击「新增投递」开始记录")
        return

    # 筛选栏
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_status = st.multiselect("状态筛选", STATUS_FLOW, key="filter_status")
    with col_f2:
        filter_direction = st.multiselect("方向筛选", DIRECTIONS, key="filter_direction")
    with col_f3:
        search_keyword = st.text_input("🔍 搜索公司/岗位", placeholder="输入关键词...")
    with col_f4:
        sort_by = st.selectbox("排序", ["更新时间↓", "创建时间↓", "公司名"], key="sort_by")

    # 应用筛选
    filtered = records
    if filter_status:
        filtered = [r for r in filtered if r.get("status") in filter_status]
    if filter_direction:
        filtered = [r for r in filtered if r.get("direction") in filter_direction]
    if search_keyword:
        kw = search_keyword.lower()
        filtered = [r for r in filtered if kw in r.get("company", "").lower() or kw in r.get("position", "").lower()]

    # 排序
    if sort_by == "更新时间↓":
        filtered = sorted(filtered, key=lambda r: r.get("updated_at", ""), reverse=True)
    elif sort_by == "创建时间↓":
        filtered = sorted(filtered, key=lambda r: r.get("created_at", ""), reverse=True)
    else:
        filtered = sorted(filtered, key=lambda r: r.get("company", ""))

    st.caption(f"共 {len(filtered)} 条记录（总计 {len(records)} 条）")

    # 卡片列表
    for i, record in enumerate(filtered):
        status = record.get("status", "待投递")
        color = STATUS_COLORS.get(status, "#90A4AE")

        with st.container():
            col_main, col_action = st.columns([6, 1])
            with col_main:
                st.markdown(
                    f"### {record.get('company', '?')} — {record.get('position', '?')} "
                    f"<span style='color:{color};font-size:14pt'>● {status}</span>",
                    unsafe_allow_html=True,
                )
                meta_parts = []
                if record.get("city"): meta_parts.append(record["city"])
                if record.get("salary"): meta_parts.append(record["salary"])
                if record.get("platform"): meta_parts.append(record["platform"])
                if record.get("direction"): meta_parts.append(record["direction"])
                st.caption(" | ".join(meta_parts))

                if record.get("notes"):
                    st.caption(f"📝 {record['notes'][:100]}{'...' if len(record.get('notes', '')) > 100 else ''}")

            with col_action:
                st.markdown(f"<small>{record.get('updated_at', '')[:10]}</small>", unsafe_allow_html=True)
                if st.button("📝 编辑", key=f"edit_{i}", use_container_width=True):
                    st.session_state["editing_record"] = record["id"]
                    st.rerun()
                if st.button("🗑️ 删除", key=f"del_{i}", use_container_width=True):
                    st.session_state["deleting_record"] = record["id"]
                    st.rerun()

            st.divider()


def render_edit_dialog(records):
    """编辑/删除弹窗"""
    edit_id = st.session_state.get("editing_record")
    del_id = st.session_state.get("deleting_record")

    # 删除确认
    if del_id:
        target = next((r for r in records if r["id"] == del_id), None)
        if target:
            st.warning(f"确认删除 **{target['company']} - {target['position']}** ？")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("✅ 确认删除", type="primary", use_container_width=True):
                    records = [r for r in records if r["id"] != del_id]
                    save_history(records)
                    st.session_state["deleting_record"] = None
                    st.success("已删除")
                    st.rerun()
            with col_cancel:
                if st.button("❌ 取消", use_container_width=True):
                    st.session_state["deleting_record"] = None
                    st.rerun()

    # 编辑弹窗
    if edit_id:
        target = next((r for r in records if r["id"] == edit_id), None)
        if target:
            st.subheader(f"📝 编辑：{target['company']} - {target['position']}")

            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    company = st.text_input("公司名称", value=target.get("company", ""))
                    position = st.text_input("岗位名称", value=target.get("position", ""))
                    city = st.selectbox("城市", ["上海", "北京", "沈阳", "杭州", "深圳", "广州", "成都", "其他"],
                                        index=["上海", "北京", "沈阳", "杭州", "深圳", "广州", "成都", "其他"].index(target.get("city", "上海")) if target.get("city") in ["上海", "北京", "沈阳", "杭州", "深圳", "广州", "成都", "其他"] else 0)
                    direction = st.selectbox("求职方向", DIRECTIONS,
                                             index=DIRECTIONS.index(target.get("direction", "通用")) if target.get("direction") in DIRECTIONS else 3)
                with col2:
                    salary = st.text_input("薪资范围", value=target.get("salary", ""))
                    platform = st.selectbox("投递渠道", ["Boss直聘", "猎聘", "脉脉", "官网", "内推", "其他"],
                                            index=["Boss直聘", "猎聘", "脉脉", "官网", "内推", "其他"].index(target.get("platform", "Boss直聘")) if target.get("platform") in ["Boss直聘", "猎聘", "脉脉", "官网", "内推", "其他"] else 0)
                    contact = st.text_input("联系人/HR", value=target.get("contact", ""))
                    new_status = st.selectbox("当前状态", STATUS_FLOW,
                                              index=STATUS_FLOW.index(target.get("status", "待投递")) if target.get("status") in STATUS_FLOW else 0)

                jd_text = st.text_area("岗位JD", value=target.get("jd_text", ""), height=120)
                notes = st.text_area("备注", value=target.get("notes", ""), height=60)

                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.form_submit_button("💾 保存修改", type="primary", use_container_width=True):
                        target["company"] = company
                        target["position"] = position
                        target["city"] = city
                        target["direction"] = direction
                        target["salary"] = salary
                        target["platform"] = platform
                        target["contact"] = contact
                        target["jd_text"] = jd_text
                        target["notes"] = notes
                        target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

                        # 状态变更历史
                        if new_status != target.get("status"):
                            target.setdefault("history", []).append({
                                "status": new_status,
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            })
                        target["status"] = new_status

                        save_history(records)
                        st.session_state["editing_record"] = None
                        st.success("已保存")
                        st.rerun()
                with col_cancel:
                    if st.form_submit_button("❌ 取消", use_container_width=True):
                        st.session_state["editing_record"] = None
                        st.rerun()


def render_dashboard(records):
    """投递看板"""
    if not records:
        return

    st.subheader("📊 投递看板")

    col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
    with col_k1:
        st.metric("总投递", len(records))
    with col_k2:
        active = len([r for r in records if r.get("status") not in ["已拒", "归档", "offer"]])
        st.metric("进行中", active)
    with col_k3:
        interview = len([r for r in records if r.get("status") in ["一面", "二面", "终面"]])
        st.metric("面试中", interview)
    with col_k4:
        offers = len([r for r in records if r.get("status") == "offer"])
        st.metric("offer", offers, delta="🎉" if offers > 0 else None)
    with col_k5:
        rejected = len([r for r in records if r.get("status") == "已拒"])
        st.metric("已拒", rejected)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        # 状态分布
        status_counts = {}
        for r in records:
            s = r.get("status", "未知")
            status_counts[s] = status_counts.get(s, 0) + 1
        status_df = pd.DataFrame({"状态": list(status_counts.keys()), "数量": list(status_counts.values())})
        fig_status = px.bar(status_df, x="状态", y="数量", color="状态",
                            color_discrete_map=STATUS_COLORS, title="投递状态分布")
        st.plotly_chart(fig_status, use_container_width=True)

    with col_c2:
        # 方向分布
        dir_counts = {}
        for r in records:
            d = r.get("direction", "未知")
            dir_counts[d] = dir_counts.get(d, 0) + 1
        dir_df = pd.DataFrame({"方向": list(dir_counts.keys()), "数量": list(dir_counts.values())})
        fig_dir = px.pie(dir_df, names="方向", values="数量", title="求职方向分布", hole=0.3)
        st.plotly_chart(fig_dir, use_container_width=True)

    # 时间线
    status_order = {s: i for i, s in enumerate(STATUS_FLOW)}
    with st.expander("📋 状态流转明细"):
        for r in sorted(records, key=lambda x: x.get("updated_at", ""), reverse=True)[:20]:
            history = r.get("history", [])
            if history:
                timeline = " → ".join([f"{h['status']}({h['time'][:10]})" for h in history])
                st.caption(f"**{r['company']}** - {r['position']}: {timeline}")


# ═══════════════════════════════════════
# 模块2：JD 智能分析
# ═══════════════════════════════════════

JD_ANALYSIS_PROMPT = """你是资深HR和职业规划师。请分析以下岗位JD，输出结构化JSON。

要求：
1. 提取关键信息，不得编造JD中没有的内容
2. 技能要求按"必须"和"加分"分级
3. 如果JD中未明确某项信息，字段值设为null

输出格式：
{
  "company_name": "公司名称（从JD中提取，无则null）",
  "position": "岗位名称",
  "city": "工作城市",
  "salary_range": "薪资范围（原文）",
  "industry": "行业/赛道",
  "summary": "岗位一句话概述（20字以内）",
  "hard_skills": ["硬性技能1", "硬性技能2"],
  "nice_skills": ["加分技能1", "加分技能2"],
  "experience_required": "经验年限要求",
  "degree_required": "学历要求",
  "key_responsibilities": ["核心职责1", "核心职责2", "核心职责3"],
  "soft_requirements": ["软性要求1", "软性要求2"],
  "matched_direction": "最匹配的求职方向：AI产品运营/服务体验运营/AI项目管理/通用"
}"""


def parse_jd_with_llm(jd_text):
    """使用LLM解析JD"""
    if not HAS_ANTHROPIC:
        return {"error": "anthropic SDK 未安装，请执行 pip install anthropic"}

    if not jd_text or len(jd_text) < 20:
        return {"error": "JD文本太短，请粘贴完整岗位描述"}

    try:
        client = get_anthropic_client()
        if not client:
            return {"error": "API Key 未配置。请在 Streamlit Cloud Secrets 或 .env 中设置 ANTHROPIC_AUTH_TOKEN"}
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=1500,
            temperature=0.1,
            system="你是一个精准的JD分析工具。只输出合法JSON，不添加任何解释。",
            messages=[{
                "role": "user",
                "content": f"{JD_ANALYSIS_PROMPT}\n\n---JD文本---\n{jd_text[:3000]}"
            }],
        )
        # 处理 thinking block 和多 content 类型
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip()
                break
        if not raw:
            raw = str(resp.content)
        # 提取JSON（处理可能的markdown包裹）
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["_raw_response"] = raw
            result["_parsed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            return result
        else:
            return {"error": "LLM返回格式异常", "_raw": raw[:500]}
    except Exception as e:
        return {"error": f"API调用失败: {str(e)}"}


def render_jd_analysis():
    """JD分析页面"""
    st.subheader("🔍 JD 智能分析")

    jd_text = st.text_area(
        "粘贴岗位JD文本",
        height=200,
        placeholder="粘贴完整的岗位描述，包括岗位职责、任职要求、公司介绍等...\n系统将自动提取：公司、岗位、技能要求、经验要求、匹配方向等",
        key="jd_input",
    )

    col_a1, col_a2 = st.columns([1, 3])
    with col_a1:
        analyze_btn = st.button("🔍 开始分析", type="primary", use_container_width=True, disabled=not jd_text)
    with col_a2:
        st.caption("使用 DeepSeek LLM 进行结构化提取，分析耗时约 3-5 秒")

    if analyze_btn and jd_text:
        with st.spinner("正在分析JD..."):
            result = parse_jd_with_llm(jd_text)

        if "error" in result:
            st.error(result["error"])
            if "_raw" in result:
                st.code(result["_raw"], language="json")
        else:
            st.success("✅ 分析完成")

            # 展示结构化结果
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📋 基本信息")
                info_items = {
                    "公司": result.get("company_name"),
                    "岗位": result.get("position"),
                    "城市": result.get("city"),
                    "薪资": result.get("salary_range"),
                    "行业": result.get("industry"),
                    "经验要求": result.get("experience_required"),
                    "学历要求": result.get("degree_required"),
                    "推荐方向": result.get("matched_direction"),
                }
                for label, value in info_items.items():
                    if value:
                        st.markdown(f"**{label}**：{value}")

            with col2:
                st.markdown("### 🎯 技能要求")
                if result.get("hard_skills"):
                    st.markdown("**必备技能**")
                    for s in result["hard_skills"]:
                        st.markdown(f"- 🔴 {s}")
                if result.get("nice_skills"):
                    st.markdown("**加分技能**")
                    for s in result["nice_skills"]:
                        st.markdown(f"- 🟢 {s}")

            st.markdown("### 📝 核心职责")
            if result.get("key_responsibilities"):
                for i, r in enumerate(result["key_responsibilities"], 1):
                    st.markdown(f"{i}. {r}")

            if result.get("soft_requirements"):
                st.markdown("### 🤝 软性要求")
                st.markdown(" | ".join([f"`{s}`" for s in result["soft_requirements"]]))

            # 一键创建投递记录
            st.divider()
            st.markdown("### ➕ 一键创建投递记录")
            with st.form("quick_add_from_jd"):
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    company = st.text_input("公司", value=result.get("company_name") or "")
                    position = st.text_input("岗位", value=result.get("position") or "")
                    city = st.text_input("城市", value=result.get("city") or "上海")
                with col_q2:
                    salary = st.text_input("薪资", value=result.get("salary_range") or "")
                    direction = st.selectbox("方向", DIRECTIONS,
                        index=DIRECTIONS.index(result.get("matched_direction")) if result.get("matched_direction") in DIRECTIONS else 3)
                    platform = st.selectbox("渠道", ["Boss直聘", "猎聘", "脉脉", "官网", "内推", "其他"])

                notes = st.text_area("备注", value=result.get("summary", ""), height=60)

                if st.form_submit_button("✅ 保存为投递记录", type="primary", use_container_width=True):
                    record = {
                        "id": str(uuid.uuid4())[:8],
                        "company": company.strip(),
                        "position": position.strip(),
                        "city": city.strip(),
                        "direction": direction,
                        "salary": salary.strip(),
                        "platform": platform,
                        "contact": "",
                        "status": "待投递",
                        "jd_text": jd_text.strip(),
                        "jd_analysis": result,
                        "notes": notes.strip(),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "history": [{"status": "待投递", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}],
                    }
                    records = load_history()
                    records.append(record)
                    save_history(records)
                    st.success(f"已保存：{company} - {position}")
                    st.rerun()


# ═══════════════════════════════════════
# 模块3：匹配度评估
# ═══════════════════════════════════════

MATCH_PROMPT = """你是资深职业规划师。根据候选人的经验库和岗位JD分析结果，进行多维匹配度评估。

## 评估规则
1. 每个维度满分100分，基于JD要求和经验库事实严格打分
2. 差距分析必须具体，指出"缺什么"而非"不够好"
3. 面试重点基于匹配薄弱环节提出
4. 不得编造经验库中没有的内容

## 输出JSON格式
{
  "overall_score": 加权总分(整数),
  "dimensions": {
    "技能匹配": {"score": 0-100, "matched": ["匹配项"], "missing": ["缺失项"], "note": "分析"},
    "经验匹配": {"score": 0-100, "matched": ["匹配项"], "missing": ["缺失项"], "note": "分析"},
    "学历匹配": {"score": 0-100, "matched": ["匹配项"], "missing": ["缺失项"], "note": "分析"},
    "方向匹配": {"score": 0-100, "matched": ["匹配项"], "missing": ["缺失项"], "note": "分析"},
    "软性匹配": {"score": 0-100, "matched": ["匹配项"], "missing": ["缺失项"], "note": "分析"}
  },
  "gap_analysis": "差距总结（50字内）",
  "interview_focus": ["面试应重点准备的3-5个方向"],
  "improvement_suggestions": ["针对差距的1-3条提升建议"],
  "recommended_direction": "推荐用的简历方向",
  "recommended_experience_ids": ["从经验库中选择最相关的经验ID"]
}"""


def score_match(jd_analysis, experience_lib):
    """LLM多维匹配度评估"""
    if not HAS_ANTHROPIC:
        return {"error": "需要 anthropic SDK"}

    # 提取经验库摘要（只传结构化数据，不传全文节省token）
    exp_summary = {
        "skills": [s for s in experience_lib.get("skills", []) if s.get("level") in ["expert", "advanced"]],
        "experiences": [{
            "id": e["id"],
            "summary": e["summary"],
            "category": e["category"],
            "keywords": list(set(kw for b in e["bullets"] for kw in b.get("keywords", []))),
        } for e in experience_lib.get("experiences", [])],
        "education": experience_lib.get("education", []),
        "certifications": experience_lib.get("certifications", []),
        "projects": [{"name": p["name"], "description": p["description"]} for p in experience_lib.get("personal_projects", [])],
    }

    try:
        client = get_anthropic_client()
        if not client:
            return {"error": "API Key 未配置。请在 Streamlit Cloud Secrets 或 .env 中设置 ANTHROPIC_AUTH_TOKEN"}
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=2000,
            temperature=0.1,
            system="只输出合法JSON，不添加解释。严格基于事实打分，不得编造。",
            messages=[{
                "role": "user",
                "content": f"{MATCH_PROMPT}\n\n---JD分析---\n{json.dumps(jd_analysis, ensure_ascii=False)}\n\n---经验库摘要---\n{json.dumps(exp_summary, ensure_ascii=False)}"
            }],
        )
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip()
                break
        if not raw:
            raw = str(resp.content)

        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"error": "JSON解析失败", "_raw": raw[:500]}
    except Exception as e:
        return {"error": f"匹配评估失败: {str(e)}"}


def render_match_report(match_result, jd_analysis):
    """渲染匹配报告"""
    if "error" in match_result:
        st.error(match_result["error"])
        return

    overall = match_result.get("overall_score", 0)
    color = "#66BB6A" if overall >= 80 else "#FFA726" if overall >= 60 else "#FF4444"

    st.markdown(f"## 综合匹配度：<span style='color:{color}'>{overall}/100</span>", unsafe_allow_html=True)

    # 维度雷达数据
    dims = match_result.get("dimensions", {})
    if dims:
        categories = list(dims.keys())
        values = [dims[c]["score"] for c in categories]

        col_r1, col_r2 = st.columns([1, 2])
        with col_r1:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill="toself", name="匹配度"))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=300, margin=dict(l=30, r=30, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col_r2:
            for dim_name, dim_data in dims.items():
                score = dim_data.get("score", 0)
                bar_color = "#66BB6A" if score >= 80 else "#FFA726" if score >= 60 else "#FF4444"
                st.markdown(f"**{dim_name}**：{score}/100")
                st.progress(score / 100)
                if dim_data.get("matched"):
                    st.caption(f"✅ 匹配：{'、'.join(dim_data['matched'][:5])}")
                if dim_data.get("missing"):
                    st.caption(f"⚠️ 缺失：{'、'.join(dim_data['missing'][:5])}")
                if dim_data.get("note"):
                    st.caption(f"💬 {dim_data['note']}")

    # 差距分析
    if match_result.get("gap_analysis"):
        st.warning(f"📊 差距分析：{match_result['gap_analysis']}")

    # 面试重点
    if match_result.get("interview_focus"):
        st.markdown("### 🎯 面试准备重点")
        for item in match_result["interview_focus"]:
            st.markdown(f"- {item}")

    # 提升建议
    if match_result.get("improvement_suggestions"):
        st.markdown("### 📈 提升建议")
        for item in match_result["improvement_suggestions"]:
            st.markdown(f"- 💡 {item}")


# ═══════════════════════════════════════
# 模块4：简历定制生成
# ═══════════════════════════════════════

RESUME_TEMPLATES = {
    "AI产品运营": """# 牟思雨 — 个人简历

**求职方向**：AI产品运营 / 大模型应用运营 | **工作年限**：4年 | **期望薪资**：18k-26k（可议）
**电话**：18504284554 | **邮箱**：msy1994dut@163.com | **所在地**：上海/北京/沈阳
**硕士**：东北财经大学 · 工程管理（数据挖掘与商务智能） | **本科**：大连理工大学

---

## 个人优势

{summary}

---

## 核心能力

{skills}

---

## 工作经历

{experiences}

---

## 个人作品（Vibe Coding 实现 · AI应用方向）

{projects}

---

## 教育经历

| 时间 | 学校 | 学历 | 专业 | 亮点 |
|------|------|------|------|------|
| 2020.09–2022.06 | 东北财经大学 | 硕士 | 工程管理（数据挖掘与商务智能） | 省优秀毕业生 / 一等学业奖学金 |
| 2013.09–2017.06 | 大连理工大学 | 本科 | 金属材料与工程 | 985院校 |

**证书**：PMP · IPMP-D · 携程6-Sigma绿带 · AI项目管理专项培训
""",

    "服务体验运营": """# 牟思雨 — 个人简历

**求职方向**：服务体验运营 / 平台治理运营 | **工作年限**：4年 | **期望薪资**：18k-25k
**电话**：18504284554 | **邮箱**：msy1994dut@163.com | **所在地**：上海/北京
**硕士**：东北财经大学 · 工程管理（数据挖掘与商务智能） | **本科**：大连理工大学

---

## 个人优势

{summary}

---

## 核心能力

{skills}

---

## 工作经历

{experiences}

---

## 个人作品（Vibe Coding 实现 · 服务治理方向）

{projects}

---

## 教育经历

| 时间 | 学校 | 学历 | 专业 | 亮点 |
|------|------|------|------|------|
| 2020.09–2022.06 | 东北财经大学 | 硕士 | 工程管理（数据挖掘与商务智能） | 省优秀毕业生 / 一等学业奖学金 |
| 2013.09–2017.06 | 大连理工大学 | 本科 | 金属材料与工程 | 985院校 |

**证书**：PMP · IPMP-D · 携程6-Sigma绿带 · AI项目管理专项培训
""",

    "AI项目管理": """# 牟思雨 — 个人简历

**求职方向**：AI项目管理 / 技术项目管理（AI方向） | **工作年限**：4年 | **期望薪资**：18k-24k（可议）
**电话**：18504284554 | **邮箱**：msy1994dut@163.com | **所在地**：上海
**硕士**：东北财经大学 · 工程管理（数据挖掘与商务智能） | **本科**：大连理工大学

---

## 个人优势

{summary}

---

## 核心能力

{skills}

---

## 工作经历

{experiences}

---

## 个人作品（Vibe Coding 实现 · 项目管理能力佐证）

{projects}

---

## 教育经历

| 时间 | 学校 | 学历 | 专业 | 亮点 |
|------|------|------|------|------|
| 2020.09–2022.06 | 东北财经大学 | 硕士 | 工程管理（数据挖掘与商务智能） | 省优秀毕业生 / 一等学业奖学金 |
| 2013.09–2017.06 | 大连理工大学 | 本科 | 金属材料与工程 | 985院校 |

**证书**：PMP · IPMP-D · 携程6-Sigma绿带 · AI项目管理专项培训
""",
}


def generate_customized_resume(direction, match_result, experience_lib, jd_analysis):
    """基于经验库生成定制简历（规则驱动，不编造内容）"""
    exp_lib_exp = {e["id"]: e for e in experience_lib.get("experiences", [])}

    # 获取推荐的经验ID
    recommended_ids = match_result.get("recommended_experience_ids", [])
    if not recommended_ids:
        # 回退：用方向预设的经验
        dir_config = experience_lib.get("resume_directions", {}).get(direction, {})
        recommended_ids = dir_config.get("primary_experiences", [])

    # 筛选经验条目
    selected_exps = []
    for eid in recommended_ids:
        if eid in exp_lib_exp:
            selected_exps.append(exp_lib_exp[eid])

    # 生成经历文本
    exp_text_parts = []
    current_company = None
    for exp in selected_exps:
        if exp["company"] != current_company:
            if current_company:
                exp_text_parts.append("\n---\n")
            current_company = exp["company"]
            exp_text_parts.append(f"### {exp['company']} | {exp['role']} | {exp['time']}\n")
            exp_text_parts.append(f"{exp['summary']}。\n")
        for bullet in exp["bullets"]:
            exp_text_parts.append(f"- {bullet['text']}\n")

    experiences_text = "".join(exp_text_parts)

    # 生成技能标签
    dir_config = experience_lib.get("resume_directions", {}).get(direction, {})
    emphasize = dir_config.get("emphasize_skills", [])
    skill_tags = [f"`{s}`" for s in emphasize[:10]]
    skills_text = " ".join(skill_tags)

    # 生成个人优势
    summary = dir_config.get("summary_template", "4年AI产品落地与服务体验治理经验。")
    # 从匹配结果中补充JD关键词
    if jd_analysis.get("hard_skills"):
        summary += f" 匹配岗位核心要求：{'、'.join(jd_analysis['hard_skills'][:3])}。"

    # 生成作品集
    projects = experience_lib.get("personal_projects", [])
    projects_text = "\n".join([
        f"- **{p['name']}** — {p['description']}\n  {p['url']}"
        for p in projects
    ])

    # 选模板
    template = RESUME_TEMPLATES.get(direction, RESUME_TEMPLATES["AI产品运营"])

    resume_md = template.format(
        summary=summary,
        skills=skills_text,
        experiences=experiences_text,
        projects=projects_text,
    )
    return resume_md


def render_resume_customizer():
    """简历定制页面"""
    st.subheader("📝 简历定制生成")

    # 第一步：选择JD来源
    records = load_history()
    jd_records = [r for r in records if r.get("jd_text") and len(r.get("jd_text", "")) > 20]

    if not jd_records:
        st.info("📭 暂无带JD的投递记录。请先在「JD分析」或「新增投递」中录入JD。")
        return

    # 选择要定制的岗位
    jd_options = {f"{r['company']} - {r['position']} ({r.get('direction', '未知')})": r for r in jd_records}
    selected_label = st.selectbox("选择岗位", list(jd_options.keys()))
    selected_record = jd_options[selected_label]

    # 第二步：获取或生成JD分析
    jd_analysis = selected_record.get("jd_analysis")
    if not jd_analysis or "error" in jd_analysis:
        st.warning("该岗位尚未进行JD分析，正在自动分析...")
        with st.spinner("分析中..."):
            jd_analysis = parse_jd_with_llm(selected_record.get("jd_text", ""))
            if "error" not in jd_analysis:
                # 更新记录
                selected_record["jd_analysis"] = jd_analysis
                save_history(records)
        if "error" in jd_analysis:
            st.error("JD分析失败，请手动到「JD分析」页面重新分析")
            return

    direction = jd_analysis.get("matched_direction", "AI产品运营")
    if direction not in DIRECTIONS:
        direction = "通用"

    st.markdown(f"**推荐方向**：{direction} | **岗位**：{selected_record['company']} - {selected_record['position']}")

    # 第三步：生成匹配报告 + 定制简历
    if st.button("🚀 生成匹配报告与定制简历", type="primary", use_container_width=True):
        exp_lib = load_experience_lib()

        with st.spinner("正在多维度匹配评估..."):
            match_result = score_match(jd_analysis, exp_lib)

        if "error" in match_result:
            st.error(match_result["error"])
            return

        st.session_state["match_result"] = match_result
        st.session_state["jd_analysis"] = jd_analysis
        st.session_state["selected_record"] = selected_record
        st.session_state["direction"] = direction
        st.rerun()

    # 展示结果
    if st.session_state.get("match_result"):
        match_result = st.session_state["match_result"]
        jd_analysis = st.session_state["jd_analysis"]
        direction = st.session_state["direction"]

        st.divider()
        st.markdown("## 📊 匹配度评估报告")
        render_match_report(match_result, jd_analysis)

        st.divider()
        st.markdown("## 📝 定制简历预览")

        exp_lib = load_experience_lib()
        resume_md = generate_customized_resume(direction, match_result, exp_lib, jd_analysis)

        # 编辑区
        edited_resume = st.text_area("简历Markdown（可直接编辑）", value=resume_md, height=500, key="edited_resume")
        st.session_state["edited_resume"] = edited_resume

        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            if st.button("🔄 重新生成", use_container_width=True):
                st.session_state["match_result"] = None
                st.rerun()
        with col_e2:
            st.download_button(
                "⬇️ 下载 MD",
                data=edited_resume,
                file_name=f"简历_{direction}_{selected_record['company']}_{selected_record['position']}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_e3:
            if st.button("📋 复制到剪贴板", use_container_width=True):
                st.info("请选中上方文本框内容 Ctrl+C 复制")

        # 更新投递记录
        st.divider()
        if st.button("✅ 确认并关联到投递记录", type="primary", use_container_width=True):
            selected_record["customized_resume"] = edited_resume
            selected_record["match_result"] = match_result
            selected_record["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_history(records)
            st.session_state["match_result"] = None
            st.success("已保存！简历已关联到该投递记录。")
            st.rerun()


# ═══════════════════════════════════════
# 模块6：JD在线搜索 + 定点监控
# ═══════════════════════════════════════

# JD缓存使用共享路径（不需要按用户隔离）
MONITORED_COMPANIES = [
    {"name": "美团", "career_url": "https://zhaopin.meituan.com/", "keywords": ["服务运营", "AI", "大模型", "治理", "体验", "流程管理"]},
    {"name": "百度", "career_url": "https://talent.baidu.com/", "keywords": ["AI产品运营", "大模型平台", "智能客服", "产品运营"]},
    {"name": "得物", "career_url": "https://poizon.jobs.feishu.cn/", "keywords": ["服务体验", "AI质检", "智能解决方案", "运营"]},
    {"name": "京东", "career_url": "https://zhaopin.jd.com/", "keywords": ["体验治理", "服务运营", "用户体验", "策略运营"]},
    {"name": "字节跳动", "career_url": "https://jobs.bytedance.com/", "keywords": ["AI产品运营", "智能助手", "客服", "体验"]},
    {"name": "滴滴", "career_url": "https://talent.didiglobal.com/", "keywords": ["平台治理", "规则运营", "体验治理", "服务运营"]},
    {"name": "小红书", "career_url": "https://job.xiaohongshu.com/", "keywords": ["用户体验", "服务策略", "社区治理"]},
    {"name": "饿了么", "career_url": "https://www.ele.me/", "keywords": ["服务流程", "体验运营", "规则"]},
    {"name": "拼多多", "career_url": "https://www.pinduoduo.com/", "keywords": ["平台治理", "服务运营", "规则"]},
    {"name": "携程", "career_url": "https://www.ctrip.com/", "keywords": ["服务运营", "体验治理", "AI", "项目管理"]},
]

SEARCH_CITIES = ["上海", "北京", "沈阳", "杭州", "深圳", "广州", "成都"]


def load_jd_cache():
    jd_cache_file = os.path.join(get_profile_path(get_active_profile()), "jd_cache.json")
    if not os.path.exists(jd_cache_file):
        return []
    with open(jd_cache_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jd_cache(entries):
    jd_cache_file = os.path.join(get_profile_path(get_active_profile()), "jd_cache.json")
    with open(jd_cache_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def search_jobs_web(keywords, city, direction, limit=20):
    """通过Web搜索查找岗位"""
    query = f"{city} {direction} {' '.join(keywords)} 招聘 2026"
    results = []

    try:
        # 使用内置WebSearch
        import urllib.request
        import urllib.parse
        # 这里使用简单的搜索URL构建
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={limit}"

        # 实际环境中需要用更robust的方式
        # MVP阶段：返回搜索指引
        results.append({
            "title": f"搜索: {query}",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
            "snippet": f"请在浏览器中打开搜索，或使用工具内置搜索",
            "source": "web_search",
            "company": "",
            "position": "",
            "city": city,
            "direction": direction,
            "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    except Exception as e:
        pass

    return results


def scrape_company_career_page(company_info):
    """抓取单个公司招聘页（占位——实际需要浏览器自动化或API）"""
    return {
        "company": company_info["name"],
        "url": company_info["career_url"],
        "status": "pending",
        "note": "需要手动打开招聘页搜索关键词",
        "keywords": company_info["keywords"],
    }


def render_jd_search():
    """JD搜索与缓存管理页面"""
    st.subheader("🌐 JD 搜索与监控")

    tab_s, tab_m, tab_c = st.tabs(["🔍 搜索岗位", "📡 定点监控", "📦 缓存管理"])

    # ── Tab1: 搜索 ──
    with tab_s:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            search_kw = st.text_input("搜索关键词", placeholder="如：大模型 智能客服 Agent")
        with col_s2:
            search_city = st.selectbox("城市", SEARCH_CITIES, index=0, key="search_city")
        with col_s3:
            search_dir = st.selectbox("方向", DIRECTIONS, key="search_dir")

        if st.button("🔍 搜索", type="primary", use_container_width=True, disabled=not search_kw):
            with st.spinner(f"正在搜索 {search_city} {search_dir} 相关岗位..."):
                kw_list = [k.strip() for k in search_kw.split() if k.strip()]
                results = search_jobs_web(kw_list, search_city, search_dir)

            if results:
                st.success(f"找到 {len(results)} 条结果")

            # 引导手动搜索
            st.markdown("### 🔗 快速搜索链接（点击在新标签页打开）")
            for company in MONITORED_COMPANIES[:8]:
                query = f"{company['name']} {search_kw} {search_city} 招聘"
                encoded = query.replace(" ", "+")
                # Baidu search
                baidu_url = f"https://www.baidu.com/s?wd={encoded}"
                st.markdown(f"- [{company['name']} — {search_kw} {search_city}]({baidu_url})")

            st.divider()
            st.caption("💡 点击链接在浏览器中搜索 → 找到目标岗位 → 复制JD → 粘贴到「JD分析」页面")

    # ── Tab2: 定点监控 ──
    with tab_m:
        st.markdown("### 📡 目标公司监控列表")
        st.caption("配置你关注的公司和对应的搜索关键词，定期检查是否有新岗位发布")

        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            st.dataframe(
                pd.DataFrame([{
                    "公司": c["name"],
                    "招聘页": c["career_url"],
                    "关注关键词": "、".join(c["keywords"][:4]),
                } for c in MONITORED_COMPANIES]),
                use_container_width=True,
                hide_index=True,
            )
        with col_m2:
            st.metric("监控公司数", len(MONITORED_COMPANIES))
            st.caption("💡 点击招聘页链接，在公司官网搜索关键词筛选岗位")

        st.divider()
        st.markdown("### ⏰ 下次检查提醒")
        for company in MONITORED_COMPANIES[:5]:
            with st.expander(f"🏢 {company['name']} — 搜索关键词：{'、'.join(company['keywords'][:3])}"):
                st.markdown(f"**招聘页**：{company['career_url']}")
                st.markdown(f"**搜索建议**：{'、'.join(company['keywords'])}")
                st.text_input(f"上次检查时间 ({company['name']})", "尚未检查", key=f"last_check_{company['name']}", disabled=True)

        if st.button("✅ 标记全部已检查", use_container_width=True):
            st.success("已更新检查时间")
            st.caption("建议每2-3天检查一次各公司招聘页")

    # ── Tab3: 缓存管理 ──
    with tab_c:
        st.markdown("### 📦 已缓存岗位")

        cached = load_jd_cache()
        if not cached:
            st.info("📭 缓存为空。使用搜索功能找到的岗位可以保存到这里。")

            # 手动添加缓存
            st.divider()
            st.markdown("### ➕ 手动添加岗位到缓存")
            with st.form("add_to_cache"):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    cache_company = st.text_input("公司名称")
                    cache_position = st.text_input("岗位名称")
                with col_a2:
                    cache_city = st.text_input("城市", value="上海")
                    cache_url = st.text_input("招聘链接")
                cache_jd = st.text_area("岗位JD", height=100)
                if st.form_submit_button("保存到缓存"):
                    entry = {
                        "id": str(uuid.uuid4())[:8],
                        "company": cache_company.strip(),
                        "position": cache_position.strip(),
                        "city": cache_city.strip(),
                        "url": cache_url.strip(),
                        "jd_text": cache_jd.strip(),
                        "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "source": "manual",
                    }
                    cached.append(entry)
                    save_jd_cache(cached)
                    st.success(f"已缓存：{cache_company} - {cache_position}")
                    st.rerun()
        else:
            for i, entry in enumerate(cached):
                with st.expander(f"📌 {entry.get('company', '?')} — {entry.get('position', '?')} ({entry.get('city', '')})"):
                    st.caption(f"缓存时间：{entry.get('cached_at', '')} | 来源：{entry.get('source', '')}")
                    if entry.get("url"):
                        st.markdown(f"🔗 {entry['url']}")
                    if entry.get("jd_text"):
                        st.text(entry["jd_text"][:300])

                    col_b1, col_b2, col_b3 = st.columns(3)
                    with col_b1:
                        if st.button("🔍 分析此JD", key=f"analyze_{i}", use_container_width=True):
                            st.session_state["jd_to_analyze"] = entry.get("jd_text", "")
                            st.rerun()
                    with col_b2:
                        if st.button("➕ 创建投递记录", key=f"create_app_{i}", use_container_width=True):
                            record = {
                                "id": str(uuid.uuid4())[:8],
                                "company": entry.get("company", ""),
                                "position": entry.get("position", ""),
                                "city": entry.get("city", ""),
                                "direction": "通用",
                                "salary": "",
                                "platform": "其他",
                                "contact": "",
                                "status": "待投递",
                                "jd_text": entry.get("jd_text", ""),
                                "notes": "",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "history": [{"status": "待投递", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}],
                            }
                            records = load_history()
                            records.append(record)
                            save_history(records)
                            st.success("已创建投递记录")
                            st.rerun()
                    with col_b3:
                        if st.button("🗑️ 删除", key=f"del_cache_{i}", use_container_width=True):
                            cached.pop(i)
                            save_jd_cache(cached)
                            st.rerun()

            if st.button("🗑️ 清空全部缓存", use_container_width=True):
                save_jd_cache([])
                st.rerun()


# ═══════════════════════════════════════
# V1.5 新增功能：幻觉检测+关键词覆盖+Gap包装+完整度+简历解析+模板
# ═══════════════════════════════════════

def check_hallucination(resume_text, exp_lib):
    """检测AI生成简历中的事实错误"""
    issues = []

    # 收集经历库中所有数值（用于交叉验证）
    known_numbers = {}  # number -> source
    for exp in exp_lib.get("experiences", []):
        for bullet in exp["bullets"]:
            nums = re.findall(r'[\d.]+%?[亿万千百]?\w*', bullet["text"])
            for n in nums:
                known_numbers[n] = f"{exp['company']}-{bullet['text'][:50]}"

    # 收集经历库中的所有百分比
    known_pcts = set()
    for exp in exp_lib.get("experiences", []):
        for bullet in exp["bullets"]:
            for pct in re.findall(r'(\d+)%', bullet["text"]):
                known_pcts.add(pct)

    # 收集经历库中的数量词
    known_quantities = set()
    for exp in exp_lib.get("experiences", []):
        for bullet in exp["bullets"]:
            for q in re.findall(r'(\d+(?:\.\d+)?[万亿千]?(?:人次|单|条|个))', bullet["text"]):
                known_quantities.add(q)

    # 检查简历中的百分比是否在经历库范围内
    resume_pcts = re.findall(r'(\d+)%', resume_text)
    for pct in resume_pcts:
        if pct not in known_pcts:
            # 检查是否与已知百分比接近（±5以内视为同一数据的不同表述）
            found_close = any(abs(int(pct) - int(kp)) <= 5 for kp in known_pcts)
            if not found_close:
                issues.append({
                    "type": "百分比数据",
                    "value": f"{pct}%",
                    "detail": f"简历中出现 {pct}%，但经历库中无此数据。请核实该数字是否准确"
                })

    # 检查数量词
    resume_quantities = re.findall(r'(\d+(?:\.\d+)?[万亿千]?(?:人次|单|条|个))', resume_text)
    for qty in resume_quantities:
        if qty not in known_quantities:
            # 提取纯数字比较
            num = re.findall(r'(\d+)', qty)
            if num:
                found = any(num[0] in kq for kq in known_quantities)
                if not found:
                    issues.append({
                        "type": "数量数据",
                        "value": qty,
                        "detail": f"简历中出现 {qty}，经历库未找到。请核实"
                    })

    # 检查关键指标（3000、1580、24、34、14、10、20 等简历中反复出现的数字）
    key_metrics = {}
    for exp in exp_lib.get("experiences", []):
        for bullet in exp["bullets"]:
            for m in re.findall(r'(\d+(?:\.\d+)?)\s*(人次|单|条|个|万|千|%)', bullet["text"]):
                key_metrics[m[0]] = bullet["text"][:80]

    resume_metrics = re.findall(r'(\d+(?:\.\d+)?)\s*(人次|单|条|个|万)', resume_text)
    for num, unit in resume_metrics:
        if num not in key_metrics:
            # 尝试模糊匹配（±10%）
            found = False
            for km in key_metrics:
                try:
                    if abs(float(num) - float(km)) / max(float(km), 1) < 0.1:
                        found = True
                        break
                except:
                    pass
            if not found and float(num) > 100:
                issues.append({
                    "type": "关键指标",
                    "value": f"{num}{unit}",
                    "detail": f"简历中出现 {num}{unit}，经历库中无匹配数据"
                })

    return issues[:5]  # 最多返回5条


def check_keyword_coverage(resume_text, jd_analysis):
    """检查JD硬技能关键词在简历中的覆盖率"""
    hard_skills = jd_analysis.get("hard_skills", [])
    if not hard_skills:
        return {"coverage": 100, "covered": [], "missing": []}

    covered = []
    missing = []
    for skill in hard_skills:
        # 模糊匹配（处理中英文、缩写差异）
        skill_lower = skill.lower()
        text_lower = resume_text.lower()
        if skill_lower in text_lower or any(part in text_lower for part in skill_lower.split()):
            covered.append(skill)
        else:
            missing.append(skill)

    coverage = round(len(covered) / len(hard_skills) * 100) if hard_skills else 100
    return {"coverage": coverage, "covered": covered, "missing": missing}


GAP_NARRATIVE_PROMPT = """你是职业规划师。为候选人的职业空窗期生成得体、正面的叙事解释。

## 规则
1. 如实说明空窗原因，不编造经历
2. 将空窗期包装为"职业能力建设期"或"主动选择期"
3. 叙事要积极正面，展现成熟决策能力
4. 字数控制在80字以内

## 空窗期信息
{gap_info}

## 候选人背景
{background}

请输出纯文本叙事（不要JSON），直接给面试话术："""


def generate_gap_narrative(exp_lib):
    """为Gap期生成叙事包装"""
    gaps = []

    # 识别空窗期
    # Gap 1: 2018.04 - 2020.08 (考研备考)
    gaps.append({
        "period": "2018.05–2020.08",
        "duration": "约2年",
        "reason": "全职备考硕士研究生，同期完成PMP和IPMP-D认证",
        "packaging": "职业能力建设期：此期间全职备考管理科学与工程硕士，并系统完成PMP与IPMP-D项目管理认证学习。这段经历为后续的数据驱动项目管理奠定了理论基础，硕士研究方向（数据挖掘与商务智能）直接支撑了工作中AI产品落地的数据思维。",
    })

    # Gap 2: 2026.02 至今 (拼多多离职后)
    gaps.append({
        "period": "2026.03–至今",
        "duration": "约3个月",
        "reason": "离开拼多多后，系统性梳理过去4年的服务治理与AI落地经验，同时独立开发3个AI工具原型（Vibe Coding），持续学习大模型/Agent前沿技术",
        "packaging": "经验沉淀与技能升级期：离开拼多多后，我将过去4年的服务治理与AI落地经验进行了系统性复盘和方法论沉淀。同期通过Vibe Coding独立开发了3个可部署上线的AI工具原型（客诉智能分类、VOC风险预警、AI对话质量评估），持续跟进大模型、Agent、Prompt工程等前沿方向。这段时间不是'空窗'，而是将隐性经验转化为显性能力的关键期。",
    })

    return gaps


def score_experience_completeness(exp_lib):
    """经历完整度评分 0-100"""
    score = 0
    suggestions = []
    max_score = 100

    # 基本信息 (10分)
    basic = exp_lib.get("basic", {})
    if basic.get("name") and basic.get("phone") and basic.get("email"):
        score += 10
    else:
        suggestions.append("补充基本信息（姓名、手机、邮箱）")

    # 教育经历 (15分)
    edu = exp_lib.get("education", [])
    if len(edu) >= 2:
        score += 15
    elif len(edu) == 1:
        score += 8
        suggestions.append("补充本科教育经历")
    else:
        suggestions.append("添加教育经历")

    # 工作经历 (35分)
    exps = exp_lib.get("experiences", [])
    if len(exps) >= 3:
        score += 35
    elif len(exps) >= 2:
        score += 20
        suggestions.append("补充更多工作经历细节")
    else:
        score += 10
        suggestions.append("工作经历不足，会影响匹配准确性")

    # 每段经历的质量（有量化数据+10分）
    has_metrics = sum(1 for e in exps for b in e.get("bullets", []) if any(c.isdigit() for c in b["text"]))
    if has_metrics >= 5:
        score += 10
    else:
        suggestions.append(f"经历中量化成果不足（目前{has_metrics}处），建议补充数据点")

    # 技能 (15分)
    skills = exp_lib.get("skills", [])
    if len(skills) >= 15:
        score += 15
    elif len(skills) >= 8:
        score += 10
        suggestions.append("补充更多技能标签")
    else:
        score += 5
        suggestions.append("技能标签过少")

    # 证书 (5分)
    certs = exp_lib.get("certifications", [])
    if len(certs) >= 2:
        score += 5
    else:
        suggestions.append("添加专业证书")

    # 个人作品 (5分)
    projects = exp_lib.get("personal_projects", [])
    if len(projects) >= 2:
        score += 5
    elif len(projects) == 1:
        score += 3

    # 面试素材 (5分)
    entries = exp_lib.get("interview_entries", [])
    if len(entries) >= 3:
        score += 5
    elif len(entries) >= 1:
        score += 3
        suggestions.append("补充更多面试素材（建议≥3条）")
    else:
        suggestions.append("补充面试素材库")

    return {
        "score": min(score, 100),
        "max_score": max_score,
        "suggestions": suggestions,
        "level": "优秀" if score >= 80 else "良好" if score >= 60 else "待完善" if score >= 40 else "需重点补充",
    }


def parse_resume_text_with_llm(resume_text):
    """LLM解析简历文本为结构化经历"""
    if not HAS_ANTHROPIC or not resume_text or len(resume_text) < 50:
        return {"error": "文本太短或SDK未安装"}

    prompt = """你是简历解析专家。将以下简历文本拆解为结构化JSON，严格基于原文，不编造任何信息。

输出格式：
{
  "basic": {"name": "", "phone": "", "email": ""},
  "education": [{"time": "", "school": "", "degree": "", "major": "", "highlights": []}],
  "skills": [{"name": "", "category": "AI/domain/methodology/tech", "level": "expert/advanced/intermediate"}],
  "experiences": [{"company": "", "role": "", "time": "", "summary": "", "bullets": [{"text": "", "keywords": []}]}],
  "certifications": [],
  "parsing_notes": "解析说明"
}"""

    try:
        client = get_anthropic_client()
        if not client:
            return {"error": "API Key 未配置。请在 Streamlit Cloud Secrets 或 .env 中设置 ANTHROPIC_AUTH_TOKEN"}
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=3000, temperature=0.1,
            system="只输出合法JSON，严格基于简历原文。",
            messages=[{"role": "user", "content": f"{prompt}\n\n---简历文本---\n{resume_text[:4000]}"}],
        )
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip(); break
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"error": "解析失败", "_raw": raw[:300]}
    except Exception as e:
        return {"error": str(e)}


# 新增模板：现代风格
RESUME_TEMPLATE_MODERN = """# 牟思雨

**{direction_label}** | 4年经验 | 18k-26k | 18504284554 | msy1994dut@163.com
📍 上海/北京/沈阳 · 🎓 东北财经大学硕士 · 大连理工大学本科

---

## 专业概要

{summary}

## 核心能力

{skills}

## 职业经历

{experiences}

## 个人作品（Vibe Coding）

{projects}

## 教育

| 时间 | 学校 | 学位 | 专业 |
|------|------|------|------|
| 2020.09–2022.06 | 东北财经大学 | 硕士 | 工程管理（数据挖掘与商务智能） |
| 2013.09–2017.06 | 大连理工大学 | 本科 | 金属材料与工程 |

**资质**：PMP · IPMP-D · 6σ绿带 · AI项目管理
"""

# 新增模板：简约风格
RESUME_TEMPLATE_MINIMAL = """牟思雨
{direction_label} · 4年 · 18k-26k
msy1994dut@163.com · 18504284554

{summary}

{skills}

{experiences}

{projects}

教育：东北财经大学 硕士(工程管理) · 大连理工大学 本科(金属材料) · PMP/IPMP-D/6σ绿带
"""

RESUME_TEMPLATE_STYLES = {
    "标准专业版": "standard",
    "现代风格": "modern",
    "简约风格": "minimal",
}


# ═══════════════════════════════════════
# 模块7：个人经历库
# ═══════════════════════════════════════

CAREER_ANALYSIS_PROMPT = """你是资深职业生涯规划师。根据候选人的完整经历库，进行深度分析。

## 分析要求
1. 严格基于经历库中的事实，不得编造
2. 识别候选人的核心竞争力和差异化优势
3. 指出职业发展中可优化的方向
4. 推荐3个最适合的求职方向，按匹配度排序

## 输出JSON格式
{
  "core_strengths": ["核心竞争力1(附经历佐证)", "核心竞争力2"],
  "differentiators": ["差异化优势1", "差异化优势2"],
  "career_directions": [
    {"direction": "方向名", "match_score": 0-100, "reason": "理由", "suitable_roles": ["岗位1", "岗位2"]}
  ],
  "skill_gaps": {"方向名": ["缺失技能1", "缺失技能2"]},
  "learning_suggestions": [
    {"direction": "方向名", "topic": "学习主题", "resource": "推荐资源", "priority": "高/中/低"}
  ],
  "project_suggestions": [
    {"direction": "方向名", "project": "项目建议", "goal": "项目目标", "tech_stack": "建议技术栈"}
  ],
  "interview_highlights": ["面试中应重点展示的经历1", "经历2"],
  "career_narrative": "职业故事线（100字内）"
}"""


def analyze_career(exp_lib):
    """LLM职业分析"""
    if not HAS_ANTHROPIC:
        return {"error": "需要 anthropic SDK"}

    # 提取关键信息
    analysis_input = {
        "skills": exp_lib.get("skills", []),
        "experiences": [{"company": e["company"], "role": e["role"], "summary": e["summary"],
                         "category": e["category"]} for e in exp_lib.get("experiences", [])],
        "education": exp_lib.get("education", []),
        "certifications": exp_lib.get("certifications", []),
        "projects": [{"name": p["name"], "description": p["description"], "tech": p["tech"]}
                     for p in exp_lib.get("personal_projects", [])],
    }

    try:
        client = get_anthropic_client()
        if not client:
            return {"error": "API Key 未配置。请在 Streamlit Cloud Secrets 或 .env 中设置 ANTHROPIC_AUTH_TOKEN"}
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=3000, temperature=0.3,
            system="你是资深职业生涯规划师。只输出合法JSON，严格基于事实分析。",
            messages=[{"role": "user", "content": f"{CAREER_ANALYSIS_PROMPT}\n\n---经历库---\n{json.dumps(analysis_input, ensure_ascii=False)}"}],
        )
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip(); break
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"error": "JSON解析失败", "_raw": raw[:500]}
    except Exception as e:
        return {"error": f"分析失败: {str(e)}"}


def render_experience_library():
    """个人经历库页面"""
    st.subheader("📚 个人经历库")

    exp_lib = load_experience_lib()

    # 完整度评分
    completeness = score_experience_completeness(exp_lib)
    col_comp1, col_comp2 = st.columns([1, 4])
    with col_comp1:
        color = "#66BB6A" if completeness["score"] >= 80 else "#FFA726" if completeness["score"] >= 60 else "#FF4444"
        st.markdown(f"### 完整度<br><span style='color:{color};font-size:24pt'>{completeness['score']}/100</span>", unsafe_allow_html=True)
        st.caption(completeness["level"])
    with col_comp2:
        if completeness["suggestions"]:
            st.markdown("**改进建议**：")
            for s in completeness["suggestions"]:
                st.markdown(f"- 💡 {s}")

    # Gap包装
    gaps = generate_gap_narrative(exp_lib)
    if gaps:
        with st.expander("📌 职业空窗期叙事包装（面试必备）", expanded=completeness["score"] < 80):
            for g in gaps:
                st.markdown(f"**{g['period']}**（{g['duration']}）")
                st.info(g["packaging"])
                st.caption(f"原由：{g['reason']}")

    st.divider()

    tab_e1, tab_e2, tab_e3, tab_e4, tab_e5 = st.tabs(["📋 经历管理", "📊 AI职业分析", "🎯 学习与项目建议", "📝 自动生成简历", "📤 简历上传解析"])

    # ── Tab1: 经历管理 ──
    with tab_e1:
        st.markdown("### 技能库")
        skills = exp_lib.get("skills", [])
        skill_data = pd.DataFrame([{
            "技能": s["name"], "类别": s["category"], "水平": s["level"]
        } for s in skills])
        st.dataframe(skill_data, use_container_width=True, hide_index=True)

        # 去重分析
        if st.button("🔍 智能去重分析", use_container_width=True):
            with st.spinner("正在分析经历库中的重复内容..."):
                dedup_result = analyze_duplicates(exp_lib)
                st.session_state["dedup_result"] = dedup_result
                st.rerun()

        if st.session_state.get("dedup_result"):
            result = st.session_state["dedup_result"]
            if result.get("duplicate_groups"):
                st.warning(f"发现 {len(result['duplicate_groups'])} 组相似内容")
                for i, group in enumerate(result["duplicate_groups"]):
                    with st.expander(f"🔴 相似组 {i+1}：{group.get('topic','')}（{len(group['items'])}条）"):
                        for item in group["items"]:
                            st.markdown(f"- {item['text'][:120]}")
                            st.caption(f"  来源：{item.get('source','')}")
                        if st.button(f"✅ 保留最佳版本（删其余）", key=f"dedup_{i}"):
                            # 保留最长/最完整的版本
                            best = max(group["items"], key=lambda x: len(x["text"]))
                            # 删除其他条目
                            for item in group["items"]:
                                if item != best:
                                    remove_bullet_from_lib(exp_lib, item)
                            save_experience_lib(exp_lib)
                            st.session_state["dedup_result"] = None
                            st.success(f"已去重，保留了：{best['text'][:60]}...")
                            st.rerun()
                if st.button("🗑️ 忽略去重建议"):
                    st.session_state["dedup_result"] = None
                    st.rerun()
            else:
                st.success("✅ 未发现明显重复内容")

        st.divider()

        # 添加技能
        with st.expander("➕ 添加技能"):
            with st.form("add_skill"):
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    skill_name = st.text_input("技能名")
                with col_s2:
                    skill_cat = st.selectbox("类别", ["AI", "domain", "methodology", "tech"])
                with col_s3:
                    skill_level = st.selectbox("水平", ["expert", "advanced", "intermediate", "beginner"])
                if st.form_submit_button("添加技能"):
                    if skill_name:
                        skills.append({"name": skill_name, "category": skill_cat, "level": skill_level})
                        save_experience_lib(exp_lib)
                        st.success(f"已添加：{skill_name}")
                        st.rerun()

        st.divider()
        st.markdown("### 工作经历")

        experiences = exp_lib.get("experiences", [])

        # 按公司合并经历
        from collections import defaultdict
        company_groups = defaultdict(list)
        for exp in experiences:
            company_groups[exp["company"]].append(exp)

        for company, exps in company_groups.items():
            # 合并时间段：取最早和最晚
            times = [e["time"] for e in exps]
            roles = list(set(e["role"] for e in exps))
            categories = list(set(c for e in exps for c in e.get("category", [])))
            all_bullets = [(e["summary"], b) for e in exps for b in e.get("bullets", [])]

            with st.expander(f"💼 {company} | {'/'.join(roles[:2])} | {times[0].split('–')[0]}–{times[-1].split('–')[-1] if '–' in times[-1] else times[-1]}"):
                st.markdown(f"**涵盖方向**：{'、'.join(categories[:6])}")
                st.markdown(f"**记录数**：{len(exps)} 条经历 | **条目数**：{len(all_bullets)} 条")

                # 按原始经历分组展示
                for ei, exp in enumerate(exps):
                    if len(exps) > 1:
                        st.caption(f"▸ {exp['role']}（{exp['time']}）— {exp['summary']}")
                    for j, bullet in enumerate(exp.get("bullets", [])):
                        st.markdown(f"{j+1}. {bullet['text']}")
                        if bullet.get("keywords"):
                            st.caption(f"   🏷️ {'、'.join(bullet['keywords'])}")
                    if len(exps) > 1 and ei < len(exps) - 1:
                        st.divider()

        # 添加经历
        with st.expander("➕ 添加工作经历"):
            with st.form("add_experience"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    exp_company = st.text_input("公司名称")
                    exp_role = st.text_input("岗位")
                with col_e2:
                    exp_time = st.text_input("时间段", placeholder="如：2022.08–2025.07")
                    exp_cat = st.text_input("类别（逗号分隔）", placeholder="如：AI产品落地, 项目管理")
                exp_summary = st.text_input("概述", placeholder="一句话概括这段经历")
                exp_bullets = st.text_area("详细条目（每行一条，格式：条目文本 | 关键词1,关键词2）", height=150,
                    placeholder="主导AI助手0-1落地，完成3000条样本标注 | AI产品落地, 数据标注, Prompt工程\n准确率70%→94% | 模型评测, badcase")
                if st.form_submit_button("添加经历"):
                    bullets = []
                    for line in exp_bullets.strip().split("\n"):
                        if "|" in line:
                            text, kws = line.split("|", 1)
                            bullets.append({"text": text.strip(), "keywords": [k.strip() for k in kws.split(",") if k.strip()]})
                        elif line.strip():
                            bullets.append({"text": line.strip(), "keywords": []})
                    exp_lib["experiences"].append({
                        "id": f"exp_{str(uuid.uuid4())[:8]}",
                        "company": exp_company, "role": exp_role, "time": exp_time,
                        "category": [c.strip() for c in exp_cat.split(",") if c.strip()],
                        "summary": exp_summary, "bullets": bullets,
                    })
                    save_experience_lib(exp_lib)
                    st.success("已添加")
                    st.rerun()

        st.divider()
        st.markdown("### 🎤 面试素材库")
        st.caption("分段记录STAR故事、常见问题回答、复盘总结，支持AI逐条优化建议")

        # 初始化 interview_entries
        if "interview_entries" not in exp_lib:
            exp_lib["interview_entries"] = []

        entries = exp_lib.get("interview_entries", [])

        # 展示已有条目
        for i, entry in enumerate(entries):
            entry_type = entry.get("type", "其他")
            type_icon = {"STAR故事": "⭐", "常见问题": "❓", "复盘总结": "📝", "话术模板": "💬", "其他": "📌"}.get(entry_type, "📌")
            with st.expander(f"{type_icon} {entry.get('title', f'条目{i+1}')} — {entry_type}", expanded=False):
                col_e1, col_e2 = st.columns([3, 1])
                with col_e1:
                    st.markdown(entry.get("content", ""))
                    if entry.get("tags"):
                        st.caption(f"🏷️ {'、'.join(entry['tags'])}")
                    if entry.get("ai_suggestion"):
                        st.info(f"💡 AI建议：{entry['ai_suggestion']}")
                with col_e2:
                    if st.button("🤖 AI优化", key=f"ai_opt_{i}", use_container_width=True):
                        suggestion = analyze_interview_entry(entry, exp_lib)
                        entry["ai_suggestion"] = suggestion
                        save_experience_lib(exp_lib)
                        st.rerun()
                    if st.button("🗑️ 删除", key=f"del_entry_{i}", use_container_width=True):
                        exp_lib["interview_entries"].pop(i)
                        save_experience_lib(exp_lib)
                        st.rerun()

        # 新增条目
        with st.expander("➕ 添加面试素材"):
            with st.form("add_interview_entry"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    entry_title = st.text_input("标题", placeholder="如：为什么离开拼多多")
                    entry_type = st.selectbox("类型", ["STAR故事", "常见问题", "复盘总结", "话术模板", "其他"])
                with col_f2:
                    entry_tags = st.text_input("标签（逗号分隔）", placeholder="如：离职原因, 高频问题")
                entry_content = st.text_area("内容", height=120, placeholder="记录完整的回答要点、STAR故事、或复盘总结...")
                if st.form_submit_button("💾 保存"):
                    if entry_title and entry_content:
                        entries.append({
                            "title": entry_title.strip(),
                            "type": entry_type,
                            "content": entry_content.strip(),
                            "tags": [t.strip() for t in entry_tags.split(",") if t.strip()],
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "ai_suggestion": "",
                        })
                        exp_lib["interview_entries"] = entries
                        save_experience_lib(exp_lib)
                        st.success(f"已保存：{entry_title}")
                        st.rerun()

        # 批量AI分析
        if entries and st.button("🚀 批量AI优化全部条目", type="primary", use_container_width=True):
            with st.spinner(f"正在分析 {len(entries)} 条素材..."):
                for i, entry in enumerate(entries):
                    if not entry.get("ai_suggestion"):
                        suggestion = analyze_interview_entry(entry, exp_lib)
                        entry["ai_suggestion"] = suggestion
                save_experience_lib(exp_lib)
                st.success(f"已完成 {len(entries)} 条分析")
                st.rerun()

    # ── Tab2: AI职业分析 ──
    with tab_e2:
        st.markdown("### 🤖 AI 职业分析")

        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            with st.spinner("正在深度分析你的经历库..."):
                analysis = analyze_career(exp_lib)

            if "error" in analysis:
                st.error(analysis["error"])
            else:
                st.session_state["career_analysis"] = analysis
                st.rerun()

        if st.session_state.get("career_analysis"):
            analysis = st.session_state["career_analysis"]

            st.markdown("### 💪 核心竞争力")
            for s in analysis.get("core_strengths", []):
                st.markdown(f"- ✅ {s}")

            st.markdown("### 🌟 差异化优势")
            for d in analysis.get("differentiators", []):
                st.markdown(f"- 🔥 {d}")

            st.markdown("### 🎯 推荐职业方向")
            for i, d in enumerate(analysis.get("career_directions", [])):
                score = d.get("match_score", 0)
                bar_color = "#66BB6A" if score >= 80 else "#FFA726"
                st.markdown(f"**{i+1}. {d['direction']}** — {score}/100")
                st.progress(score / 100)
                st.caption(f"理由：{d.get('reason','')} | 适合岗位：{'、'.join(d.get('suitable_roles',[]))}")

            st.markdown("### 📖 职业故事线")
            if analysis.get("career_narrative"):
                st.info(analysis["career_narrative"])

            st.markdown("### 🎤 面试展示重点")
            for h in analysis.get("interview_highlights", []):
                st.markdown(f"- 💬 {h}")

    # ── Tab3: 学习与项目建议 ──
    with tab_e3:
        st.markdown("### 🎯 学习与提升建议")

        analysis = st.session_state.get("career_analysis")
        if not analysis:
            st.info("请先在「AI职业分析」标签页中运行分析")
        else:
            if analysis.get("skill_gaps"):
                st.markdown("### ⚠️ 技能差距")
                for direction, gaps in analysis["skill_gaps"].items():
                    if gaps:
                        with st.expander(f"📌 {direction} — 缺失技能"):
                            for g in gaps:
                                st.markdown(f"- 🔴 {g}")

            if analysis.get("learning_suggestions"):
                st.markdown("### 📚 学习建议")
                for item in analysis["learning_suggestions"]:
                    priority_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(item.get("priority", "中"), "🟡")
                    st.markdown(f"{priority_icon} **{item['direction']}** — {item['topic']}")
                    st.caption(f"   资源：{item.get('resource','')} | 优先级：{item.get('priority','')}")

            if analysis.get("project_suggestions"):
                st.markdown("### 🛠️ 项目建议")
                for item in analysis["project_suggestions"]:
                    with st.expander(f"💡 {item['direction']} — {item['project']}"):
                        st.markdown(f"**目标**：{item.get('goal','')}")
                        st.markdown(f"**技术栈**：{item.get('tech_stack','')}")

    # ── Tab4: 自动生成简历 ──
    with tab_e4:
        st.markdown("### 📝 从经历库自动生成简历")

        col_gen1, col_gen2 = st.columns(2)
        with col_gen1:
            gen_direction = st.selectbox("选择方向", list(exp_lib.get("resume_directions", {}).keys()), key="gen_dir")
        with col_gen2:
            gen_style = st.selectbox("简历风格", ["标准专业版", "现代风格", "简约风格"])

        if st.button("🔮 生成简历", type="primary", use_container_width=True):
            dir_config = exp_lib.get("resume_directions", {}).get(gen_direction, {})

            # 生成技能标签
            skills = dir_config.get("emphasize_skills", [])
            skills_text = " ".join([f"`{s}`" for s in skills[:12]])

            # 生成经历
            exp_ids = dir_config.get("primary_experiences", [])
            exp_map = {e["id"]: e for e in exp_lib.get("experiences", [])}
            exp_parts = []
            current_co = None
            for eid in exp_ids:
                if eid not in exp_map:
                    continue
                exp = exp_map[eid]
                if exp["company"] != current_co:
                    if current_co:
                        exp_parts.append("\n---\n")
                    current_co = exp["company"]
                    exp_parts.append(f"### {exp['company']} | {exp['role']} | {exp['time']}\n")
                    exp_parts.append(f"{exp['summary']}。\n")
                for b in exp["bullets"]:
                    exp_parts.append(f"- {b['text']}\n")
            experiences_text = "".join(exp_parts)

            # 生成作品
            projects = exp_lib.get("personal_projects", [])
            proj_parts = [f"- **{p['name']}** — {p['description']}\n  {p['url']}" for p in projects]
            projects_text = "\n".join(proj_parts)

            # 摘要（注入Gap期叙事）
            summary = dir_config.get("summary_template", "")
            if st.session_state.get("career_analysis"):
                summary += " " + st.session_state["career_analysis"].get("career_narrative", "")

            # 根据风格选模板
            direction_label = gen_direction
            if gen_style == "现代风格":
                template = RESUME_TEMPLATE_MODERN
            elif gen_style == "简约风格":
                template = RESUME_TEMPLATE_MINIMAL
            else:
                template = RESUME_TEMPLATES.get(gen_direction, RESUME_TEMPLATES["AI产品运营"])
                direction_label = ""

            if direction_label:
                resume = template.format(direction_label=direction_label, summary=summary, skills=skills_text, experiences=experiences_text, projects=projects_text)
            else:
                resume = template.format(summary=summary, skills=skills_text, experiences=experiences_text, projects=projects_text)

            # 幻觉检测
            hallucinations = check_hallucination(resume, exp_lib)
            st.session_state["generated_resume"] = resume
            st.session_state["gen_hallucinations"] = hallucinations
            st.session_state["gen_style"] = gen_style
            st.session_state["gen_direction"] = gen_direction
            st.rerun()

        if st.session_state.get("generated_resume"):
            resume_md = st.session_state["generated_resume"]

            # 幻觉检测结果
            hallucinations = st.session_state.get("gen_hallucinations", [])
            if hallucinations:
                st.error(f"⚠️ 幻觉检测：发现 {len(hallucinations)} 处可疑内容")
                for h in hallucinations:
                    st.warning(f"· {h.get('type','')} — {h.get('detail','')}")
            else:
                st.success("✅ 幻觉检测通过：简历内容均在经历库中有据可查")

            resume_md = st.text_area("简历预览（可编辑）", value=resume_md, height=400, key="resume_preview_final")

            # 如果有JD分析结果，显示关键词覆盖率
            jd_for_coverage = st.session_state.get("jd_analysis")
            if jd_for_coverage:
                coverage = check_keyword_coverage(resume_md, jd_for_coverage)
                col_cov1, col_cov2 = st.columns([1, 3])
                with col_cov1:
                    cov_color = "#66BB6A" if coverage["coverage"] >= 80 else "#FFA726" if coverage["coverage"] >= 60 else "#FF4444"
                    st.metric("JD关键词覆盖率", f"{coverage['coverage']}%")
                with col_cov2:
                    if coverage["covered"]:
                        st.success(f"✅ 已覆盖：{'、'.join(coverage['covered'][:8])}")
                    if coverage["missing"]:
                        st.error(f"⚠️ 遗漏：{'、'.join(coverage['missing'])} —— 建议补充到简历中")
                        # 自动补充建议
                        if st.button("🔧 自动补充遗漏关键词", key="auto_fix_kw"):
                            fixed = resume_md
                            for kw in coverage["missing"]:
                                if kw not in fixed:
                                    fixed = fixed.replace("## 核心能力", f"## 核心能力\n\n`{kw}`")
                            st.session_state["generated_resume"] = fixed
                            st.rerun()

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button("⬇️ 下载 MD", data=resume_md,
                    file_name=f"简历_{st.session_state.get('gen_direction','定制')}_自动生成.md", mime="text/markdown", use_container_width=True)
            with col_d2:
                if st.button("📋 复制全文", use_container_width=True):
                    st.info("请选中上方文本框内容 Ctrl+C")


def analyze_duplicates(exp_lib):
    """分析经历库中的重复/高度相似内容"""
    from collections import defaultdict

    # 收集所有条目
    all_items = []
    for exp in exp_lib.get("experiences", []):
        for bullet in exp.get("bullets", []):
            all_items.append({
                "text": bullet["text"],
                "source": f"{exp['company']} - {exp['role']}",
                "exp_id": exp["id"],
                "keywords": bullet.get("keywords", []),
            })

    # 按公司分组后比较
    company_groups = defaultdict(list)
    for item in all_items:
        company = item["source"].split(" - ")[0]  # 只取公司名
        company_groups[company].append(item)

    duplicate_groups = []

    # 简单规则：同一公司下，文本相似度 > 0.6 视为重复
    for company, items in company_groups.items():
        if len(items) < 2:
            continue

        checked = set()
        for i in range(len(items)):
            if i in checked:
                continue
            similar = [items[i]]
            for j in range(i + 1, len(items)):
                if j in checked:
                    continue
                sim = text_similarity(items[i]["text"], items[j]["text"])
                if sim > 0.4:
                    similar.append(items[j])
                    checked.add(j)

            if len(similar) >= 2:
                duplicate_groups.append({
                    "topic": similar[0]["keywords"][0] if similar[0]["keywords"] else similar[0]["text"][:30],
                    "items": similar,
                    "source": company,
                })
                checked.add(i)

    return {"duplicate_groups": duplicate_groups}


def text_similarity(a, b):
    """文本相似度（基于共同子串+关键词重合）"""
    if not a or not b:
        return 0
    # 字符集重合度
    set_a = set(a)
    set_b = set(b)
    char_sim = len(set_a & set_b) / len(set_a | set_b) if set_a | set_b else 0
    # 数字匹配（关键指标重复）
    nums_a = set(re.findall(r'\d+', a))
    nums_b = set(re.findall(r'\d+', b))
    num_overlap = len(nums_a & nums_b) / max(len(nums_a | nums_b), 1)
    return char_sim * 0.5 + num_overlap * 0.5


def remove_bullet_from_lib(exp_lib, target_item):
    """从经历库中移除指定条目"""
    for exp in exp_lib.get("experiences", []):
        bullets = exp.get("bullets", [])
        exp["bullets"] = [b for b in bullets if b["text"] != target_item["text"]]


def analyze_interview_entry(entry, exp_lib):
    """AI分析单条面试素材，给出优化建议"""
    if not HAS_ANTHROPIC:
        return "（需要anthropic SDK）"

    prompt = f"""你是面试教练。分析以下面试素材，给出1-2条具体的优化建议。

素材类型：{entry.get('type', '')}
素材标题：{entry.get('title', '')}
素材内容：{entry.get('content', '')[:1000]}

优化方向：
- STAR故事：是否有清晰的Situation/Task/Action/Result？数据是否具体？
- 常见问题：回答是否有结构？是否避免了负面表述？
- 复盘总结：是否提炼了可复用的经验？
- 话术模板：是否自然不生硬？

请用中文输出50字以内的优化建议（只输出建议文本）："""

    try:
        client = get_anthropic_client()
        if not client:
            return {"error": "API Key 未配置。请在 Streamlit Cloud Secrets 或 .env 中设置 ANTHROPIC_AUTH_TOKEN"}
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=150, temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                return block.text.strip()[:100]
        return ""
    except:
        return "（AI分析暂不可用）"


def save_experience_lib(exp_lib):
    """保存经验库"""
    if st.session_state.get("is_guest"):
        st.session_state["guest_exp_lib"] = exp_lib
        return
    with open(_current_exp_lib_file(), "w", encoding="utf-8") as f:
        json.dump(exp_lib, f, ensure_ascii=False, indent=2)


    # ── Tab5: 简历上传解析 ──
    with tab_e5:
        st.markdown("### 📤 上传简历自动解析")
        st.caption("粘贴现有简历文本，AI自动拆解并填入经历库。支持纯文本格式。")

        resume_upload_text = st.text_area(
            "粘贴简历文本",
            height=250,
            placeholder="粘贴你的完整简历文本（.md/.txt 格式）...\n\nAI将自动提取：基本信息、教育经历、工作经历、技能、证书\n解析后可在「经历管理」标签中查看和修改",
        )

        if st.button("🔮 AI解析简历", type="primary", use_container_width=True, disabled=not resume_upload_text):
            with st.spinner("正在解析简历..."):
                parsed = parse_resume_text_with_llm(resume_upload_text)

            if "error" in parsed:
                st.error(parsed["error"])
            else:
                st.success("✅ 解析完成！请确认以下内容后合并到经历库")

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.markdown("**基本信息**")
                    st.json(parsed.get("basic", {}))
                    st.markdown("**教育**")
                    st.json(parsed.get("education", []))
                with col_p2:
                    st.markdown(f"**技能**（{len(parsed.get('skills', []))}项）")
                    st.json(parsed.get("skills", [])[:8])
                    st.markdown(f"**经历**（{len(parsed.get('experiences', []))}段）")
                    st.json([{"company": e.get("company", ""), "role": e.get("role", "")} for e in parsed.get("experiences", [])])

                if st.button("✅ 合并到经历库", type="primary", use_container_width=True):
                    # 智能合并：新增不重复项
                    existing_companies = {e["company"] for e in exp_lib.get("experiences", [])}
                    for exp in parsed.get("experiences", []):
                        if exp.get("company") not in existing_companies:
                            exp["id"] = f"parsed_{str(uuid.uuid4())[:8]}"
                            exp_lib["experiences"].append(exp)

                    existing_skills = {s["name"] for s in exp_lib.get("skills", [])}
                    for s in parsed.get("skills", []):
                        if s.get("name") not in existing_skills:
                            exp_lib["skills"].append(s)

                    for cert in parsed.get("certifications", []):
                        if cert not in exp_lib.get("certifications", []):
                            exp_lib["certifications"].append(cert)

                    for edu in parsed.get("education", []):
                        existing_edu = {e["school"]: e for e in exp_lib.get("education", [])}
                        if edu.get("school") not in existing_edu:
                            exp_lib["education"].append(edu)

                    save_experience_lib(exp_lib)
                    st.success(f"已合并：{len(parsed.get('experiences',[]))}段经历、{len(parsed.get('skills',[]))}项技能")
                    st.rerun()


# ═══════════════════════════════════════
# 模块8：半自动投递
# ═══════════════════════════════════════

def estimate_quick_match(job, exp_lib):
    """快速估算匹配度（无需LLM）"""
    score = 50
    job_skills = set(s.lower() for s in job.get("hard_skills", []))
    my_skills = set(s["name"].lower() for s in exp_lib.get("skills", []))
    if job_skills:
        overlap = len(job_skills & my_skills) / len(job_skills)
        score += int(overlap * 30)
    my_directions = list(exp_lib.get("resume_directions", {}).keys())
    job_dir = job.get("direction", "")
    if any(d in job_dir for d in my_directions):
        score += 15
    return min(score, 98)


JOB_DISCOVERY_PROMPT = """你是招聘市场分析师。根据候选人的经历库，推荐5个当前市场上最匹配的真实在招岗位。

## 候选人档案
- 方向：{directions}
- 核心技能：{skills}
- 工作经验：{experience_summary}
- 目标城市：{cities}
- 薪资期望：{salary_range}

## 输出要求
1. 推荐真实存在的公司和岗位（基于2026年5月市场情况）
2. 每个岗位说明为什么匹配
3. 给出薪资范围估算

输出JSON数组：
[{{"company":"公司","position":"岗位","city":"城市","salary":"薪资范围","direction":"方向","match_reason":"匹配原因(30字)","hard_skills":["要求技能"]}}]"""


def discover_jobs(exp_lib):
    """AI主动发现匹配岗位"""
    if not HAS_ANTHROPIC:
        return []

    directions = list(exp_lib.get("resume_directions", {}).keys())
    skills = [s["name"] for s in exp_lib.get("skills", []) if s.get("level") in ["expert", "advanced"]]
    cities = exp_lib.get("basic", {}).get("cities", ["上海", "北京"])
    salary_range = f"{exp_lib.get('basic',{}).get('salary_min',18)}k-{exp_lib.get('basic',{}).get('salary_max',26)}k"
    exp_summary = "、".join([e["summary"] for e in exp_lib.get("experiences", [])[:3]])

    prompt = JOB_DISCOVERY_PROMPT.format(
        directions="、".join(directions[:3]) if directions else "AI产品运营/服务体验运营",
        skills="、".join(skills[:10]),
        experience_summary=exp_summary[:200],
        cities="、".join(cities[:4]) if isinstance(cities, list) else str(cities),
        salary_range=salary_range,
    )

    try:
        client = get_anthropic_client()
        if not client:
            return []
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=1500, temperature=0.5,
            system="只输出合法JSON数组。基于2026年5月市场真实情况推荐，不确定的标注'需核实'。",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip(); break
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            jobs = json.loads(m.group())
            # 为每个岗位做匹配打分
            for job in jobs:
                job["id"] = str(uuid.uuid4())[:8]
                job["source"] = "AI推荐"
                job["discovered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            return jobs
    except:
        pass
    return []


def render_auto_apply():
    """半自动投递页面（v2.0 重构：推荐+填表+状态联动）"""
    st.subheader("🚀 智能投递中心")

    records = load_history()
    exp_lib = load_experience_lib()

    # ── Tab: 主动发现 vs 已有岗位 ──
    tab_d1, tab_d2 = st.tabs(["🔍 AI岗位发现", "📋 我的待投递"])

    # ═══ Tab 1: AI主动发现岗位 ═══
    with tab_d1:
        st.caption("AI根据你的经历库，主动搜索当前市场上最匹配的在招岗位")

        if st.button("🔍 发现匹配岗位", type="primary", use_container_width=True):
            with st.spinner("AI正在扫描市场岗位..."):
                discovered = discover_jobs(exp_lib)
                st.session_state["discovered_jobs"] = discovered
                st.rerun()

        if st.session_state.get("discovered_jobs"):
            discovered = st.session_state["discovered_jobs"]
            st.success(f"发现 {len(discovered)} 个匹配岗位")

            for i, job in enumerate(discovered):
                with st.container():
                    col_j1, col_j2, col_j3 = st.columns([4, 2, 1.5])
                    with col_j1:
                        st.markdown(f"**{job.get('company','')}** — {job.get('position','')}")
                        st.caption(f"📍 {job.get('city','')} | 💰 {job.get('salary','')} | 🏷️ {job.get('direction','')}")
                        if job.get("match_reason"):
                            st.caption(f"💡 {job['match_reason']}")
                        if job.get("hard_skills"):
                            st.caption(f"🔧 {' · '.join(job['hard_skills'][:5])}")
                    with col_j2:
                        # 快速匹配度估算
                        quick_score = estimate_quick_match(job, exp_lib)
                        score_color = "#66BB6A" if quick_score >= 80 else "#FFA726" if quick_score >= 60 else "#FF4444"
                        st.markdown(f"预估匹配：<span style='color:{score_color};font-size:14pt'>{quick_score}</span>/100", unsafe_allow_html=True)
                    with col_j3:
                        if st.button("➕ 追踪", key=f"track_{i}", use_container_width=True):
                            # 创建投递记录
                            new_record = {
                                "id": str(uuid.uuid4())[:8],
                                "company": job.get("company", ""),
                                "position": job.get("position", ""),
                                "city": job.get("city", ""),
                                "direction": job.get("direction", "通用"),
                                "salary": job.get("salary", ""),
                                "platform": "AI推荐",
                                "contact": "",
                                "status": "待投递",
                                "jd_text": f"AI推荐岗位：{job.get('company','')} - {job.get('position','')}\n要求：{'、'.join(job.get('hard_skills',[]))}",
                                "notes": f"匹配原因：{job.get('match_reason','')}",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "history": [{"status": "待投递", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}],
                            }
                            records.append(new_record)
                            save_history(records)
                            st.success(f"已添加：{job['company']}")
                            st.rerun()
                    st.divider()
        else:
            st.info("👆 点击上方按钮，AI将根据你的经历库主动发现匹配岗位")

    # ═══ Tab 2: 已有待投递 ═══
    with tab_d2:
        st.caption("你已录入的待投递岗位，按匹配度排序")

        pending = [r for r in records if r.get("status") in ["待投递", "已投递"]]

    if not pending:
        st.info("📭 暂无待投递岗位。请先在「JD分析」中录入目标岗位。")
        # 引导入口
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("🔍 去JD分析", use_container_width=True, type="primary"):
                st.session_state["nav"] = "🔍 JD分析"
                st.rerun()
        with col_e2:
            if st.button("🌐 去JD搜索", use_container_width=True):
                st.session_state["nav"] = "🌐 JD搜索"
                st.rerun()
        return

    # 按匹配度排序推荐
    sorted_pending = sorted(pending, key=lambda r: r.get("match_result", {}).get("overall_score", 0), reverse=True)

    # 推荐卡片
    for i, record in enumerate(sorted_pending[:5]):  # Top 5推荐
        match = record.get("match_result", {})
        score = match.get("overall_score", 0) if match else 0
        has_resume = bool(record.get("customized_resume"))

        score_color = "#66BB6A" if score >= 80 else "#FFA726" if score >= 60 else "#FF4444"
        status_badge = {"待投递": "🟡", "已投递": "🔵"}.get(record.get("status", ""), "⚪")

        with st.container():
            col_r1, col_r2, col_r3 = st.columns([4, 2, 1])
            with col_r1:
                st.markdown(f"**{record['company']}** — {record['position']}")
                st.caption(f"{record.get('city','')} | {record.get('salary','')} | {record.get('platform','')}")
            with col_r2:
                st.markdown(f"匹配度：<span style='color:{score_color};font-size:16pt'>{score}</span>/100", unsafe_allow_html=True)
                st.caption(f"{status_badge} {record.get('status','')} | {'✅ 已定制' if has_resume else '⚠️ 待定制'}")
            with col_r3:
                if st.button("🚀 投递", key=f"quick_apply_{i}", type="primary", use_container_width=True):
                    st.session_state["apply_target"] = record["id"]
                    st.rerun()
            st.divider()

    # ── 投递向导（当选中具体岗位时显示）──
    if st.session_state.get("apply_target"):
        target_id = st.session_state["apply_target"]
        target = next((r for r in records if r["id"] == target_id), None)

        if target:
            st.divider()
            st.markdown(f"## 📋 投递向导：{target['company']} — {target['position']}")

            # 进度指示器
            apply_step = st.session_state.get("apply_step", 1)
            step_names = ["准备材料", "填写信息", "确认投递"]
            cols = st.columns(3)
            for j, name in enumerate(step_names):
                with cols[j]:
                    if j + 1 < apply_step:
                        st.success(f"✅ {name}")
                    elif j + 1 == apply_step:
                        st.markdown(f"**🔵 {name}**")
                    else:
                        st.caption(f"⚪ {name}")

            st.divider()

            # Step 1: 准备材料
            if apply_step == 1:
                st.markdown("### 📝 Step 1：准备申请材料")

                # 自动生成/获取简历
                if not target.get("customized_resume"):
                    st.warning("尚未定制简历，正在自动生成...")
                    jd = target.get("jd_analysis") or (parse_jd_with_llm(target.get("jd_text", "")) if target.get("jd_text") else None)
                    if jd and "error" not in jd:
                        match_result = score_match(jd, exp_lib) if "error" not in jd else {}
                        direction = jd.get("matched_direction", "AI产品运营")
                        if direction not in DIRECTIONS:
                            direction = "AI产品运营"
                        resume = generate_customized_resume(direction, match_result, exp_lib, jd)
                        target["customized_resume"] = resume
                        target["match_result"] = match_result
                        target["jd_analysis"] = jd
                        save_history(records)
                        st.success("✅ 简历已自动生成")
                        st.rerun()

                # 生成填表数据包
                basic = exp_lib.get("basic", {})
                form_data = {
                    "姓名": basic.get("name", "牟思雨"),
                    "手机": basic.get("phone", "18504284554"),
                    "邮箱": basic.get("email", "msy1994dut@163.com"),
                    "工作年限": "4年",
                    "最高学历": "硕士",
                    "毕业院校": "东北财经大学",
                    "当前所在地": target.get("city", "上海"),
                    "期望薪资": target.get("salary", "18k-26k"),
                    "求职状态": "离职，随时到岗",
                }

                # 展示材料
                tab_m1, tab_m2, tab_m3 = st.tabs(["📄 定制简历", "📋 填表数据", "✉️ 求职信"])
                with tab_m1:
                    resume_text = target.get("customized_resume", "")
                    st.text_area("简历（全选复制）", value=resume_text, height=300, key="apply_resume")
                with tab_m2:
                    st.json(form_data)
                    st.caption("💡 这些数据已按岗位预填，投递时直接复制粘贴")
                with tab_m3:
                    # 生成求职信
                    jd = target.get("jd_analysis", {})
                    if jd and "error" not in jd:
                        letter = generate_cover_letter(jd, target.get("customized_resume", ""), exp_lib)
                        st.text_area("求职信", value=letter, height=150, key="apply_letter")

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button("取消", use_container_width=True):
                        st.session_state["apply_target"] = None
                        st.session_state["apply_step"] = 1
                        st.rerun()
                with col_s2:
                    if st.button("下一步 → 填写信息", type="primary", use_container_width=True):
                        st.session_state["apply_step"] = 2
                        st.rerun()

            # Step 2: 填写信息
            elif apply_step == 2:
                st.markdown("### ✍️ Step 2：在招聘平台填写信息")

                platform = target.get("platform", "Boss直聘")
                st.info(f"当前投递渠道：**{platform}**")

                # 平台快捷入口
                platform_urls = {
                    "Boss直聘": "https://www.zhipin.com/",
                    "猎聘": "https://www.liepin.com/",
                    "脉脉": "https://maimai.cn/",
                    "官网": "",
                    "内推": "",
                    "其他": "",
                }
                url = platform_urls.get(platform, "")
                if url:
                    st.markdown(f"🔗 [打开 {platform} 去投递]({url})")
                else:
                    st.caption(f"请在 {platform} 上找到对应岗位进行投递")

                # 填表指引
                st.markdown("#### 📋 需要填写/上传的内容")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.checkbox("个人信息（姓名/手机/邮箱）", value=True, disabled=True)
                    st.checkbox("教育经历", value=True, disabled=True)
                    st.checkbox("工作经历", value=bool(target.get("customized_resume")))
                with col_f2:
                    st.checkbox("上传附件简历", value=False)
                    st.checkbox("发送求职信/招呼语", value=False)
                    st.checkbox("填写期望薪资", value=False)

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button("← 上一步", use_container_width=True):
                        st.session_state["apply_step"] = 1
                        st.rerun()
                with col_s2:
                    if st.button("下一步 → 确认投递", type="primary", use_container_width=True):
                        st.session_state["apply_step"] = 3
                        st.rerun()

            # Step 3: 确认投递
            elif apply_step == 3:
                st.markdown("### ✅ Step 3：确认投递并更新状态")
                st.success("请在招聘平台上完成投递后，点击下方按钮确认")

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    new_status = st.selectbox("更新状态为", ["已投递", "初筛", "待反馈"],
                        key="final_status")
                    apply_note = st.text_area("备注（可选）", key="final_note", height=60,
                        placeholder="如：已发送，HR说3个工作日内回复")
                with col_c2:
                    st.metric("岗位", f"{target['company']} - {target['position']}")
                    st.metric("渠道", target.get("platform", ""))

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button("← 上一步", use_container_width=True):
                        st.session_state["apply_step"] = 2
                        st.rerun()
                with col_s2:
                    if st.button("✅ 确认已投递", type="primary", use_container_width=True):
                        # 自动更新状态
                        old_status = target.get("status", "待投递")
                        if new_status != old_status:
                            target.setdefault("history", []).append({
                                "status": new_status,
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            })
                        target["status"] = new_status
                        if apply_note:
                            target["notes"] = f"{target.get('notes','')}\n[投递确认 {datetime.now().strftime('%m-%d %H:%M')}] {apply_note}".strip()
                        target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        target["submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_history(records)

                        # 清理状态
                        st.session_state["apply_target"] = None
                        st.session_state["apply_step"] = 1
                        st.success(f"🎉 投递成功！{target['company']} - {target['position']} 状态已更新为「{new_status}」")
                        st.rerun()

    # ── 底部：投递统计 ──
    st.divider()
    st.markdown("### 📊 投递总览")
    total = len(records)
    submitted = len([r for r in records if r.get("status") not in ["待投递"]])
    interviewing = len([r for r in records if r.get("status") in ["一面", "二面", "终面"]])
    offer_count = len([r for r in records if r.get("status") == "offer"])

    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1: st.metric("总岗位", total)
    with col_p2: st.metric("已投递", submitted)
    with col_p3: st.metric("面试中", interviewing)
    with col_p4: st.metric("offer", offer_count, delta="🎉" if offer_count > 0 else None)


# ═══════════════════════════════════════
# V1.7 新增：求职信 + 面试预测 + 管道看板 + 导出 + 面试复盘
# ═══════════════════════════════════════

def generate_cover_letter(jd_analysis, resume_text, exp_lib):
    """AI生成求职信"""
    if not HAS_ANTHROPIC:
        return "需要 anthropic SDK"

    prompt = f"""你是专业求职顾问。根据以下信息写一封200字以内的求职信（cover letter），用于Boss直聘/猎聘私信。

要求：
- 开头直接表明匹配度，不用客套
- 中间用1-2个具体经历数据证明能力
- 结尾表达进一步沟通意愿
- 语气专业但不生硬

---JD信息---
公司：{jd_analysis.get('company_name','')}
岗位：{jd_analysis.get('position','')}
核心要求：{'、'.join(jd_analysis.get('hard_skills',[]))}

---候选人关键经历---
{resume_text[:1500]}

请输出纯文本求职信（不要称呼，不要标题）："""

    try:
        client = get_anthropic_client()
        if not client:
            return "API Key 未配置"
        resp = client.messages.create(model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=500, temperature=0.5,
            messages=[{"role": "user", "content": prompt}])
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                return block.text.strip()
        return ""
    except Exception as e:
        return f"生成失败: {e}"


def predict_interview_questions(jd_analysis, exp_lib):
    """AI预测面试问题"""
    if not HAS_ANTHROPIC:
        return []

    prompt = f"""你是面试官。根据以下JD，预测5个最可能被问到的面试问题，并给出回答框架。

---JD分析---
{json.dumps(jd_analysis, ensure_ascii=False)[:1500]}

---候选人背景---
学历：硕士(数据挖掘)
经验：4年(携程3年+拼多多4个月)
核心方向：AI产品运营/服务体验治理

输出JSON格式（只输出JSON）：
[{{"question":"问题","why":"为什么问这个","framework":"回答框架要点","key_points":["要点1","要点2"]}}]"""

    try:
        client = get_anthropic_client()
        if not client:
            return "API Key 未配置"
        resp = client.messages.create(model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=2000, temperature=0.5,
            system="只输出合法JSON。",
            messages=[{"role": "user", "content": prompt}])
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip(); break
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return []
    except:
        return []


def render_cover_letter_page():
    """求职信生成页面"""
    st.subheader("✉️ 求职信生成")

    records = load_history()
    jd_records = [r for r in records if r.get("customized_resume")]

    if not jd_records:
        st.info("请先在「简历定制」中生成定制简历")
        return

    selected = st.selectbox("选择岗位", [f"{r['company']} - {r['position']}" for r in jd_records])
    record = next((r for r in jd_records if f"{r['company']} - {r['position']}" == selected), None)

    if record and st.button("🔮 生成求职信", type="primary", use_container_width=True):
        jd = record.get("jd_analysis") or parse_jd_with_llm(record.get("jd_text", ""))
        with st.spinner("生成中..."):
            letter = generate_cover_letter(jd, record.get("customized_resume", ""), load_experience_lib())
        st.text_area("求职信（可编辑）", value=letter, height=200, key="cover_letter")
        st.download_button("⬇️ 下载", data=letter, file_name=f"求职信_{record['company']}.txt", mime="text/plain")
        st.caption("💡 复制到Boss直聘/猎聘私信框发送")


def render_interview_prep_page():
    """面试准备页面"""
    st.subheader("🎯 面试题库预测")

    records = load_history()
    jd_records = [r for r in records if r.get("jd_analysis") and "error" not in r["jd_analysis"]]

    if not jd_records:
        st.info("请先在「JD分析」中分析岗位")
        return

    selected = st.selectbox("选择岗位", [f"{r['company']} - {r['position']}" for r in jd_records], key="interview_jd")
    record = next((r for r in jd_records if f"{r['company']} - {r['position']}" == selected), None)

    if record and st.button("🔮 预测面试问题", type="primary", use_container_width=True):
        with st.spinner("AI正在模拟面试官..."):
            questions = predict_interview_questions(record["jd_analysis"], load_experience_lib())
        st.session_state["predicted_questions"] = questions
        st.rerun()

    if st.session_state.get("predicted_questions"):
        for i, q in enumerate(st.session_state["predicted_questions"]):
            with st.expander(f"Q{i+1}. {q.get('question','')}"):
                st.markdown(f"**为什么问**：{q.get('why','')}")
                st.markdown(f"**回答框架**：{q.get('framework','')}")
                if q.get("key_points"):
                    st.markdown("**关键要点**：")
                    for kp in q["key_points"]:
                        st.markdown(f"- {kp}")


def render_pipeline_kanban():
    """管道看板"""
    st.subheader("📋 投递管道看板")

    records = load_history()
    if not records:
        st.info("暂无投递记录")
        return

    stages = ["待投递", "已投递", "初筛", "一面", "二面", "终面", "offer", "已拒"]
    cols = st.columns(len(stages))

    for i, stage in enumerate(stages):
        with cols[i]:
            stage_records = [r for r in records if r.get("status") == stage]
            color = STATUS_COLORS.get(stage, "#90A4AE")
            st.markdown(f"**{stage}** ({len(stage_records)})")
            for r in stage_records:
                with st.container():
                    st.markdown(f"🏢 {r['company']}")
                    st.caption(r['position'][:20])
                    new_stage = st.selectbox("→", stages, index=stages.index(stage),
                        key=f"pipe_{r['id']}", label_visibility="collapsed")
                    if new_stage != stage:
                        r.setdefault("history", []).append({"status": new_stage, "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
                        r["status"] = new_stage
                        r["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_history(records)
                        st.rerun()
            st.divider()

    # 效果分析
    st.divider()
    st.subheader("📊 简历效果分析")
    submitted = [r for r in records if r.get("status") not in ["待投递"]]
    interviewed = [r for r in records if r.get("status") in ["一面", "二面", "终面", "offer"]]
    if submitted:
        interview_rate = len(interviewed) / len(submitted) * 100 if submitted else 0
        st.metric("面试邀约率", f"{interview_rate:.1f}%", delta="目标>15%")
        # 按方向分析
        for direction in DIRECTIONS[:4]:
            dir_records = [r for r in submitted if r.get("direction") == direction]
            dir_interviews = [r for r in interviewed if r.get("direction") == direction]
            if dir_records:
                dir_rate = len(dir_interviews) / len(dir_records) * 100
                st.caption(f"{direction}：{dir_rate:.0f}%（{len(dir_interviews)}/{len(dir_records)}）")


def render_settings_page():
    """设置与导出"""
    st.subheader("⚙️ 设置与数据管理")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("### 📤 数据导出")
        if st.button("导出经历库 JSON", use_container_width=True):
            exp_lib = load_experience_lib()
            st.download_button("⬇️ 下载", data=json.dumps(exp_lib, ensure_ascii=False, indent=2),
                file_name="experience_library_backup.json", mime="application/json", use_container_width=True)

        if st.button("导出投递记录 CSV", use_container_width=True):
            records = load_history()
            if records:
                df = pd.DataFrame(records)
                csv = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("⬇️ 下载", data=csv, file_name="application_history_backup.csv",
                    mime="text/csv", use_container_width=True)

        st.markdown("### 📥 数据导入")
        uploaded_exp = st.file_uploader("导入经历库 JSON", type=["json"], key="import_exp")
        if uploaded_exp:
            try:
                imported = json.load(uploaded_exp)
                current = load_experience_lib()
                # 合并技能
                existing_skills = {s["name"] for s in current.get("skills", [])}
                for s in imported.get("skills", []):
                    if s["name"] not in existing_skills:
                        current["skills"].append(s)
                save_experience_lib(current)
                st.success(f"已合并 {len(imported.get('skills',[]))} 项技能")
            except:
                st.error("文件格式错误")

    with col_s2:
        st.markdown("### 🎨 界面偏好")
        st.caption("（功能规划中，Streamlit 风格由系统默认控制）")

        st.markdown("### 📊 数据统计")
        records = load_history()
        exp_lib = load_experience_lib()
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("投递记录", len(records))
            st.metric("经历条目", sum(len(e.get("bullets",[])) for e in exp_lib.get("experiences",[])))
        with col_b:
            st.metric("面试素材", len(exp_lib.get("interview_entries", [])))
            st.metric("技能标签", len(exp_lib.get("skills",[])))


# ═══════════════════════════════════════
# V1.7 面试复盘模块
# ═══════════════════════════════════════

INTERVIEW_REVIEW_PROMPT = """你是资深面试教练。分析以下面试复盘记录，给出专业建议。

分析维度：
1. 问题回答质量：哪些回答有力，哪些需要改进
2. 面试节奏与沟通：时间分配、表达清晰度、互动质量
3. 技术与业务匹配：回答是否展现了岗位需要的核心能力
4. 改进优先级：最需要提升的1-2个方向

输出JSON格式：
{
  "overall_assessment": "整体评价（50字）",
  "strengths": ["亮点1", "亮点2"],
  "weaknesses": ["不足1", "不足2"],
  "improvement_actions": ["具体改进行动1", "具体改进行动2"],
  "key_questions_optimized": [{"question": "面试问题", "better_answer": "优化后的回答框架"}],
  "next_interview_focus": "下次面试重点准备方向"
}"""


def load_reviews():
    """加载面试复盘数据"""
    fpath = os.path.join(get_profile_path(get_active_profile()), "interview_reviews.json")
    if not os.path.exists(fpath):
        return []
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reviews(reviews):
    fpath = os.path.join(get_profile_path(get_active_profile()), "interview_reviews.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


def analyze_interview_review(review):
    """AI分析面试复盘"""
    if not HAS_ANTHROPIC:
        return None

    # 构建分析输入
    questions_text = "\n".join([
        f"Q: {q.get('question','')}\nA: {q.get('my_answer','')[:200]}\n自评: {q.get('self_rating','')}/5"
        for q in review.get("questions", [])
    ])

    try:
        client = get_anthropic_client()
        if not client:
            return "API Key 未配置"
        resp = client.messages.create(model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
            max_tokens=1500, temperature=0.3,
            system="只输出合法JSON。",
            messages=[{"role": "user", "content": f"""{INTERVIEW_REVIEW_PROMPT}

---面试信息---
公司：{review.get('company','')} | 岗位：{review.get('position','')}
轮次：{review.get('round','')} | 日期：{review.get('date','')}
整体自评：{review.get('overall_rating','')}/10
结果：{review.get('result','')}

---面试问答---
{questions_text}

---复盘笔记---
{review.get('notes','')[:500]}
"""}])
        raw = ""
        for block in resp.content:
            if hasattr(block, 'text') and block.text:
                raw = block.text.strip(); break
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except:
        pass
    return None


def render_interview_review():
    """面试复盘页面"""
    st.subheader("🔄 面试复盘分析")

    reviews = load_reviews()

    tab_r1, tab_r2, tab_r3 = st.tabs(["➕ 新增复盘", "📋 历史复盘", "📊 模式分析"])

    # ── Tab1: 新增复盘 ──
    with tab_r1:
        st.markdown("### 记录面试复盘")

        with st.form("add_review"):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                company = st.text_input("公司", key="rev_company")
                position = st.text_input("岗位", key="rev_position")
                interview_round = st.selectbox("面试轮次", ["一面", "二面", "三面/终面", "HR面", "其他"])
            with col_r2:
                interview_date = st.date_input("面试日期", value=date.today())
                overall_rating = st.slider("整体自评", 1, 10, 6)
                result = st.selectbox("面试结果", ["进行中", "通过", "未通过", "等待反馈"])

            st.divider()
            st.markdown("### 面试问题记录")
            st.caption("逐条记录面试中被问到的问题、你的回答要点、自评分数")

            # 问题列表（动态行）
            num_questions = st.number_input("问题数量", 1, 15, 3)
            questions = []
            for i in range(int(num_questions)):
                col_q1, col_q2, col_q3 = st.columns([3, 2, 1])
                with col_q1:
                    q_text = st.text_input(f"问题{i+1}", key=f"q_{i}", placeholder="面试官问了什么？")
                with col_q2:
                    q_answer = st.text_area(f"你的回答{i+1}", key=f"a_{i}", height=60, placeholder="回答要点...")
                with col_q3:
                    q_rating = st.selectbox(f"自评{i+1}", [5,4,3,2,1], key=f"r_{i}", format_func=lambda x: f"{'⭐'*x}")
                if q_text:
                    questions.append({"question": q_text, "my_answer": q_answer, "self_rating": q_rating})

            notes = st.text_area("复盘笔记", height=100, placeholder="整体感受、意料之外的问题、下次要注意的点...")

            if st.form_submit_button("💾 保存复盘", type="primary", use_container_width=True):
                if company and position:
                    review = {
                        "id": str(uuid.uuid4())[:8],
                        "company": company, "position": position,
                        "round": interview_round, "date": str(interview_date),
                        "overall_rating": overall_rating, "result": result,
                        "questions": questions, "notes": notes,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    reviews.append(review)
                    save_reviews(reviews)
                    st.success(f"已保存：{company} - {position}（{interview_round}）")
                    st.rerun()

    # ── Tab2: 历史复盘 ──
    with tab_r2:
        if not reviews:
            st.info("暂无面试复盘记录")
        else:
            for i, review in enumerate(reversed(reviews)):
                result_icon = {"通过": "✅", "未通过": "❌", "进行中": "🔄", "等待反馈": "⏳"}.get(review.get("result", ""), "📌")
                with st.expander(
                    f"{result_icon} {review['company']} — {review['position']} ({review.get('round','')}) "
                    f"| {review.get('date','')} | 自评{review.get('overall_rating','')}/10",
                    expanded=(i == 0)
                ):
                    st.markdown(f"**整体自评**：{'⭐'*review.get('overall_rating',0)} {review['overall_rating']}/10")
                    st.markdown(f"**结果**：{review.get('result','')}")

                    if review.get("questions"):
                        st.markdown("**面试问题记录**：")
                        for j, q in enumerate(review["questions"]):
                            st.markdown(f"**Q{j+1}**: {q.get('question','')}")
                            st.markdown(f"> {q.get('my_answer','')[:200]}")
                            st.caption(f"自评：{'⭐'*q.get('self_rating',0)}")

                    if review.get("notes"):
                        st.markdown(f"**复盘笔记**：{review['notes']}")

                    # AI 分析
                    if review.get("ai_analysis"):
                        analysis = review["ai_analysis"]
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            st.success(f"✅ 亮点：")
                            for s in analysis.get("strengths", []):
                                st.markdown(f"- {s}")
                        with col_a2:
                            st.warning(f"⚠️ 改进：")
                            for w in analysis.get("weaknesses", []):
                                st.markdown(f"- {w}")

                        if analysis.get("improvement_actions"):
                            st.info(f"💡 行动计划：")
                            for act in analysis["improvement_actions"]:
                                st.markdown(f"- {act}")

                        if analysis.get("key_questions_optimized"):
                            with st.expander("📝 关键问题优化建议"):
                                for qo in analysis["key_questions_optimized"]:
                                    st.markdown(f"**原问题**：{qo.get('question','')}")
                                    st.markdown(f"**优化回答**：{qo.get('better_answer','')}")

                    # 操作按钮
                    col_act1, col_act2, col_act3 = st.columns(3)
                    with col_act1:
                        if not review.get("ai_analysis") and st.button("🤖 AI分析", key=f"analyze_review_{i}", use_container_width=True):
                            with st.spinner("分析中..."):
                                analysis = analyze_interview_review(review)
                                if analysis:
                                    review["ai_analysis"] = analysis
                                    save_reviews(reviews)
                                    st.rerun()
                    with col_act2:
                        if st.button("🗑️ 删除", key=f"del_review_{i}", use_container_width=True):
                            reviews = [r for r in reviews if r["id"] != review["id"]]
                            save_reviews(reviews)
                            st.rerun()

    # ── Tab3: 模式分析 ──
    with tab_r3:
        if len(reviews) < 2:
            st.info("需要至少2条复盘记录才能进行模式分析")
        else:
            st.markdown("### 📊 面试模式分析")

            # 统计
            passed = len([r for r in reviews if r.get("result") == "通过"])
            failed = len([r for r in reviews if r.get("result") == "未通过"])
            avg_rating = sum(r.get("overall_rating", 0) for r in reviews) / len(reviews)

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1: st.metric("总复盘", len(reviews))
            with col_m2: st.metric("通过率", f"{passed/max(len(reviews),1)*100:.0f}%")
            with col_m3: st.metric("平均自评", f"{avg_rating:.1f}/10")

            # 常见问题类型
            all_questions = []
            for r in reviews:
                for q in r.get("questions", []):
                    all_questions.append(q.get("question", ""))

            # 自评趋势
            dates = [r.get("date", "") for r in reviews]
            ratings = [r.get("overall_rating", 0) for r in reviews]
            if len(dates) > 1:
                st.markdown("**自评趋势**")
                trend_df = pd.DataFrame({"日期": dates, "自评": ratings})
                st.line_chart(trend_df.set_index("日期"))

            # AI 分析汇总
            analyzed = [r for r in reviews if r.get("ai_analysis")]
            if analyzed:
                st.markdown("### 🎯 AI 综合分析")
                all_weaknesses = []
                all_strengths = []
                for r in analyzed:
                    all_weaknesses.extend(r["ai_analysis"].get("weaknesses", []))
                    all_strengths.extend(r["ai_analysis"].get("strengths", []))

                if all_weaknesses:
                    st.warning("**高频短板**（多次面试中反复出现）：")
                    from collections import Counter
                    weak_counter = Counter(all_weaknesses)
                    for w, count in weak_counter.most_common(5):
                        st.markdown(f"- {w}（出现{count}次）")

            # 建议
            if analyzed and st.button("🔮 AI综合提升建议", type="primary", use_container_width=True):
                st.info("基于全部复盘记录的综合分析已整合至各条复盘详情中，请逐条查看AI分析结果。")


# V1.8 新增：面试日程 + 公司背调 + 用户反馈
# ═══════════════════════════════════════

# ── 面试日程管理 ──

SCHEDULE_FILE = "interview_schedule.json"

def load_schedule():
    fpath = os.path.join(get_profile_path(get_active_profile()), SCHEDULE_FILE)
    if not os.path.exists(fpath):
        return []
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_schedule(items):
    fpath = os.path.join(get_profile_path(get_active_profile()), SCHEDULE_FILE)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def render_schedule():
    st.subheader("📅 面试日程管理")

    items = load_schedule()

    tab_s1, tab_s2 = st.tabs(["📋 日程列表", "➕ 添加日程"])

    with tab_s1:
        if not items:
            st.info("暂无日程。添加即将到来的面试或准备任务。")
        else:
            # 按日期排序
            items_sorted = sorted(items, key=lambda x: x.get("date", "9999"))
            upcoming = [i for i in items_sorted if i.get("date", "9999") >= str(date.today())]
            past = [i for i in items_sorted if i.get("date", "9999") < str(date.today())]

            if upcoming:
                st.markdown("### 🔜 即将到来")
                for i, item in enumerate(upcoming):
                    days_left = (datetime.strptime(item["date"], "%Y-%m-%d").date() - date.today()).days
                    urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 3 else "🟢"
                    with st.expander(f"{urgency} {item['date']} | {item.get('type','面试')} | {item.get('company','')} — {item.get('title','')}（{days_left}天后）"):
                        st.markdown(f"**公司/岗位**：{item.get('company','')} — {item.get('position','')}")
                        st.markdown(f"**时间**：{item.get('date','')} {item.get('time','')}")
                        st.markdown(f"**类型**：{item.get('type','面试')} | **状态**：{item.get('status','待确认')}")
                        if item.get("prep_checklist"):
                            st.markdown("**准备清单**：")
                            for j, check in enumerate(item["prep_checklist"]):
                                done = st.checkbox(check["text"], value=check.get("done", False), key=f"check_{i}_{j}")
                                if done != check.get("done", False):
                                    item["prep_checklist"][j]["done"] = done
                                    save_schedule(items)
                                    st.rerun()
                        if item.get("notes"):
                            st.caption(f"📝 {item['notes']}")
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            if st.button("✅ 标记完成", key=f"done_sched_{i}", use_container_width=True):
                                item["status"] = "已完成"
                                save_schedule(items)
                                st.rerun()
                        with col_s2:
                            if st.button("🗑️ 删除", key=f"del_sched_{i}", use_container_width=True):
                                items.pop(items.index(item))
                                save_schedule(items)
                                st.rerun()

            if past:
                st.markdown("### 📂 历史")
                for item in past[:5]:
                    st.caption(f"📌 {item['date']} | {item.get('company','')} — {item.get('title','')} | {item.get('status','')}")

    with tab_s2:
        with st.form("add_schedule"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                sched_date = st.date_input("日期", value=date.today())
                sched_time = st.text_input("时间", placeholder="如：14:00-15:00")
                sched_type = st.selectbox("类型", ["面试", "笔试", "电话沟通", "准备任务", "其他"])
            with col_s2:
                sched_company = st.text_input("公司", placeholder="如：美团")
                sched_position = st.text_input("岗位", placeholder="如：大模型智能客服运营")
                sched_status = st.selectbox("状态", ["待确认", "已确认", "已完成", "已取消"])
            sched_title = st.text_input("标题", placeholder="如：美团二面")
            sched_notes = st.text_area("备注", height=60)

            # 准备清单
            st.caption("准备清单（每行一项）")
            checklist_text = st.text_area("清单内容", height=80, placeholder="研究公司业务和最新动态\n准备自我介绍（2分钟版）\n准备3个反问面试官的问题\n复习JD核心要求")
            if st.form_submit_button("💾 保存日程", type="primary", use_container_width=True):
                checklist = [{"text": line.strip(), "done": False} for line in checklist_text.strip().split("\n") if line.strip()]
                items.append({
                    "id": str(uuid.uuid4())[:8],
                    "date": str(sched_date), "time": sched_time,
                    "type": sched_type, "company": sched_company,
                    "position": sched_position, "title": sched_title or f"{sched_company}{sched_type}",
                    "status": sched_status, "notes": sched_notes,
                    "prep_checklist": checklist,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                save_schedule(items)
                st.success("已保存")
                st.rerun()


# ── 公司背调助手 ──

COMPANY_RESEARCH_PROMPT = """你是求职顾问。根据公司名称，提供面试前需要了解的公司背景信息。

输出JSON：
{
  "overview": "公司一句话介绍",
  "business_lines": ["核心业务线1", "核心业务线2"],
  "recent_news": ["近期动态1（2025-2026）", "近期动态2"],
  "culture": "公司文化特点",
  "interview_tips": ["面试建议1", "面试建议2"],
  "key_prep_points": ["准备重点1", "准备重点2"]
}"""

def render_company_research():
    st.subheader("🏢 公司背调助手")

    company_name = st.text_input("输入公司名称", placeholder="如：美团、得物、百度...")

    if company_name and st.button("🔍 AI背调分析", type="primary", use_container_width=True):
        if not HAS_ANTHROPIC:
            st.error("需要 anthropic SDK")
            return

        with st.spinner(f"正在分析 {company_name}..."):
            try:
                client = Anthropic(base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
                                  api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
                resp = client.messages.create(model=os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
                    max_tokens=1500, temperature=0.3,
                    system="只输出合法JSON。基于公开信息，不确定的标注'待核实'。",
                    messages=[{"role": "user", "content": f"{COMPANY_RESEARCH_PROMPT}\n\n公司：{company_name}"}])
                raw = ""
                for block in resp.content:
                    if hasattr(block, 'text') and block.text:
                        raw = block.text.strip(); break
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if m:
                    result = json.loads(m.group())
                    st.session_state["company_research"] = result
                    st.rerun()
                else:
                    st.error("分析失败，请重试")
            except Exception as e:
                st.error(f"API错误: {e}")

    if st.session_state.get("company_research"):
        result = st.session_state["company_research"]
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("### 📋 公司概况")
            if result.get("overview"):
                st.info(result["overview"])
            if result.get("business_lines"):
                st.markdown("**核心业务**")
                for b in result["business_lines"]:
                    st.markdown(f"- {b}")
            if result.get("culture"):
                st.markdown(f"**文化特点**：{result['culture']}")
        with col_c2:
            if result.get("recent_news"):
                st.markdown("### 📰 近期动态")
                for n in result["recent_news"]:
                    st.markdown(f"- {n}")
            if result.get("interview_tips"):
                st.markdown("### 💡 面试建议")
                for t in result["interview_tips"]:
                    st.markdown(f"- {t}")
        if result.get("key_prep_points"):
            st.markdown("### 🎯 准备重点")
            for p in result["key_prep_points"]:
                st.markdown(f"- ✅ {p}")

        st.caption("⚠️ AI生成内容基于公开信息，仅供参考。面试前建议额外查证最新动态。")


# ── 用户反馈模块 ──

FEEDBACK_FILE = "user_feedback.json"

def save_feedback_entry(entry):
    fpath = os.path.join(get_profile_path(get_active_profile()), FEEDBACK_FILE)  # 用户隔离
    existing = []
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing.append(entry)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def render_feedback():
    st.subheader("💬 用户反馈")

    col_f1, col_f2 = st.columns([3, 2])
    with col_f1:
        st.markdown("### 提交反馈")
        st.caption("报告问题、提出功能建议、分享使用体验")
        with st.form("feedback_form"):
            fb_type = st.selectbox("反馈类型", ["功能建议", "问题报告", "使用体验", "其他"])
            fb_title = st.text_input("标题", placeholder="一句话描述")
            fb_content = st.text_area("详细描述", height=120, placeholder="请详细描述你的需求、问题或建议...")
            fb_priority = st.select_slider("优先级", ["低", "中", "高"], value="中")
            if st.form_submit_button("📤 提交反馈", type="primary", use_container_width=True):
                if fb_title and fb_content:
                    entry = {
                        "id": str(uuid.uuid4())[:8],
                        "type": fb_type, "title": fb_title,
                        "content": fb_content, "priority": fb_priority,
                        "user": get_active_profile(),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "status": "待处理",
                    }
                    save_feedback_entry(entry)
                    st.success("感谢反馈！已记录。")
                    st.rerun()

    with col_f2:
        st.markdown("### 📋 反馈记录")
        fpath = os.path.join(get_profile_path(get_active_profile()), FEEDBACK_FILE)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
            for fb in reversed(feedbacks[-5:]):
                icon = {"功能建议": "💡", "问题报告": "🐛", "使用体验": "💬", "其他": "📌"}.get(fb.get("type", ""), "📌")
                st.caption(f"{icon} [{fb.get('priority','')}] {fb.get('title','')} — {fb.get('created_at','')[:10]}")
        else:
            st.caption("暂无反馈记录")


# ═══════════════════════════════════════
# 后台管理系统
# ═══════════════════════════════════════

ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
DEFAULT_ADMIN = {
    "email": "admin@jobmatcher",
    "password": hash_password("admin123"),
    "name": "系统管理员",
    "role": "admin",
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
}

def init_admin():
    """初始化管理员账号"""
    if not os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_ADMIN, f, ensure_ascii=False, indent=2)

def get_admin():
    if not os.path.exists(ADMIN_FILE):
        init_admin()
    with open(ADMIN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_admin(admin_data):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump(admin_data, f, ensure_ascii=False, indent=2)

def verify_admin(email, password):
    admin = get_admin()
    if email == admin["email"]:
        return verify_password(password, admin["password"])
    return False

def load_all_feedback():
    """收集所有用户的反馈"""
    all_fb = []
    if os.path.exists(PROFILES_DIR):
        for uid in os.listdir(PROFILES_DIR):
            fb_file = os.path.join(PROFILES_DIR, uid, FEEDBACK_FILE)
            if os.path.exists(fb_file):
                with open(fb_file, "r", encoding="utf-8") as f:
                    user_fb = json.load(f)
                # 获取用户名
                info_file = os.path.join(PROFILES_DIR, uid, "info.json")
                user_name = uid
                if os.path.exists(info_file):
                    with open(info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        user_name = info.get("name", uid)
                for fb in user_fb:
                    fb["user_name"] = user_name
                    fb["user_id"] = uid
                all_fb.extend(user_fb)
    return sorted(all_fb, key=lambda x: x.get("created_at", ""), reverse=True)

def get_system_stats():
    """系统统计"""
    users = list_profiles()
    total_records = 0
    total_experiences = 0
    for u in users:
        hist = get_history_file(u["id"])
        if os.path.exists(hist):
            with open(hist, "r", encoding="utf-8") as f:
                total_records += len(json.load(f))
        expf = get_exp_lib_file(u["id"])
        if os.path.exists(expf):
            with open(expf, "r", encoding="utf-8") as f:
                exp = json.load(f)
                total_experiences += len(exp.get("experiences", []))
    return {
        "total_users": len(users),
        "total_applications": total_records,
        "total_experiences": total_experiences,
        "total_feedback": len(load_all_feedback()),
    }

def render_admin_panel():
    """后台管理面板"""
    st.title("🛡️ 后台管理系统")
    st.caption(f"管理员：{get_admin()['email']}")

    admin_tabs = st.tabs(["📊 概览", "💬 反馈管理", "👥 用户管理", "⚙️ 系统配置"])

    # ── Tab1: 概览 ──
    with admin_tabs[0]:
        stats = get_system_stats()
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("总用户数", stats["total_users"])
        with col2: st.metric("总投递记录", stats["total_applications"])
        with col3: st.metric("总经历条目", stats["total_experiences"])
        with col4: st.metric("总反馈数", stats["total_feedback"])

        st.divider()
        st.markdown("### 📋 用户列表")
        users = list_profiles()
        if users:
            user_data = []
            for u in users:
                info_file = os.path.join(PROFILES_DIR, u["id"], "info.json")
                last_login = ""
                if os.path.exists(info_file):
                    with open(info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        last_login = info.get("created_at", "")
                user_data.append({
                    "姓名": u.get("name", ""), "邮箱": u.get("email", ""),
                    "ID": u["id"], "创建时间": last_login,
                })
            st.dataframe(pd.DataFrame(user_data), use_container_width=True, hide_index=True)

    # ── Tab2: 反馈管理 ──
    with admin_tabs[1]:
        st.markdown("### 💬 用户反馈管理")
        all_fb = load_all_feedback()
        if not all_fb:
            st.info("暂无用户反馈")
        else:
            # 筛选
            fb_filter = st.selectbox("状态筛选", ["全部", "待处理", "处理中", "已完成"], key="admin_fb_filter")
            filtered = all_fb
            if fb_filter != "全部":
                filtered = [f for f in all_fb if f.get("status", "待处理") == fb_filter]

            for i, fb in enumerate(filtered):
                status_color = {"待处理": "🟡", "处理中": "🟠", "已完成": "🟢"}.get(fb.get("status", ""), "⚪")
                with st.expander(f"{status_color} [{fb.get('type','')}] {fb.get('title','')} — {fb.get('user_name','')} ({fb.get('created_at','')[:10]})"):
                    st.markdown(f"**用户**：{fb.get('user_name','')} | **优先级**：{fb.get('priority','')}")
                    st.markdown(f"**内容**：{fb.get('content','')}")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        new_status = st.selectbox("状态", ["待处理", "处理中", "已完成"],
                            index=["待处理", "处理中", "已完成"].index(fb.get("status", "待处理")),
                            key=f"adm_status_{i}")
                    with col_f2:
                        admin_note = st.text_input("管理员备注", value=fb.get("admin_note", ""), key=f"adm_note_{i}")
                    with col_f3:
                        if st.button("💾 保存", key=f"adm_save_{i}"):
                            fb["status"] = new_status
                            fb["admin_note"] = admin_note
                            all_fb_copy = load_all_feedback()
                            for orig in all_fb_copy:
                                if orig["id"] == fb["id"]:
                                    orig["status"] = new_status
                                    orig["admin_note"] = admin_note
                                    # 写回对应用户的反馈文件
                                    uid = orig.get("user_id", "")
                                    if uid:
                                        fb_file = os.path.join(PROFILES_DIR, uid, FEEDBACK_FILE)
                                        if os.path.exists(fb_file):
                                            with open(fb_file, "r", encoding="utf-8") as fh:
                                                user_fb = json.load(fh)
                                            for uf in user_fb:
                                                if uf["id"] == fb["id"]:
                                                    uf["status"] = new_status
                                                    uf["admin_note"] = admin_note
                                            with open(fb_file, "w", encoding="utf-8") as fh:
                                                json.dump(user_fb, fh, ensure_ascii=False, indent=2)
                                    break
                            st.success("已保存")
                            st.rerun()

    # ── Tab3: 用户管理 ──
    with admin_tabs[2]:
        st.markdown("### 👥 用户管理")
        users = list_profiles()
        for u in users:
            with st.expander(f"👤 {u.get('name','')} — {u.get('email','')} ({u['id']})"):
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    st.markdown(f"**创建时间**：{u.get('created_at','')}")
                    # 统计该用户数据
                    hist = get_history_file(u["id"])
                    app_count = 0
                    if os.path.exists(hist):
                        with open(hist, "r", encoding="utf-8") as f:
                            app_count = len(json.load(f))
                    st.markdown(f"**投递记录**：{app_count} 条")
                with col_u2:
                    st.markdown(f"**邮箱**：{u.get('email','')}")
                    st.markdown(f"**手机**：{u.get('phone','')}")
                if st.button("🔒 重置密码", key=f"reset_pw_{u['id']}"):
                    # 重置为默认密码
                    info_file = os.path.join(PROFILES_DIR, u["id"], "info.json")
                    if os.path.exists(info_file):
                        with open(info_file, "r", encoding="utf-8") as f:
                            info = json.load(f)
                        info["password"] = hash_password("123456")
                        with open(info_file, "w", encoding="utf-8") as f:
                            json.dump(info, f, ensure_ascii=False, indent=2)
                        st.success(f"密码已重置为 123456")

    # ── Tab4: 系统配置 ──
    with admin_tabs[3]:
        st.markdown("### ⚙️ 系统配置")
        admin_data = get_admin()

        with st.form("admin_config"):
            st.caption("管理员账号设置")
            new_admin_email = st.text_input("管理员邮箱", value=admin_data.get("email", ""))
            new_admin_pw = st.text_input("新密码（留空不修改）", type="password")
            new_admin_name = st.text_input("管理员名称", value=admin_data.get("name", ""))

            if st.form_submit_button("💾 保存配置", type="primary", use_container_width=True):
                admin_data["email"] = new_admin_email
                admin_data["name"] = new_admin_name
                if new_admin_pw:
                    admin_data["password"] = hash_password(new_admin_pw)
                save_admin(admin_data)
                st.success("配置已保存")

        st.divider()
        st.markdown("### 📋 日志")
        st.caption(f"系统启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption(f"数据目录：{DATA_DIR}")
        st.caption(f"用户目录：{PROFILES_DIR}")


# ═══════════════════════════════════════
# 主界面
# ═══════════════════════════════════════

def login_screen():
    """登录界面"""
    st.markdown("<h1 style='text-align:center;margin-top:60px'>🎯 JobMatcher</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#666'>AI 智能投递管理工具</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        profiles = list_profiles()
        if not profiles:
            with st.form("first_login"):
                st.markdown("### 👋 欢迎首次使用")
                name = st.text_input("姓名", value="牟思雨")
                email = st.text_input("邮箱")
                pw = st.text_input("设置密码", type="password")
                pw2 = st.text_input("确认密码", type="password")
                if st.form_submit_button("创建账户并登录", type="primary", use_container_width=True):
                    if not pw or len(pw) < 4:
                        st.error("密码至少4位")
                    elif pw != pw2:
                        st.error("两次密码不一致")
                    else:
                        pid = create_profile(name, email, "", pw)
                        set_active_profile(pid)
                        init_user_data(pid)
                        st.session_state["logged_in"] = True
                        st.rerun()

            st.divider()
            st.caption("或")
            if st.button("🔓 免登录试用（数据不保存）", use_container_width=True):
                st.session_state["logged_in"] = True
                st.session_state["is_guest"] = True
                # 访客使用内存存储
                st.session_state["guest_exp_lib"] = {"basic": {}, "education": [], "skills": [], "experiences": [], "certifications": [], "personal_projects": [], "resume_directions": {}, "interview_entries": []}
                st.session_state["guest_history"] = []
                st.rerun()
        else:
            with st.form("login_form"):
                st.markdown("### 🔐 登录")
                login_email = st.text_input("邮箱", placeholder="输入注册邮箱")
                login_pw = st.text_input("密码", type="password")
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    submit_login = st.form_submit_button("用户登录", type="primary", use_container_width=True)
                with col_l2:
                    submit_admin = st.form_submit_button("🔑 管理员", use_container_width=True)

                if submit_login:
                    found = None
                    for p in profiles:
                        if p.get("email") == login_email:
                            found = p; break
                    if not found:
                        for p in profiles:
                            if p["id"] == login_email:
                                found = p; break
                    if not found:
                        st.error("用户不存在")
                    elif verify_login(found["id"], login_pw):
                        set_active_profile(found["id"])
                        init_user_data(found["id"])
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密码错误")

                if submit_admin:
                    if verify_admin(login_email, login_pw):
                        st.session_state["logged_in"] = True
                        st.session_state["is_admin"] = True
                        st.rerun()
                    else:
                        st.error("管理员验证失败")

            st.divider()
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("➕ 注册新用户", use_container_width=True):
                    st.session_state["show_register"] = True
                    st.rerun()
            with col_b2:
                if st.button("🔓 免登录试用", use_container_width=True):
                    st.session_state["logged_in"] = True
                    st.session_state["is_guest"] = True
                    st.session_state["guest_exp_lib"] = {"basic": {}, "education": [], "skills": [], "experiences": [], "certifications": [], "personal_projects": [], "resume_directions": {}, "interview_entries": []}
                    st.session_state["guest_history"] = []
                    st.rerun()

        if st.session_state.get("show_register"):
            with st.form("register_form"):
                st.markdown("### 📝 创建新账户")
                reg_name = st.text_input("姓名")
                reg_email = st.text_input("邮箱")
                reg_pw = st.text_input("设置密码", type="password")
                if st.form_submit_button("注册", type="primary", use_container_width=True):
                    if not reg_name or not reg_pw:
                        st.error("姓名和密码为必填")
                    else:
                        pid = create_profile(reg_name, reg_email, "", reg_pw)
                        set_active_profile(pid)
                        init_user_data(pid)
                        st.session_state["logged_in"] = True
                        st.session_state["show_register"] = False
                        st.rerun()

        # 设备激活（记住本设备）
        with st.expander("📱 激活本设备（记住登录状态）"):
            with st.form("device_auth"):
                device_key = st.text_input("设备密钥", type="password", placeholder="输入设备密钥以记住本设备")
                if st.form_submit_button("激活设备"):
                    if device_key == DEVICE_SECRET:
                        st.query_params["key"] = DEVICE_SECRET
                        st.session_state["device_authorized"] = True
                        st.success("设备已激活！下次打开自动识别")
                        st.caption("收藏当前网址，以后直接打开即可")
                        st.rerun()
                    else:
                        st.error("密钥错误")


def main():
    # 初始化管理员
    init_admin()

    # 登录检查
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "show_register" not in st.session_state:
        st.session_state["show_register"] = False
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    # 登录检查：已登录用户正常使用，未登录进入登录/试用选择页
    if not st.session_state["logged_in"]:
        login_screen()
        return

    # 非访客用户：初始化数据（真实设备加载种子，其他设备加载模拟数据）
    if not st.session_state.get("is_guest"):
        init_user_data(get_active_profile())

    # 访客模式标识
    if st.session_state.get("is_guest"):
        st.warning("🔒 试用模式：数据不会保存，刷新后丢失。登录后可永久保存数据。", icon="🔒")

    # 管理员模式（仍可通过侧边栏手动切换）
    if st.session_state.get("is_admin"):
        render_admin_panel()
        # 侧边栏最小化
        with st.sidebar:
            st.markdown("### 🛡️ 管理员模式")
            if st.button("🚪 退出管理", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state["logged_in"] = False
                st.rerun()
        return

    st.title("🎯 JobMatcher")
    if is_owner_device():
        st.success("🔑 已识别为真实数据设备", icon="🔑")
    # 不暴露密钥状态给其他设备
    st.caption("v1.8 — JobMatcher：投递+分析+定制+求职信+面试预测+复盘+日程+背调+反馈")

    # 检查依赖
    if not HAS_ANTHROPIC:
        st.warning("⚠️ anthropic SDK 未安装，JD分析功能不可用。运行: pip install anthropic")

    # 初始化 session state
    if "editing_record" not in st.session_state:
        st.session_state["editing_record"] = None
    if "deleting_record" not in st.session_state:
        st.session_state["deleting_record"] = None
    if "match_result" not in st.session_state:
        st.session_state["match_result"] = None
    if "jd_analysis" not in st.session_state:
        st.session_state["jd_analysis"] = None
    if "edited_resume" not in st.session_state:
        st.session_state["edited_resume"] = ""
    if "jd_to_analyze" not in st.session_state:
        st.session_state["jd_to_analyze"] = ""
    if "career_analysis" not in st.session_state:
        st.session_state["career_analysis"] = None
    if "generated_resume" not in st.session_state:
        st.session_state["generated_resume"] = ""
    if "dedup_result" not in st.session_state:
        st.session_state["dedup_result"] = None
    if "show_new_profile" not in st.session_state:
        st.session_state["show_new_profile"] = False
    if "predicted_questions" not in st.session_state:
        st.session_state["predicted_questions"] = None
    if "apply_target" not in st.session_state:
        st.session_state["apply_target"] = None
    if "apply_step" not in st.session_state:
        st.session_state["apply_step"] = 1
    if "discovered_jobs" not in st.session_state:
        st.session_state["discovered_jobs"] = None
    if "is_guest" not in st.session_state:
        st.session_state["is_guest"] = False
    if "device_authorized" not in st.session_state:
        st.session_state["device_authorized"] = False

    records = load_history()

    # 侧边栏
    with st.sidebar:
        st.header("📂 导航")
        page = st.radio("模块导航", [
            "📋 投递记录", "📊 投递看板", "➕ 新增投递",
            "🔍 JD分析", "📝 简历定制", "✉️ 求职信",
            "🎯 面试预测", "🔄 面试复盘", "📅 日程管理",
            "🏢 公司背调", "📚 经历库", "🚀 半自动投递",
            "🌐 JD搜索", "💬 反馈", "⚙️ 设置",
        ], key="nav")

        st.divider()
        if st.session_state.get("is_guest"):
            st.caption("🔒 试用模式 · 数据不保存")
            st.caption(f"📝 投递记录：{len(records)}")
            if st.button("🔐 注册/登录以保存数据", use_container_width=True, type="primary"):
                st.session_state["logged_in"] = False
                st.session_state["is_guest"] = False
                st.rerun()
        else:
            st.caption("✅ 已登录 · 数据自动保存")
            st.caption(f"📝 投递记录：{len(records)}")
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()

    # 路由
    if page == "📋 投递记录":
        render_edit_dialog(records.copy())
        render_record_list(records.copy())

    elif page == "📊 投递看板":
        render_pipeline_kanban()

    elif page == "➕ 新增投递":
        render_add_form()

    elif page == "🔍 JD分析":
        render_jd_analysis()

    elif page == "📝 简历定制":
        render_resume_customizer()

    elif page == "🌐 JD搜索":
        render_jd_search()

    elif page == "📚 经历库":
        render_experience_library()

    elif page == "🚀 半自动投递":
        render_auto_apply()

    elif page == "✉️ 求职信":
        render_cover_letter_page()

    elif page == "🎯 面试预测":
        render_interview_prep_page()

    elif page == "🔄 面试复盘":
        render_interview_review()

    elif page == "📅 日程管理":
        render_schedule()

    elif page == "🏢 公司背调":
        render_company_research()

    elif page == "💬 反馈":
        render_feedback()

    elif page == "⚙️ 设置":
        render_settings_page()


if __name__ == "__main__":
    main()
