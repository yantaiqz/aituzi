import streamlit as st
import google.generativeai as genai
from zhipuai import ZhipuAI
import PyPDF2
from docx import Document
from PIL import Image
import io
import json
import time

# -------------------------------------------------------------
# 1. 页面配置与 CSS 样式
# -------------------------------------------------------------
st.set_page_config(
    page_title="AI 内容与剽窃检测系统",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 美化界面
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

# -------------------------------------------------------------
# 4. 模型调用函数
# -------------------------------------------------------------

def analyze_with_zhipu(api_key, content, is_image=False, image_data=None):
    """
    使用智谱 AI 进行分析。
    """
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
    """
    使用 Google Gemini 进行分析。
    """
    if not api_key:
        return {"error": "未检测到 Gemini API Key，请检查 secrets 配置。"}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
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
# 5. UI 布局与主逻辑
# -------------------------------------------------------------

# --- 侧边栏：设置 ---
with st.sidebar:
    st.header("⚙️ 配置面板")
    
    model_provider = st.radio(
        "选择分析模型",
        ("智谱 AI (默认)", "Google Gemini (进阶)"),
        captions=["国内访问稳定，GLM-4模型", "多模态能力强，Gemini-1.5模型"]
    )
    
    st.markdown("---")
    
    # 修改点：不再显示输入框，而是显示状态
    if "Gemini" in model_provider:
        if "GEMINI_API_KEY" in st.secrets:
            st.success("✅ Gemini API Key 已配置")
        else:
            st.error("❌ 未配置 GEMINI_API_KEY")
    else:
        if "ZHIPU_API_KEY" in st.secrets:
            st.success("✅ 智谱 API Key 已配置")
        else:
            st.error("❌ 未配置 ZHIPU_API_KEY")

    st.info("""
    **系统提示：**
    Key 现已通过云端 Secrets 安全读取，无需手动输入。
    """)
    
    st.markdown("---")
    st.markdown("🔒 安全模式：API Key 不会在前端显示。")

# --- 主页面 ---
st.markdown('<div class="main-header">🕵️ AI 内容与剽窃检测系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">上传文档、图片或输入文本，一键检测 AI 生成痕迹与内容剽窃风险</div>', unsafe_allow_html=True)

# 输入方式选项卡
tab1, tab2, tab3 = st.tabs(["📝 文本输入", "📂 文档上传 (PDF/Word)", "🖼️ 图片分析"])

content_to_analyze = ""
image_to_analyze = None
is_image_mode = False
process_trigger = False

with tab1:
    text_input = st.text_area("在此粘贴或输入需要检测的文字：", height=200)
    if st.button("开始分析文本", key="btn_text"):
        if text_input.strip():
            content_to_analyze = text_input
            process_trigger = True
        else:
            st.warning("请输入文字。")

with tab2:
    uploaded_file = st.file_uploader("上传文档", type=['pdf', 'docx'])
    if st.button("开始分析文档", key="btn_doc"):
        if uploaded_file:
            with st.spinner("正在解析文档..."):
                if uploaded_file.name.endswith('.pdf'):
                    content_to_analyze = extract_text_from_pdf(uploaded_file)
                elif uploaded_file.name.endswith('.docx'):
                    content_to_analyze = extract_text_from_docx(uploaded_file)
                
                if content_to_analyze and len(content_to_analyze) > 10:
                    process_trigger = True
                    st.success(f"文档解析成功！共 {len(content_to_analyze)} 字。")
                else:
                    st.error("文档解析失败或内容为空。")
        else:
            st.warning("请先上传文件。")

with tab3:
    uploaded_image = st.file_uploader("上传包含文字的图片", type=['png', 'jpg', 'jpeg'])
    if uploaded_image:
        image_to_analyze = Image.open(uploaded_image)
        st.image(image_to_analyze, caption="预览图片", use_container_width=True)
        if st.button("开始分析图片", key="btn_img"):
            is_image_mode = True
            process_trigger = True

# --- 执行分析 ---
if process_trigger:
    
    # 修改点：根据选择自动获取 Key
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
        if "Gemini" in model_provider:
            result = analyze_with_gemini(current_api_key, content_to_analyze, is_image_mode, image_to_analyze)
        else:
            result = analyze_with_zhipu(current_api_key, content_to_analyze, is_image_mode, image_to_analyze)
        
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
