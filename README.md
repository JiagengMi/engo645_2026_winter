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
spatial_analysis.py              - 空间分析
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

### 可选功能
```bash
# 下一年预测
python predict_next_year.py

# 空间分析
python spatial_analysis.py
```

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
