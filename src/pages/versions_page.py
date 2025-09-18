"""Versions page for managing LCA versions."""

import streamlit as st
import pandas as pd
from ..utils.version_manager import VersionManager
from ..utils.calculations import LCACalculator
from ..models.assessment import Assessment

class VersionsPage:
    """Versions page for managing different LCA assessment versions."""
    
    @staticmethod
    def _ensure_assessment_model():
        """Ensure assessment data is properly structured."""
        try:
            Assessment(**st.session_state.assessment)
        except Exception:
            st.session_state.assessment = Assessment().model_dump()
    
    @staticmethod
    def _render_save_tab(vm: VersionManager):
        """Render the save version tab."""
        st.subheader("Save Current Assessment")
        
        # Check if there's data to save
        if not st.session_state.get("assessment", {}).get("selected_materials"):
            st.warning("No assessment data to save. Please go to the Actual Tool page and create an assessment first.")
            return
        
        # Input fields
        name = st.text_input(
            "Version Name",
            placeholder="e.g., Office Chair v1, Sustainable Desk Concept",
            help="Must be unique and contain only letters, numbers, spaces, dots, dashes, and underscores (max 64 chars)"
        )
        
        description = st.text_area(
            "Description (Optional)",
            placeholder="Brief description of this version, changes made, or design notes...",
            height=100
        )
        
        # Show preview of what will be saved
        if st.session_state.get("materials") and st.session_state.get("assessment"):
            with st.expander("📋 Preview of data to be saved"):
                results = LCACalculator.compute_results(
                    st.session_state.assessment,
                    st.session_state.materials
                )
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Materials", len(st.session_state.assessment.get("selected_materials", [])))
                col2.metric("Total CO₂e", f"{results['total_co2e']:.1f} kg")
                col3.metric("Recycled Content", f"{results['recycled_content_pct']:.1f}%")
        
        # Save button
        if st.button("💾 Save Version", type="primary"):
            if not name.strip():
                st.error("Please enter a version name.")
            else:
                # Prepare data to save
                data = dict(st.session_state.assessment)
                
                # Add computed results
                if st.session_state.get("materials"):
                    results = LCACalculator.compute_results(
                        st.session_state.assessment,
                        st.session_state.materials
                    )
                    data.update(results)
                
                # Save version
                success, message = vm.save(name.strip(), data, description.strip())
                
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
    
    @staticmethod
    def _render_load_tab(vm: VersionManager):
        """Render the load version tab."""
        st.subheader("📂 Load Saved Version")
        
        metadata = vm.list_versions()
        
        if not metadata:
            st.info("No versions saved yet. Go to the Save tab to save your first version.")
            return
        
        # Show versions table
        st.markdown("### Available Versions")
        
        # Prepare data for display
        preview_rows = []
        for name, info in metadata.items():
            preview_rows.append({
                "Name": name,
                "Description": info.get("description", "")[:50] + ("..." if len(info.get("description", "")) > 50 else ""),
                "Created": info.get("created_at", "")[:16].replace("T", " "),
                "Materials": info.get("materials_count", 0),
                "Total CO₂": f"{info.get('total_co2', 0):.1f} kg"
            })
        
        # Sort by creation date (newest first)
        df = pd.DataFrame(preview_rows)
        if not df.empty:
            df = df.sort_values("Created", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Selection and load controls
        st.markdown("### Load Version")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_version = st.selectbox(
                "Select Version to Load",
                options=list(metadata.keys()),
                format_func=lambda x: f"{x} ({metadata[x].get('created_at', '')[:16].replace('T', ' ')})"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            load_button = st.button("📂 Load", type="primary")
        
        # Show details of selected version
        if selected_version:
            with st.expander(f"📋 Details for '{selected_version}'"):
                info = metadata[selected_version]
                st.write(f"**Description:** {info.get('description', 'No description')}")
                st.write(f"**Created:** {info.get('created_at', '')}")
                st.write(f"**Materials:** {info.get('materials_count', 0)}")
                st.write(f"**Total CO₂:** {info.get('total_co2', 0):.1f} kg")
        
        # Load functionality
        if load_button and selected_version:
            data, message = vm.load(selected_version)
            
            if data:
                # Update session state
                st.session_state.assessment = data
                VersionsPage._ensure_assessment_model()
                
                st.success(message)
                st.info("✅ Version loaded! Go to the Actual Tool or Results page to see the loaded data.")
                
                # Show what was loaded
                with st.expander("📋 Loaded data preview"):
                    st.write(f"**Materials:** {len(data.get('selected_materials', []))}")
                    st.write(f"**Lifetime:** {data.get('lifetime_weeks', 52)} weeks")
                    if data.get('selected_materials'):
                        st.write("**Selected materials:**")
                        for material in data.get('selected_materials', []):
                            st.write(f"- {material}")
            else:
                st.error(message)
    
    @staticmethod
    def _render_manage_tab(vm: VersionManager):
        """Render the manage versions tab."""
        st.subheader("🗂️ Manage Versions")
        
        metadata = vm.list_versions()
        
        if not metadata:
            st.info("No versions to manage yet.")
            return
        
        # Summary statistics
        stats = vm.get_summary_stats()
        
        st.markdown("### Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Versions", stats["total_versions"])
        
        with col2:
            st.metric("Latest Version", stats["latest_version"] or "None")
        
        with col3:
            st.metric("Total Materials", stats["total_materials"])
        
        with col4:
            st.metric("Avg CO₂", f"{stats['avg_co2']:.1f} kg")
        
        st.markdown("---")
        
        # Delete functionality
        st.markdown("### Delete Version")
        st.warning("⚠️ Deletion is permanent and cannot be undone!")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            version_to_delete = st.selectbox(
                "Select Version to Delete",
                options=list(metadata.keys()),
                format_func=lambda x: f"{x} ({metadata[x].get('created_at', '')[:16].replace('T', ' ')})"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            delete_button = st.button("🗑️ Delete", type="secondary")
        
        # Show details of version to delete
        if version_to_delete:
            with st.expander(f"📋 Details for '{version_to_delete}'"):
                info = metadata[version_to_delete]
                st.write(f"**Description:** {info.get('description', 'No description')}")
                st.write(f"**Created:** {info.get('created_at', '')}")
                st.write(f"**Materials:** {info.get('materials_count', 0)}")
                st.write(f"**Total CO₂:** {info.get('total_co2', 0):.1f} kg")
        
        # Delete functionality with confirmation
        if delete_button and version_to_delete:
            # Add a confirmation step
            if f"confirm_delete_{version_to_delete}" not in st.session_state:
                st.session_state[f"confirm_delete_{version_to_delete}"] = False
            
            if not st.session_state[f"confirm_delete_{version_to_delete}"]:
                st.warning(f"⚠️ Are you sure you want to delete '{version_to_delete}'?")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", key=f"confirm_yes_{version_to_delete}"):
                        success, message = vm.delete(version_to_delete)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                with col2:
                    if st.button("❌ Cancel", key=f"confirm_no_{version_to_delete}"):
                        st.info("Deletion cancelled.")
    
    @staticmethod
    def render():
        """Render the complete versions page."""
        st.header("📁 Version Management")
        st.markdown("Save, load, and manage different versions of your LCA assessments.")
        
        # Initialize version manager
        if "version_manager" not in st.session_state:
            st.session_state.version_manager = VersionManager()
        
        vm = st.session_state.version_manager
        
        # Create tabs
        tab1, tab2, tab3 = st.tabs(["💾 Save", "📂 Load", "🗂️ Manage"])
        
        with tab1:
            VersionsPage._render_save_tab(vm)
        
        with tab2:
            VersionsPage._render_load_tab(vm)
        
        with tab3:
            VersionsPage._render_manage_tab(vm)
