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
import hashlib

# -------------------------------------------------------------
# 1. 页面配置与 CSS 样式（新增快捷按钮样式）
# -------------------------------------------------------------
st.set_page_config(
    page_title="AI兔子 内容与剽窃检测系统",
    page_icon="🐰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义 CSS 美化界面（新增快捷按钮样式）
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 20px;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 40px;
    }
    .result-card {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-label {
        font-weight: bold;
        color: #333;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4caf50, #ffeb3b, #f44336);
    }
    .warning-text {
        color: #e65100;
        font-size: 0.9rem;
        font-style: italic;
    }
    .model-config-card {
        background-color: #e8f4f8;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 30px;
        border-left: 4px solid #1E88E5;
    }
    .stRadio > div {
        flex-direction: row;
        gap: 20px;
        justify-content: center;
    }
    /* 新增：内嵌上传按钮样式 */
    .upload-container {
        margin: 10px 0;
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .upload-btn {
        flex: 1;
        min-width: 120px;
    }
    .file-info {
        font-size: 0.85rem;
        color: #2196F3;
        margin-top: 5px;
    }
    .text-area-container {
        position: relative;
    }
    /* 新增：快捷按钮样式 */
    .shortcut-btn-container {
        display: flex;
        gap: 10px;
        margin-bottom: 15px;
        flex-wrap: wrap;
    }
    .shortcut-btn {
        padding: 8px 16px;
        border-radius: 6px;
        border: 1px solid #1E88E5;
        background-color: #e8f4f8;
        color: #1E88E5;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s ease;
    }
    .shortcut-btn:hover {
        background-color: #1E88E5;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

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
# 3. 示例文本配置（可自定义修改）
# -------------------------------------------------------------
SAMPLE_TEXTS = {
    "示例一（AI生成文本）": """
人工智能技术的快速发展正深刻改变着人类社会的生产与生活方式。从工业自动化到智能家居，从医疗诊断到金融风控，AI 技术的应用场景日益广泛。其核心优势在于能够高效处理海量数据，发现人类难以察觉的规律与趋势。

在教育领域，AI 可以实现个性化教学，根据学生的学习进度和能力水平定制学习方案。在交通领域，自动驾驶技术有望大幅降低交通事故发生率，提升出行效率。然而，AI 技术的发展也带来了诸如数据隐私、就业结构调整等问题，需要通过完善的法律法规和伦理框架加以规范。
    """,
    "示例二（AI生成文本）": """
随着全球数字化进程的加速，云计算作为新一代信息技术的核心，已经成为企业数字化转型的重要支撑。云计算具有资源池化、按需分配、弹性扩展等特点，能够帮助企业降低 IT 基础设施成本，提升运营效率。

从公有云到私有云，从混合云到边缘云，云计算的形态不断演进，以满足不同行业的多样化需求。在金融行业，云计算可以支撑高频交易和风险建模；在制造业，云计算能够实现生产数据的实时分析与优化。未来，随着 5G 技术和物联网的融合发展，云计算的应用边界将进一步拓展。
    """,
    "示例三（人工编写文本）": """
今天早上我六点半就醒了，窗外的天还是灰蒙蒙的，听见楼下有卖豆浆油条的吆喝声，突然就很想吃。磨蹭了十分钟才起床，洗漱完下楼的时候，那个大爷的摊子已经快收了，还好剩最后一份，热乎乎的油条泡在豆浆里，简直是人间美味！

上午在家写作业，数学的最后一道大题卡了我快一个小时，草稿纸用了三张，最后还是去问了隔壁的姐姐，她讲的方法比老师的简单多了，一下子就懂了。下午和同学去公园打球，风有点大，但是玩得特别开心，回家的时候天都黑了，妈妈做了我爱吃的红烧肉，今天真是充实的一天。
    """,
    "示例四（人工编写文本）": """
我家的小猫叫咪咪，是去年冬天从楼下捡回来的流浪猫，刚来的时候瘦瘦小小的，毛都打结了，还特别怕人，躲在沙发底下好几天不肯出来。我每天都给它喂猫粮和温水，慢慢的它才敢出来蹭我的腿。

现在咪咪已经长成一只胖乎乎的大猫了，黄色的毛油光水滑的，特别喜欢趴在我的书桌上睡觉，有时候还会踩我的笔记本键盘，把我写了一半的文档弄乱。虽然经常捣乱，但每次我不开心的时候，它都会跳上我的膝盖，用小脑袋蹭我的手，瞬间就觉得心情好多了。咪咪真是我最好的小伙伴！
    """
}

# -------------------------------------------------------------
# 4. 工具函数：文档解析
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

def extract_text_from_image(image):
    """从图片中提取文字（复用模型的多模态能力）"""
    try:
        # 先尝试用PIL处理图片
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr
    except Exception as e:
        st.error(f"图片处理失败: {e}")
        return None

# -------------------------------------------------------------
# 5. 模型调用函数
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
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
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
                Image.open(io.BytesIO(image_data))
            ])
        else:
            response = model.generate_content(content)
            
        return json.loads(response.text)
        
    except Exception as e:
        return {"error": f"Gemini API 调用失败: {str(e)}"}

# -------------------------------------------------------------
# 6. 访问统计逻辑
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

def get_stable_visitor_id():
    """
    生成稳定的访客ID：基于用户设备特征（浏览器/语言/时区等），跨会话不变
    无需获取IP/隐私信息，仅使用Streamlit可获取的公开客户端信息
    """
    # 优先从 cookies 读取已生成的访客ID（跨会话持久化）
    if "visitor_id_stable" in st.session_state:
        return st.session_state["visitor_id_stable"]
    
    try:
        # 1. 获取客户端特征（Streamlit 1.28+ 支持）
        client_info = st.runtime.get_instance()._session_client_info
        # 提取稳定的设备特征（避免敏感信息）
        device_fingerprint = {
            "browser": client_info.get("browser", "unknown"),
            "browser_version": client_info.get("browser_version", "unknown"),
            "os": client_info.get("os", "unknown"),
            "language": client_info.get("language", "unknown"),
            "screen_resolution": client_info.get("screen_resolution", "unknown"),
            "timezone": client_info.get("timezone", "unknown")
        }
        
        # 2. 对特征进行哈希（生成固定长度的唯一标识）
        fingerprint_str = json.dumps(device_fingerprint, sort_keys=True)
        stable_id = hashlib.md5(fingerprint_str.encode()).hexdigest()  # MD5仅用于生成标识，无安全风险
        
    except Exception as e:
        # 降级方案：若无法获取客户端信息，使用浏览器本地存储（cookies）
        stable_id = st.query_params.get("vid", str(uuid.uuid4()))
        # 将ID写入查询参数，供下次访问使用
        st.query_params["vid"] = stable_id
    
    # 3. 持久化到会话状态
    st.session_state["visitor_id_stable"] = stable_id
    return stable_id

def track_and_get_stats():
    """修复版：使用稳定访客ID，避免同一用户重复计UV"""
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    today_str = datetime.datetime.utcnow().date().isoformat()
    visitor_id = get_stable_visitor_id()  # 替换为稳定ID生成函数

    # --- 1. PV 统计：每次页面加载都+1 ---
    c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
    c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))

    # --- 2. UV 统计：仅新访客（稳定ID未存在）才+1 ---
    c.execute("SELECT visitor_id FROM visitors WHERE visitor_id=?", (visitor_id,))
    exists = c.fetchone()
    
    if not exists:
        # 新访客：插入记录（UV+1）
        c.execute("INSERT INTO visitors (visitor_id, first_visit_date, last_visit_date) VALUES (?, ?, ?)", 
                  (visitor_id, today_str, today_str))
    else:
        # 老访客：仅更新最后访问时间
        c.execute("UPDATE visitors SET last_visit_date=? WHERE visitor_id=?", (today_str, visitor_id))

    conn.commit()  # 必须提交所有修改

    # --- 读取统计数据 ---
    # 今日 UV：今日有访问记录的唯一访客数
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    # 历史总 UV：所有唯一访客数
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    # 今日 PV
    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    
    return today_uv, total_uv, today_pv

# -------------------------------------------------------------
# 7. 主UI布局（核心：新增快捷按钮+文本框内嵌上传功能）
# -------------------------------------------------------------
# 页面标题
st.markdown('<div class="main-header">🐰 AI兔子 内容与剽窃检测系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">输入文本、上传文档/图片，一键检测 AI 生成痕迹与内容剽窃风险</div>', unsafe_allow_html=True)

# 模型选择
model_provider = st.radio(
    "选择分析模型",
    ("智谱 AI (默认)", "Google Gemini (进阶)"),
    captions=["免费访问，GLM-4模型", "多模态能力强，Gemini-2.5模型"],
    key="model_selector"
)

st.markdown("---")

# 初始化会话状态
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "uploaded_image_data" not in st.session_state:
    st.session_state.uploaded_image_data = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = ""
if "is_image_mode" not in st.session_state:
    st.session_state.is_image_mode = False

# 核心：文本输入区域（新增快捷按钮）
st.markdown("### 📝 输入待检测内容")

# -------------------------- 新增快捷按钮 --------------------------
st.markdown('<div class="shortcut-btn-container">', unsafe_allow_html=True)
for btn_label, sample_text in SAMPLE_TEXTS.items():
    if st.button(btn_label, key=f"btn_{btn_label}", use_container_width=False):
        st.session_state.input_text = sample_text.strip()
        st.session_state.is_image_mode = False
        st.session_state.uploaded_file_name = ""
st.markdown('</div>', unsafe_allow_html=True)
# ------------------------------------------------------------------

# 文本输入框
text_input = st.text_area(
    "在此粘贴文本，或上传文档/图片自动提取文字",
    value=st.session_state.input_text,
    height=200,
    key="main_text_area"
)
# 同步输入框内容到会话状态
st.session_state.input_text = text_input

# 内嵌上传按钮区域
st.markdown('<div class="upload-container">', unsafe_allow_html=True)
# 文档上传按钮
doc_file = st.file_uploader(
    "上传文档 (PDF/Word)",
    type=['pdf', 'docx'],
    key="doc_uploader",
    label_visibility="collapsed"
)

# 图片上传按钮
img_file = st.file_uploader(
    "上传图片 (PNG/JPG)",
    type=['png', 'jpg', 'jpeg'],
    key="img_uploader",
    label_visibility="collapsed"
)
st.markdown('</div>', unsafe_allow_html=True)

# 处理文档上传
if doc_file:
    with st.spinner("正在解析文档..."):
        file_name = doc_file.name
        if file_name.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(doc_file)
        elif file_name.endswith('.docx'):
            extracted_text = extract_text_from_docx(doc_file)
        
        if extracted_text and len(extracted_text) > 10:
            st.session_state.input_text = extracted_text
            st.session_state.uploaded_file_name = file_name
            st.session_state.is_image_mode = False
            st.success(f"✅ 文档《{file_name}》解析成功！共 {len(extracted_text)} 字")
            st.rerun()
        else:
            st.error("❌ 文档解析失败或内容为空")

# 处理图片上传
if img_file:
    with st.spinner("正在处理图片..."):
        image = Image.open(img_file)
        st.image(image, caption=f"预览：{img_file.name}", width=300)
        image_data = extract_text_from_image(image)
        if image_data:
            st.session_state.uploaded_image_data = image_data
            st.session_state.uploaded_file_name = img_file.name
            st.session_state.is_image_mode = True
            st.session_state.input_text = ""  # 图片模式清空文本框
            st.success(f"✅ 图片《{img_file.name}》上传成功！")
        else:
            st.error("❌ 图片处理失败")

# 显示已上传文件信息
if st.session_state.uploaded_file_name:
    st.markdown(f'<div class="file-info">当前已加载：{st.session_state.uploaded_file_name}</div>', unsafe_allow_html=True)

# 分析按钮
process_trigger = False
col1, col2 = st.columns([1, 10])
with col1:
    if st.button("开始分析", type="primary", key="btn_analyze"):
        # 检查输入
        if st.session_state.input_text.strip() or (st.session_state.is_image_mode and st.session_state.uploaded_image_data):
            process_trigger = True
        else:
            st.warning("⚠️ 请输入文本或上传有效文件")

# --- 执行分析 ---
if process_trigger:
    # 获取API Key
    current_api_key = None
    try:
        if "Gemini" in model_provider:
            current_api_key = st.secrets["GEMINI_API_KEY"]
        else:
            current_api_key = st.secrets["ZHIPU_API_KEY"]
    except KeyError as e:
        st.error(f"❌ 缺少配置：未在 Secrets 中找到 {e}。请在 .streamlit/secrets.toml 中配置。")
        st.stop()
    except FileNotFoundError:
        st.error("❌ 配置文件丢失：未找到 .streamlit/secrets.toml 文件。")
        st.stop()

    result_container = st.container()
    
    with st.spinner(f"正在调用 {'Gemini' if 'Gemini' in model_provider else '智谱AI'} 进行深度分析..."):
        start_time = time.time()
        
        # 选择模型调用
        content_to_analyze = st.session_state.input_text.strip() if not st.session_state.is_image_mode else ""
        if "Gemini" in model_provider:
            result = analyze_with_gemini(
                current_api_key, 
                content_to_analyze, 
                st.session_state.is_image_mode, 
                st.session_state.uploaded_image_data
            )
        else:
            result = analyze_with_zhipu(
                current_api_key, 
                content_to_analyze, 
                st.session_state.is_image_mode, 
                st.session_state.uploaded_image_data
            )
        
        end_time = time.time()

    # --- 结果展示 ---
    if "error" in result:
        st.error(result["error"])
    else:
        st.toast(f"分析完成！耗时 {end_time - start_time:.2f} 秒")
        
        # 解析结果
        ai_data = result.get("ai_detection", {})
        copy_data = result.get("plagiarism_detection", {})
        
        # 1. AI 检测结果展示
        st.markdown("### 🤖 维度一：AI 生成检测")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            score = ai_data.get("score", 0)
            label = ai_data.get("label", "未知")
            
            # 动态颜色
            color = "green"
            if score > 40: color = "orange"
            if score > 80: color = "red"
            
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {color}; border-radius: 10px;">
                <h2 style="color: {color}; margin: 0;">{label}</h2>
                <h1 style="font-size: 3rem; margin: 0;">{score}%</h1>
                <p style="color: #666;">AI 疑似度</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(f"**判定理由：**\n\n{ai_data.get('reason', '无详细理由')}")
            st.progress(score / 100)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # 2. 剽窃检测结果展示
        st.markdown("### 📝 维度二：剽窃/抄袭检测")
        col3, col4 = st.columns([1, 2])
        
        with col3:
            copy_score = copy_data.get("percentage", 0)
            
            # 动态颜色
            copy_color = "green"
            if copy_score > 20: copy_color = "orange"
            if copy_score > 50: copy_color = "red"
            
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {copy_color}; border-radius: 10px;">
                <h2 style="color: {copy_color}; margin: 0;">剽窃风险</h2>
                <h1 style="font-size: 3rem; margin: 0;">{copy_score}%</h1>
                <p style="color: #666;">重复率预估</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(f"**分析详情：**\n\n{copy_data.get('reason', '无详细理由')}")
            st.markdown(f"**📚 可能来源：**\n\n{copy_data.get('sources', '未知')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 3. 原始数据（调试用）
        with st.expander("🔍 查看原始 JSON 数据"):
            st.json(result)

        st.markdown("""
        <div class="warning-text">
        ⚠️ 免责声明：本工具检测结果基于大模型概率预测，仅供参考，不作为最终的学术或法律依据。
        AI 模型可能会产生幻觉（Hallucination），对于剽窃来源的引用请务必进行人工核实。
        </div>
        """, unsafe_allow_html=True)

# --- 访问统计展示 ---
try:
    today_uv, total_uv, today_pv = track_and_get_stats()
except Exception as e:
    st.error(f"统计模块出错: {e}")
    today_uv, total_uv, today_pv = 0, 0, 0

# 展示数据
st.markdown("---")
st.markdown(f"""
<div class="metric-container">
    <div class="metric-box">
        <div class="metric-sub">今日 UV: {today_uv} 访客数</div>
    </div>
    <div class="metric-box" style="border-left: 1px solid #dee2e6; border-right: 1px solid #dee2e6; padding-left: 20px; padding-right: 20px;">
        <div class="metric-sub">历史总 UV: {total_uv} 总独立访客</div>
    </div>
    <div class="metric-box">
        <div class="metric-sub">今日 PV: {today_pv} 访问量</div>
    </div>
</div>
""", unsafe_allow_html=True)
