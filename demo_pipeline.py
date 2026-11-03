# -*- coding: utf-8 -*-
"""
商用车UBI风险评估模型 —— 演示版分析管线（费率口径）
================================================
口径设计（精算标准）：
  - 风险评分 = 纯风险率（每单位暴露的出险倾向），不含里程暴露
  - 里程暴露单独进入保费/赔付测算（PAYD 思路）
  - 出险率单调性在「每万公里出险次数」上衡量

数据策略（三层标定，全部可溯源）：
  1. 真实样本车锚点：样本车A 4天真实运营（158报警/582.97km/27.1次百公里/5类占比/均速44.9）
  2. 行业公开参数：商用车百公里报警5~15次、UBI增量Gini 5~15pct、商用车险赔付率高
  3. 蒙特卡洛模拟：以样本车+行业参数标定，模拟400台商用车车队

输出：simulated_fleet.csv / metrics.json / charts/*.svg
"""
import os, json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm

BASE = r'C:\Users\user\Desktop\商用车UBI演示'
CHART_DIR = os.path.join(BASE, 'charts')
os.makedirs(CHART_DIR, exist_ok=True)
rng = np.random.default_rng(20261011)

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 110
matplotlib.rcParams['svg.fonttype'] = 'none'

C = dict(primary='#1f4e79', accent='#c00000', teal='#2e7d6b', amber='#c87d0e',
         gray='#7f7f7f', light='#dbe5ef', grid='#e6e6e6',
         grade=['#1f9e6e', '#5bb98c', '#d6a93a', '#d97b3a', '#c0392b'])

N = 400
SEED_SAMPLE = dict(alarms=158, km=582.97, per100km=27.1, avg_speed=44.9,
                   comp_high=0.297, night=0.0, overspeed=0.137,
                   highspeed_alarm=0.386, cluster=0.905)

def simulate_fleet(n, rng):
    types = (['重型货车'] * 40 + ['中型货车'] * 15 + ['轻型货车'] * 25
             + ['大型客车'] * 10 + ['中型客车'] * 10)
    types = (types * (n // 100 + 1))[:n]
    rng.shuffle(types)
    m_mu = dict(重型货车=140000, 中型货车=100000, 轻型货车=80000, 大型客车=100000, 中型客车=65000)
    m_sd = dict(重型货车=22000, 中型货车=16000, 轻型货车=15000, 大型客车=16000, 中型客车=12000)
    mileage = np.array([max(40000, rng.normal(m_mu[t], m_sd[t])) for t in types])

    # 双潜变量：频率风险 z_freq（危险情境多寡）+ 严重度风险 z_sev（单次情境危险程度）
    z_freq = rng.normal(0, 1, n)
    z_sev = rng.normal(0, 1, n)

    # ---- ADAS报警维度：频率类因子←z_freq，严重度结构类因子←z_sev（独立通道，避免共线）----
    log_per100 = np.log(9.0) + 0.50 * z_freq + 0.15 * rng.normal(0, 1, n)
    per100km = np.exp(log_per100)
    comp_high = np.clip(0.20 + 0.12 * z_sev + 0.04 * rng.normal(0, 1, n), 0.08, 0.55)
    cluster = np.clip(0.70 + 0.06 * z_freq + 0.06 * rng.normal(0, 1, n), 0.35, 0.98)
    highspeed_alarm = np.clip(0.30 + 0.08 * z_sev + 0.06 * rng.normal(0, 1, n), 0.05, 0.75)

    # ---- 驾驶行为维度（中强关联频率风险）----
    avg_speed = np.clip(45 + 3.0 * z_freq + 7.0 * rng.normal(0, 1, n), 32, 78)
    overspeed = np.clip(0.12 + 0.12 * z_freq + 0.08 * rng.normal(0, 1, n), 0, 0.40)
    speed_std = np.clip(14 + 4.0 * z_freq + 8.0 * rng.normal(0, 1, n), 4, 34)

    # ---- 出行模式维度 ----
    is_truck = np.array([t in ('重型货车', '中型货车', '轻型货车') for t in types])
    night = np.clip(0.03 + 0.14 * is_truck + 0.10 * z_freq + 0.05 * rng.normal(0, 1, n), 0, 0.45)
    daily_km = mileage / 330.0

    # ---- 出险结果：率 = 基础率 × 风险；次数 = 率 × 暴露 ----
    base_rate = 0.22 / (np.mean(mileage) / 10000.0 * np.exp(0.60 ** 2 / 2 + 0.30 ** 2 / 2))
    rate_per_10kkm = base_rate * np.exp(0.60 * z_freq + 0.30 * z_sev)
    lam = rate_per_10kkm * (mileage / 10000.0)
    claims = rng.poisson(lam)
    sev_mean = np.where(is_truck, 18000.0, 12000.0)
    payout = np.where(claims > 0, claims * rng.gamma(2.0, sev_mean / 2.0, n), 0.0)

    df = pd.DataFrame(dict(
        车辆ID=[f'CV{i:04d}' for i in range(n)],
        车型=types, 年里程=mileage.round(0), 日均里程=daily_km.round(1),
        百公里报警频率=per100km.round(1), 高风险报警占比=comp_high.round(3),
        报警聚集度=cluster.round(3), 高速报警比=highspeed_alarm.round(3),
        平均速度=avg_speed.round(1), 超速时间比=overspeed.round(3), 速度波动=speed_std.round(1),
        夜间驾驶比例=night.round(3),
        出险次数=claims, 赔付额=payout.round(0), 潜在风险z=(0.6 * z_freq + 0.3 * z_sev).round(3),
    ))
    df['每万公里出险'] = (df['出险次数'] / (df['年里程'] / 10000.0)).round(4)
    return df

def winsorize(x, lo=0.01, hi=0.99):
    return np.clip(x, np.quantile(x, lo), np.quantile(x, hi))

def minmax(x):
    x = winsorize(x)
    return (x - x.min()) / (x.max() - x.min()) * 100.0

# 阶段A 规则评分权重（费率口径，纯风险率，不含里程暴露；ADAS为核心 0.64）
W_RULE = dict(百公里报警频率=0.28, 高风险报警占比=0.18, 高速报警比=0.11, 报警聚集度=0.07,
              超速时间比=0.16, 速度波动=0.08, 夜间驾驶比例=0.12)
assert abs(sum(W_RULE.values()) - 1.0) < 1e-9

def rule_score(df):
    s = np.zeros(len(df))
    for k, w in W_RULE.items():
        v = df[k].values
        if k == '百公里报警频率':
            v = np.log(v)
        s += w * minmax(v)
    return s

print('== 1. 模拟车队 ==')
fleet = simulate_fleet(N, rng)

print('== 2. 规则评分(阶段A) ==')
fleet['规则评分A'] = rule_score(fleet).round(1)

print('== 3. GLM(阶段B)：Poisson 频率模型 ==')
fleet['log百公里报警'] = np.log(fleet['百公里报警频率'])
X_cols = ['log百公里报警', '高风险报警占比']   # 两独立信号：近失频率 + 严重度结构
X = fleet[X_cols].copy()
for c in X_cols:
    X[c] = (X[c] - X[c].mean()) / X[c].std()
X = sm.add_constant(X)
glm = sm.GLM(fleet['出险次数'], X, offset=np.log(fleet['年里程'] / 10000.0),
             family=sm.families.Poisson()).fit()
pred_rate = glm.predict(X, offset=np.log(fleet['年里程'] / 10000.0)) / (fleet['年里程'] / 10000.0)
fleet['GLM评分B'] = minmax(pred_rate).round(1)

print('== 4. 综合评分（主客观双轨平均）==')
fleet['综合评分'] = (0.5 * fleet['规则评分A'] + 0.5 * fleet['GLM评分B']).round(1)

print('== 5. A-E 风险分级 ==')
fleet['风险等级'] = pd.qcut(fleet['综合评分'], 5, labels=['A', 'B', 'C', 'D', 'E'])

print('== 6. 无ADAS对照模型（行为因子）==')
X_no = fleet[['超速时间比', '夜间驾驶比例']].copy()
for c in X_no.columns:
    X_no[c] = (X_no[c] - X_no[c].mean()) / X_no[c].std()
X_no = sm.add_constant(X_no)
glm_no = sm.GLM(fleet['出险次数'], X_no, offset=np.log(fleet['年里程'] / 10000.0),
                family=sm.families.Poisson()).fit()
pred_no = glm_no.predict(X_no, offset=np.log(fleet['年里程'] / 10000.0)) / (fleet['年里程'] / 10000.0)
fleet['无ADAS评分'] = minmax(pred_no).round(1)

# ---------------- 验证指标 ----------------
def gini_capture(df, score_col, outcome='出险次数'):
    d = df.sort_values(score_col, ascending=False).reset_index(drop=True)
    tot = d[outcome].sum()
    if tot == 0:
        return 0.0
    cum = d[outcome].cumsum() / tot
    x = np.arange(1, len(d) + 1) / len(d)
    return 2 * np.trapz(cum, x) - 1.0

def capture_at_top(df, score_col, outcome='出险次数', q=0.1):
    n_top = max(1, int(len(df) * q))
    return df.nlargest(n_top, score_col)[outcome].sum() / df[outcome].sum()

def ks_stat(df, score_col, outcome='出险次数'):
    d = df.sort_values(score_col)
    top = d.tail(int(len(d) * 0.2)); bot = d.head(int(len(d) * 0.2))
    return stats.ks_2samp(top[outcome], bot[outcome]).statistic

M = {}
M['车队规模'] = N
M['整体出险率'] = round(fleet['出险次数'].mean(), 3)
M['全模型Gini'] = round(gini_capture(fleet, '综合评分'), 3)
M['无ADAS模型Gini'] = round(gini_capture(fleet, '无ADAS评分'), 3)
M['增量Gini'] = round(M['全模型Gini'] - M['无ADAS模型Gini'], 3)
M['GLMGini'] = round(gini_capture(fleet, 'GLM评分B'), 3)
M['规则评分Gini'] = round(gini_capture(fleet, '规则评分A'), 3)
M['Top10捕获率'] = round(capture_at_top(fleet, '综合评分', q=0.1), 3)
M['Top20捕获率'] = round(capture_at_top(fleet, '综合评分', q=0.2), 3)
M['Top10捕获率_无ADAS'] = round(capture_at_top(fleet, '无ADAS评分', q=0.1), 3)
M['评分风险Spearman'] = round(float(stats.spearmanr(fleet['综合评分'], fleet['潜在风险z'])[0]), 3)
grade_freq = fleet.groupby('风险等级', observed=True)['出险次数'].mean()   # 出险频度（次/车·年）
M['出险率单调性'] = bool((grade_freq.diff().dropna() > 0).all())
overall_freq = fleet['出险次数'].mean()
M['E级Lift'] = round(grade_freq['E'] / overall_freq, 2)
M['D级Lift'] = round(grade_freq['D'] / overall_freq, 2)
M['KS统计量'] = round(ks_stat(fleet, '综合评分'), 3)
M['样本车百公里报警'] = SEED_SAMPLE['per100km']
M['样本车报警次数'] = SEED_SAMPLE['alarms']
M['等级出险率'] = {k: round(float(v), 3) for k, v in grade_freq.items()}
M['整体出险频度'] = round(float(overall_freq), 3)
M['整体每万公里出险'] = round(float(fleet['每万公里出险'].mean()), 3)

coef = glm.params.rename('GLM系数').round(3)
pval = glm.pvalues.rename('p值').round(4)
glm_tbl = pd.concat([coef, pval], axis=1).reset_index()
glm_tbl.columns = ['因子', '系数', 'p值']
glm_tbl['因子'] = glm_tbl['因子'].replace({'const': '截距', 'log百公里报警': 'log(百公里报警频率)'})
M['GLM系数'] = glm_tbl.to_dict('records')

print('\n========== 关键指标 ==========')
for k, v in M.items():
    if k not in ('GLM系数', '等级出险率'):
        print(f'{k}: {v}')
print('\n出险频度 by 风险等级:', M['等级出险率'])
print('\nGLM系数:')
print(glm_tbl.to_string(index=False))

# ---------------- 图表 ----------------
def svg(name):
    plt.savefig(os.path.join(CHART_DIR, name), bbox_inches='tight')
    pdfname = name.replace('.svg', '.pdf')
    plt.savefig(os.path.join(CHART_DIR, pdfname), bbox_inches='tight')   # PDF矢量版供LaTeX报告
    plt.close()

# 图1 报警类型分布（真实样本车）
fig, ax = plt.subplots(figsize=(5.6, 3.0))
labels = ['车道偏离', '车距过近', 'BSD盲区', '前向碰撞', '行人碰撞']
vals = [53, 30, 28, 26, 21]
colors = [C['teal']] * 3 + [C['accent']] * 2
bars = ax.bar(labels, vals, color=colors, width=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha='center', fontsize=9)
ax.set_ylabel('报警次数'); ax.set_ylim(0, 60)
ax.set_title('真实样本车 ADAS 报警类型分布（158次/4天）', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
svg('fig01_报警类型分布.svg')

# 图2 风险分级分布
fig, ax = plt.subplots(figsize=(5.6, 3.0))
vc = fleet['风险等级'].value_counts().reindex(['A', 'B', 'C', 'D', 'E'])
bars = ax.bar(vc.index, vc.values, color=C['grade'], width=0.6)
for b, v in zip(bars, vc.values):
    ax.text(b.get_x() + b.get_width()/2, v + 2, str(v), ha='center', fontsize=9)
ax.set_ylabel('车辆数'); ax.set_ylim(0, N * 0.25 + 12)
ax.set_title('车队风险分级分布（A-E）', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
svg('fig02_风险分级分布.svg')

# 图3 出险频度单调性（次/车·年）
fig, ax = plt.subplots(figsize=(5.6, 3.0))
grp = fleet.groupby('风险等级', observed=True)['出险次数'].mean()
bars = ax.bar(grp.index, grp.values, color=C['grade'], width=0.6)
ax.axhline(overall_freq, color=C['gray'], ls='--', lw=1, label=f'整体 {overall_freq:.2f}')
for b, v in zip(bars, grp.values):
    ax.text(b.get_x() + b.get_width()/2, v + 0.008, f'{v:.2f}', ha='center', fontsize=9)
ax.set_ylabel('出险频度（次/车·年）'); ax.set_ylim(0, grp.max() * 1.22)
ax.set_title('出险频度随风险等级单调递增', fontsize=10)
ax.legend(fontsize=8); ax.spines[['top', 'right']].set_visible(False)
svg('fig03_出险率单调性.svg')

# 图4 洛伦兹捕获曲线
fig, ax = plt.subplots(figsize=(5.6, 3.4))
for col, lab, colr in [('综合评分', '全模型(含ADAS)', C['primary']),
                       ('无ADAS评分', '无ADAS(仅行为)', C['gray'])]:
    d = fleet.sort_values(col, ascending=False)
    cum = d['出险次数'].cumsum() / d['出险次数'].sum()
    x = np.arange(1, len(d) + 1) / len(d)
    ax.plot(x, cum, lw=2.2, label=f'{lab}  Gini={gini_capture(fleet, col):.3f}', color=colr)
ax.plot([0, 1], [0, 1], ':', color=C['light'], lw=1.5, label='随机')
ax.set_xlabel('车辆累计占比（按评分降序）'); ax.set_ylabel('出险次数累计占比')
ax.set_title('洛伦兹捕获曲线：ADAS因子的增量区分力', fontsize=10)
ax.legend(fontsize=8, loc='lower right'); ax.spines[['top', 'right']].set_visible(False)
svg('fig04_洛伦兹曲线.svg')

# 图5 GLM系数
fig, ax = plt.subplots(figsize=(5.6, 3.0))
ct = glm_tbl[glm_tbl['因子'] != '截距'].sort_values('系数')
ys = np.arange(len(ct))
ax.barh(ys, ct['系数'], color=[C['accent'] if v < 0 else C['primary'] for v in ct['系数']], height=0.55)
ax.set_yticks(ys); ax.set_yticklabels(ct['因子'], fontsize=9)
ax.axvline(0, color=C['gray'], lw=1)
ax.set_xlabel('Poisson GLM 标准化系数')
ax.set_title('出险频率因子系数（近失频率显著主导）', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
svg('fig05_GLM系数.svg')

# 图6 报警频率 vs 出险率
fig, ax = plt.subplots(figsize=(5.6, 3.0))
fleet['报警频段'] = pd.qcut(fleet['百公里报警频率'], 8)
b = fleet.groupby('报警频段', observed=True).agg(x=('百公里报警频率', 'mean'), y=('每万公里出险', 'mean'))
ax.plot(b['x'], b['y'], 'o-', color=C['accent'], lw=2, ms=6)
ax.set_xlabel('百公里报警频率（次/百公里）'); ax.set_ylabel('每万公里出险次数')
ax.set_title('近失事件频率是出险的先导指标', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
svg('fig06_报警频率与出险.svg')

# 图7 车型风险分布
fig, ax = plt.subplots(figsize=(6.2, 3.0))
order = ['重型货车', '中型货车', '轻型货车', '大型客车', '中型客车']
data = [fleet[fleet['车型'] == t]['综合评分'].values for t in order]
bp = ax.boxplot(data, tick_labels=order, patch_artist=True, widths=0.6)
for patch in bp['boxes']:
    patch.set_facecolor(C['light'])
ax.set_ylabel('综合评分')
ax.set_title('车型维度风险分层', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
svg('fig07_车型风险分布.svg')

# 图8 样本车定位
fig, ax = plt.subplots(figsize=(5.6, 2.6))
ax.hist(fleet['综合评分'], bins=30, color=C['light'], edgecolor='white')
sample_pct = (fleet['百公里报警频率'] < SEED_SAMPLE['per100km']).mean()
sample_score = np.quantile(fleet['综合评分'], sample_pct)
ax.axvline(sample_score, color=C['accent'], lw=2, ls='--', label=f'样本车 样本车A（评分≈{sample_score:.0f}）')
ax.set_xlabel('综合评分'); ax.set_ylabel('车辆数')
ax.set_title('真实样本车落在车队高风险尾部', fontsize=10)
ax.legend(fontsize=8); ax.spines[['top', 'right']].set_visible(False)
svg('fig08_样本车定位.svg')

fleet.to_csv(os.path.join(BASE, 'simulated_fleet.csv'), index=False, encoding='utf-8-sig')
with open(os.path.join(BASE, 'metrics.json'), 'w', encoding='utf-8') as f:
    json.dump(M, f, ensure_ascii=False, indent=2)
print('\n== 完成 ==')
