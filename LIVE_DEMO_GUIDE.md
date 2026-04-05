# ⚡ QUICK REFERENCE: Live Demo Guide

## 🎮 How to Operate the Interactive Maps (During Presentation)

### Opening the Map
1. **Before presentation**: Have the HTML file already open and zoomed to Calgary area
2. **During presentation**: Full-screen the browser window (F11 or maximize)
3. **Alt+Tab**: Can quickly switch between two maps if comparing

---

## 🎯 DEMO SCRIPT: 2-Minute Walkthrough

### Setup
- **Map**: `pm25_event_1_interactive.html` (July 24 event)
- **Position**: Zoom level 7, Calgary centered
- **Controls visible**: Time slider at top-left

### Act 1: Show Day 1 (Slow buildup)
```
Narrator: "Look at July 21st - this is 3 days before the peak event."
Action: Slider is at position "1/8"
What to point out:
  - Small GREEN ellipse (low PM2.5)
  - Weak arrow (blue, small)
  - Info shows: PM2.5 ~15 ug/m³
Audience sees: "Looks normal"
```

### Act 2: Advance to Day 3 (Building tension)
```
Narrator: "By July 23rd, 2 days later, we see the pollution building..."
Action: Drag slider to position "3/8"
What to point out:
  - LARGER RED ellipse (high PM2.5)
  - Arrow is now ORANGE (stronger wind)
  - Info shows: PM2.5 ~50 ug/m³
Audience reaction: "It's getting worse!"
```

### Act 3: PEAK - Day 4 (Dramatic reveal)
```
Narrator: "And THIS is July 24th - the worst day. Look at this!"
Action: Drag slider to position "4/8"
What to point out:
  - MASSIVE DARK RED ellipse (CRITICAL)
  - Info shows: ★ PEAK DAY ★ (red star marker)
  - Impact radius: ~125 km
  - PM2.5: 134.0 ug/m³ (HIGHEST)
Audience reaction: "WOW! That's HUGE!"
Talking point:
  "This ellipse represents the entire pollution impact zone.
   Anyone in this area would experience dangerous air quality.
   That covers from downtown Calgary potentially 200 kilometers away."
```

### Act 4: Recovery begins - Days 5-8
```
Narrator: "Now watch as nature recovers..."
Action: Slowly drag slider from "5" toward "8"
What to observe:
  - Day 5: Ellipse smaller, color fades to orange
  - Day 6: Back to GREEN, much smaller, safe again
  - Day 7-8: Barely visible green ellipse
Transition: "In just 3-4 days, pollution cleared completely"
```

### Act 5: Compare with Event #2 (Optional)
```
Action: Switch to pm25_event_2_interactive.html
Drag its slider to "4" (peak day: August 15)
Comparison comment:
  "Same type of event, but August 15th was about 2.5x less severe.
   The ellipse is half the size, different wind pattern.
   This shows environmental conditions change day-to-day."
```

---

## 🕹️ Slider Controls Cheat Sheet

### Slider Control
```
Position 1 = July 21 (3 days before peak)
Position 2 = July 22 (2 days before peak)
Position 3 = July 23 (1 day before peak)
Position 4 = July 24 (★ PEAK DAY ★) ← MOST DRAMATIC
Position 5 = July 25 (1 day after peak)
Position 6-8 = Recovery days
```

### Button Controls
- **← Previous**: Goes back one day (good for step-by-step)
- **Next →**: Goes forward one day

### Keyboard Alternative
- Press LEFT/RIGHT arrows on keyboard (if clicked in correct area)

---

## 💬 What to Highlight to Audience

### When showing the ELLIPSE:
- "This is calculated from PM2.5 concentration and wind speed"
- "Bigger ellipse = larger impact radius"
- "Color intensity shows severity (green=safe, red=severe, dark red=critical)"
- "Notice it ROTATES with wind direction - ellipse points where wind blows"

### When showing the ARROW:
- "This arrow represents wind direction and speed"
- "Blue = weak wind, Red = strong wind"
- "Direction shows which way the wind is blowing"
- "Combined with ellipse: tells us where pollution is being carried"

### When showing INFO PANEL:
- "PM2.5 is the pollutant - measured in micrograms per cubic meter"
- "Wind speed (m/s) affects how quickly pollution disperses"
- "Wind direction (degrees) shows the compass heading"
- "These environmental factors control dispersion more than emission alone"

---

## �danger: Common Mistakes to Avoid

❌ **DON'T:**
- Zoom in too much (lose the full ellipse visualization)
- Drag slider too fast (audience can't see the details)
- Forget to point out the PEAK DAY marker (★)
- Skip showing multiple days (show the progression, not just peak)

✅ **DO:**
- Drag slowly so audience sees smooth transition
- Pause on peak day (day 4) for dramatic effect - hold for 5 seconds
- Point at specific features (arrow, ellipse, info panel)
- Use repetition: "See how the green expands and then shrinks?"

---

## 📱 Technical Fallbacks

**If slider doesn't work:**
- Right-click on slider, reload page
- Try different browser (use Chrome if it fails)
- Drag should work; if not, use Previous/Next buttons instead

**If ellipse doesn't show:**
- Zoom out to see full area (use mouse wheel or +/- buttons)
- Refresh page (F5)
- Make sure browser is maximized

**If map doesn't load at all:**
- Verify file path is correct
- Double-click the HTML file (open with browser)
- Try dragging file directly into browser window

---

## ⏱️ TIMING GUIDE

- Opening/context: 1 minute
- Day-by-day walkthrough: 2 minutes
  - Days 1-3: 20 seconds
  - Day 4 (peak): 30 seconds (dramatic pause!)
  - Days 5-8: 20 seconds
- Event #2 comparison: 1 minute (optional)
- Analysis/conclusions: 1 minute

**Total demo time: 3-5 minutes** ✓ (Good for presentation flow)

---

## 🎬 SAMPLE NARRATION (Copy-paste ready)

### 30-Second Version
> "Here's our PM2.5 interactive model for Calgary. Watch what happens during a major pollution event. [Drag to day 4] On July 24th, 2024, PM2.5 hit 134 micrograms per cubic meter - our worst day ever. The dark red ellipse represents the impact zone - spanning potentially 200 kilometers. Wind patterns shown by the arrow determined how pollution dispersed. [Drag to day 8] Within 4 days, natural processes cleared the air completely. This is how environmental factors control pollution, and why predictive modeling matters for public health."

### 60-Second Version
> "Our model successfully predicts high-pollution events with 98% accuracy. Let me show you a real example from July 2024. [Start at day 1] Three days before the peak, you see a small green ellipse - everything's normal. [Drag slowly through days 2-3] The ellipse grows and turns orange - pollution is building. [Stop at day 4 with dramatic pause] This is July 24th. The ellipse becomes massive and dark red. This represents 134 μg/m³ - dangerously high. The arrow shows wind direction. [Drag to days 5-8] Now watch the recovery. By day 8, everything returns to green. Environmental conditions - particularly wind speed and direction - determine how quickly pollution disperses. Our data mining approach captured these patterns, enabling accurate predictions."

---

## 🏁 PRESENTATION CHECKLIST (5 min before)

- [ ] HTML file open in browser and tested
- [ ] Map zoomed to show full Calgary area
- [ ] Slider works smoothly
- [ ] Ellipse and arrow visible
- [ ] Info panel displays correctly
- [ ] Resolved any technical issues
- [ ] Browser maximized/fullscreen ready
- [ ] You know which HTML file is for which event
- [ ] You have your talking points ready
- [ ] Audience can see the screen clearly

---

**You've got this! 🎉**

*Go in there and show your professor an amazing interactive visualization with a successful data mining project!*
