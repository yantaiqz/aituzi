import streamlit as st
import google.generativeai as genai
from zhipuai import ZhipuAI
import PyPDF2
from docx import Document
from PIL import Image
import io
import json
import time
import sqlite3
import uuid
import datetime

# -------------------------------------------------------------
# 页面配置（必须放在最前面）
# -------------------------------------------------------------
st.set_page_config(
    page_title="AI兔子 内容与剽窃检测系统",
    page_icon="🐰",
    layout="wide",
    initial_sidebar_state="collapsed"  # 强制折叠侧边栏
)

# -------------------------- 全局样式优化（紧凑化核心） --------------------------
st.markdown("""
<style>
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    
    /* 全局紧凑化 */
    .stApp {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 98% !important;
    }
    
    /* 标题样式（更紧凑） */
    .main-header {
        font-size: 1.8rem !important;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem !important;
        font-weight: 700;
        line-height: 1.2;
    }
    .sub-header {
        font-size: 1rem !important;
        color: #555;
        text-align: center;
        margin-bottom: 1rem !important;
        line-height: 1.3;
    }
    
    /* 结果卡片（更紧凑） */
    .result-card {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        line-height: 1.4;
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4caf50, #ffeb3b, #f44336);
    }
    
    /* 警告文本 */
    .warning-text {
        color: #e65100;
        font-size: 0.85rem !important;
        font-style: italic;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
    }
    
    /* 模型配置卡片 */
    .model-config-card {
        background-color: #e8f4f8;
        border-radius: 8px;
        padding: 12px !important;
        margin-bottom: 15px !important;
        border-left: 4px solid #1E88E5;
    }
    
    /* 单选按钮横向排列 */
    .stRadio > div {
        flex-direction: row !important;
        gap: 15px !important;
        justify-content: center !important;
        margin-bottom: 0.5rem !important;
    }
    .stRadio label {
        font-size: 0.9rem !important;
    }
    
    /* 快捷按钮容器（核心紧凑化） */
    .shortcut-btn-container {
        display: flex;
        gap: 8px !important;
        margin-bottom: 10px !important;
        width: 100%;
        flex-wrap: nowrap;
        overflow-x: auto;
        padding: 3px 0 !important;
    }
    .shortcut-btn-container > button {
        flex: 1;
        min-width: 140px !important;
        padding: 6px 4px !important;
        border-radius: 6px !important;
        border: 1px solid #1E88E5;
        background-color: #e8f4f8;
        color: #1E88E5;
        font-size: 0.8rem !important;
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
        height: 36px !important;
    }
    .shortcut-btn-container > button:hover {
        background-color: #1E88E5;
        color: white;
        border-color: #1976D2;
    }
    
    /* 统计模块（紧凑化） */
    .metric-container {
        display: flex;
        justify-content: center;
        gap: 15px !important;
        margin-top: 15px !important;
        margin-bottom: 5px !important;
        padding: 8px !important;
        background-color: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .metric-box {
        text-align: center;
    }
    .metric-sub {
        font-size: 0.75rem !important;
        color: #6c757d;
        line-height: 1.2;
    }
    
    /* 按钮样式统一 */
    .stButton > button {
        box-shadow: none !important;
        padding: 6px 12px !important;
        font-size: 0.9rem !important;
        border-radius: 6px !important;
        height: auto !important;
    }
    .stButton > button[type="primary"] {
        padding: 8px 16px !important;
    }
    
    /* 文本输入框紧凑化 */
    .stTextArea textarea {
        height: 160px !important;
        font-size: 0.9rem !important;
        padding: 8px !important;
    }
    
    /* 标签页样式优化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        margin-bottom: 0.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 6px 12px !important;
        font-size: 0.9rem !important;
    }
    
    /* 右上角按钮样式 */
    .neal-btn {
        font-family: 'Inter', sans-serif;
        background: #fff;
        border: 1px solid #e5e7eb;
        color: #111;
        font-weight: 600;
        font-size: 0.85rem !important;
        padding: 6px 12px !important;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
        text-decoration: none !important;
        width: 100%;
        height: 36px !important;
    }
    .neal-btn:hover {
        background: #f9fafb;
        border-color: #111;
        transform: translateY(-1px);
    }
    .neal-btn-link { 
        text-decoration: none; 
        width: 100%; 
        display: block; 
    }
    
    /* 上传组件紧凑化 */
    .stFileUploader {
        margin-bottom: 0.5rem !important;
    }
    .stFileUploader label {
        font-size: 0.9rem !important;
    }
    
    /* 图片预览紧凑化 */
    .stImage {
        margin-bottom: 0.5rem !important;
    }
    
    /* 展开栏紧凑化 */
    .stExpander {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .stExpanderHeader {
        padding: 6px 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------- 右上角功能区（紧凑化） --------------------------
col_empty, col_more = st.columns([0.85, 0.15])  # 调整列宽比例，更紧凑

with col_more:
    st.markdown(
        f"""
        <a href="https://haowan.streamlit.app/" target="_blank" class="neal-btn-link">
            <button class="neal-btn">✨ 更多好玩应用</button>
        </a>
        """, 
        unsafe_allow_html=True
    )

# -------------------------------------------------------------
# 1. 示例文本配置
# -------------------------------------------------------------
SAMPLE_TEXTS = {
    "示例1：人工-成人文学": """
人生最宝贵的是生命，生命属于人只有一次。一个人的生命应当这样度过：当他回忆往事的时候，他不致因虚度年华而悔恨，也不致因碌碌无为而羞愧；在临死的时候，他能够说：“我的整个生命和全部精力，都已献给世界上最壮丽的事业 —— 为人类的解放而斗争。
    """,
    "示例2：AI生成-武侠": """
林风紧握着手中的长剑，眼神中透露出一丝决绝。对面的黑衣人冷笑一声，身形瞬间消失在原地。 当然，以下是为您续写的打斗场景： 空气中爆发出刺耳的音爆声，黑衣人的匕首直刺林风的咽喉。林风侧身一闪，长剑顺势上撩……
    """,
    "示例3：人工-小学作文": """
欢乐海岸非常好玩，因为不仅有好玩的还有好吃的。一到周未那里就人山人海，欢乐海岸分成商场、户外活动区和海景区。一天上午我和妈妈还有爸爸一起去欢乐海岸去吃午饭。我们午饭吃的是西贝吃完饭之后看见西贝旁边有卖瓜的我买一桶吃了起来。吃着吃着我又想吃冰淇淋。过了一会儿我看见有冰淇淋我买了一个吃；吃完之后，我还去了探洞工场。我们买了票之后去玩，玩累的时候我就回家了。真是开心又美好的一天。
    """,
    "示例4：AI-花生酱与圣经": """
And lo, the Lord spoke unto His people, saying, "For thou shalt take thine peanut butter sandwich from out of the VCR, using great care and caution. First, thou shalt gently pull on the edges of the sandwich, so that it may be loosened from its place. Next, thou shalt tilt the VCR on its side, so that the sandwich may slide forth and be removed. Finally, thou shalt give thanks to the Lord for His guidance and assistance, and partake of the sandwich with joy and gratitude." Amen.
    """
}

# -------------------------------------------------------------
# 2. 核心分析逻辑与 Prompt
# -------------------------------------------------------------
ANALYSIS_SYSTEM_PROMPT = """
你是一位专业的法医语言学家和学术诚信专家。你的任务是分析用户提供的文本（或图片中的文字），完成以下两个核心任务：

1. **AI 生成检测**：判断文本是否由 AI 生成。分析行文逻辑、词汇重复度、情感连贯性、幻觉特征等。
    - 分类标准：
      - "AI特征" (80%-100%): 极高概率由 AI 生成。
      - "疑似AI" (40%-79%): 混合特征，无法确定，但有明显 AI 痕迹。
      - "人工特征" (0%-39%): 具有典型的人类写作特征（如个人经历、非标准语法、情感细微差别）。

2. **剽窃/抄袭检测**：判断文本是否存在抄袭嫌疑。
    - 基于你的训练数据，分析文本是否与知名文章、论文、网络内容高度雷同。
    - 如果发现抄袭，请指出可能的来源。

请务必以严格的 **JSON 格式**返回结果，不要包含 Markdown 代码块标记（```json ... ```），直接返回 JSON 字符串。格式如下：

{
    "ai_detection": {
        "label": "AI特征" | "疑似AI" | "人工特征",
        "score": 0-100,
        "reason": "详细的分析理由，列出具体的特征点（如：过度使用连接词、缺乏具体细节、逻辑过于完美等）。"
    },
    "plagiarism_detection": {
        "percentage": 0-100,
        "reason": "详细的分析理由。",
        "sources": "列出可能的原文来源，如果没有发现明显来源，请填'未在训练数据中发现明显匹配源'。"
    }
}
"""

# -------------------------------------------------------------
# 3. 工具函数：文档解析
# -------------------------------------------------------------
def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"PDF 解析失败: {e}")
        return None

def extract_text_from_docx(file):
    try:
        doc = Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        st.error(f"Word 解析失败: {e}")
        return None

# -------------------------------------------------------------
# 4. 模型调用函数
# -------------------------------------------------------------
def analyze_with_zhipu(api_key, content, is_image=False, image_data=None):
    """使用智谱 AI 进行分析"""
    if not api_key:
        return {"error": "未检测到智谱 API Key，请检查 secrets 配置。"}
    
    client = ZhipuAI(api_key=api_key)
    
    try:
        if is_image and image_data:
            # 图片模式 (GLM-4V)
            import base64
            img_byte_arr = io.BytesIO()
            image_data.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            
            response = client.chat.completions.create(
                model="glm-4v", 
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": ANALYSIS_SYSTEM_PROMPT + "\n\n请分析这张图片中的文字内容："
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            )
        else:
            # 文本模式 (GLM-4)
            response = client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ],
                temperature=0.1
            )
            
        return json.loads(response.choices[0].message.content.replace('```json', '').replace('```', ''))
    
    except json.JSONDecodeError:
        return {"error": "模型返回格式解析失败，请重试。"}
    except Exception as e:
        return {"error": f"智谱 API 调用失败: {str(e)}"}

def analyze_with_gemini(api_key, content, is_image=False, image_data=None):
    """使用 Google Gemini 进行分析"""
    if not api_key:
        return {"error": "未检测到 Gemini API Key，请检查 secrets 配置。"}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=ANALYSIS_SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"}
        )
        
        if is_image and image_data:
            response = model.generate_content([
                "请分析这张图片中的文字内容，并按照系统提示的 JSON 格式输出。", 
                image_data
            ])
        else:
            response = model.generate_content(content)
            
        return json.loads(response.text)
        
    except Exception as e:
        return {"error": f"Gemini API 调用失败: {str(e)}"}

# -------------------------------------------------------------
# 5. 访问统计逻辑
# -------------------------------------------------------------
DB_FILE = "aituzi_visit_stats.db"

def init_db():
    """初始化数据库（包含自动修复旧表结构的功能）"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 1. 确保表存在
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic 
                 (date TEXT PRIMARY KEY, 
                  pv_count INTEGER DEFAULT 0)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                 (visitor_id TEXT PRIMARY KEY, 
                  first_visit_date TEXT)''')
    
    # 2. 手动检查并添加缺失的列
    c.execute("PRAGMA table_info(visitors)")
    columns = [info[1] for info in c.fetchall()]
    
    if "last_visit_date" not in columns:
        try:
            c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
            c.execute("UPDATE visitors SET last_visit_date = first_visit_date WHERE last_visit_date IS NULL")
        except Exception as e:
            print(f"数据库升级失败: {e}")

    conn.commit()
    conn.close()

def get_visitor_id():
    """获取或生成访客ID"""
    if "visitor_id" not in st.session_state:
        st.session_state["visitor_id"] = str(uuid.uuid4())
    return st.session_state["visitor_id"]

def track_and_get_stats():
    """核心统计逻辑"""
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    today_str = datetime.datetime.utcnow().date().isoformat()
    visitor_id = get_visitor_id()

    # --- 写操作 (仅当本Session未计数时执行) ---
    if "has_counted" not in st.session_state:
        try:
            # 1. 更新每日PV
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))
            
            # 2. 更新访客UV信息
            c.execute("SELECT visitor_id FROM visitors WHERE visitor_id=?", (visitor_id,))
            exists = c.fetchone()
            
            if exists:
                c.execute("UPDATE visitors SET last_visit_date=? WHERE visitor_id=?", (today_str, visitor_id))
            else:
                c.execute("INSERT INTO visitors (visitor_id, first_visit_date, last_visit_date) VALUES (?, ?, ?)", 
                          (visitor_id, today_str, today_str))
            
            conn.commit()
            st.session_state["has_counted"] = True
            
        except Exception as e:
            st.error(f"数据库写入错误: {e}")

    # --- 读操作 ---
    # 1. 获取今日UV
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    # 2. 获取历史总UV
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    # 3. 获取今日PV
    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    
    return today_uv, total_uv, today_pv

# -------------------------------------------------------------
# 6. UI 布局与主逻辑（紧凑化）
# -------------------------------------------------------------
# 页面标题（更紧凑）
st.markdown('<div class="main-header">🐰 AI兔子 内容与剽窃检测系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">上传文档、图片或输入文本，一键检测 AI 生成痕迹与内容剽窃风险</div>', unsafe_allow_html=True)

# 模型选择（更紧凑）
model_provider = st.radio(
    "选择分析模型",
    ("智谱 AI (默认)", "Google Gemini (进阶)"),
    captions=["免费访问，GLM-4模型", "多模态能力强，Gemini-2.5模型"],
    key="model_selector",
    label_visibility="collapsed"  # 隐藏标签，更紧凑
)

# 初始化会话状态
if "sample_text" not in st.session_state:
    st.session_state.sample_text = ""

# 输入方式选项卡
tab1, tab2, tab3 = st.tabs(["📝 文本输入", "📂 文档上传", "🖼️ 图片分析"])

content_to_analyze = ""
image_to_analyze = None
is_image_mode = False
process_trigger = False

with tab1:
    # 快捷按钮并排容器
    st.markdown('<div class="shortcut-btn-container">', unsafe_allow_html=True)
    btn_cols = st.columns(4)
    for idx, (btn_label, sample_content) in enumerate(SAMPLE_TEXTS.items()):
        with btn_cols[idx]:
            if st.button(btn_label, key=f"btn_sample_{btn_label}", use_container_width=True):
                st.session_state.sample_text = sample_content.strip()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 文本输入框（更紧凑）
    text_input = st.text_area(
        "",  # 隐藏标签
        value=st.session_state.sample_text,
        placeholder="在此粘贴或输入需要检测的文字...",
        key="text_input"
    )
    
    col_btn1, col_empty1 = st.columns([0.2, 0.8])
    with col_btn1:
        if st.button("开始分析", key="btn_text", type="primary", use_container_width=True):
            if text_input.strip():
                content_to_analyze = text_input
                process_trigger = True
            else:
                st.warning("请输入文字。")

with tab2:
    uploaded_file = st.file_uploader("上传PDF/Word文档", type=['pdf', 'docx'], label_visibility="collapsed")
    
    col_btn2, col_empty2 = st.columns([0.2, 0.8])
    with col_btn2:
        if st.button("开始分析", key="btn_doc", type="primary", use_container_width=True):
            if uploaded_file:
                with st.spinner("解析文档中..."):
                    if uploaded_file.name.endswith('.pdf'):
                        content_to_analyze = extract_text_from_pdf(uploaded_file)
                    elif uploaded_file.name.endswith('.docx'):
                        content_to_analyze = extract_text_from_docx(uploaded_file)
                    
                    if content_to_analyze and len(content_to_analyze) > 10:
                        process_trigger = True
                        st.success(f"解析成功！{len(content_to_analyze)} 字")
                    else:
                        st.error("解析失败或内容为空")
            else:
                st.warning("请先上传文件")

with tab3:
    uploaded_image = st.file_uploader("上传包含文字的图片", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
    if uploaded_image:
        image_to_analyze = Image.open(uploaded_image)
        st.image(image_to_analyze, caption="预览", use_container_width=True)
        
        col_btn3, col_empty3 = st.columns([0.2, 0.8])
        with col_btn3:
            if st.button("开始分析", key="btn_img", type="primary", use_container_width=True):
                is_image_mode = True
                process_trigger = True

# --- 执行分析 ---
if process_trigger:
    # 获取API Key
    current_api_key = None
    try:
        if "Gemini" in model_provider:
            current_api_key = st.secrets.get("GEMINI_API_KEY")
        else:
            current_api_key = st.secrets.get("ZHIPU_API_KEY")
    except:
        st.error("❌ 请配置API Key")
        st.stop()
    
    if not current_api_key:
        st.error("❌ API Key未配置")
        st.stop()

    with st.spinner(f"分析中（{model_provider}）..."):
        start_time = time.time()
        
        # 调用模型
        if "Gemini" in model_provider:
            result = analyze_with_gemini(current_api_key, content_to_analyze, is_image_mode, image_to_analyze)
        else:
            result = analyze_with_zhipu(current_api_key, content_to_analyze, is_image_mode, image_to_analyze)
        
        end_time = time.time()

    # 结果展示（紧凑化）
    if "error" in result:
        st.error(result["error"])
    else:
        st.toast(f"分析完成！耗时 {end_time - start_time:.2f} 秒")
        
        # 解析结果
        ai_data = result.get("ai_detection", {})
        copy_data = result.get("plagiarism_detection", {})
        
        # AI检测结果
        st.markdown("### 🤖 AI生成检测")
        col1, col2 = st.columns([0.3, 0.7])
        
        with col1:
            score = ai_data.get("score", 0)
            label = ai_data.get("label", "未知")
            color = "green" if score < 40 else "orange" if score < 80 else "red"
            
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; border: 2px solid {color}; border-radius: 8px;">
                <h3 style="color: {color}; margin: 0; font-size: 1rem;">{label}</h3>
                <h2 style="font-size: 2rem; margin: 5px 0;">{score}%</h2>
                <p style="color: #666; font-size: 0.8rem; margin: 0;">AI疑似度</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(f"**判定理由：** {ai_data.get('reason', '无')}")
            st.progress(score / 100)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # 剽窃检测结果
        st.markdown("### 📝 剽窃/抄袭检测")
        col3, col4 = st.columns([0.3, 0.7])
        
        with col3:
            copy_score = copy_data.get("percentage", 0)
            copy_color = "green" if copy_score < 20 else "orange" if copy_score < 50 else "red"
            
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; border: 2px solid {copy_color}; border-radius: 8px;">
                <h3 style="color: {copy_color}; margin: 0; font-size: 1rem;">剽窃风险</h3>
                <h2 style="font-size: 2rem; margin: 5px 0;">{copy_score}%</h2>
                <p style="color: #666; font-size: 0.8rem; margin: 0;">重复率预估</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(f"**分析详情：** {copy_data.get('reason', '无')}")
            st.markdown(f"**来源：** {copy_data.get('sources', '未知')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 原始数据
        with st.expander("🔍 原始数据", expanded=False):
            st.json(result)

        # 免责声明
        st.markdown("""
        <div class="warning-text">
        ⚠️ 免责声明：检测结果仅供参考，不构成学术/法律依据，请人工核实。
        </div>
        """, unsafe_allow_html=True)

# --- 访问统计展示（紧凑化） ---
try:
    today_uv, total_uv, today_pv = track_and_get_stats()
except Exception as e:
    today_uv, total_uv, today_pv = 0, 0, 0

st.markdown(f"""
<div class="metric-container">
    <div class="metric-box">
        <div class="metric-sub">今日 UV: {today_uv} | PV: {today_pv}</div>
    </div>
    <div class="metric-box">
        <div class="metric-sub">历史总 UV: {total_uv}</div>
    </div>
</div>
""", unsafe_allow_html=True)
