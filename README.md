# DecisionMate3 - Revision 2

DecisionMate3 is a multilingual smart decision-making tool for engineers, business analysts, and project managers.  
This revision includes:
- 🔄 Over 60 interactive modules for decision analysis, planning, simulation, and more
- 🌐 Multilingual support (English, Azerbaijani, Russian, Turkish, Spanish)
- 🔐 Firebase integration for login, save/load
- 📊 PDF/Excel export, radar/tornado charts, and custom visualizations
- 🛠️ Modular architecture with categories like Finance, Simulation, Agile, Contracts, and Engineering

## 🔧 Features

- **Life & Career**: Decision scoring, SWOT, Pros/Cons
- **Finance**: CAPEX, OPEX, NPV, IRR, Break-even, Rent vs Buy
- **Planning**: Critical Path, S-Curve, Gantt, Work Package Builder
- **Simulation**: Oil & Gas process tools (compressor, pump, valves, stream calculator, etc.)
- **Engineering**: Civil, Electrical, Instrumentation modules
- **Agile**: Kanban, Daily Standups, Sprint & Retrospective boards
- **Contracts**: Analyzer and Contract Generator
- **UI**: Classic + Modern dashboard, Firebase login, Theme toggle

## 📁 Structure

```
DecisionMate3/
│
├── app.py                  # Main app launcher
├── translations.py         # Multilingual keys
├── modules/                # Folder with all feature modules
├── serviceAccountKey.json  # Firebase credentials (not included in repo)
├── requirements.txt        # Python dependencies
└── .streamlit/
    └── config.toml         # Streamlit cloud config
```

## 🚀 Deployment Options

- [x] Streamlit Cloud
- [x] Android app (using Streamlit Android / WebView)
- [ ] WebView packaging (.apk/.aab for Play Store)

## 🔒 Notes

- Do not upload `serviceAccountKey.json` to GitHub.
- Ensure translation keys are synchronized in `translations.py`.
- All modules support Firebase saving/loading and multilingual UIs.

---

Developed by Nijat Isgandarov, Fulbright Scholar, Industrial & Systems Engineer.
