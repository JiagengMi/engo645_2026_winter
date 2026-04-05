# 模型性能分析：高Accuracy vs 低Precision/F1分数问题

## 执行总结
三个模型（XGBoost, HistGradientBoosting, RandomForest）显示**高准确度（97%+）但低精确度和F1分数**的现象。这是**严重的类不平衡问题**导致的典型症状。

---

## 核心问题：严重的类不平衡

### 数据分布不均
| 数据集 | 总样本 | 正例（PM2.5≥25） | 负例（PM2.5<25） | 正例比例 | 不平衡比 |
|--------|--------|-----------------|-----------------|---------|---------|
| **Train** | 1,652 | 44 | 1,608 | 2.7% | 1:36.5 |
| **Val** | 354 | 29 | 325 | 8.2% | 1:11.2 |
| **Test** | 355 | 13 | 342 | 3.7% | 1:26.3 |
| **Master** | 2,361 | 86 | 2,275 | 3.6% | 1:26.4 |

### 为什么会导致高Accuracy但低Precision/F1？

**问题根源：**模型学会了"几乎总是预测负例"的策略，因为：
- 负例占96.3%，预测所有都是负例 → Accuracy = 96.3% ✓（看起来很好）
- 当模型预测正例时（很少发生），由于缺乏正例学习样本（只有13个），预测错误率高 → Precision低 ✗
- 模型难以学到正例的特征，错误分类正例 → Recall低 ✗
- F1 = 2×(Precision×Recall)/(Precision+Recall) → 当其中一个低就会很低 ✗

**混淆矩阵示意：**
```
                  预测负例    预测正例
实际负例（342个）   ~340       ~2        → 高TN，低FP
实际正例（13个）     ~11       ~2        → 低TP，高FN

Accuracy = (TN+TP)/Total ≈ 97% ✓（TN贡献最大）
Precision = TP/(TP+FP) ≈ 50-85% ✗（TP很小）
Recall = TP/(TP+FN) ≈ 15-46% ✗（FN太多）
```

---

## 数据清理问题

### 1. 完全缺失的特征列
```
wx_precip_max_mm: 100%缺失（2361/2361行无数据）
```
**影响：** 模型试图使用无信息的特征，增加了学习负例的倾向

### 2. 零方差特征（常数列）
```
pm25_station_count: 所有值都是1.0（恒定）- 完全无信息
wx_precip_total_mm: 方差=0
fire_smoke_transport_index: 方差=0.001（极低）
```
**影响：** 这些列占用特征空间但没有区分能力，模型浪费学习容量

### 3. 数据有效性问题
```
原始数据中有13个负PM2.5值（物理上不可能，应为≥0）
⟹ 数据源质量问题
```

### 4. 数据丢弃
```
197行被移除（7.7%）因为PM2.5缺失
⟹ 本来就少的正例可能被进一步减少
```

---

## 详细的模型性能对比

```
Model                      Accuracy  Precision  Recall  F1     ROC-AUC
────────────────────────────────────────────────────────────────────
XGBoost                    97.7%     85.7%      46.2%   60.0%  96.2%
HistGradientBoosting       97.5%     75.0%      46.2%   57.1%  96.5%
RandomForest               96.9%     75.0%      23.1%   35.3%  96.0%
LogisticRegression         82.5%     17.3%      100%    29.5%  95.9%
```

**关键观察：**
- **Accuracy很相似（82-97%）**：因为主要贡献来自预测负例（96%的数据都是负例）
- **ROC-AUC都很高（95-96%）**：ROC-AUC对不平衡数据更鲁棒，表明模型实际上有区分能力
- **Precision与Recall权衡**：
  - XGBoost/HistGBM选择保守（高precision，中等recall）
  - LogisticRegression激进（低precision，高recall=100%）
  - RandomForest很激进（中等precision，低recall）

---

## 问题根本原因总结

| 问题 | 严重程度 | 来源 |
|------|--------|------|
| 严重类不平衡（正例3.7%） | 🔴 **极严重** | 数据本身特性 |
| 测试集正例极少（仅13个） | 🔴 **极严重** | 数据清理和分割 |
| 零方差/低方差特征 | 🟡 **中等** | 数据清理 |
| 完全缺失的特征列 | 🟡 **中等** | 源数据问题 |
| 无效数据值（负PM2.5） | 🟠 **轻中等** | 源数据质量 |

---

## 解决方案建议

### A. 数据清理改进
```python
# 1. 移除无信息特征
features_to_remove = ['pm25_station_count', 'wx_precip_max_mm',
                      'wx_precip_total_mm', 'fire_smoke_transport_index']

# 2. 过滤无效数据
df = df[df['pm25'] >= 0]  # 移除负值

# 3. 数据验证
assert df[numeric_cols].var().min() > 0.01  # 检查方差
assert df['pm25'].notna().sum() == len(df)  # 确保无缺失
```

### B. 应对类不平衡
```python
# 选项1：类权重
from sklearn.utils.class_weight import compute_class_weight
class_weights = compute_class_weight('balanced',
                                     classes=np.unique(y),
                                     y=y)

# 选项2：过采样正例或欠采样负例
from imblearn.over_sampling import SMOTE
smote = SMOTE(sampling_strategy=0.5)  # 使正例达到负例的50%
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

# 选项3：调整决策阈值（使用ROC-AUC找最优）
# 优化后 precision-recall 权衡

# 选项4：用F1/AUC作为评估指标而不是Accuracy
from sklearn.metrics import f1_score, make_scorer
f1_scorer = make_scorer(f1_score)
```

### C. 特征工程
```python
# 1. 检查/创建与PM2.5高污染相关的特征
#    - 火灾强度指标的平方项（非线性）
#    - 逆风火灾的加权组合
#    - 气象条件与火灾的交互项

# 2. 移除/替换无信息的特征
#    - 用有意义的代理特征替换零方差列

# 3. 特征选择
#    基于信息增益或互信息的特征排名
```

### D. 模型调整
```python
# 1. XGBoost可以直接处理class权重
xgb.XGBClassifier(scale_pos_weight=26.3)  # 26.3 = 不平衡比

# 2. 调整概率阈值而不是用默认的0.5
# 基于business需求（宁可误报也别漏报？）选择阈值
threshold = 0.3  # 提高recall，降低precision

# 3. 用不同的metric进行交叉验证
# F1-weighted 或 AUC 而不是 Accuracy
```

### E. 评估指标改进
```python
# 不再用Accuracy，改用：
# - F1分数（加权）
# - PR-AUC（精确率-召回率曲线）
# - ROC-AUC已经不错，可以保留
# - 考虑业务成本（误报的成本vs漏报的成本）
```

### F. 数据采集
```
• 收集更多PM2.5≥25的日期样本（可能需要扩展到更多地点或年份）
• 改进源数据的质量控制（验证PM2.5不为负）
• 添加更多相关的预测特征
```

---

## 建议优先级

**立即做（高优先级）：**
1. ✅ 移除零方差特征
2. ✅ 验证和清理无效数据（负PM2.5值）
3. ✅ 在训练中使用class_weights
4. ✅ 改用F1或AUC-PR评估

**短期内做（中优先级）：**
5. ✅ 尝试SMOTE过采样
6. ✅ 优化决策阈值
7. ✅ 特征工程和选择

**长期改进（低优先级）：**
8. ✅ 收集更多高PM2.5样本
9. ✅ 改进数据源质量
10. ✅ 建立专门的异常值检测模型

---

## 展示给教授的关键点

这个现象是**机器学习中的经典教学案例**，展示了：
- ✅ 为什么Accuracy是个**欺骗性指标**对于不平衡数据
- ✅ 为什么需要**多个评估指标**
- ✅ 为什么**数据质量和平衡**对模型性能的重要性
- ✅ 如何**识别和诊断模型问题**的根本原因
- ✅ **现实世界数据挑战**（PM2.5高污染事件少见）

**这是一个很好的学习机会来展示数据科学中的关键思维！**
