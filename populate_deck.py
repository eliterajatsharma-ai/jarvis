import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR

def build_presentation():
    src = r"C:\Users\Hp\.gemini\antigravity\brain\37e4ba2e-66f5-4263-b981-661f0642e93b\.user_uploaded\media_1794210550237_2daafb54.pptx"
    dst = r"C:\Users\Hp\.gemini\antigravity\scratch\jarvis\NITSHACKS_9_UPPU_JARVIS.pptx"
    img_command_center = r"C:\Users\Hp\.gemini\antigravity\brain\37e4ba2e-66f5-4263-b981-661f0642e93b\.user_uploaded\media_1794211682763_02523621.png"
    img_chaos_lab = r"C:\Users\Hp\.gemini\antigravity\brain\37e4ba2e-66f5-4263-b981-661f0642e93b\.user_uploaded\media_1794211682764_4d75fc47.png"

    prs = Presentation(src)

    COLOR_DARK = RGBColor(15, 23, 42)       # Slate 900 #0F172A (crisp high contrast)
    COLOR_MUTED = RGBColor(100, 116, 139)   # Slate 500 #64748B
    COLOR_BODY = RGBColor(51, 65, 85)       # Slate 700 #334155 (readable body text)
    COLOR_PRIMARY = RGBColor(2, 132, 199)   # Sky 600 #0284C7
    COLOR_ACCENT = RGBColor(14, 165, 233)   # Sky 500 #0EA5E9

    def set_clean_text(shape, text, font_size_pt=14, bold=False, color=COLOR_DARK):
        tf = shape.text_frame
        tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.word_wrap = True
        tf.clear()
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = text
        r.font.size = Pt(font_size_pt)
        r.font.bold = bold
        r.font.color.rgb = color
        return p

    def add_textbox_bullets(slide, left, top, width, height, bullet_items, font_size_title=13.0, font_size_body=12.0, space_after=12):
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.word_wrap = True
        tf.margin_top = 0
        tf.margin_bottom = 0
        tf.margin_left = 0
        tf.margin_right = 0
        for idx, (title, body) in enumerate(bullet_items):
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            p.space_after = Pt(space_after)
            p.line_spacing = 1.15
            if title:
                r1 = p.add_run()
                r1.text = "• " + title + ": "
                r1.font.bold = True
                r1.font.size = Pt(font_size_title)
                r1.font.color.rgb = COLOR_DARK

            r2 = p.add_run()
            r2.text = body
            r2.font.bold = False
            r2.font.size = Pt(font_size_body)
            r2.font.color.rgb = COLOR_BODY
        return txBox

    # ============================================================
    # SLIDE 1: COVER
    # ============================================================
    slide1 = prs.slides[0]
    for s in slide1.shapes:
        if s.shape_id == 19:
            set_clean_text(s, "J.A.R.V.I.S.: Autonomous Incident Intelligence & Deterministic Causal RCA for Distributed Cloud Microservices", font_size_pt=14.5, bold=True, color=COLOR_DARK)
        elif s.shape_id == 26:
            set_clean_text(s, "AIOps / Autonomous DevOps & Cloud Infrastructure Reliability", font_size_pt=14, bold=True, color=COLOR_DARK)
        elif s.shape_id == 24:
            set_clean_text(s, "uppu", font_size_pt=20, bold=True, color=COLOR_PRIMARY)

    # Team members callout below Field 3
    tbox = slide1.shapes.add_textbox(731520, 6380000, 5852160, 650000)
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    r_team = p1.add_run()
    r_team.text = "Team Members: Kaustab Karmakar, Rajat Sharma\n"
    r_team.font.size = Pt(12)
    r_team.font.bold = True
    r_team.font.color.rgb = COLOR_DARK

    r_url = p1.add_run()
    r_url.text = "Live Interactive Prototype: https://frontend-three-alpha-90.vercel.app"
    r_url.font.size = Pt(11)
    r_url.font.bold = True
    r_url.font.color.rgb = COLOR_ACCENT

    # ============================================================
    # SLIDE 2: 01 / PROPOSED SOLUTION
    # ============================================================
    slide2 = prs.slides[1]
    for s in slide2.shapes:
        if s.shape_id == 2:
            set_clean_text(s, "uppu", font_size_pt=13, bold=True, color=COLOR_MUTED)
        elif s.shape_id == 4:
            set_clean_text(s, "J.A.R.V.I.S. — Deterministic Causal Incident Intelligence", font_size_pt=28, bold=True, color=COLOR_DARK)
        elif s.shape_id in [11, 13, 16, 18]:
            s.text_frame.clear()

    # Left column: 4 pillars with large, prominent 13pt / 12pt typography and generous vertical coverage
    pillars = [
        ("Causal Graph Walk", "Eliminates alert-arrival bias. Reconstructs directed topology to trace upstream root causes vs cascading victim alarms."),
        ("Live Counterfactual Proof", "Our signature breakthrough. Operators click 'Verify Fix' to heal the suspected service in the live simulator and mathematically verify 100% downstream error recovery."),
        ("Calibrated Confidence & Honest Ambiguity", "Refuses to hallucinate certainty when evidence is split (Scenario 17); triggers an explicit Ambiguous state with a targeted lowest-cost disambiguation query."),
        ("Grounded AI War Room", "Deterministic 6-feature causal engine computes the verdict; the LLM strictly serves as an interface bound to cite verified [EVT-xxx] evidence chips.")
    ]
    add_textbox_bullets(slide2, 820000, 3050000, 5300000, 3300000, pillars, font_size_title=13.0, font_size_body=12.0, space_after=14)

    # Right column: Embedded Chaos Lab screenshot + structured explanation
    slide2.shapes.add_picture(img_chaos_lab, 6350000, 2600000, 4950000, 1980000)

    cap_box = slide2.shapes.add_textbox(6350000, 4750000, 4950000, 1600000)
    tf_cap = cap_box.text_frame
    tf_cap.word_wrap = True
    p_cap1 = tf_cap.paragraphs[0]
    p_cap1.space_after = Pt(6)
    r_cap1 = p_cap1.add_run()
    r_cap1.text = "⚡ Live Chaos Injection Lab (Built & Deployed):\n"
    r_cap1.font.bold = True
    r_cap1.font.size = Pt(12.5)
    r_cap1.font.color.rgb = COLOR_DARK

    p_cap2 = tf_cap.add_paragraph()
    p_cap2.line_spacing = 1.2
    r_cap2 = p_cap2.add_run()
    r_cap2.text = "Judges can trigger unscripted live faults (Kill DB Pool, DB Latency Spike, Bad Deploy, Stripe Outage, or 'Surprise Me') and watch J.A.R.V.I.S. isolate the root cause in 1.8 seconds with complete causal telemetry."
    r_cap2.font.size = Pt(11.5)
    r_cap2.font.color.rgb = COLOR_BODY

    # ============================================================
    # SLIDE 3: 02 / BUILD PLAN
    # ============================================================
    slide3 = prs.slides[2]
    for s in slide3.shapes:
        if s.shape_id == 2:
            set_clean_text(s, "uppu", font_size_pt=13, bold=True, color=COLOR_MUTED)
        elif s.shape_id == 4:
            set_clean_text(s, "Architecture, Stack & Causal Pipeline", font_size_pt=28, bold=True, color=COLOR_DARK)
        elif s.shape_id in [17, 19]:
            s.text_frame.clear()

    # Left card: Technologies Used
    tech_bullets = [
        ("Backend & Analytics", "Python 3.11+, FastAPI, WebSockets, NetworkX graph walks, scikit-learn, Drain3 online log pattern mining."),
        ("Frontend HUD", "React 18, Vite, Tailwind CSS, SVG Directed Vector Canvas (viewBox 800x250), Lucide Icons."),
        ("Storage & Ingestion", "SQLite (WAL mode), multi-source parsers (.log, .json, .csv) with regex PII masking, Prometheus/Grafana webhooks."),
        ("Chaos Simulator", "Asynchronous 6-microservice emulator with cascade propagation physics and live fault injection.")
    ]
    add_textbox_bullets(slide3, 750000, 3100000, 3900000, 3200000, tech_bullets, font_size_title=12.5, font_size_body=11.5, space_after=14)

    # Right card: Methodology text & full Command Center screenshot
    meth_bullets = [
        ("Causal Pipeline", "Ingestion → Anomaly Detection (MAD + EWMA) → Topological Correlation → 6-Feature Deterministic RCA → Counterfactual Proof."),
        ("Performance Metrics", "1.8s MTTI | 97.8% Alert Storm Reduction | 20/20 Scenarios Pass.")
    ]
    add_textbox_bullets(slide3, 5250000, 3050000, 6100000, 800000, meth_bullets, font_size_title=12.5, font_size_body=11.5, space_after=4)

    # Embed Command Center screenshot
    slide3.shapes.add_picture(img_command_center, 5250000, 4000000, 6100000, 2350000)

    # ============================================================
    # SLIDE 4: 03 / REALITY CHECK (Strictly below headers at top=3.92M!)
    # ============================================================
    slide4 = prs.slides[3]
    for s in slide4.shapes:
        if s.shape_id == 2:
            set_clean_text(s, "uppu", font_size_pt=13, bold=True, color=COLOR_MUTED)
        elif s.shape_id == 4:
            set_clean_text(s, "Feasibility, Production Viability & Mitigations", font_size_pt=28, bold=True, color=COLOR_DARK)
        elif s.shape_id in [46, 54, 62]:
            s.text_frame.clear()

    # Column 1: Feasibility (starts cleanly below "Feasibility" title at top=3920000)
    feas_bullets = [
        ("Zero Heavy Infra", "Runs as a single lightweight async runtime without requiring heavyweight Kafka, Zookeeper, or distributed DB clusters."),
        ("100% Offline Resilience", "Engineered with 3-tier fallback (Hosted Cloud API → Local Ollama → Deterministic Template) to guarantee zero failure during live venue demonstrations."),
        ("Non-Invasive Adoption", "Directly ingests standard Syslog, JSON structured logs, and Prometheus webhooks without altering existing application source code.")
    ]
    add_textbox_bullets(slide4, 868680, 3920000, 2834640, 2300000, feas_bullets, font_size_title=12.0, font_size_body=11.0, space_after=14)

    # Column 2: Challenges & Risks (starts cleanly below "Challenges & Risks" title at top=3920000)
    risk_bullets = [
        ("Victim-Alarms-First", "Downstream caller services alarm first due to cascade delays, deceiving naive tools."),
        ("LLM Hallucinations", "Generative AI models independently hallucinate non-existent root causes under high diagnostic stress."),
        ("Flapping Alert Storms", "Repeated micro-outages trigger 40+ duplicate fragmented incidents, causing alert fatigue."),
        ("Sparse Telemetry Gaps", "Legacy microservices often lack complete OpenTelemetry trace coverage.")
    ]
    add_textbox_bullets(slide4, 4677156, 3920000, 2834640, 2300000, risk_bullets, font_size_title=11.5, font_size_body=10.5, space_after=10)

    # Column 3: Mitigations (starts cleanly below "Mitigation" title at top=3920000)
    mit_bullets = [
        ("Topological Leaf Priority", "Walks reversed dependency graphs; prioritizes failing leaf nodes with zero downstream anomalous dependencies."),
        ("Zero LLM in Causal Loop", "Deterministic 6-feature causal scoring engine computes verdict; citations strictly verified."),
        ("Stateful Debouncing", "Requires sustained multi-window deviations while preserving true initial onset timestamps."),
        ("Inferred Topology Mode", "Automatically tags inferred call edges with low-confidence warnings rather than guessing.")
    ]
    add_textbox_bullets(slide4, 8485632, 3920000, 2834640, 2300000, mit_bullets, font_size_title=11.5, font_size_body=10.5, space_after=10)

    # ============================================================
    # SLIDE 5: 04 / WHY IT MATTERS (Proper top=3.55M & 3.4M coordinates)
    # ============================================================
    slide5 = prs.slides[4]
    for s in slide5.shapes:
        if s.shape_id == 2:
            set_clean_text(s, "uppu", font_size_pt=13, bold=True, color=COLOR_MUTED)
        elif s.shape_id == 4:
            set_clean_text(s, "Quantified Business Impact & Target Audience", font_size_pt=28, bold=True, color=COLOR_DARK)
        elif s.shape_id == 21:
            s.text_frame.clear()

    # Left card: Target Audience (starts cleanly below "Target Audience" title at top=3650000)
    aud_bullets = [
        ("SREs & DevOps Teams", "Provides instant causal isolation in 1.8 seconds, eliminates 3 AM alert storms, and provides verified 1-click rollback playbooks."),
        ("Incident Commanders & Leadership", "Generates 1-click Executive Briefs translating raw technical telemetry into exact revenue impact and recovery timelines."),
        ("Cloud-Native Enterprises & Fintech", "Protects high-volume transaction architectures (e-commerce, banking) where 1 minute of downtime costs $10,000+.")
    ]
    add_textbox_bullets(slide5, 868680, 3650000, 4754880, 2500000, aud_bullets, font_size_title=13.0, font_size_body=12.0, space_after=16)

    # Right card: Benefits (starts cleanly below "Benefits" title at top=3350000)
    bene_bullets = [
        ("97.8% Alert Storm Collapse", "Eliminates operator fatigue by collapsing 47 noisy cascading alarms into 1 actionable incident."),
        ("1.8s vs 45min MTTI", "Slashes Mean Time to Identify from 45 minutes of frantic Slack triage down to sub-2 seconds."),
        ("$84.50 / Failed Tx Revenue Shield", "Maps blast radius to critical user journeys (Checkout, Login) and calculates exact real-time revenue at risk."),
        ("Zero Burnout for On-Call", "Automated playbooks with safety risk badges and dry-run commands empower junior engineers to remediate safely.")
    ]
    add_textbox_bullets(slide5, 6534531, 3350000, 4754880, 2800000, bene_bullets, font_size_title=13.0, font_size_body=12.0, space_after=14)

    # ============================================================
    # SLIDE 6: 05 / EVIDENCE (Proper top=3.4M coordinates)
    # ============================================================
    slide6 = prs.slides[5]
    for s in slide6.shapes:
        if s.shape_id == 2:
            set_clean_text(s, "uppu", font_size_pt=13, bold=True, color=COLOR_MUTED)
        elif s.shape_id == 4:
            set_clean_text(s, "Algorithmic Rigor, Benchmarks & References", font_size_pt=28, bold=True, color=COLOR_DARK)

    # Left card: Research (starts cleanly below "Research" title at top=3400000)
    res_bullets = [
        ("RCAEval Benchmark Grounding", "Evaluated against standardized microservice failure benchmarks (Online Boutique, Sock Shop, Train Ticket) covering 11 fault classes."),
        ("MicroRCA Graph Walks", "Implemented personalized PageRank on reversed directed call graphs to isolate upstream root causes from cascading victims."),
        ("Drain3 Online Parsing", "Fixed-depth tree log pattern mining achieving 99%+ template accuracy on high-cardinality cloud logs."),
        ("BARO Baseline Metric Cross-Checking", "Layered metric ranking combining robust MAD Z-scores with EWMA trend filtering.")
    ]
    add_textbox_bullets(slide6, 774954, 3400000, 4800000, 2600000, res_bullets, font_size_title=12.5, font_size_body=11.5, space_after=14)

    # Right card: References (starts cleanly below "References" title at top=3400000)
    ref_bullets = [
        ("MicroRCA", "'Root Cause Analysis of Anomalies in Microservices through Graph Walks' — IEEE INFOCOM."),
        ("Drain", "'An Online Log Parsing Approach with Fixed Depth Tree' — IEEE ICWS."),
        ("Google SRE Book", "'Addressing Cascading Failures & Managing Incidents' — Betsy Beyer et al., O'Reilly Media."),
        ("MITRE ATT&CK & CNCF", "Microservice Observability & OpenTelemetry Standards.")
    ]
    add_textbox_bullets(slide6, 6471666, 3400000, 4800000, 2600000, ref_bullets, font_size_title=12.5, font_size_body=11.5, space_after=14)

    # Delete Slide 7
    if len(prs.slides) > 6:
        rId = prs.slides._sldIdLst[6].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[6]
        print("Slide 7 deleted cleanly.")

    prs.save(dst)
    print(f"Presentation saved to: {dst}")

if __name__ == "__main__":
    build_presentation()
