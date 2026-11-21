# DeficitLens 中文概览

同样一段运动，Apple Watch 记录的活动热量与实验室测得的能量消耗会相差多少？DeficitLens 将手表信号与摄氧量对齐，轮流留出一名参与者，用其他人的数据训练校正模型，再检验它对这个人的估计。

在 WEEE 数据集的 17 名参与者、6 类活动中，Series 6 原始读数的平均绝对误差为 1.651 千卡/分钟，校正后为 1.082 千卡/分钟。报告还分活动展示误差，以独立的 Series 8 数据比较设备读数，并计算测量误差会如何改变能量收支情景。[查看完整结果](../artifacts/verified/report.html)

快速体验：

```bash
python -m pip install -e ".[dev]"
deficitlens demo --output artifacts/demo
deficitlens cases
```

四条案例路径分别对应：Series 6 受试者外推基准、Series 8 独立设备一致性审计、本地 Apple
Health 隐私审计，以及多假设减脂误差敏感性分析。案例目录、证据状态、输出和表述边界均可
由 CLI 读取，而不是只写在 README 中。

真实结果、样本量、校验和和运行环境以
[`artifacts/verified/run_manifest.json`](../artifacts/verified/run_manifest.json) 为准；完整方法见
[`methodology.md`](methodology.md)，适用边界见 [`model-card.md`](model-card.md)。

当前状态是本地发布候选版，尚无已核验的公开仓库、独立复现、真实用户、部署、采用或影响
证据；这些项目在 [`external-evidence.json`](../evidence/external-evidence.json) 中按零值或
“未观测”如实记录。

在 WEEE 17 名参与者的 811 个窗口上，逐人等权时，组合模型相对原始手表的平均绝对误差降低 0.5533 千卡/分钟。在同一组参与者之间重新分配 25% 的权重，最低改善仍为 0.2053 千卡/分钟；达到平局需要重新分配约 45.29% 的权重。[计算方法和原始预测](methodology.md#how-much-can-the-mix-of-people-change-a-model-comparison)
