import streamlit as st
import google.generativeai as genai
import requests
import json
import datetime
import os
import time
import re

# -------------------------------------------------------------
# --- 0. 页面配置 ---
# -------------------------------------------------------------

st.set_page_config(
    page_title="德国财税专家QFS", 
    page_icon="🇩🇪", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# --- 1. CSS 注入 (Legalon Tech 风格 + 去除顶部留白) ---
# -------------------------------------------------------------

st.markdown("""
<style>
    /* === 1. 全局重置与字体 === */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');

    * {
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #f4f7f9 !important; /* Legalon 风格浅灰背景 */
        font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        color: #333333 !important;
    }

    /* === 2. 彻底去除顶部留白 === */
    [data-testid="stHeader"] {
        display: none !important;
    }
    #[data-testid="stToolbar"] {
    #    display: none !important;
    #}

    /* 关键修改：删除 [data-testid="stToolbar"] 的 display: none 样式，或改为以下样式 */
    [data-testid="stToolbar"] {
        /* 保留工具栏，但调整位置/透明度，不破坏页面布局 */
        position: fixed !important;
        top: 0 !important;
        right: 0 !important;
        z-index: 9999 !important; /* 确保在最上层 */
        background-color: transparent !important;
        border: none !important;
    }

    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 6rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    
    /* === 3. 顶部导航栏模拟 === */
    .nav-bar {
        background-color: #ffffff;
        border-bottom: 1px solid #e0e0e0;
        padding: 15px 40px;
        position: sticky;
        top: 0;
        z-index: 999;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .logo-text {
        font-size: 1.2rem;
        font-weight: 700;
        color: #003567; /* Legalon 深蓝 */
        letter-spacing: 0.5px;
    }
    .nav-tag {
        background-color: #eef4fc;
        color: #0056b3;
        font-size: 0.75rem;
        padding: 4px 8px;
        border-radius: 4px;
        margin-left: 12px;
        font-weight: 500;
    }

    /* === 4. 主容器限制 === */
    .main-content-wrapper {
        max-width: 900px;
        margin: 0 auto;
        padding: 30px 20px;
    }

    /* === 5. 标题区域 === */
    .hero-section {
        margin-bottom: 30px;
        text-align: left;
    }
    .page-title {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1a1a1a !important;
        margin-bottom: 8px !important;
    }
    .subtitle {
        font-size: 1rem !important;
        color: #666666 !important;
        font-weight: 400 !important;
    }

    /* === 6. 聊天气泡 (商务风格) === */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 10px 0 !important;
    }
    [data-testid="stChatMessage"] > div:first-child {
        display: none !important; /* 隐藏默认头像，使用自定义 */
    }
    
    /* 自定义气泡容器 */
    .chat-row {
        display: flex;
        margin-bottom: 20px;
        width: 100%;
    }
    .chat-row.user {
        justify-content: flex-end;
    }
    .chat-row.assistant {
        justify-content: flex-start;
    }
    
    .chat-avatar {
        width: 36px;
        height: 36px;
        border-radius: 6px; /* 方形圆角 */
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
    }
    .assistant .chat-avatar {
        background-color: #003567;
        color: white;
        margin-right: 12px;
    }
    .user .chat-avatar {
        background-color: #0f7bff;
        color: white;
        margin-left: 12px;
        order: 2;
    }

    .chat-bubble {
        padding: 16px 20px;
        border-radius: 8px; /* 较小的圆角，更显专业 */
        font-size: 0.95rem;
        line-height: 1.6;
        max-width: 85%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .assistant .chat-bubble {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        color: #1a1a1a;
    }
    .user .chat-bubble {
        background-color: #0056b3; /* 更稳重的蓝 */
        color: white;
        text-align: left;
    }

    /* === 7. 模型卡片 (Panel 风格) === */
    .model-section-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #555;
        margin: 30px 0 15px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-left: 4px solid #003567;
        padding-left: 10px;
    }

    .model-card {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    .model-card-header {
        padding: 12px 20px;
        font-size: 0.9rem;
        font-weight: 600;
        background-color: #f8f9fa;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        align-items: center;
    }
    
    .gemini-header { color: #0056b3; } /* 统一蓝色系 */
    .glm-header { color: #0056b3; }

    .model-card-content {
        padding: 20px;
        font-size: 0.95rem;
        line-height: 1.7;
        color: #333;
    }

    /* === 8. 语义总结卡片 (高亮风格) === */
    .semantic-card {
        background-color: #f0f7ff; /* 极淡的蓝 */
        border: 1px solid #cce5ff;
        border-radius: 8px;
        padding: 20px;
    }
    .semantic-content h4, .semantic-content strong {
        color: #003567 !important; /* 标题使用深蓝 */
        font-weight: 700 !important;
        margin-top: 10px !important;
        display: block;
    }
    .semantic-content ul {
        margin-left: 20px !important;
    }
    .semantic-content li {
        margin-bottom: 6px !important;
    }

    /* === 9. 底部输入框 === */
    [data-testid="stChatInput"] {
        background-color: white !important;
        padding: 20px 0 !important;
        border-top: 1px solid #e0e0e0 !important;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.03) !important;
        z-index: 1000;
    }
    [data-testid="stChatInput"] > div {
        max-width: 900px !important;
        margin: 0 auto !important;
    }

    /* === 10. 按钮样式 (扁平化) === */
    div.stButton > button {
        border-radius: 6px !important;
        border: 1px solid #dcdfe6 !important;
        background-color: white !important;
        color: #333 !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    div.stButton > button:hover {
        border-color: #0056b3 !important;
        color: #0056b3 !important;
        background-color: #ecf5ff !important;
    }
    
    /* 清除按钮特殊样式 */
    [data-testid="stButton"] button[kind="secondary"] {
        margin-top: 20px;
        width: 100%;
        border-style: dashed !important;
    }

    /* 光标动画 */
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
    .blinking-cursor { animation: blink 1s infinite; color: #0056b3; font-weight: bold; margin-left: 2px;}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# --- 工具函数：Markdown 渲染 + 格式化 ---
# -------------------------------------------------------------
def clean_extra_newlines(text):
    """清理冗余换行/空格"""
    cleaned = re.sub(r'\n{3,}', '\n\n', text) # 保留最多两个换行
    cleaned = re.sub(r'　+', '', cleaned)
    cleaned = cleaned.strip('\n')
    return cleaned

def markdown_to_html(text):
    """
    将 Markdown 转为 HTML，过滤 ### 标题，优化 Legalon 风格输出。
    """
    # 第一步：彻底删除所有 ### 开头的行 + 清理孤立的 ### 符号
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        # 过滤 ### 标题行 + 清理行内孤立的 ###
        if not line.startswith("###"):
            clean_line = re.sub(r'###+', '', line)  # 删除所有###符号
            lines.append(clean_line)
    
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        
        # 处理加粗标题 (**标题**)
        if line.startswith("**") and line.endswith("**"):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = line.strip("*")
            html_lines.append(f"<div style='color: #003567; font-weight: 700; margin-top: 16px; margin-bottom: 8px; font-size: 1rem;'>{content}</div>")
            
        # 处理列表项 (- xxx)
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul style='margin: 0 0 16px 20px; padding: 0;'>")
                in_list = True
            content = line[2:].strip()
            content = re.sub(r'\*\*(.*?)\*\*', r'<span style="color:#0056b3; font-weight:600;">\1</span>', content)
            html_lines.append(f"<li style='margin-bottom: 6px;'>{content}</li>")
            
        # 处理普通段落
        elif line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            line = re.sub(r'\*\*(.*?)\*\*', r'<span style="color:#0056b3; font-weight:600;">\1</span>', line)
            html_lines.append(f"<p style='margin-bottom: 10px;'>{line}</p>")
            
    if in_list:
        html_lines.append("</ul>")
        
    return "\n".join(html_lines)

# -------------------------------------------------------------
# --- 1. 常量定义 ---
# -------------------------------------------------------------
USER_ICON = "👤"
ASSISTANT_ICON = "⚖️"
GEMINI_ICON = "♊️"
GLM_ICON = "🧠"

COMMON_LEGAL_QUESTIONS = [
    "怎么应对德国税务稽查？",
    "货物出口德国如何判断增值税地点？",
    "企业在德国做重组，怎么做税务优化？"
]

SYSTEM_INSTRUCTION = """
角色：德国资深税务师（Legalon Tech 认证专家）
服务对象：中国出海企业
核心要求：
1. 基于德国现行法律法规，提供专业、严谨、可落地的合规建议；
2. 结构化输出：核心风险点 → 法律依据 (引用法条) → 合规建议；
3. 语气专业、冷静、客观，避免过度营销口吻。
"""

# -------------------------------------------------------------
# --- 2. 核心逻辑函数 ---
# -------------------------------------------------------------

def stream_gemini_response(prompt, model, max_retries=3):
    for attempt in range(max_retries):
        try:
            stream = model.generate_content(prompt, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    time.sleep(0.02)
            return # 成功后退出函数
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 2秒, 4秒, 8秒
                    print(f"遇到 429 错误，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 达到最大重试次数，最终失败
                    yield f"⚠️ Gemini调用失败 (429 Quota Exceeded)：多次重试后仍失败。{error_str[:100]}..."
                    break # 退出循环
            else:
                # 其他非 429 错误，直接报告
                yield f"⚠️ Gemini调用失败：{error_str[:100]}..."
                break

def stream_glm_response(prompt, api_key, model_name="glm-4"):
    if not api_key:
        yield "⚠️ 未配置智谱GLM API Key。"
        return
    try:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        full_prompt = f"{SYSTEM_INSTRUCTION}\n用户问题：{prompt}"
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.1,
            "stream": True
        }
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    line = line[6:]
                    if line == '[DONE]': break
                    try:
                        chunk = json.loads(line)
                        if content := chunk['choices'][0]['delta'].get('content'):
                            yield content
                    except: continue
    except Exception as e:
        yield f"⚠️ GLM调用失败：{str(e)[:100]}..."
        
def generate_semantic_compare(gemini_resp, glm_resp, user_question, gemini_api_key, max_retries=3):
    """
    生成格式严格的语义对比分析，并带有 429 错误重试机制。
    """
    # 关键修复：移除 Prompt 中的 ### 标题，改用普通文本
    compare_prompt = f"""
    作为德国财税分析专家，请对比以下两个模型针对"{user_question}"的回答，并严格按照指定格式输出语义异同分析。

    待分析内容：
    [Gemini]: {gemini_resp[:1500]}
    [GLM]: {glm_resp[:1500]}

    必须严格遵守的输出格式（不要包含Markdown代码块符号，不要使用###标题）：

    **核心共识**
    - [共识点1]
    - [共识点2]

    **观点差异**
    - Gemini侧重：[描述]
    - GLM侧重：[描述]

    **综合建议**
    [100字左右的综合实操建议]
    """
      
    # === 新增重试循环 ===
    for attempt in range(max_retries):
        try:
            genai.configure(api_key=gemini_api_key)
            summary_model = genai.GenerativeModel('gemini-2.5-flash')
            stream = summary_model.generate_content(compare_prompt, stream=True)
            
            # 如果成功获取到流，则开始流式输出并跳出重试循环
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    time.sleep(0.03)
            
            # 正常完成，退出整个函数
            return
            
        except Exception as e:
            error_str = str(e)
            
            # --- 检查是否为 429 配额错误 ---
            if "429" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 2秒, 4秒, 8秒
                    # 这里使用 yield 来提示用户正在重试
                    yield f"**警告：** 遇到配额限制 (429)。等待 {wait_time} 秒后尝试第 {attempt + 2} 次重试..."
                    time.sleep(wait_time)
                    continue # 继续下一次循环 (重试)
                else:
                    # 达到最大重试次数，执行最终失败的错误处理
                    error_message = f"**错误！语义总结失败：**\n\n- **原因:** Quota Exceeded (429)，多次重试后仍失败。 \n- **详情:** {error_str[:150]}...\n- **请检查:** API Key、付费状态或等待几分钟后重试。"
                    yield f"**核心共识**\n- 均强调合规重要性\n\n**观点差异**\n- 分析服务暂时不可用 (请查看日志)\n\n**综合建议**\n{error_message}"
                    return # 最终失败，退出函数
            
            # --- 其他非 429 错误 ---
            else:
                # 捕获其他非 429 错误，并输出详细信息
                error_message = f"**错误！语义总结失败：**\n\n- **原因:** {type(e).__name__} \n- **详情:** {error_str[:150]}...\n- **请检查:** 模型名称或 API Key 权限。"
                yield f"**核心共识**\n- 均强调合规重要性\n\n**观点差异**\n- 分析服务暂时不可用 (请查看日志)\n\n**综合建议**\n{error_message}"
                return # 其他错误，直接退出


# -------------------------------------------------------------
# --- 3. 初始化与状态 ---
# -------------------------------------------------------------
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
glm_api_key = st.secrets.get("GLM_API_KEY", "")
st.session_state["api_configured"] = bool(gemini_api_key)

@st.cache_resource
def initialize_gemini_model():
    if not gemini_api_key: return None
    return genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=SYSTEM_INSTRUCTION
    )

gemini_model = initialize_gemini_model()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "您好，我是 QFS 德国财税合规助手。请告诉我您遇到的具体问题。"}
    ]

# -------------------------------------------------------------
# --- 4. 页面渲染 ---
# -------------------------------------------------------------

# --- 自定义顶部导航栏 ---
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🇩🇪 QFS | Germany Compliance</div>
    <div class="nav-tag">AI Legal Assistant</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# --- Hero 区域 ---
st.markdown("""
<div class="hero-section">
    <h1 class="page-title">德国财税合规咨询</h1>
    <div class="subtitle">基于双模型 (Gemini & GLM) 的交叉验证分析系统</div>
</div>
""", unsafe_allow_html=True)

# --- 常见问题按钮组 ---
st.markdown('<div style="font-weight:600; margin-bottom:10px; color:#555;">💡 常见合规场景</div>', unsafe_allow_html=True)
cols = st.columns(3) # 改为3列更美观
prompt_from_button = None
for i, question in enumerate(COMMON_LEGAL_QUESTIONS):
    with cols[i % 3]:
        if st.button(question, key=f"q_{i}", use_container_width=True):
            prompt_from_button = question

# --- 历史消息渲染 (自定义 HTML 气泡) ---
st.markdown('<div style="margin-top: 30px;"></div>', unsafe_allow_html=True)
for msg in st.session_state.messages:
    role_class = "user" if msg["role"] == "user" else "assistant"
    avatar = USER_ICON if msg["role"] == "user" else ASSISTANT_ICON
    
    # 简单的 Markdown 转 HTML 用于历史记录
    content_html = markdown_to_html(msg["content"])
    
    st.markdown(f"""
    <div class="chat-row {role_class}">
        <div class="chat-avatar">{avatar}</div>
        <div class="chat-bubble">{content_html}</div>
    </div>
    """, unsafe_allow_html=True)


# --- 输入处理 ---
chat_input_text = st.chat_input("请输入具体业务场景或法规问题...")
user_input = prompt_from_button if prompt_from_button else chat_input_text

if user_input and st.session_state.get("api_configured", False):
    # 1. 显示用户提问
    st.markdown(f"""
    <div class="chat-row user">
        <div class="chat-avatar">{USER_ICON}</div>
        <div class="chat-bubble">{user_input}</div>
    </div>
    """, unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2. 占位容器 (改为自上而下)
    st.markdown('<div class="model-section-title">🔍 AI 模型交叉分析</div>', unsafe_allow_html=True)
    
    # === 移除 st.columns(2) ===
    gemini_placeholder = st.empty() 
    glm_placeholder = st.empty() 
    semantic_placeholder = st.empty()

    # 3. 串行流式生成 
    
    # --- Gemini 生成 (不再使用 with c1) ---
    gemini_full = ""
    # st.spinner() 是一个 Streamlit 内置的进度条，可以增强用户体验
    with st.spinner(f"正在获取 {GEMINI_ICON} Gemini Flash 的专业分析..."):
        for chunk in stream_gemini_response(user_input, gemini_model):
            gemini_full += chunk
            # 实时更新占位符，注意这里不再需要 c1/c2
            gemini_html = markdown_to_html(clean_extra_newlines(gemini_full))
            gemini_placeholder.markdown(f"""
            <div class="model-card">
                <div class="model-card-header gemini-header">{GEMINI_ICON} Gemini Flash</div>
                <div class="model-card-content">{gemini_html}<span class="blinking-cursor">|</span></div>
            </div>
            """, unsafe_allow_html=True)
    
    # 完成态去除光标
    gemini_placeholder.markdown(f"""
    <div class="model-card">
        <div class="model-card-header gemini-header">{GEMINI_ICON} Gemini Flash</div>
        <div class="model-card-content">{markdown_to_html(clean_extra_newlines(gemini_full))}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- GLM 生成 (不再使用 with c2) ---
    glm_full = ""
    with st.spinner(f"正在获取 {GLM_ICON} 智谱GLM-4 的专业分析..."):
        for chunk in stream_glm_response(user_input, glm_api_key):
            glm_full += chunk
            glm_html = markdown_to_html(clean_extra_newlines(glm_full))
            glm_placeholder.markdown(f"""
            <div class="model-card">
                <div class="model-card-header glm-header">{GLM_ICON} 智谱GLM-4</div>
                <div class="model-card-content">{glm_html}<span class="blinking-cursor">|</span></div>
            </div>
            """, unsafe_allow_html=True)

    glm_placeholder.markdown(f"""
    <div class="model-card">
        <div class="model-card-header glm-header">{GLM_ICON} 智谱GLM-4</div>
        <div class="model-card-content">{markdown_to_html(clean_extra_newlines(glm_full))}</div>
    </div>
    """, unsafe_allow_html=True)

    # 增加短暂延迟，避免立即触发 Gemini 总结模型的 429 限制
    time.sleep(1.5)

    # --- 语义对比分析 (保持不变，因为它本身就是垂直排列) ---
    st.markdown('<div class="model-section-title">📊 专家综合意见 (基于双模型)</div>', unsafe_allow_html=True)
    semantic_full = ""
    for chunk in generate_semantic_compare(gemini_full, glm_full, user_input, gemini_api_key):
        semantic_full += chunk
        semantic_html = markdown_to_html(clean_extra_newlines(semantic_full))
        semantic_placeholder.markdown(f"""
        <div class="semantic-card">
            <div class="semantic-content">{semantic_html}<span class="blinking-cursor">|</span></div>
        </div>
        """, unsafe_allow_html=True)

    semantic_placeholder.markdown(f"""
    <div class="semantic-card">
        <div class="semantic-content">{markdown_to_html(clean_extra_newlines(semantic_full))}</div>
    </div>
    """, unsafe_allow_html=True)

    # 保存历史 (仅保存总结，避免Token过长)
    st.session_state.messages.append({"role": "assistant", "content": semantic_full})

# --- 底部清空 ---
if st.button('重置对话', key="reset_btn", help="清空所有历史"):
    st.session_state.messages = [{"role": "assistant", "content": "您好，我是 QFS 德国财税合规助手。请告诉我您遇到的具体问题。"}]
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
