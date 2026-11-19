# Hardware note — open-weights model

Filled from the machine the local model ran on. Update the lines marked *(fill after run)*
before freezing the repo; `src/report.py` prints the first six bullet lines into the report.

- Machine: ASUS laptop, Windows 11 Pro (10.0.26200)
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8 GB VRAM
- RAM: 24 GB
- Runtime: Ollama *(fill after run: `ollama --version`)*, model `qwen2.5-coder:7b` (Q4_K_M, ~4.7 GB, fits fully in VRAM)
- Speed: *(fill after run: tokens/s from results/summary.csv `tokens_per_s`)*
- Cost assumptions (src/config.py): laptop $1,300 over 3 years at 8 h/day, 0.14 kW at $0.20/kWh, 4 h/month ops at $25/h

The model runs on our own machine through Ollama's local HTTP API (`http://localhost:11434`).
No third-party hosted API is used for the open-weights model.
