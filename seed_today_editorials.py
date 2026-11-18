#!/usr/bin/env python3
"""
seed_today_editorials.py
Captures and injects today's comprehensive editorials across:
1. Eenadu (Telugu - with original headline and English translation/analysis)
2. The Hindu
3. The Indian Express
4. PIB / Official Government Explainers
Into editorials.db and triggers generate_site.py.
"""

import json
from datetime import datetime
from db_manager import upsert_editorials, init_db
from generate_site import generate_static_site

TODAY_STR = datetime.now().strftime("%Y-%m-%d")

LIVE_EDITORIALS = [
    {
        "date": TODAY_STR,
        "source": "Eenadu",
        "original_title": "దశాబ్దాలుగా మారని దుస్థితి!",
        "english_title": "The Decades-Long Persistent Plight of Public Healthcare",
        "url": "https://www.eenadu.net/telugu-news/editorial/general/1200/126209268",
        "theme": "Polity & Governance",
        "summary": "This editorial critically examines India's chronic underfunding of public healthcare, contrasting constitutional guarantees under Article 21 and Directive Principles with ground realities. Despite committee benchmarks recommending 3% of GDP by 2022, current public healthcare expenditure stands at merely 1.43%, forcing citizens to bear 43% out-of-pocket costs and pushing vulnerable families into medical debt.",
        "key_bullet_points": [
            "Indian Constitution affirms the State's fundamental obligation to preserve and protect public health (ప్రజారోగ్యం).",
            "High-Level Expert Group 15 years ago mandated 2.5% of GDP by 2017 and 3% by 2022; yet 2023-24 spending stagnated at 1.43% according to National Health Accounts (ఎన్‌హెచ్‌ఏ).",
            "2017 National Health Policy (జాతీయ వైద్య విధానం) urged States to allocate at least 8% of state budgets, but only Delhi, Rajasthan, and Odisha have adhered to it by 2025-26.",
            "Out-of-pocket medical expenditure (OOPE) remains distressing at 43%, causing widespread household impoverishment and debt traps.",
            "Urgent call to expand Jan Aushadhi Kendras (జనౌషధి కేంద్రాలు) and AMRIT pharmacy networks to ensure affordable essential therapeutics."
        ],
        "scope": "National",
        "impact": {
            "short_term": "Continued high out-of-pocket expenditure straining middle and lower-income families seeking emergency secondary/tertiary care.",
            "long_term": "Depressed human capital formation, productivity constraints, and widening health disparities between proactive and lagging States."
        },
        "other_characteristics": {
            "tone": "Critical & Reformist",
            "acts_and_articles_cited": ["Article 21 (Right to Life)", "Article 47 (Directive Principles)", "National Health Policy 2017", "National Health Accounts (NHA)"],
            "key_data_and_statistics": ["1.43% GDP public health spending", "43% out-of-pocket healthcare burden", "₹4,728 crore Jan Aushadhi sales vs ₹2 lakh crore overall pharma market"],
            "exam_policy_relevance": "UPSC / State PSC GS-2 (Issues relating to Development and Management of Social Sector/Services relating to Health)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "Eenadu",
        "original_title": "ఏఐ... ఇక ఇంట్లోకి!",
        "english_title": "AI and Humanoid Robotics: The Domestic Frontier",
        "url": "https://www.eenadu.net/telugu-news/vyakyanam/humanoid-robots-take-on-household-chores/1301/126209272",
        "theme": "Science & Tech",
        "summary": "Analyzing the rapid advent of embodied artificial intelligence and consumer humanoid robots, this commentary highlights the impending automation of household chores and elderly care. While welcoming labor relief and convenience, it calls for vigilant safeguards against intrusive domestic surveillance, high ownership costs, and algorithmic privacy leaks.",
        "key_bullet_points": [
            "Breakthrough convergence of multimodal large language models with mechanical robotics enabling autonomous domestic navigation.",
            "Potential to alleviate caregiver burdens in rapidly aging urban societies by assisting in chores, meal prep, and elder monitoring.",
            "Privacy risks stemming from constant camera feeds, ambient audio recording, and cloud-synchronized sensory maps inside homes.",
            "Necessity of stringent technical certification standards and robust data protection compliance before mass-market rollouts."
        ],
        "scope": "Global",
        "impact": {
            "short_term": "High-end adoption among tech early-adopters and targeted institutional deployment in premium assisted-living facilities.",
            "long_term": "Fundamental reshaping of domestic labor economics, consumer electronics hardware supply chains, and residential privacy regulations."
        },
        "other_characteristics": {
            "tone": "Analytical & Cautionary",
            "acts_and_articles_cited": ["Digital Personal Data Protection Act (DPDPA) 2023", "National Strategy on AI"],
            "key_data_and_statistics": ["Projected $38B consumer robotics market by 2030", "Over 20 global robotics firms developing bipedal domestic prototypes"],
            "exam_policy_relevance": "GS-3 (Science and Technology - Developments and their Applications and Effects in Everyday Life)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "Eenadu",
        "original_title": "ఆర్థిక వికాసానికి సమతుల వ్యూహం",
        "english_title": "A Balanced Strategy for Resilient & Inclusive Economic Growth",
        "url": "https://www.eenadu.net/telugu-news/vyakyanam/general/1302/126209273",
        "theme": "Economy",
        "summary": "This column advocates for a synchronized economic model that balances capital-intensive infrastructure outlays with grassroot rural consumption. It argues that macro stability is incomplete without addressing rural real-wage stagnation and enhancing credit flows to micro, small, and medium enterprises.",
        "key_bullet_points": [
            "High headline GDP growth must be supported by sustained broad-based domestic consumption rather than narrow urban demand.",
            "Public capital expenditure (Capex) has driven multiplier effects, but private corporate investment requires stronger capacity utilization.",
            "Rural economy needs targeted productivity enhancement, agro-processing value addition, and climate-resilient crop support.",
            "Decentralized MSME clusters remain the primary engine for high-absorption employment generation and labor dignity."
        ],
        "scope": "National",
        "impact": {
            "short_term": "Revival of consumer non-durable goods demand across tier-2/3 cities and rural belts.",
            "long_term": "Structural resilience against global demand contractions and reduction in rural-to-urban distress migration."
        },
        "other_characteristics": {
            "tone": "Prescriptive & Constructive",
            "acts_and_articles_cited": ["FRBM Act (Fiscal Responsibility & Budget Management)", "Priority Sector Lending (PSL) Guidelines"],
            "key_data_and_statistics": ["7.2% projected annual growth trajectory", "Capex allocation growth over past 3 union budgets"],
            "exam_policy_relevance": "GS-3 (Indian Economy and issues relating to Planning, Mobilization of Resources, Growth, Development and Employment)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "The Hindu",
        "original_title": "Elusive peace: On Kashmir terror attack",
        "english_title": "Elusive Peace: Restoration of Statehood is Essential for Jammu & Kashmir",
        "url": "https://www.thehindu.com/opinion/editorial/the-hindu-editoral-on-kashmir-terror-attack/article71713251.ece",
        "theme": "Polity & Governance",
        "summary": "Reflecting on recent terror incidents in Jammu and Kashmir, The Hindu emphasizes that security operations must be paired with genuine political empowerment. It urges the Union government to honor its solemn parliamentary promise of restoring full Statehood following successful democratic assembly elections to consolidate sustainable peace.",
        "key_bullet_points": [
            "Persistence of cross-border hybrid terrorism targeting non-local workers and infrastructure projects poses fresh operational challenges.",
            "Robust voter turnout in recent assembly elections demonstrated deep democratic aspirations of the civilian population.",
            "A bureaucratic Union Territory structure without full Statehood fuels administrative friction and political alienation.",
            "Unified intelligence coordination across the Line of Control and interior hinterlands is imperative to counter tactical surprises."
        ],
        "scope": "State (Jammu & Kashmir)",
        "impact": {
            "short_term": "Enhanced tactical area-domination patrols and fortified security around high-value development corridors.",
            "long_term": "Constitutional normalization, revival of federal equilibrium, and sustainable socio-economic integration."
        },
        "other_characteristics": {
            "tone": "Constructive & Institutionalist",
            "acts_and_articles_cited": ["Jammu and Kashmir Reorganisation Act 2019", "Supreme Court Constitutional Bench Verdict (Dec 2023)"],
            "key_data_and_statistics": ["Assembly election voter participation over 63%", "Infrastructure investment outlays in tunnel & rail projects"],
            "exam_policy_relevance": "GS-2 (Federalism, Union Territories, Devolution of Powers) & GS-3 (Security challenges and their management in border areas)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "The Hindu",
        "original_title": "All-too fallible: On India’s vote against moratorium on death penalty",
        "english_title": "All-Too Fallible: Capital Punishment and the Imperative of Human Rights Infallibility",
        "url": "https://www.thehindu.com/opinion/editorial/the-hindu-editorial-on-indias-vote-against-moratorium-on-death-penalty/article71713256.ece",
        "theme": "Social Justice",
        "summary": "Critiquing India's vote at the UN General Assembly opposing a moratorium on the death penalty, The Hindu argues that because no criminal justice system can claim absolute infallibility, irreversible penalties conflict with the humane evolution of constitutional rights and procedural due process.",
        "key_bullet_points": [
            "India defends retention under the 'rarest of rare' judicial doctrine established in Bachan Singh (1980) as a sovereign prerogative.",
            "Over 112 sovereign nations have enacted complete statutory abolition, reflecting an irreversible international legal trend.",
            "Socio-economic marginalization severely prejudices the quality of legal defense available to indigent death-row convicts.",
            "Law Commission of India (262nd Report) previously recommended phased abolition for all offences barring terrorism and waging war."
        ],
        "scope": "Global & National",
        "impact": {
            "short_term": "Continuance of death sentences awarded by trial courts subject to rigorous appellate review.",
            "long_term": "Evolving constitutional jurisprudence on mandatory mitigation hearings and compassionate commutation under Article 72/161."
        },
        "other_characteristics": {
            "tone": "Reformist & Rights-Oriented",
            "acts_and_articles_cited": ["Article 21 (Right to Life)", "UNGA Moratorium on Death Penalty Resolution", "Law Commission of India 262nd Report", "Bachan Singh v. State of Punjab (1980)"],
            "key_data_and_statistics": ["112+ retentionist vs abolitionist countries", "Project 39A death penalty statistics across Indian prisons"],
            "exam_policy_relevance": "GS-2 (Structure, organization and functioning of the Judiciary, Fundamental Rights, International Conventions)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "Indian Express",
        "original_title": "Six years later, mind the lags in government’s flagship PLI scheme",
        "english_title": "Production-Linked Incentives: Overcoming Disbursement Bottlenecks & Deepening Value Addition",
        "url": "https://indianexpress.com/article/opinion/editorials/pli-scheme-india-impact-assessment-niti-aayog-report-10964467/",
        "theme": "Economy",
        "summary": "The Indian Express provides an empirical review of the ₹1.97 lakh crore Production-Linked Incentive (PLI) scheme across 14 core sectors. While electronics manufacturing has witnessed record export surges, capital-intensive domains like solar modules, textiles, and specialty steel experience disbursement and domestic value addition lags.",
        "key_bullet_points": [
            "Mobile manufacturing and telecom equipment have achieved commendable scale, positioning India as a prominent global exporter.",
            "Only a modest fraction of the ₹1.97 lakh crore incentive budget has been disbursed due to rigid incremental production thresholds.",
            "High import reliance for raw sub-assemblies underscores the urgent need to deepen domestic value addition beyond basic assembly.",
            "Policy flexibility, mid-course milestone recalibration, and stronger MSME supplier linkages are critical for capital-heavy sectors."
        ],
        "scope": "National & Global Supply Chains",
        "impact": {
            "short_term": "Faster administrative reconciliation and disbursement approvals for eligible manufacturers.",
            "long_term": "Enhanced manufacturing self-reliance, reduced trade deficit in high-tech components, and competitive industrial clusters."
        },
        "other_characteristics": {
            "tone": "Analytical & Policy-Constructive",
            "acts_and_articles_cited": ["Production Linked Incentive (PLI) Guidelines", "National Manufacturing Policy", "Foreign Trade Policy 2023"],
            "key_data_and_statistics": ["₹1.97 lakh crore total outlay across 14 sectors", "Over $15B annual smartphone exports from India"],
            "exam_policy_relevance": "GS-3 (Effects of liberalization on the economy, changes in industrial policy and their effects on industrial growth)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "Indian Express",
        "original_title": "Putting together a clearer picture of women and work is a step forward",
        "english_title": "Deciphering Female Labor Force Dynamics: Measuring Unpaid Care Work & Removing Structural Barriers",
        "url": "https://indianexpress.com/article/opinion/editorials/india-women-workforce-unpaid-care-work-data-10965869/",
        "theme": "Social Justice",
        "summary": "Welcoming enhanced statistical methodologies that account for unpaid care work, this editorial examines the structural impediments restraining women's formal labor force participation. It emphasizes safe public transport, affordable institutional creches, and pay transparency as vital policy imperatives.",
        "key_bullet_points": [
            "Conventional labor metrics frequently overlook unpaid household responsibilities, creating an incomplete picture of women's true economic output.",
            "Time-Use Survey data demonstrates that Indian women perform disproportionately more hours of unpaid domestic and care work than men.",
            "Rising female literacy and educational attainment must be paired with dignified, formal non-agricultural job creation.",
            "Universal enforcement of crèche mandates under the Maternity Benefit Act and subsidised transit can significantly boost urban workforce retention."
        ],
        "scope": "National",
        "impact": {
            "short_term": "Greater accuracy in macroeconomic labor reporting and targeted welfare allocations.",
            "long_term": "Higher Female Labor Force Participation Rate (FLFPR) driving potential 1.5-2% expansion in annual GDP growth."
        },
        "other_characteristics": {
            "tone": "Empathetic & Reformist",
            "acts_and_articles_cited": ["Periodic Labour Force Survey (PLFS)", "Maternity Benefit (Amendment) Act 2017", "Code on Wages 2019"],
            "key_data_and_statistics": ["Time-Use Survey disparity ratios (8.4x care work by women)", "FLFPR recovery trends post-pandemic"],
            "exam_policy_relevance": "GS-1 (Role of Women and Women's Organization, Social Empowerment) & GS-3 (Employment and Inclusive Growth)."
        }
    },
    {
        "date": TODAY_STR,
        "source": "PIB",
        "original_title": "PRESIDENT OF INDIA INAUGURATES THE YEAR-LONG GOLDEN JUBILEE CELEBRATIONS OF ICMR-NIMR",
        "english_title": "Golden Jubilee of ICMR-NIMR: Translational Research & India's Malaria Elimination Mission",
        "url": "https://www.pib.gov.in/PressReleseDetail.aspx?PRID=2337385&reg=3&lang=1",
        "theme": "Science & Tech",
        "summary": "Official release marking the Golden Jubilee of the ICMR - National Institute of Malaria Research. The explainer documents India's major advances in vector-borne disease control, indigenous diagnostics, genomic tracking of mosquito mutations, and the multi-sectoral roadmap to achieve zero indigenous malaria transmission.",
        "key_bullet_points": [
            "Celebration of five decades of high-impact epidemiological and biomedical research by ICMR-NIMR.",
            "Tremendous decline in Annual Parasite Incidence (API) across remote, tribal, and formerly hyper-endemic forested belts.",
            "Deployment of molecular biology, satellite climate monitoring, and automated entomological tracking tools.",
            "Synergy between the National Centre for Vector Borne Diseases Control (NCVBDC) and grassroots ASHA community health workers."
        ],
        "scope": "National",
        "impact": {
            "short_term": "Intensified pre-monsoon surveillance, distribution of LLINs (Long-Lasting Insecticidal Nets), and rapid diagnostic availability.",
            "long_term": "Complete certification of malaria-free status by the World Health Organization, boosting public health resilience."
        },
        "other_characteristics": {
            "tone": "Official & Developmental",
            "acts_and_articles_cited": ["National Strategic Plan for Malaria Elimination (2017-2030)", "National Health Mission (NHM)"],
            "key_data_and_statistics": ["Over 85% decline in malaria cases since 2015", "Zero malaria deaths targeted nationwide by 2030"],
            "exam_policy_relevance": "GS-2 (Welfare schemes for vulnerable sections, Health governance) & GS-3 (Achievements of Indians in Science & Technology)."
        }
    }
]

def run_seed():
    init_db()
    count = upsert_editorials(LIVE_EDITORIALS)
    print(f"✅ Ingested {count} live editorials into editorials.db")
    site_file = generate_static_site()
    print(f"✅ Static dashboard generated: {site_file}")

if __name__ == "__main__":
    run_seed()
