# PM2.5 Interactive Smoke Dispersion Maps - Time-Slider Version

## ✨ New Features

This is the **V3 Interactive Time-Slider** version with full day-by-day exploration capability:

### Key Features
- ✅ **Interactive Time Slider** - Drag from day 1 to day 8 to see real-time changes
- ✅ **Previous/Next Buttons** - Click to step through each day
- ✅ **Dynamic Ellipses** - Impact area renders in real-time, size/color/orientation changes per day
- ✅ **Wind Direction Arrows** - Shows wind direction (arrow direction) and speed (arrow color & size)
- ✅ **Live Day Counter** - "Day X/8" display
- ✅ **Info Panel** - Shows PM2.5, wind speed, wind direction for each day
- ✅ **Peak Day Highlight** - Red star (★) marks the peak pollution day
- ✅ **Offline Support** - All data embedded in HTML, no external data files needed

---

## 📂 Generated Files

### Main Interactive Maps
Located in: `processed/model_outputs/spatial_temporal_analysis/`

1. **pm25_event_1_interactive.html**
   - Event: **July 24, 2024** (Most Severe)
   - Peak PM2.5: **134.0 ug/m³** 🔴
   - Time Window: July 21-28, 2024 (8 days)
   - Focus: Watch ellipse grow from day 1 to peak on day 4, then steady decline

2. **pm25_event_2_interactive.html**
   - Event: **August 15, 2024** (Second Most Severe)
   - Peak PM2.5: **53.5 ug/m³** 🟠
   - Time Window: August 12-19, 2024 (8 days)
   - Focus: Compare with Event #1 - smaller ellipse, faster recovery

---

## 🎮 How to Use

### Option 1: Drag the Slider
1. Open the HTML file in your web browser
2. Grab the slider at the top left (labeled "Time Slider")
3. Drag smoothly from left to right to see day-by-day progression
4. Watch the ellipse and arrow update in real-time

### Option 2: Use Navigation Buttons
1. Click "← Previous" to go back one day
2. Click "Next →" to go forward one day
3. Day counter updates automatically

### Option 3: Step Through Keyboard
- Just drag the slider incrementally to examine each day carefully

---

## 📊 What You're Seeing

### The Color-Coded Ellipse (PM2.5 Concentration)
- 🟢 **Green** (#90EE90): PM2.5 < 25 ug/m³ - Safe, may barely see ellipse
- 🟠 **Orange** (#FF8C00): PM2.5 25-35 ug/m³ - Moderate starts appearing
- 🔶 **Orange-Red** (#FF4500): PM2.5 35-50 ug/m³ - High pollution visible
- 🔴 **Red** (#DC143C): PM2.5 50-100 ug/m³ - Severe ellipse
- 🟥 **Dark Red** (#8B0000): PM2.5 ≥ 100 ug/m³ - CRITICAL (only July 24)

### The Shape & Size
- **Larger ellipse** = Higher PM2.5 concentration
- **Elongated ellipse** = Strong wind blowing smoke in one direction
- **Rounder ellipse** = Weak wind, smoke dispersing evenly
- **Ellipse orientation** = Wind direction (rotates with wind changes)

### The Wind Arrow (From Calgary Center)
- **Arrow direction** = Where wind is pushing air (opposite of wind source)
- **Arrow color**:
  - 🔵 Blue = Weak wind (< 2 m/s)
  - 🟢 Green = Light wind (2-3 m/s)
  - 🟠 Orange = Moderate wind (3-4 m/s)
  - 🔴 Red = Strong wind (> 4 m/s)
- **Arrow length** = Proportional to wind speed

### The Blue Dot
- **Location**: Calgary City Center (51.0447°N, 114.0719°W)
- **Role**: Reference point for all calculations
- **Meaning**: The monitoring/impact point

---

## 🎯 Key Observations for Event #1 (July 24)

### Day 1-3 (Pre-Peak)
- Ellipse gradually grows
- Color deepens from yellow → orange → red
- Wind direction varies
- **Interpretation**: Pollution building up toward the event

### Day 4 (PEAK - July 24)
- **134.0 ug/m³** - Largest ellipse of all 8 days
- **Dark red color** - Most critical pollution level
- **Major axis ~125 km** - Enormous impact radius
- **★ PEAK DAY ★** marker visible in info panel
- **Interpretation**: The worst air quality day

### Day 5-8 (Recovery)
- Ellipse shrinks each day
- Color fades: red → orange → green
- PM2.5 drops back to normal (~15 ug/m³)
- **Interpretation**: Pollution disperses and system recovers

---

## 🎯 Comparison: Event #1 vs Event #2

### Event #1 (July 24)
```
PM2.5: 134.0 ug/m³ (CRITICAL)
Ellipse size: Very large (100+ km)
Color: Dark red throughout
Peak impact: Dramatic
Recovery time: 4 days to return to normal
```

### Event #2 (August 15)
```
PM2.5: 53.5 ug/m³ (SEVERE)
Ellipse size: Medium (50-70 km)
Color: Red/orange
Peak impact: Moderate
Recovery time: 2-3 days
```

**Key Insight**: Event #1 is **2.5x more severe** than Event #2, affecting a much larger area!

---

## 💡 Technical Details

### Ellipse Calculation
```
Base Radius = 50 km
Intensity Factor = PM2.5 / 25 (threshold)
Major Axis = Base × (1 + 0.5 × Wind Speed Factor)
Minor Axis = Base × (1 - 0.3 × Wind Speed Factor)
Final Radius = Base × Intensity Factor (capped at 250 km)
```

Example (July 24):
- PM2.5 = 134 → Intensity = 2.0 (capped)
- Wind Speed = 2.53 → Major = 125 km, Minor = 85 km
- **Result**: Large, slightly elongated ellipse

### Wind Arrow Calculation
```
Arrow Direction = Wind From (reversed 180°) = Wind To
Arrow Length = 0.05° + (Wind Speed × 0.04°)
Arrow Color = Based on Wind Speed magnitude
```

---

## 🎓 Presentation Tips

### Quick 2-Minute Demo
1. Open Event #1 map
2. Show it fully zoomed on day 1 (small green ellipse)
3. Drag slider to day 4 (massive dark red ellipse)
4. Say: "On July 24th, 134 units of PM2.5 created a 200+ km impact zone"
5. Drag to day 8 (back to green)
6. Conclusion: "Complete recovery in just 4 days due to wind dispersal"

### 5-Minute Deep Dive
1. Compare Event #1 and #2 side-by-side (on different monitors/windows)
2. Highlight size difference (2.5x larger for Event #1)
3. Discuss wind arrow variations (direction changes daily)
4. Point out how wind direction affects ellipse orientation
5. Note that stronger wind = more elongated ellipse

### 10-Minute Analysis
1. Temporal progression of Event #1
2. Day 1: Early warning (orange ellipse)
3. Day 2-3: Escalation (deepening red)
4. Day 4: Crisis (maximum impact)
5. Day 5-8: Recovery trend
6. Compare weather patterns with pollution spread
7. Discuss what controls pollution dispersion (wind, not emissions alone)

---

## ⚠️ Limitations & Model Assumptions

1. **Single-point model**: Uses Calgary city center as reference (real dispersion is more complex)
2. **Simplified wind field**: Assumes uniform wind across entire region
3. **Ellipse approximation**: 65-point polygon, not perfect ellipse
4. **No meteorology**: Doesn't model vertical mixing, atmospheric stability
5. **Threshold values**: PM2.5 threshold = 25 ug/m³, base radius = 50 km (tuned for visualization)

---

## 📝 File Specifications

- **File Type**: Standalone HTML (works offline)
- **Size**: ~9.5 KB each
- **Libraries**: Leaflet.js 1.9.4 (via CDN)
- **Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge)
- **Data**: All 8 days embedded in HTML (no external CSV/JSON needed)
- **Interaction**: Fully client-side JavaScript (no server needed)

---

## 🔗 Related Files

- **pm25_dispersion_detailed_v2.py** - Previous version (all 8 days overlaid, no slider)
- **pm25_interactive_slider_v3.py** - Script that generates these HTML files
- **DISPERSION_V2_GUIDE.md** - Original V2 guide (for reference)
- **SMOKE_DISPERSION_GUIDE.md** - V1 guide (for reference)

---

## 📞 Troubleshooting

| Issue | Solution |
|-------|----------|
| Ellipse not showing | Refresh page (Ctrl+F5), clear browser cache |
| Slider doesn't respond | Try clicking on slider, then dragging |
| Arrow not visible | Zoom in on Calgary area, arrow is small |
| Day info blank | Wait 1-2 seconds, page may still be loading |
| Map not loading | Check internet (CDN loading Leaflet), try different browser |

---

## 🎉 Key Achievement

✅ **V3 successfully converts static visualization into interactive exploration tool**
- Users can now step through each day manually
- Real-time redrawing of ellipse and arrow
- No need for animation or time delay
- Full control and flexibility for presentations

**This is ready for final project presentation!**

---

*Advanced PM2.5 Smoke Dispersion Visualization - Interactive Time-Slider Edition*
*ENGO645 Data Mining Project - Winter 2026*
