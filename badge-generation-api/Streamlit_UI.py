# streamlit_app.py
import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import psutil
import base64

st.set_page_config(page_title="Badge Generator", page_icon="🏆", layout="wide")
st.title("🏆 Open Badge Generator — Demo")

API_BASE = "http://localhost:8000"

# -------------------------
# Helpers
# -------------------------
@st.cache_data(ttl=300)
def fetch_styles() -> Dict[str, Any]:
    """Fetch available badge styles from API"""
    try:
        r = requests.get(f"{API_BASE}/styles", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {
            "badge_styles": {
                "detailed": "comprehensive explanations with specific learning outcomes",
                "concise": "brief, focused descriptions",
                "technical": "precise technical terminology",
                "narrative": "storytelling approach",
                "professional": "formal business language"
            },
            "badge_tones": {
                "formal": "professional academic language",
                "engaging": "dynamic, motivational language",
                "authoritative": "confident, expert tone",
                "accessible": "clear, jargon-free language",
                "inspiring": "uplifting, empowering language"
            },
            "criterion_styles": {
                "Task-Oriented": "[Action verb], [action verb], [action verb]... (imperative commands directing learners to perform tasks)",
                "Evidence-Based": "Learner has/can/successfully [action verb], has/can/effectively [action verb], has/can/accurately [action verb]... (focusing on demonstrated abilities and accomplishments)",
                "Outcome-Focused": "Students will be able to [action verb], will be prepared to [action verb], will [action verb]... (future tense emphasizing expected outcomes and capabilities)"
            }
        }

@st.cache_data(ttl=60)
def get_system_health() -> Dict[str, Any]:
    """Check API health status"""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"status": "unhealthy"}

def get_badge_history() -> List[Dict[str, Any]]:
    """Get badge generation history"""
    try:
        r = requests.get(f"{API_BASE}/badge_history", timeout=5)
        r.raise_for_status()
        return r.json().get("history", [])
    except Exception:
        return []

def clear_badge_history() -> bool:
    """Clear badge generation history"""
    try:
        r = requests.delete(f"{API_BASE}/badge_history", timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def generate_badge(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate badge using API"""
    try:
        resp = requests.post(f"{API_BASE}/generate_badge", json=payload, timeout=180)
        resp.raise_for_status()
        return {"success": True, "data": resp.json()}
    except requests.RequestException as e:
        return {"success": False, "error": str(e), "status_code": getattr(e.response, 'status_code', None)}

def get_system_stats() -> Dict[str, float]:
    """Get current system resource usage"""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        return {"cpu": cpu, "memory": mem}
    except Exception:
        return {"cpu": 0.0, "memory": 0.0}

def display_image_config(config: Dict[str, Any]):
    """Display image configuration in a formatted way"""
    if not config:
        st.write("No image configuration available")
        return
    
    st.write("**Canvas:**", f"{config.get('canvas', {}).get('width', 'N/A')}x{config.get('canvas', {}).get('height', 'N/A')}")
    
    layers = config.get('layers', [])
    st.write(f"**Layers:** {len(layers)} total")
    
    if layers:
        with st.expander("View Layer Details"):
            for i, layer in enumerate(layers):
                layer_type = layer.get('type', 'Unknown')
                z_index = layer.get('z', 'N/A')
                st.write(f"**Layer {i+1}:** {layer_type} (z: {z_index})")
                
                if layer_type == "ShapeLayer":
                    shape = layer.get('shape', 'N/A')
                    fill_mode = layer.get('fill', {}).get('mode', 'N/A')
                    st.write(f"  - Shape: {shape}, Fill: {fill_mode}")
                elif layer_type == "TextLayer":
                    text = layer.get('text', 'N/A')
                    font_size = layer.get('font', {}).get('size', 'N/A')
                    st.write(f"  - Text: '{text}', Font Size: {font_size}")
                elif layer_type in ["ImageLayer", "LogoLayer"]:
                    path = layer.get('path', 'N/A')
                    st.write(f"  - Path: {path}")

# -------------------------
# Load styles and check system health
# -------------------------
styles_data = fetch_styles()
health_status = get_system_health()

# -------------------------
# Session state initialization
# -------------------------
if "current_badge" not in st.session_state:
    st.session_state["current_badge"] = None
if "generation_history" not in st.session_state:
    st.session_state["generation_history"] = []

# -------------------------
# Sidebar: System Information
# -------------------------
with st.sidebar:
    st.header("🔧 System Status")
    
    # API Health
    if health_status.get("status") == "healthy":
        st.success("✅ API Connected")
        if health_status.get("timestamp"):
            st.caption(f"Last check: {health_status['timestamp']}")
    else:
        st.error("❌ API Unavailable")
    
    # System stats
    current_stats = get_system_stats()
    st.metric("CPU Usage", f"{current_stats['cpu']:.1f}%")
    st.metric("Memory Usage", f"{current_stats['memory']:.1f}%")
    
    st.divider()
    
    # Clear history button
    if st.button("🗑️ Clear Badge History"):
        if clear_badge_history():
            st.success("History cleared!")
            st.rerun()
        else:
            st.error("Failed to clear history")

# -------------------------
# Main content
# -------------------------
col1, col2 = st.columns([1, 1])

# -------------------------
# Left column: Course input form
# -------------------------
with col1:
    st.header("📚 Course Input")
    
    course_input = st.text_area(
        "Course Description", 
        height=150,
        placeholder="Enter your course description, learning objectives, and content details...",
        help="Minimum 10 characters required"
    )
    
    with st.expander("⚙️ Generation Settings"):
        # Badge Style
        badge_styles = styles_data.get("badge_styles", {})
        style_options = list(badge_styles.keys())
        default_style_idx = style_options.index("detailed") if "detailed" in style_options else 0
        
        selected_style = st.selectbox(
            "Badge Style", 
            style_options,
            index=default_style_idx,
            format_func=lambda x: x.title(),
            key="badge_style_select"
        )
        
        # Show help text for selected style
        if selected_style in badge_styles:
            st.caption(f"ℹ️ {badge_styles[selected_style]}")
        
        # Badge Tone
        badge_tones = styles_data.get("badge_tones", {})
        tone_options = list(badge_tones.keys())
        default_tone_idx = tone_options.index("formal") if "formal" in tone_options else 0
        
        selected_tone = st.selectbox(
            "Badge Tone",
            tone_options,
            index=default_tone_idx,
            format_func=lambda x: x.title(),
            key="badge_tone_select"
        )
        
        # Show help text for selected tone
        if selected_tone in badge_tones:
            st.caption(f"ℹ️ {badge_tones[selected_tone]}")
        
        # Criterion Style - Updated section
        criterion_styles = styles_data.get("criterion_styles", {})
        criterion_options = list(criterion_styles.keys())
        default_criterion_idx = criterion_options.index("Task-Oriented") if "Task-Oriented" in criterion_options else 0
        
        selected_criterion = st.selectbox(
            "Criterion Style",
            criterion_options,
            index=default_criterion_idx,
            key="criterion_style_select"
        )
        
        # Show detailed explanation for selected criterion style
        if selected_criterion in criterion_styles:
            criterion_description = criterion_styles[selected_criterion]
            st.caption(f"ℹ️ {criterion_description}")
            
            # Additional examples based on criterion style
            if selected_criterion == "Task-Oriented":
                st.info("**Example:** Complete the project, submit documentation, present findings")
            elif selected_criterion == "Evidence-Based":
                st.info("**Example:** Learner has successfully implemented algorithms, can effectively debug code, accurately applies design patterns")
            elif selected_criterion == "Outcome-Focused":
                st.info("**Example:** Students will be able to develop web applications, will be prepared to lead development teams, will architect scalable systems")
        
        # Badge Level
        badge_level = st.selectbox(
            "Badge Level", 
            ["", "beginner", "intermediate", "advanced"],
            format_func=lambda x: x.title() if x else "Not Specified"
        )
    
    custom_instructions = st.text_input(
        "Custom Instructions", 
        placeholder="Additional context or specific requirements..."
    )
    
    institution_name = st.text_input("Issuing Institution", placeholder="Your institution name")

    # Generate badge button
    if st.button("🚀 Generate Badge", type="primary", use_container_width=True):
        if not course_input.strip():
            st.warning("Please enter a course description.")
        elif len(course_input.strip()) < 10:
            st.warning("Course description must be at least 10 characters long.")
        else:
            payload = {
                "course_input": course_input.strip(),
                "badge_style": selected_style,
                "badge_tone": selected_tone,
                "criterion_style": selected_criterion,
                "badge_level": badge_level if badge_level else None,
                "custom_instructions": custom_instructions.strip() if custom_instructions else None,
                "institution": institution_name.strip() if institution_name else None
            }
            
            # Store payload to trigger processing in col2
            st.session_state["generate_payload"] = payload
            st.session_state["generate_trigger"] = True

# -------------------------
# Right column: Badge display
# -------------------------
with col2:
    st.header("✅ Generated Badge")
    
    # Check if generation was triggered
    if st.session_state.get("generate_trigger", False):
        payload = st.session_state.get("generate_payload")
        st.session_state["generate_trigger"] = False  # Reset trigger
        
        with st.spinner("🤖 Generating badge..."):
            result = generate_badge(payload)
            
            if result["success"]:
                badge_data = result["data"]
                st.session_state["current_badge"] = badge_data
                st.success("✅ Badge generated successfully!")
                st.balloons()
            else:
                error_msg = result.get("error", "Unknown error")
                status_code = result.get("status_code")
                if status_code:
                    st.error(f"❌ Server error ({status_code}): {error_msg}")
                else:
                    st.error(f"❌ Generation failed: {error_msg}")
    
    # Display current badge
    current_badge = st.session_state.get("current_badge")
    if current_badge:
        # Badge name
        badge_name = current_badge.get("name", "Unnamed Badge")
        st.markdown(f"### {badge_name}")
        
        # Badge description
        badge_desc = current_badge.get("description", "No description available")
        with st.container():
            st.markdown("**Description:**")
            st.write(badge_desc)
        
        # Criteria
        with st.expander("📝 Criteria Details"):
            criteria = current_badge.get("criteria", "No criteria available")
            st.write(criteria)
        
        # Image Configuration
        with st.expander("🎨 Image Configuration"):
            image_config = current_badge.get("imageConfig", {})
            display_image_config(image_config)
        
        st.markdown("---")
        
        # Download section
        st.subheader("📥 Download")
        
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            # Download badge JSON
            json_str = json.dumps(current_badge, indent=2)
            st.download_button(
                "📄 Download Badge JSON",
                json_str,
                file_name=f"badge_{badge_name.replace(' ', '_').lower()}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col_dl2:
            # Download image config only
            if image_config:
                config_str = json.dumps(image_config, indent=2)
                st.download_button(
                    "⚙️ Download Image Config",
                    config_str,
                    file_name=f"config_{badge_name.replace(' ', '_').lower()}.json",
                    mime="application/json",
                    use_container_width=True
                )

    else:
        st.info("👈 No badge generated yet. Fill in the course content on the left and click 'Generate Badge' to get started.")

# -------------------------
# Badge history section
# -------------------------
st.markdown("---")
st.header("📚 Recent Badge History")

try:
    history = get_badge_history()
    if history:
        # Show last 5 badges
        for entry in reversed(history[-5:]):
            timestamp = entry.get("timestamp", "")
            try:
                ts_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime("%m/%d %H:%M")
            except Exception:
                ts_str = timestamp or "N/A"
            
            course_preview = entry.get('course_input', '')[:100]
            if len(entry.get('course_input', '')) > 100:
                course_preview += "..."
            
            with st.expander(f"🏆 {ts_str} - {course_preview}"):
                col_hist1, col_hist2 = st.columns([3, 1])
                
                with col_hist1:
                    st.write(f"**Style:** {entry.get('badge_style', 'N/A')}")
                    st.write(f"**Tone:** {entry.get('badge_tone', 'N/A')}")
                    st.write(f"**Criterion Style:** {entry.get('criterion_style', 'N/A')}")
                    if entry.get("badge_level"):
                        st.write(f"**Level:** {entry.get('badge_level')}")
                    if entry.get("institution"):
                        st.write(f"**Institution:** {entry.get('institution')}")
                    if entry.get("custom_instructions"):
                        st.write(f"**Custom:** {entry.get('custom_instructions')}")
                
                with col_hist2:
                    gen_time = entry.get('generation_time', 0)
                    st.metric("Gen Time", f"{gen_time:.2f}s")
                    st.write(f"**Image Type:** {entry.get('selected_image_type', 'N/A')}")
    else:
        st.info("No badge history available. Generate your first badge!")
        
except Exception as e:
    st.warning(f"Could not fetch badge history: {e}")

# -------------------------
# Footer
# -------------------------
st.markdown("---")

current_stats = get_system_stats()
st.markdown(f"""
<div style="text-align: center; color: #666; padding: 1rem; background-color: #f8f9fa; border-radius: 0.5rem;">
    <strong>🏆 Open Badge Generator</strong><br>
    <em>Powered by MIT-DCC| Built with OneOrigin</em><br>
    <a href="https://www.imsglobal.org/spec/ob/v3p0" target="_blank">📖 Open Badges 3.0 Specification</a><br><br>
    <small>
        System: CPU {current_stats['cpu']:.1f}% | Memory {current_stats['memory']:.1f}% | API Status: {'✅' if health_status.get('status') == 'healthy' else '❌'}<br>
        Endpoints: /generate_badge | /styles | /badge_history | /health
    </small>
</div>
""", unsafe_allow_html=True)
