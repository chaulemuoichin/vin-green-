# Dashboard Screenshots

These images are referenced from the project [README.md](../../README.md). They need to be captured manually on a live `make prod-up` stack — no automation for this in Week 1.

| File | What to capture |
| --- | --- |
| `01_map.png` | Dashboard at default state, map tab visible with heatmap + wind arrows + downwind wedges. Use hour T+8 with `bac_tu_liem` selected. |
| `02_vn_aqi.png` | "🇻🇳 VN_AQI (QCVN)" tab showing the dual-scale comparison table and the delta-to-US-EPA chip. |
| `03_sources.png` | "🥧 Nguồn ô nhiễm" tab — pie + 24h stacked share bar for `hoan_kiem`. |
| `04_actions.png` | "✅ Hành động" tab with both citizen and government action panels filled. |

## How to capture (Windows)

```powershell
# 1. Bring up the stack and wait for healthchecks
make prod-up
# 2. Open the dashboard, set hour=T+8, district=Bắc Từ Liêm
Start-Process http://localhost/
# 3. Use Win+Shift+S to snip each tab and save into this directory.
```

After capturing, the README screenshot grid will render automatically.
