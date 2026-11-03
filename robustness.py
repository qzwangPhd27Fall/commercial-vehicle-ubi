# -*- coding: utf-8 -*-
"""稳健性检验：规则权重±10%扰动下评分排序的稳定性"""
import pandas as pd, numpy as np
from scipy import stats

fleet = pd.read_csv('simulated_fleet.csv')
W = dict(百公里报警频率=0.28, 高风险报警占比=0.18, 高速报警比=0.11, 报警聚集度=0.07,
         超速时间比=0.16, 速度波动=0.08, 夜间驾驶比例=0.12)

def winsor(x, lo=0.01, hi=0.99):
    return np.clip(x, np.quantile(x, lo), np.quantile(x, hi))
def mm(x):
    x = winsor(x); return (x - x.min()) / (x.max() - x.min()) * 100.0

def rule_score(W):
    s = np.zeros(len(fleet))
    for k, w in W.items():
        v = fleet[k].values
        if k == '百公里报警频率':
            v = np.log(v)
        s += w * mm(v)
    return s

base = fleet['综合评分'].values
rng = np.random.default_rng(42)
spearman = []
top10_overlap = []
for _ in range(500):
    Wp = {k: w * (1 + rng.uniform(-0.1, 0.1)) for k, w in W.items()}
    tot = sum(Wp.values())
    Wp = {k: v / tot for k, v in Wp.items()}
    sp = rule_score(Wp)
    comb = 0.5 * sp + 0.5 * fleet['GLM评分B'].values
    spearman.append(stats.spearmanr(comb, base)[0])
    top10_overlap.append(len(set(np.argsort(-comb)[:40]) & set(np.argsort(-base)[:40])) / 40)

spearman = np.array(spearman); top10_overlap = np.array(top10_overlap)
print(f'权重扰动秩相关：均值 {spearman.mean():.4f}，最小 {spearman.min():.4f}')
print(f'Top10(40台)重合率：均值 {top10_overlap.mean():.3f}，最小 {top10_overlap.min():.3f}')
