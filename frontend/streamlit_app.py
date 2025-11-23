"""
EduSlide AI - Main Streamlit Application
Personalized Presentation Generation Platform
"""
import streamlit as st
import time
import requests     # Added only for fallback download
from config import Config
from api_client import APIClient
from utils import (
    init_session_state,
    add_to_history,
    display_info_card,
    display_success_message,
    display_error_message,
    display_warning_message,
    get_style_description,
    get_audience_description,
    estimate_generation_time,
    validate_topic
)

# Page Configuration
st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #667eea;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #764ba2;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .slide-preview {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def render_header():
    """Render application header"""
    st.markdown(f"""
    <div class="main-header">
        <h1>🎓 EduSlide AI</h1>
        <p style="font-size: 1.2rem; margin: 0;">
            Personalized Presentation Generation Platform
        </p>
        <p style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.9;">
            IIT Bombay Eduthon 2025 | Version {Config.APP_VERSION}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar with settings and info"""
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=EduSlide+AI", use_container_width=True)

        st.markdown("---")

        st.subheader("🔌 System Status")
        api_client = APIClient()

        with st.spinner("Checking backend..."):
            health = api_client.check_health()

        if health.get("status") == "healthy":
            st.success("✅ Backend Connected")
            st.caption(f"Backend: {Config.BACKEND_URL}")
        else:
            st.error("❌ Backend Offline")
            display_warning_message("Make sure the backend server is running on http://localhost:8000")

        st.markdown("---")

        st.subheader("📊 Quick Stats")
        history_count = len(st.session_state.get('generation_history', []))
        st.metric("Presentations Generated", history_count)

        st.markdown("---")

        st.subheader("ℹ️ About")
        st.markdown("""
        **EduSlide AI** uses advanced AI to generate personalized, 
        content-rich presentations tailored to your teaching needs.
        
        **Features:**
        - 🤖 AI-powered content generation
        - 🖼️ Automatic image integration
        - 🎨 Multiple presentation styles
        - 🌐 Multi-language support
        - 📝 Speaker notes generation
        """)

        st.markdown("---")

        with st.expander("❓ How to Use"):
            st.markdown("""
            1. Enter your presentation topic
            2. Select your target audience
            3. Choose presentation style
            4. Configure advanced options
            5. Click "Generate Presentation"
            6. Download your PowerPoint file
            """)

        st.markdown("---")
        st.caption("Made with ❤️ for IIT Bombay Eduthon 2025")


def render_main_form():
    """Render main presentation generation form"""
    st.header("📝 Create Your Presentation")

    st.subheader("1️⃣ What's your topic?")
    topic = st.text_area(
        "Enter presentation topic or description",
        placeholder="Example: Photosynthesis for Class 10 students with diagrams and real-world examples",
        height=100,
        help="Describe what you want to teach. Be specific for better results!"
    )

    if topic:
        is_valid, message = validate_topic(topic)
        if not is_valid:
            display_error_message(message)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("2️⃣ Who's your audience?")
        audience_type = st.selectbox("Select target audience", Config.AUDIENCE_TYPES)

        if audience_type:
            st.info(f"📖 {get_audience_description(audience_type)}")

    with col2:
        st.subheader("3️⃣ How many slides?")
        num_slides = st.slider("Number of slides", Config.MIN_SLIDES, Config.MAX_SLIDES, Config.DEFAULT_SLIDES)

        include_images_preview = st.checkbox("Include images", value=True, key="img_preview")
        time_estimate = estimate_generation_time(num_slides, include_images_preview)
        st.caption(f"⏱️ Estimated time: {time_estimate}")

    st.markdown("---")

    st.subheader("4️⃣ Choose presentation style")
    style = st.selectbox("Presentation style", Config.PRESENTATION_STYLES)

    if style:
        st.info(f"🎨 {get_style_description(style)}")

    st.markdown("---")

    with st.expander("⚙️ Advanced Options"):
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            language = st.selectbox("Language", Config.LANGUAGES)
            complexity = st.selectbox("Content Complexity", Config.COMPLEXITY_LEVELS, index=1)

        with col_a2:
            include_images = st.checkbox("Include Images", value=True)
            include_notes = st.checkbox("Generate Speaker Notes", value=False)

    st.markdown("---")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        generate_button = st.button("🚀 Generate Presentation", use_container_width=True)

    if generate_button:

        is_valid, validation_message = validate_topic(topic)
        if not is_valid:
            display_error_message(validation_message)
            return

        with st.spinner("🎨 Creating your presentation..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            api_client = APIClient()

            status_text.text("📝 Analyzing your topic...")
            progress_bar.progress(20)
            time.sleep(0.5)

            status_text.text("🤖 Generating AI content...")
            progress_bar.progress(40)

            result = api_client.generate_presentation(
                topic=topic,
                audience_type=audience_type,
                num_slides=num_slides,
                style=style,
                language=language,
                complexity=complexity,
                include_images=include_images,
                include_notes=include_notes
            )

            progress_bar.progress(70)
            status_text.text("🖼️ Adding images...")
            time.sleep(0.5)

            progress_bar.progress(90)
            status_text.text("✨ Finalizing presentation...")
            time.sleep(0.5)

            progress_bar.progress(100)
            status_text.text("✅ Complete!")
            time.sleep(0.5)

            progress_bar.empty()
            status_text.empty()

        if result.get("status") == "success":
            display_success_message("Presentation generated successfully! 🎉")

            st.session_state.presentation_data = result
            st.session_state.current_presentation_id = result.get("presentation_id")

            add_to_history(
                topic=topic,
                params={"audience": audience_type, "slides": num_slides, "style": style},
                status="success"
            )

            render_results(result)

        else:
            error_msg = result.get("message", "Unknown error occurred")
            display_error_message(f"Generation failed: {error_msg}")

            add_to_history(
                topic=topic,
                params={"audience": audience_type, "slides": num_slides, "style": style},
                status="failed"
            )


def render_results(result):
    """Render generation results"""
    st.markdown("---")
    st.header("📊 Your Presentation")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color:#667eea;">📄</h3>
            <p style="font-size:1.5rem;font-weight:bold;">{result.get("total_slides","N/A")}</p>
            <p style="color:#666;">Total Slides</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color:#667eea;">🖼️</h3>
            <p style="font-size:1.5rem;font-weight:bold;">{result.get("images_added","N/A")}</p>
            <p style="color:#666;">Images Added</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color:#667eea;">⏱️</h3>
            <p style="font-size:1.5rem;font-weight:bold;">{result.get("generation_time",0):.1f}s</p>
            <p style="color:#666;">Generation Time</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color:#667eea;">📝</h3>
            <p style="font-size:1.5rem;font-weight:bold;">{
                "Yes" if result.get("has_notes") else "No"
            }</p>
            <p style="color:#666;">Speaker Notes</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------
    # FIXED DOWNLOAD SECTION
    # -------------------------------
    st.subheader("💾 Download Your Presentation")

    file_bytes = result.get("file_data")
    download_url = result.get("download_url")
    filename = result.get("filename", "presentation.pptx")

    # CASE 1 → If file_data exists, use it directly
    if file_bytes:
        st.download_button(
            label="⬇️ Download PowerPoint (.pptx)",
            data=file_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True
        )

    # CASE 2 → file_data missing → try fetching using download_url
    elif download_url:
        try:
            r = requests.get(download_url)
            if r.status_code == 200:
                st.download_button(
                    label="⬇️ Download PowerPoint (.pptx)",
                    data=r.content,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            else:
                st.warning("⚠ PPT generated but file unavailable. Use manual link below.")
                st.code(download_url)
        except Exception:
            st.warning("⚠ PPT generated but could not fetch file automatically.")
            st.code(download_url)

    # CASE 3 → Nothing available
    else:
        st.error("❌ PPT generation complete, but file could not be retrieved.")

    # Preview Section
    if result.get("slides"):
        st.markdown("---")
        st.subheader("👀 Slide Preview")

        slides = result.get("slides", [])
        for i, slide in enumerate(slides, 1):
            with st.expander(f"Slide {i}: {slide.get('title', 'Untitled')}", expanded=(i == 1)):
                st.markdown(f"### {slide.get('title', 'Untitled')}")
                st.markdown(slide.get('content', ''))

                if slide.get('image_url'):
                    st.image(slide['image_url'], caption=f"Image for slide {i}", use_container_width=True)

                if slide.get('notes'):
                    st.info(f"📝 **Speaker Notes:** {slide['notes']}")


def render_history():
    """Render generation history"""
    if st.session_state.get('generation_history'):
        st.markdown("---")
        st.header("📜 Generation History")

        for item in st.session_state.generation_history[:5]:
            status_icon = "✅" if item['status'] == 'success' else "❌"
            with st.expander(f"{status_icon} {item['topic'][:50]}... - {item['timestamp']}"):
                st.write(f"**Audience:** {item['params'].get('audience')}")
                st.write(f"**Slides:** {item['params'].get('slides')}")
                st.write(f"**Style:** {item['params'].get('style')}")
                st.write(f"**Status:** {item['status']}")


def main():
    init_session_state()
    render_header()
    render_sidebar()
    render_main_form()
    render_history()


if __name__ == "__main__":
    main()
