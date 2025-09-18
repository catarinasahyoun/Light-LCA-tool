"""User Guide page component."""

import streamlit as st
from ..utils.i18n import Translator

class UserGuidePage:
    """User Guide page for documentation and help."""
    
    @staticmethod
    def guidelines_content() -> dict:
        """Return the guidelines content sections."""
        sections = {
            "12 Must Haves": """
### Materials
- FSC/PEFC wood; sustainable MDF where feasible  
- Water-based paints / low-VOC adhesives  
- Avoid PVC and problematic plastics where possible  
- High recycled content where quality allows  

### Design & Build
- Modular & repairable assemblies (swap parts, keep the core)  
- Avoid mixed-material laminates that block recycling  
- Label parts for sorting (material codes)  
- Standardize repeat parts across programs  

### Process & Logistics
- Run LCA-Light before locking specs  
- Transport-efficient (flat-pack, stackable, lighter)  
- Source locally when it truly reduces impact  
- Plan end-of-life (reuse/recycle routes documented)  
""",
            "5 Golden Rules": """
- Think circular – plan reuse, modularity and end-of-life from day one  
- Start light – run LCA-Light in briefing/concept to steer choices early  
- Choose smart materials – prefer recycled/recyclable, FSC/PEFC  
- Cut waste – simplify parts/finishes/packaging; avoid over-engineering  
- Design for disassembly – standard fasteners, clear material separation  
""",
            "AI and Sustainability": """
# **Conscious Compute: The Tchai AI Playbook**

### Using AI, Sustainably 
Yes, we use AI, even in sustainability work. Elephant in the room: AI isn't "free."  
It burns energy. Think of AI as a super-fast helper who lives in a big factory far away.  
Every time we ask it to do something, the factory spins up computers and uses energy.  

So we do use AI, but we try to use it like a scalpel, not a sledgehammer — smart, not more.  

### How to use it
- When we're starting from zero, AI is great for a first rough draft, a list of options, or a quick comparison.  
- When we already know roughly what we want, AI helps tighten text, check a list, or spot gaps.  
- For images, we keep it tight: few versions as possible, clear prompts, no endless rerolls.  

We don't use AI just because it's shiny. Every extra prompt costs energy and time.  

### We can try to keep the footprint low by
- Asking fewer, better questions  
- Batching tasks (ask AI to do similar things all at once, e.g. "Give me 5 headline options" instead of 5 prompts)  
- Choosing lighter tools for simple jobs  
- Reusing what you already generated  

### Data care 
Treat AI like a postcard: assume others could read it.  
- Don't paste contracts, prices, personal data, or unreleased designs  
- Use approved tools and privacy settings  
- If in doubt, don't upload—ask IT  

### The law bit 
- Discoverable like email: chat logs can be requested in legal cases  
- Third-party issue: client NDAs may forbid sharing with AI vendors  
- GDPR applies: minimise/anonymise personal data, never upload special-category data  
- Training & retention: some AI tools use prompts/outputs unless you turn it off  
- Where data lives: cloud tools may store data outside the EU, only use approved ones  

### Quick rules to use AI safe and conscious, before you hit "Generate"
1. Be clear about what you need (one sentence)  
2. Start small (one prompt, one image set)  
3. Cap yourself (max 3 iterations)  
4. Reuse outputs; don't restart from scratch  
5. Stop if the value isn't improving  
6. Summarise, don't copy; describe the problem instead of pasting the doc  
7. Redact when necessary: names, prices, IDs, client references  
""",
            "Easy LCA Indicator Tool": """
LCA-Light is our fast sustainability check. It helps you to get early-stage insights and make comparisons in a project with a focus on materials, layouts, processes, and End of Life.  
It can help you make informed, data-based decisions already from the design process without having to run a full Life Cycle Assessment.  
""",
            "How does it work": """
### 1) **Set the lifespan**  
Tell the tool how long our solution will be in use (in weeks). That's the baseline for all the math.  

### 2) **Add materials & processes**  
Add each individual material of the design by simply:  
- a) Pick the material from the database.  
- b) Enter the total mass used (kg).  
- c) Add the process steps (what happens to it: cutting, coating, etc.).  
- d) Quick check of auto-filled facts  

When you pick a material, the tool shows: CO₂e factor (kg/kg), recycled %, density, and default end-of-life (recycle/incinerate/landfill).  
If it's not the right variant (e.g., powder-coated vs raw), choose a better dataset or flag it for update by emailing **sustainability@tchai.nl** (or Jill).  

### 3) **Let the tool crunch**  
Based on what you entered, LCA-Light calculates:  
- a) Embodied carbon (CO₂e from materials + processes).  
- b) Weighted recycled content (how much of your mass is recycled).  
- c) End-of-life split (recycle / reuse / landfill assumptions).  

### 4) **Read the summary**  
You'll get a clean snapshot with:  
- a) Total recycled content % (of overall mass).  
- b) Total CO₂e for the concept.  
- c) Tree-equivalent signal (how much CO₂e the design represents over its lifespan).  
- d) A material-by-material end-of-life view.  

### 5) **Compare versions**  
Use the dashboard to compare options (materials, finishes, layouts) on the same indicators (recycled content, carbon).  
Save different versions, revisit them, or remove them as the concept evolves.  

### 6) **How to request a change**  
Send an email to **sustainability@tchai.nl** with:  
- What you need changed (data or code)  
- Why (project/client need)  
- Deadline  
- Any source files or references  
""",
            "When do you use it": """
| User | Stage of Use | Purpose | Inputs Required |
|---|---|---|---|
| Sales | Briefing / Proposal | Compare design directions for the client pitch | Materials, finishes, size/dimensions |
| Designers | Concept phase | Evaluate multiple layout / material options | Drawings, materials, and dimensions |
| Engineers | Pre-technical / detailing | Assess impact of different alternatives | Material specs, processes, lifespan, quantity estimates |
| Project Leaders | Client discussions / final decision | Share directionally what's better and why | Final inputs (materials, processes, lifespan) |

### When **NOT** to Use It
- You want to make hard claims (the LCA-Light is an indicator tool)  
- You don't have the basics; when the minimum required data is not available (accuracy would be too low)  
- You need an official LCA for external purposes and official documentation (complete LCA report required)  
""",
        }
        return sections
    
    @staticmethod
    def render():
        """Render the User Guide page."""
        st.header("User Guide")
        content = UserGuidePage.guidelines_content()
        
        tabs = st.tabs([
            "12 Must Haves",
            "5 Golden Rules", 
            "AI and Sustainability",
            "Easy LCA Indicator Tool",
            "How does it work",
            "When do you use it",
        ])
        
        tab_names = [
            "12 Must Haves",
            "5 Golden Rules",
            "AI and Sustainability", 
            "Easy LCA Indicator Tool",
            "How does it work",
            "When do you use it",
        ]
        
        for i, tab_name in enumerate(tab_names):
            with tabs[i]:
                st.subheader(tab_name)
                st.write(content.get(tab_name, ""))