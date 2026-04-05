# ENGO645 Data Mining Project - Final Version

## 项目结构

### 📥 数据下载脚本
```
download_era5_calgary.py         - 下载ERA5气候数据
download_openaq_pm25.py          - 下载PM2.5空气质量数据
download_weather.py              - 下载天气数据
```

### 🔧 数据处理
```
data cleaning.py                 - 数据清理和特征工程
```

### 🤖 模型训练（改进版本）
```
train_logistic_regression.py                   - 逻辑回归
train_random_forest_improved.py                - 改进的随机森林
train_gradient_boosting_improved.py            - 改进的梯度提升
```

### 📊 评估与可视化
```
evaluate_final_models.py         - 最终评估（5-fold CV + 测试集）
plot_style.py                    - 绘图样式配置
view_results.py                  - 快速查看结果
```

### 🚀 管道与辅助
```
run_project_pipeline.py          - 一键运行完整管道
predict_next_year.py             - 下一年预测
spatial_analysis.py              - 火灾空间分析
pm25_spatial_temporal_analysis.py - PM2.5 时空分析（数据挖掘应用）
requirements.txt                 - Python依赖列表
```

---

## 快速开始

### 运行完整管道（推荐）
```bash
python run_project_pipeline.py
```

此命令会自动执行：
1. 数据清理
2. 训练三个模型
3. 执行5-fold交叉验证
4. 生成评估结果和可视化

### 查看结果
```bash
python view_results.py
```

---

## 可选功能

### 运行下一年预测
```bash
python predict_next_year.py
```

### 火灾空间分析
```bash
python spatial_analysis.py
```

### PM2.5 时空分析（数据挖掘应用）
```bash
python pm25_spatial_temporal_analysis.py
```

### PM2.5 时间动画地图（新增：时间可调、事件回放）
```bash
python pm25_animated_event_maps.py
```

---

## 数据挖掘应用：PM2.5 时空模式发现

### 发现的关键模式

**1. 时间模式**
- 高污染峰值月份：7月（July）- 5天
- 最安全月份：1月（January）- 0天
- 年度趋势：高污染事件逐年减少

**2. 季节性分布**
- 冬季平均 PM2.5: 7.61 μg/m³
- 春季平均 PM2.5: 6.30 μg/m³（最低）
- 夏季平均 PM2.5: 12.75 μg/m³（最高）
- 秋季平均 PM2.5: 7.21 μg/m³

**3. 污染事件分析**
- 分析期间：355 天（2024年4月-2025年4月）
- 高污染天数：13 天（3.66%）
- 最高 PM2.5 浓度：134.0 μg/m³
- 高污染日平均 PM2.5：45.99 μg/m³

**4. 模型预测性能**
- 整体准确率：98.03%
- 正确预测：348/355天
- 成功识别高污染模式

### 输出文件位置

```
processed/model_outputs/spatial_temporal_analysis/
├── SPATIAL_TEMPORAL_ANALYSIS_REPORT.txt      # 完整分析报告
├── pm25_temporal_heatmap.png                 # 月份-年份热力图
├── high_pollution_events_analysis.png        # 高污染事件分析
├── pm25_time_series_analysis.png             # 时间序列分析
├── model_predictions_analysis.png            # 模型预测分析
├── pm25_spatial_interactive_map.html         # 交互式地图
├── high_pollution_events.csv                 # 高污染事件数据
├── temporal_monthly_patterns.csv             # 月度模式统计
├── temporal_yearly_patterns.csv              # 年度模式统计
├── pm25_event_explorer_index.html           # [NEW] 事件浏览器导航（推荐！）
├── pm25_animated_timeline_map.html          # [NEW] 完整时间线动画地图
└── pm25_event_xx_yyyymmdd_7day_playback.html # [NEW] 各个事件7日回放（13个）
```

---

## 时间动画地图功能说明（NEW）

### 功能特点

**1. pm25_event_explorer_index.html** (推荐首先打开)
- 所有时间动画地图的导航索引
- 汇总13个高污染事件
- 提供快速访问链接

**2. pm25_animated_timeline_map.html** (完整时间线)
- 显示整个分析期间所有日期的PM2.5变化（2024年4月-2025年4月）
- 使用时间滑块浏览任意日期
- 自动播放功能查看整个时期变化

**3. pm25_event_xx_yyyymmdd_7day_playback.html** (13个事件地图)
- 每个高污染事件的7天追踪
- 选择任一事件查看其灾难发生->恢复的全过程
- 从事件起始日期开始回放接下来7天的PM2.5演变

### 如何使用

1. **打开导航页面**
   ```
   在浏览器中打开：pm25_event_explorer_index.html
   ```

2. **选择查看模式**
   - "完整时间线地图" - 了解整年的PM2.5全景
   - 任一"事件卡片" - 深入观察特定污染事件的7日演变

3. **播放动画**
   - 点击▶(播放)按钮自动播放各天变化
   - 自动前进到下一天，观察PM2.5如何逐日变化
   - 使用◀◀(快进)、▶▶(快退)调整播放速度

4. **手动探索**
   - 拖动时间滑块到任意日期
   - 看该日期的PM2.5水平和风险等级（颜色指示）

### 风险等级说明

| 颜色 | 风险等级 | PM2.5范围 |
|------|--------|---------|
| 🟢 绿色 | 低 | <25 μg/m³ |
| 🟠 橙色 | 中等 | 25-35 μg/m³ |
| 🔴 红色 | 高 | 35-50 μg/m³ |
| 🟥 深红 | 严重 | >50 μg/m³ |

### 关键观察点

- **7月高污染集中**：事件5-7都在7月，连续多天严重污染
- **快速恢复**：观察8月14-17事件，看到污染消退速度
- **12月异常**：唯一的冬季高污染事件（事件13）
- **演变模式**：每个事件的上升、顶峰、下降阶段

---

---

## 最终模型性能

| 排名 | 模型 | Test F1 | Precision | Recall |
|------|------|---------|-----------|--------|
| 🏆 1 | HistGradientBoosting_Improved | **0.6667** | **0.8750** | 0.5385 |
| 2 | RandomForest_Improved | 0.5405 | 0.4167 | 0.7692 |
| 3 | LogisticRegression | 0.2955 | 0.1733 | 1.0000 |

---

## 改进成果

**RandomForest 正则化：**
- Test F1: 0.3529 → 0.5405 (+53%)
- 泛化Gap: 64.2% → 19.2% (-67%)

**HistGradientBoosting L2正则化：**
- Test F1: 0.5714 → 0.6667 (+17%)
- Precision: 75% → 87.5% (+12.5%)

---

## 输出文件位置

所有结果保存在：
```
processed/model_outputs/evaluation/
├── final_test_summary.csv           # 测试集结果
├── final_cv_summary.csv             # 交叉验证结果
├── final_roc_curves.png             # ROC曲线
├── final_pr_curves.png              # Precision-Recall曲线
└── final_metrics_comparison.png     # 指标对比图
```

---

## Dependencies

See `requirements.txt` for all Python dependencies.

Key packages:
- pandas, numpy: 数据处理
- scikit-learn: 机器学习
- joblib: 模型存储
- matplotlib, seaborn: 绘图
- folium, geopandas: 空间分析
