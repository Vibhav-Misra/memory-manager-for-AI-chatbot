import streamlit as st
import requests
import json
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

# Configuration
API_BASE_URL = "http://localhost:8000"

def main():
    st.set_page_config(
        page_title="Decider Admin UI",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("The Decider v1 - Memory Management Admin")
    st.markdown("Review and manage conversational memories extracted by the Decider service.")
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Live Input", "Buffered Memories", "Stored Memories", "System Health"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Live Input":
        show_live_input()
    elif page == "Buffered Memories":
        show_buffered_memories()
    elif page == "Stored Memories":
        show_stored_memories()
    elif page == "System Health":
        show_system_health()

def show_dashboard():
    """Show system overview dashboard"""
    st.header("System Overview")
    
    try:
        # Get system statistics
        health_response = requests.get(f"{API_BASE_URL}/health/db")
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            # Display health status
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_color = "🟢" if health_data["status"] == "healthy" else "🔴"
                st.metric("Service Status", f"{status_color} {health_data['status']}")
            
            with col2:
                db_status = health_data.get("database", "unknown")
                db_color = "🟢" if db_status == "connected" else "🔴"
                st.metric("Database", f"{db_color} {db_status}")
            
            with col3:
                st.metric("Timestamp", health_data.get("timestamp", "unknown"))
            
            # Get collection counts
            if "collections" in health_data:
                collections = health_data["collections"]
                
                st.subheader("Collection Statistics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Stored Memories", collections.get("stored_memories", 0))
                
                with col2:
                    st.metric("Buffered Memories", collections.get("buffered_memories", 0))
                
                with col3:
                    st.metric("Audit Logs", collections.get("audit_logs", 0))
        
        else:
            st.error("Failed to get system health information")
            
    except Exception as e:
        st.error(f"Error connecting to service: {e}")
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Refresh System Status"):
            st.rerun()
    
    with col2:
        if st.button("📊 View Recent Activity"):
            st.info("Navigate to 'Buffered Memories' to review recent activity")

def show_live_input():
    """Show live conversation input and processing"""
    st.header("🎙️ Live Conversation Input")
    st.markdown("Type conversation turns in real-time and watch memories being extracted and stored live!")
    
    # Initialize session state for conversation history
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []
    
    # Live input section
    st.subheader("💬 Add Conversation Turn")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        speaker = st.selectbox("Speaker", ["User", "Edy", "Assistant", "Other"])
        conversation_text = st.text_area("Conversation Text", 
                                       placeholder="Type what was said in this conversation turn...",
                                       height=100)
    
    with col2:
        st.write("**Quick Actions**")
        if st.button("➕ Add Turn", key="add_turn"):
            if conversation_text.strip():
                from datetime import datetime, timezone
                new_turn = {
                    "speaker": speaker,
                    "text": conversation_text.strip(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"live_input": True}
                }
                st.session_state.conversation_history.append(new_turn)
                st.success(f"Added turn from {speaker}")
                st.rerun()
            else:
                st.error("Please enter conversation text")
        
        if st.button("🗑️ Clear All", key="clear_conversation"):
            st.session_state.conversation_history = []
            st.session_state.processing_results = []
            st.success("Conversation cleared!")
            st.rerun()
    
    # Display conversation history
    if st.session_state.conversation_history:
        st.subheader("📝 Conversation History")
        
        for i, turn in enumerate(st.session_state.conversation_history):
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.write(f"**{turn['speaker']}**")
            with col2:
                st.write(turn['text'])
            with col3:
                if st.button(f"❌", key=f"remove_{i}"):
                    st.session_state.conversation_history.pop(i)
                    st.success("Turn removed!")
                    st.rerun()
        
        # Process conversation button
        st.subheader("🚀 Process Conversation")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🧠 Extract Memories", key="extract_memories"):
                if len(st.session_state.conversation_history) >= 2:
                    process_conversation()
                else:
                    st.warning("Need at least 2 conversation turns to extract memories")
        
        with col2:
            if st.button("📊 View Results", key="view_results"):
                st.rerun()
    
    # Display processing results
    if st.session_state.processing_results:
        st.subheader("🎯 Extracted Memories")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_candidates = len(st.session_state.processing_results.get('candidates', []))
            st.metric("Total Candidates", total_candidates)
        with col2:
            stored_count = st.session_state.processing_results.get('stored_count', 0)
            st.metric("Stored", stored_count, delta=f"+{stored_count}")
        with col3:
            buffered_count = st.session_state.processing_results.get('buffered_count', 0)
            st.metric("Buffered", buffered_count, delta=f"+{buffered_count}")
        with col4:
            rejected_count = st.session_state.processing_results.get('rejected_count', 0)
            st.metric("Rejected", rejected_count, delta=f"+{rejected_count}")
        
        # Display candidates
        if 'candidates' in st.session_state.processing_results:
            candidates = st.session_state.processing_results['candidates']
            for i, candidate in enumerate(candidates):
                with st.expander(f"Memory {i+1}: {candidate.get('content', '')[:100]}..."):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Type:** {candidate.get('memory_type', 'Unknown')}")
                        st.write(f"**Content:** {candidate.get('content', '')}")
                        st.write(f"**Evidence:** {candidate.get('extraction_evidence', '')}")
                        st.write(f"**Source:** {candidate.get('source_turn', {}).get('speaker', 'Unknown')}")
                    
                    with col2:
                        st.write(f"**Confidence:** {candidate.get('confidence', 0):.3f}")
                        st.write(f"**Relevance:** {candidate.get('relevance', 0):.3f}")
                        st.write(f"**Specificity:** {candidate.get('specificity', 0):.3f}")
                        st.write(f"**Salience Score:** {candidate.get('salience_score', 0):.3f}")
                        
                        # Show decision
                        if 'decisions' in st.session_state.processing_results and i < len(st.session_state.processing_results['decisions']):
                            decision = st.session_state.processing_results['decisions'][i]
                            action = decision.get('action', 'unknown')
                            if action == 'keep':
                                st.success("✅ Stored")
                            elif action == 'buffer':
                                st.warning("⏳ Buffered")
                            elif action == 'reject':
                                st.error("❌ Rejected")
                            else:
                                st.info(f"Action: {action}")
        
        # Real-time updates info
        st.info("💡 **Live Updates**: New memories are automatically stored or buffered. Check the 'Buffered Memories' tab to review and approve/reject memories!")
        
        # Quick navigation
        st.subheader("🔗 Quick Navigation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Review Buffered Memories"):
                st.switch_page("Buffered Memories")
        with col2:
            if st.button("💾 View Stored Memories"):
                st.switch_page("Stored Memories")

def process_conversation():
    """Process the current conversation and extract memories"""
    try:
        # Prepare the request payload
        payload = {
            "turns": st.session_state.conversation_history,
            "user_id": "demo_user",
            "session_id": f"live_session_{int(datetime.now().timestamp())}",
            "context": {"live_demo": True, "timestamp": datetime.now().isoformat()}
        }
        
        # Send to the service
        response = requests.post(f"{API_BASE_URL}/extract_and_store", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.session_state.processing_results = result
            
            # Show success message
            st.success(f"✅ Successfully processed conversation! Extracted {len(result.get('candidates', []))} memories.")
            
            # Auto-refresh to show results
            st.rerun()
        else:
            st.error(f"❌ Failed to process conversation: {response.status_code}")
            st.error(f"Response: {response.text}")
            
    except Exception as e:
        st.error(f"❌ Error processing conversation: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

def show_buffered_memories():
    """Show and manage buffered memories"""
    st.header("⏳ Buffered Memories")
    st.markdown("Review memories that need manual approval or rejection.")
    
    try:
        # Get buffered memories
        response = requests.get(f"{API_BASE_URL}/buffer")
        if response.status_code == 200:
            buffered_memories = response.json()
            
            if not buffered_memories:
                st.info("No buffered memories to review.")
                return
            
            # Display memories in a table
            st.subheader(f"{len(buffered_memories)} Memories Pending Review")
            
            for i, memory in enumerate(buffered_memories):
                with st.expander(f"Memory {i+1}: {memory['candidate']['content'][:100]}..."):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Type:** {memory['candidate']['memory_type']}")
                        st.write(f"**Content:** {memory['candidate']['content']}")
                        st.write(f"**Salience Score:** {memory['candidate']['salience_score']:.3f}")
                        st.write(f"**Buffer Reason:** {memory['buffer_reason']}")
                        st.write(f"**Evidence:** {memory['candidate']['extraction_evidence']}")
                        st.write(f"**Buffered:** {memory['buffered_at']}")
                    
                    with col2:
                        st.write(f"**Confidence:** {memory['candidate']['confidence']:.3f}")
                        st.write(f"**Relevance:** {memory['candidate']['relevance']:.3f}")
                        st.write(f"**Specificity:** {memory['candidate']['specificity']:.3f}")
                        st.write(f"**Buffer Score:** {memory['buffer_score']:.3f}")
                        
                        # Action buttons
                        st.write("**Actions:**")
                        
                        # Approve button
                        if st.button(f"Approve", key=f"approve_{i}"):
                            approve_memory(memory['id'])
                            st.success("Memory approved!")
                            st.rerun()
                        
                        # Reject button
                        if st.button(f"Reject", key=f"reject_{i}"):
                            reject_memory(memory['id'])
                            st.success("Memory rejected!")
                            st.rerun()
                        
                        # Notes input
                        notes = st.text_area("Admin Notes", key=f"notes_{i}")
                        if notes:
                            st.write(f"**Notes:** {notes}")
        
        else:
            st.error("Failed to retrieve buffered memories")
            
    except Exception as e:
        st.error(f"Error: {e}")

def show_stored_memories():
    """Show stored memories"""
    st.header("Stored Memories")
    st.markdown("View all accepted and stored memories.")
    
    try:
        # Get stored memories
        response = requests.get(f"{API_BASE_URL}/memories")
        if response.status_code == 200:
            stored_memories = response.json()
            
            if not stored_memories:
                st.info("No stored memories found.")
                return
            
            st.subheader(f"{len(stored_memories)} Stored Memories")
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                memory_type_filter = st.selectbox(
                    "Filter by Type",
                    ["All"] + list(set([m['candidate']['memory_type'] for m in stored_memories]))
                )
            
            with col2:
                search_term = st.text_input("Search Content", "")
            
            # Apply filters
            filtered_memories = stored_memories
            if memory_type_filter != "All":
                filtered_memories = [m for m in filtered_memories if m['candidate']['memory_type'] == memory_type_filter]
            
            if search_term:
                filtered_memories = [m for m in filtered_memories if search_term.lower() in m['candidate']['content'].lower()]
            
            # Display filtered memories
            for i, memory in enumerate(filtered_memories):
                with st.expander(f"Memory {i+1}: {memory['candidate']['content'][:100]}..."):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Type:** {memory['candidate']['memory_type']}")
                        st.write(f"**Content:** {memory['final_content']}")
                        st.write(f"**Salience Score:** {memory['candidate']['salience_score']:.3f}")
                        st.write(f"**Decision:** {memory['decision']['action']}")
                        st.write(f"**Reason:** {memory['decision']['reason']}")
                        st.write(f"**Stored:** {memory['stored_at']}")
                    
                    with col2:
                        st.write(f"**Confidence:** {memory['candidate']['confidence']:.3f}")
                        st.write(f"**Relevance:** {memory['candidate']['relevance']:.3f}")
                        st.write(f"**Specificity:** {memory['candidate']['specificity']:.3f}")
                        if memory['decision'].get('admin_notes'):
                            st.write(f"**Admin Notes:** {memory['decision']['admin_notes']}")
        
        else:
            st.error("Failed to retrieve stored memories")
            
    except Exception as e:
        st.error(f"Error: {e}")

def show_system_health():
    """Show detailed system health information"""
    st.header("System Health")
    st.markdown("Monitor system status and performance.")
    
    try:
        # Get health information
        response = requests.get(f"{API_BASE_URL}/health/db")
        if response.status_code == 200:
            health_data = response.json()
            
            # Health status
            st.subheader("Health Status")
            
            col1, col2 = st.columns(2)
            with col1:
                st.json(health_data)
            
            with col2:
                # Health indicators
                service_status = health_data.get("status", "unknown")
                db_status = health_data.get("database", "unknown")
                
                if service_status == "healthy":
                    st.success("✅ Service is healthy")
                else:
                    st.error("❌ Service is unhealthy")
                
                if db_status == "connected":
                    st.success("✅ Database is connected")
                else:
                    st.error("❌ Database connection failed")
            
            # Collection details
            if "collections" in health_data:
                collections = health_data["collections"]
                
                st.subheader("Collection Details")
                
                # Create a DataFrame for better visualization
                df = pd.DataFrame([
                    {"Collection": "Stored Memories", "Count": collections.get("stored_memories", 0)},
                    {"Collection": "Buffered Memories", "Count": collections.get("buffered_memories", 0)},
                    {"Collection": "Audit Logs", "Count": collections.get("audit_logs", 0)}
                ])
                
                st.bar_chart(df.set_index("Collection"))
        
        else:
            st.error("Failed to get health information")
            
    except Exception as e:
        st.error(f"Error: {e}")
    
    # Manual health check
    st.subheader("Manual Health Check")
    if st.button("Check Health Now"):
        try:
            response = requests.get(f"{API_BASE_URL}/health/db")
            if response.status_code == 200:
                st.success("Health check completed successfully")
                st.json(response.json())
            else:
                st.error(f"Health check failed: {response.status_code}")
        except Exception as e:
            st.error(f"Health check error: {e}")

def approve_memory(memory_id: str):
    """Approve a buffered memory"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/buffer/{memory_id}/approve",
            json={"memory_id": memory_id, "action": "approve", "notes": ""}
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Failed to approve memory: {e}")
        return False

def reject_memory(memory_id: str):
    """Reject a buffered memory"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/buffer/{memory_id}/reject",
            json={"memory_id": memory_id, "action": "reject", "notes": ""}
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Failed to reject memory: {e}")
        return False

if __name__ == "__main__":
    main()









