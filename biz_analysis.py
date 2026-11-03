# -*- coding: utf-8 -*-
"""第八部分支撑：商业价值量化分析（基于模拟车队）
输出：商业分析数字 + 4张图(fig09-fig12 SVG+PDF) + 数字字典JSON
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = r'C:\Users\user\Desktop\商用车UBI演示'
CHART_DIR = os.path.join(BASE, 'charts')
df = pd.read_csv(os.path.join(BASE, 'simulated_fleet.csv'))

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 110
matplotlib.rcParams['svg.fonttype'] = 'none'

C = dict(primary='#1f4e79', accent='#c00000', teal='#2e7d6b', amber='#c87d0e',
         gray='#7f7f7f', light='#dbe5ef',
         grade=['#1f9e6e', '#5bb98c', '#d6a93a', '#d97b3a', '#c0392b'])

R = {}  # 数字字典
order = ['A', 'B', 'C', 'D', 'E']

# ============ 1. 风险集中度 ============
g = df.groupby('风险等级', observed=True).agg(
    车数=('车辆ID', 'count'), 出险=('出险次数', 'sum'), 赔付=('赔付额', 'sum'))
g = g.reindex(order)
tot_claims = g['出险'].sum(); tot_loss = g['赔付'].sum()
g['车数占比'] = g['车数'] / len(df)
g['出险占比'] = g['出险'] / tot_claims
g['赔付占比'] = g['赔付'] / tot_loss
g['平均赔付额'] = g['赔付'] / g['车数']

R['总赔付'] = round(tot_loss, 0)
R['总出险次数'] = int(tot_claims)
R['E级赔付占比'] = round(g.loc['E', '赔付占比'], 3)
R['E级出险占比'] = round(g.loc['E', '出险占比'], 3)
R['DE级赔付占比'] = round(g.loc['D', '赔付占比'] + g.loc['E', '赔付占比'], 3)
R['Top20赔付占比'] = R['DE级赔付占比']  # D+E = 前40%，改口径见下
R['Top10赔付占比'] = round(df.nlargest(40, '综合评分')['赔付额'].sum() / tot_loss, 3)
R['Top10出险占比'] = round(df.nlargest(40, '综合评分')['出险次数'].sum() / tot_claims, 3)
R['E级平均赔付'] = round(g.loc['E', '平均赔付额'], 0)
R['A级平均赔付'] = round(g.loc['A', '平均赔付额'], 0)
R['集中度明细'] = {k: {'车数占比': round(g.loc[k, '车数占比'], 3),
                      '出险占比': round(g.loc[k, '出险占比'], 3),
                      '赔付占比': round(g.loc[k, '赔付占比'], 3),
                      '平均赔付': round(g.loc[k, '平均赔付额'], 0)} for k in order}

# fig09 风险集中度
fig, ax = plt.subplots(figsize=(5.6, 3.2))
x = np.arange(5); w = 0.38
b1 = ax.bar(x - w/2, g['车数占比']*100, w, label='车数占比', color=C['light'])
b2 = ax.bar(x + w/2, g['赔付占比']*100, w, label='赔付额占比', color=C['accent'])
for xi, v in zip(x - w/2, g['车数占比']*100): ax.text(xi, v+1, f'{v:.0f}%', ha='center', fontsize=8)
for xi, v in zip(x + w/2, g['赔付占比']*100): ax.text(xi, v+1, f'{v:.0f}%', ha='center', fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(order)
ax.set_ylabel('占比（%）'); ax.set_ylim(0, 55)
ax.set_title('风险集中度：E级20%车辆贡献高比例赔付', fontsize=10)
ax.legend(fontsize=8); ax.spines[['top','right']].set_visible(False)
plt.savefig(os.path.join(CHART_DIR, 'fig09_风险集中度.svg'), bbox_inches='tight')
plt.savefig(os.path.join(CHART_DIR, 'fig09_风险集中度.pdf'), bbox_inches='tight'); plt.close()

# ============ 2. 风险减量价值测算 ============
base_loss = tot_loss
# 情景：对E级干预使出险率下降20%；对D+E干预各降15%
E_claims = g.loc['E', '出险']
DE_claims = g.loc['D', '出险'] + g.loc['E', '出险']
E_share = E_claims / tot_claims
DE_share = DE_claims / tot_claims
scen1_save = base_loss * E_share * 0.20   # 仅E级降20%
scen2_save = base_loss * DE_share * 0.15  # D+E各降15%
R['E级出险份额'] = round(E_share, 3)
R['DE级出险份额'] = round(DE_share, 3)
R['情景1_仅E级降20%节约赔付'] = round(scen1_save, 0)
R['情景1_节约比例'] = round(scen1_save / base_loss, 3)
R['情景2_DE级降15%节约赔付'] = round(scen2_save, 0)
R['情景2_节约比例'] = round(scen2_save / base_loss, 3)
R['全队每车均赔'] = round(base_loss / len(df), 0)
R['E级每车均赔'] = round(g.loc['E', '平均赔付额'], 0)

# fig10 风险减量
fig, ax = plt.subplots(figsize=(5.6, 3.0))
labels = ['基线', '情景1：E级出险-20%', '情景2：D+E级-15%']
vals = [base_loss/10000, (base_loss-scen1_save)/10000, (base_loss-scen2_save)/10000]
cols = [C['gray'], C['teal'], C['primary']]
bars = ax.bar(labels, vals, color=cols, width=0.55)
for b, v in zip(bars, vals): ax.text(b.get_x()+b.get_width()/2, v+1, f'{v:.1f}万', ha='center', fontsize=9)
ax.set_ylabel('车队年赔付额（万元）'); ax.set_ylim(0, max(vals)*1.15)
ax.set_title('风险减量服务的赔付节约测算', fontsize=10)
ax.spines[['top','right']].set_visible(False)
plt.savefig(os.path.join(CHART_DIR, 'fig10_风险减量.svg'), bbox_inches='tight')
plt.savefig(os.path.join(CHART_DIR, 'fig10_风险减量.pdf'), bbox_inches='tight'); plt.close()

# ============ 3. 费率浮动的赔付率均衡 ============
P0 = base_loss / len(df)  # 统一保费（纯保费口径，收入=赔付）
rate_coef = dict(A=0.82, B=0.95, C=1.00, D=1.08, E=1.15)
g['统一赔付率'] = g['平均赔付额'] / P0
g['差异化赔付率'] = g['平均赔付额'] / (P0 * g.index.map(rate_coef))
g['差异化保费'] = P0 * g.index.map(rate_coef)
g['均衡系数'] = g['平均赔付额'] / P0   # 纯保费精算：让各等级赔付率回到100%
g['均衡赔付率'] = g['平均赔付额'] / (P0 * g['均衡系数'])
R['统一保费P0'] = round(P0, 0)
R['统一赔付率明细'] = {k: round(g.loc[k, '统一赔付率'], 2) for k in order}
R['差异化赔付率明细'] = {k: round(g.loc[k, '差异化赔付率'], 2) for k in order}
R['均衡系数明细'] = {k: round(g.loc[k, '均衡系数'], 3) for k in order}
R['E级统一赔付率'] = round(g.loc['E', '统一赔付率'], 2)
R['A级统一赔付率'] = round(g.loc['A', '统一赔付率'], 2)
R['E级差异化赔付率'] = round(g.loc['E', '差异化赔付率'], 2)
R['A级差异化赔付率'] = round(g.loc['A', '差异化赔付率'], 2)
R['E级均衡系数'] = round(g.loc['E', '均衡系数'], 3)
R['A级均衡系数'] = round(g.loc['A', '均衡系数'], 3)
R['赔付率极差_统一'] = round(g['统一赔付率'].max() - g['统一赔付率'].min(), 2)
R['赔付率极差_差异化'] = round(g['差异化赔付率'].max() - g['差异化赔付率'].min(), 2)

# fig11 赔付率均衡（三方案 × A/E 两等级）
fig, ax = plt.subplots(figsize=(5.6, 3.2))
schemes = ['统一定价', '演示映射', '精算均衡']
A_vals = [g.loc['A','统一赔付率']*100, g.loc['A','差异化赔付率']*100, g.loc['A','均衡赔付率']*100]
E_vals = [g.loc['E','统一赔付率']*100, g.loc['E','差异化赔付率']*100, g.loc['E','均衡赔付率']*100]
x = np.arange(3); w = 0.34
ax.bar(x-w/2, A_vals, w, label='A级（低风险）', color='#1f9e6e')
ax.bar(x+w/2, E_vals, w, label='E级（高风险）', color=C['accent'])
ax.axhline(100, color=C['gray'], ls='--', lw=1, label='目标赔付率100%')
for xi, v in zip(x-w/2, A_vals): ax.text(xi, v+3, f'{v:.0f}%', ha='center', fontsize=9)
for xi, v in zip(x+w/2, E_vals): ax.text(xi, v+3, f'{v:.0f}%', ha='center', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(schemes)
ax.set_ylabel('赔付率（%）'); ax.set_ylim(0, 210)
ax.set_title('费率浮动逐步修正赔付率失衡', fontsize=10)
ax.legend(fontsize=8); ax.spines[['top','right']].set_visible(False)
plt.savefig(os.path.join(CHART_DIR, 'fig11_赔付率均衡.svg'), bbox_inches='tight')
plt.savefig(os.path.join(CHART_DIR, 'fig11_赔付率均衡.pdf'), bbox_inches='tight'); plt.close()

# ============ 4. 车型结构 ============
gv = df.groupby('车型', observed=True).agg(车数=('车辆ID','count'), 出险=('出险次数','sum'), 赔付=('赔付额','sum'), 均分=('综合评分','mean'))
gv = gv.sort_values('赔付', ascending=False)
gv['车数占比'] = gv['车数']/len(df); gv['赔付占比'] = gv['赔付']/tot_loss
gv['每车均赔'] = gv['赔付']/gv['车数']
R['车型明细'] = {k: {'车数占比': round(gv.loc[k,'车数占比'],3), '赔付占比': round(gv.loc[k,'赔付占比'],3), '每车均赔': round(gv.loc[k,'每车均赔'],0)} for k in gv.index}
R['货车赔付占比'] = round(gv[gv.index.str.contains('货车')]['赔付占比'].sum(), 3)
R['货车车数占比'] = round(gv[gv.index.str.contains('货车')]['车数占比'].sum(), 3)

# fig12 车型
fig, ax = plt.subplots(figsize=(6.2, 3.2))
x = np.arange(len(gv)); w = 0.38
ax.bar(x-w/2, gv['车数占比']*100, w, label='车数占比', color=C['light'])
ax.bar(x+w/2, gv['赔付占比']*100, w, label='赔付额占比', color=C['primary'])
for xi, v in zip(x-w/2, gv['车数占比']*100): ax.text(xi, v+0.8, f'{v:.0f}%', ha='center', fontsize=8)
for xi, v in zip(x+w/2, gv['赔付占比']*100): ax.text(xi, v+0.8, f'{v:.0f}%', ha='center', fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(gv.index, fontsize=9)
ax.set_ylabel('占比（%）'); ax.set_ylim(0, 55)
ax.set_title('车型维度：货车以40%车数贡献高比例赔付', fontsize=10)
ax.legend(fontsize=8); ax.spines[['top','right']].set_visible(False)
plt.savefig(os.path.join(CHART_DIR, 'fig12_车型赔付.svg'), bbox_inches='tight')
plt.savefig(os.path.join(CHART_DIR, 'fig12_车型赔付.pdf'), bbox_inches='tight'); plt.close()

with open(os.path.join(BASE, 'biz_metrics.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

print('===== 风险集中度 =====')
print(g[['车数占比','出险占比','赔付占比','平均赔付额']].round(3).to_string())
print('\n===== 关键数字 =====')
for k in ['总赔付','总出险次数','E级赔付占比','E级出险占比','Top10赔付占比','Top10出险占比',
          'E级每车均赔','全队每车均赔','统一保费P0','E级统一赔付率','A级统一赔付率',
          'E级差异化赔付率','A级差异化赔付率','赔付率极差_统一','赔付率极差_差异化',
          '情景1_仅E级降20%节约赔付','情景1_节约比例','情景2_DE级降15%节约赔付','情景2_节约比例',
          '货车赔付占比','货车车数占比']:
    print(f'{k}: {R[k]}')
print('\n===== 车型明细 =====')
print(gv[['车数占比','赔付占比','每车均赔','均分']].round(2).to_string())
print('\n完成，biz_metrics.json 已保存')
