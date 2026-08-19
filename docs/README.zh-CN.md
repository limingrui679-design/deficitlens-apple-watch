# DeficitLens 中文概览

DeficitLens 不是又一个“把 Apple Watch 圆环画得更漂亮”的项目。它先检验手表的活动能量
估计误差，再讨论这个误差会怎样影响减脂计划。

项目的核心包括：Apple Health `export.xml` 隐私化解析、Apple Watch Series 6 与 VO₂
参考值逐秒对齐、按受试者完全隔离的嵌套验证、非负凸堆叠、90% 保形预测区间、性别/
体脂/BMI/活动类型分组审计，以及 Series 8 对 COSMED K5 的独立误差审计。

最重要的边界：模型不会把手表热量、体重变化或算法预测冒充“真实热量缺口”。所有减脂
结果均为带固定假设的敏感性情景，而不是个体减重预测或医疗建议。

快速体验：

```bash
python -m pip install -e ".[dev]"
deficitlens demo --output artifacts/demo
```

真实结果、样本量、校验和和运行环境以
[`artifacts/verified/run_manifest.json`](../artifacts/verified/run_manifest.json) 为准；完整方法见
[`methodology.md`](methodology.md)，适用边界见 [`model-card.md`](model-card.md)。
