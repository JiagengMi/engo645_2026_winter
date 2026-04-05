# 模型改进计划

## 问题诊断
```
RandomForest:          CV F1=0.987 → Test F1=0.353  (gap=64.2%)
HistGradientBoosting:  CV F1=1.000 → Test F1=0.571  (gap=42.9%)

根本原因：
1. 树模型过度复杂，记住了训练数据中的罕见正例
2. 数据极度不平衡（正例3.7%）
3. 缺乏足够的正则化约束
```

## 改进策略（5个步骤）

### 步骤 1️⃣ : 减少RandomForest的复杂性
**目标**: 缩小max_depth，增加min_samples_leaf/split限制

当前配置：
- max_depth: 10, 12, None (太大!)
- min_samples_leaf: 1, 2 (太小!)

改进配置：
- max_depth: 5, 7, 10 (更小的上限)
- min_samples_leaf: 10, 20, 30 (更大的限制)
- min_samples_split: 20, 40, 60 (阻止小分裂)

### 步骤 2️⃣ : 为HistGradientBoosting添加L2正则化
**目标**: 添加l2_regularization参数防止过拟合

当前配置：
- learning_rate: 0.05, 0.03
- max_depth: 6, 8, 10
- 缺少l2_regularization

改进配置：
- 降低learning_rate: 0.01, 0.02, 0.03 (更稳定)
- 添加l2_regularization: 0.01, 0.1, 1.0
- 保持合理的max_depth: 4, 5, 6

### 步骤 3️⃣ : 对不平衡数据进行SMOTE过采样
**目标**: 增加训练集中的正例数量

当前：Train有44个正例
改进：使用SMOTE让正例达到负例的30-50%

### 步骤 4️⃣ : 优化决策阈值
**目标**: 从0.5调整到更优的阈值

当前：固定阈值0.5
改进：基于F1/Precision-Recall曲线优化

### 步骤 5️⃣ : 移除无信息特征
**目标**: 清理零方差特征

需要移除：
- pm25_station_count (恒定值1.0)
- wx_precip_total_mm (零方差)
- 超低方差的特征

---

## 执行顺序

1. **首先尝试步骤1+2** (正则化改进) - 最快最直接
   → 如果有显著改进，继续
   → 如果不够，再加步骤3+4

2. **测试每个改进** 用 evaluate_models_cv.py
   → 记录CV性能和Test性能的gap
   → 对比改进前后

3. **最后尽量简化** 移除无用特征

---

## 预期结果

如果成功：
```
原始：      RandomForest Gap = 64.2%  →  改进后: Gap < 30%
原始：      HistGBM Gap = 42.9%    →  改进后: Gap < 20%
```

目标是让Test性能接近CV性能，而不仅仅提高绝对分数！
