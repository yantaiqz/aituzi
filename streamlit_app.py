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
            model_name
