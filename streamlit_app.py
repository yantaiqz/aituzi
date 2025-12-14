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
# 1. 页面配置与 CSS 样式（优化内嵌上传按钮样式）
# -------------------------------------------------------------
st.set_page_config(
    page_title="AI兔子 内容与剽窃检测系统",
    page_icon="🐰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义 CSS 美化界面（新增内嵌上传按钮样式）
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

    # 写操作 (仅当本Session未计数时执行)
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

    # 读操作
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    
    return today_uv, total_uv, today_pv

# -------------------------------------------------------------
# 6. 主UI布局（核心：文本框内嵌上传功能）
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
if "uploaded_text" not in st.session_state:
    st.session_state.uploaded_text = ""
if "uploaded_image_data" not in st.session_state:
    st.session_state.uploaded_image_data = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = ""
if "is_image_mode" not in st.session_state:
    st.session_state.is_image_mode = False

# 核心：文本输入框 + 内嵌上传按钮
st.markdown("### 📝 输入待检测内容")
# 文本输入框
text_input = st.text_area(
    "在此粘贴文本，或上传文档/图片自动提取文字",
    value=st.session_state.uploaded_text,
    height=200,
    key="main_text_area"
)

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
            st.session_state.uploaded_text = extracted_text
            st.session_state.uploaded_file_name = file_name
            st.session_state.is_image_mode = False
            st.success(f"✅ 文档《{file_name}》解析成功！共 {len(extracted_text)} 字")
            # 刷新文本框
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
        if text_input.strip() or (st.session_state.is_image_mode and st.session_state.uploaded_image_data):
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
        content_to_analyze = text_input.strip() if not st.session_state.is_image_mode else ""
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
