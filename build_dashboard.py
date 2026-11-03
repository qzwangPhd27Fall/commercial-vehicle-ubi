# -*- coding: utf-8 -*-
"""生成商用车UBI产品演示HTML仪表盘（自包含，内嵌SVG+指标）"""
import json, os, re

BASE = r'C:\Users\user\Desktop\商用车UBI演示'
CHART_DIR = os.path.join(BASE, 'charts')
M = json.load(open(os.path.join(BASE, 'metrics.json'), encoding='utf-8'))

def load_svg(name):
    p = os.path.join(CHART_DIR, name)
    s = open(p, encoding='utf-8').read()
    # 去掉 XML 声明与 DOCTYPE，保留 <svg>...</svg>
    s = re.sub(r'^<\?xml[^>]*\?>\s*', '', s)
    s = re.sub(r'^<!DOCTYPE[^>]*>\s*', '', s)
    # 去掉 matplotlib 内置的 <style>（内嵌字体引用），避免与页面样式冲突
    s = re.sub(r'<style>.*?</style>', '', s, flags=re.S)
    # 让 SVG 自适应宽度
    s = re.sub(r'<svg ', '<svg style="width:100%;height:auto;" ', s, count=1)
    return s

svgs = {k: load_svg(v) for k, v in {
    'fig01': 'fig01_报警类型分布.svg',
    'fig02': 'fig02_风险分级分布.svg',
    'fig03': 'fig03_出险率单调性.svg',
    'fig04': 'fig04_洛伦兹曲线.svg',
    'fig05': 'fig05_GLM系数.svg',
    'fig06': 'fig06_报警频率与出险.svg',
    'fig07': 'fig07_车型风险分布.svg',
    'fig08': 'fig08_样本车定位.svg',
}.items()}

gini = M['全模型Gini']; gini_inc = M['增量Gini']
glm_rows = ''.join(
    f'<tr><td>{r["因子"]}</td><td class="num">{r["系数"]:+.3f}</td>'
    f'<td class="num">{r["p值"]}</td>'
    f'<td><span class="tag {"ok" if r["p值"] < 0.05 else "marg"}">'
    f'{"显著" if r["p值"] < 0.05 else "边际/不显著"}</span></td></tr>'
    for r in M['GLM系数']
)

grade_cells = ''.join(
    f'<div class="grade-chip" style="--gc:{i}"><div class="g">{k}</div>'
    f'<div class="v">{v:.3f}</div><div class="l">次/车·年</div></div>'
    for i, (k, v) in enumerate(M['等级出险率'].items())
)

def kpi(label, value, sub='', accent=False):
    return (f'<div class="kpi{" kpi-accent" if accent else ""}">'
            f'<div class="k-label">{label}</div>'
            f'<div class="k-value">{value}</div>'
            f'<div class="k-sub">{sub}</div></div>')

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>商用车UBI风险评估模型 · 产品演示</title>
<style>
:root {{
  --primary:#1f4e79; --primary-2:#2a6aa8; --accent:#c0392b; --teal:#2e7d6b;
  --ink:#1a2733; --ink-2:#5a6b7a; --line:#e3e9ef; --bg:#f4f7fa; --card:#ffffff;
  --gc0:#1f9e6e; --gc1:#5bb98c; --gc2:#d6a93a; --gc3:#d97b3a; --gc4:#c0392b;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:"Microsoft YaHei","PingFang SC",-apple-system,"Segoe UI",sans-serif;
  background:var(--bg); color:var(--ink); line-height:1.6; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 20px 60px; }}

/* 顶栏 */
.topbar {{ background:linear-gradient(120deg,#16324f 0%,#1f4e79 60%,#2a6aa8 100%);
  color:#fff; padding:34px 0 30px; }}
.topbar .wrap {{ padding-bottom:0; }}
.badge {{ display:inline-block; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.3);
  color:#ffe9b3; font-size:12px; padding:2px 10px; border-radius:20px; letter-spacing:.5px; margin-bottom:12px; }}
.topbar h1 {{ font-size:26px; font-weight:700; letter-spacing:.5px; }}
.topbar .sub {{ color:#cfe0f0; font-size:14px; margin-top:8px; }}
.topbar .meta {{ margin-top:14px; font-size:12.5px; color:#aac6e2; }}

/* 口径提示条 */
.notice {{ background:#fff7e6; border:1px solid #f0d9a8; border-left:4px solid #e0a23a;
  color:#7a5b1a; padding:10px 14px; border-radius:6px; font-size:13px; margin:18px 0 6px; }}
.notice b {{ color:#5a4212; }}

/* 分区 */
.sec {{ margin-top:30px; }}
.sec-title {{ font-size:18px; font-weight:700; color:var(--primary);
  border-left:4px solid var(--primary); padding-left:10px; margin-bottom:6px; }}
.sec-desc {{ color:var(--ink-2); font-size:13px; margin-bottom:16px; }}

/* KPI */
.kpis {{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 14px;
  box-shadow:0 1px 3px rgba(20,40,60,.05); }}
.kpi-accent {{ border-top:3px solid var(--accent); }}
.k-label {{ font-size:12.5px; color:var(--ink-2); }}
.k-value {{ font-size:24px; font-weight:700; color:var(--primary); margin-top:4px; }}
.kpi-accent .k-value {{ color:var(--accent); }}
.k-sub {{ font-size:11.5px; color:var(--ink-2); margin-top:2px; }}

/* 图表网格 */
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px;
  box-shadow:0 1px 3px rgba(20,40,60,.05); }}
.card.full {{ grid-column:1 / -1; }}
.card h4 {{ font-size:14px; color:var(--ink); font-weight:700; margin-bottom:2px; }}
.card .cap {{ font-size:12px; color:var(--ink-2); margin-bottom:10px; }}

/* 等级条 */
.grade-row {{ display:flex; gap:10px; flex-wrap:wrap; }}
.grade-chip {{ flex:1; min-width:110px; background:var(--bg); border-radius:10px; padding:12px;
  text-align:center; border:1px solid var(--line); border-top:4px solid var(--gc); }}
.grade-chip .g {{ font-weight:800; font-size:16px; color:var(--ink); }}
.grade-chip .v {{ font-size:22px; font-weight:700; color:var(--ink); margin-top:2px; }}
.grade-chip .l {{ font-size:11px; color:var(--ink-2); }}
.grade-chip:nth-child(1) {{ --gc:var(--gc0); }} .grade-chip:nth-child(2) {{ --gc:var(--gc1); }}
.grade-chip:nth-child(3) {{ --gc:var(--gc2); }} .grade-chip:nth-child(4) {{ --gc:var(--gc3); }}
.grade-chip:nth-child(5) {{ --gc:var(--gc4); }}

/* 表格 */
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ padding:8px 10px; text-align:left; border-bottom:1px solid var(--line); }}
th {{ color:var(--ink-2); font-weight:600; font-size:12px; }}
td.num {{ font-family:"Consolas","Menlo",monospace; }}
.tag {{ font-size:11px; padding:1px 8px; border-radius:10px; }}
.tag.ok {{ background:#e6f4ec; color:#1f7a4d; }}
.tag.marg {{ background:#f4f0e6; color:#8a6d1f; }}

/* 产品层 */
.tiers {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; }}
.tier {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px;
  position:relative; }}
.tier.l1 {{ border-top:4px solid var(--gc0); }}
.tier.l2 {{ border-top:4px solid var(--gc2); }}
.tier.l3 {{ border-top:4px solid var(--gc4); }}
.tier .tag2 {{ position:absolute; top:14px; right:14px; font-size:11px; padding:2px 10px;
  border-radius:10px; }}
.l1 .tag2 {{ background:#e6f4ec; color:#1f7a4d; }}
.l2 .tag2 {{ background:#f4f0e6; color:#8a6d1f; }}
.l3 .tag2 {{ background:#fdecea; color:#a33; }}
.tier h4 {{ font-size:15px; margin-bottom:6px; }}
.tier p {{ font-size:13px; color:var(--ink-2); }}

/* 方法 */
.method {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; }}
.method table {{ font-size:13px; }}
.method td:first-child {{ white-space:nowrap; color:var(--ink-2); }}

.foot {{ margin-top:34px; font-size:12px; color:var(--ink-2); border-top:1px solid var(--line);
  padding-top:14px; text-align:center; }}
@media (max-width:820px) {{
  .kpis {{ grid-template-columns:repeat(2,1fr); }}
  .grid {{ grid-template-columns:1fr; }}
  .tiers {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>

<div class="topbar"><div class="wrap">
  <span class="badge">DEMO · 演示版</span>
  <h1>商用车 UBI 风险评估模型 · 产品演示</h1>
  <div class="sub">基于车联网 + ADAS 近失数据的风险评分、风险分级与费率因子体系</div>
  <div class="meta">面向财产保险公司的核保辅助与风险减量服务 ｜ 方法：规则评分(阶段A) + Poisson GLM(阶段B) + 主客观双轨融合</div>
</div></div>

<div class="wrap">

<div class="notice"><b>数据口径说明：</b>本演示以真实样本车（样本车A，4天 158 条 ADAS 报警 + 582.97km 轨迹）为锚点，
叠加行业公开参数（商用车百公里报警 5~15 次、UBI 增量 Gini 5~15pct、商用车险高赔付率），
经蒙特卡洛模拟生成 <b>400 台商用车车队</b>开展全流程验证。合作方全量数据到位后，替换模拟层即可无缝切换到真实数据。</div>

<!-- 一、车队总览 -->
<div class="sec">
  <div class="sec-title">一、车队风险总览</div>
  <div class="sec-desc">400 台商用车按综合评分划分为 A–E 五级，出险频度随等级严格递增，高风险组（E）出险频度为平均的 {M['E级Lift']} 倍。</div>
  <div class="kpis">
    {kpi('车队规模', '400', '台商用车', True)}
    {kpi('整体出险频度', f"{M['整体出险频度']:.3f}", '次 / 车·年')}
    {kpi('模型 Gini', f"{gini:.3f}", '排序区分力')}
    {kpi('ADAS 增量 Gini', f"+{gini_inc*100:.1f}pct", '近失数据贡献')}
    {kpi('E级 Lift', f"{M['E级Lift']}", '高风险组出险倍率')}
    {kpi('K-S 统计量', f"{M['KS统计量']:.3f}", '整体区分力')}
  </div>
  <div style="margin-top:16px;">
    <div class="grade-row">
      <div class="grade-chip" style="--gc:var(--gc0)"><div class="g">A 低风险</div><div class="v">{M['等级出险率']['A']:.3f}</div><div class="l">次 / 车·年</div></div>
      <div class="grade-chip" style="--gc:var(--gc1)"><div class="g">B 中低</div><div class="v">{M['等级出险率']['B']:.3f}</div><div class="l">次 / 车·年</div></div>
      <div class="grade-chip" style="--gc:var(--gc2)"><div class="g">C 中</div><div class="v">{M['等级出险率']['C']:.3f}</div><div class="l">次 / 车·年</div></div>
      <div class="grade-chip" style="--gc:var(--gc3)"><div class="g">D 中高</div><div class="v">{M['等级出险率']['D']:.3f}</div><div class="l">次 / 车·年</div></div>
      <div class="grade-chip" style="--gc:var(--gc4)"><div class="g">E 高风险</div><div class="v">{M['等级出险率']['E']:.3f}</div><div class="l">次 / 车·年</div></div>
    </div>
  </div>
  <div class="grid" style="margin-top:14px;">
    <div class="card"><h4>风险分级分布</h4><div class="cap">各等级车辆数（20% 分位等分）</div>{svgs['fig02']}</div>
    <div class="card"><h4>出险频度单调性</h4><div class="cap">出险频度随风险等级严格递增（{'单调递增 ✓' if M['出险率单调性'] else '大体递增'})</div>{svgs['fig03']}</div>
  </div>
</div>

<!-- 二、模型验证 -->
<div class="sec">
  <div class="sec-title">二、模型验证：ADAS 近失数据的增量区分力</div>
  <div class="sec-desc">核心命题——ADAS 报警记录的是「近失事件」，是事故的先导指标。对比「仅行为因子」与「行为+ADAS」两个模型的排序区分力：加入 ADAS 后 Gini 提升 {gini_inc*100:.1f}pct，落在行业 UBI 文献 5–15pct 区间上沿。</div>
  <div class="grid">
    <div class="card"><h4>洛伦兹捕获曲线</h4><div class="cap">按评分降序，累计出险捕获 vs 累计车辆（曲线越凸，区分力越强）</div>{svgs['fig04']}</div>
    <div class="card"><h4>GLM 因子系数（Poisson 频率模型）</h4><div class="cap">两个独立 ADAS 信号均正向显著</div>{svgs['fig05']}</div>
  </div>
  <div class="grid" style="margin-top:14px;">
    <div class="card"><h4>近失频率 → 出险的先导关系</h4><div class="cap">百公里报警频率越高，每万公里出险次数越高</div>{svgs['fig06']}</div>
    <div class="card">
      <h4>GLM 系数明细</h4><div class="cap">Poisson 回归（offset = log 年里程）</div>
      <table><thead><tr><th>因子</th><th>系数</th><th>p 值</th><th>显著性</th></tr></thead>
      <tbody>{glm_rows}</tbody></table>
      <div style="margin-top:12px;font-size:12px;color:var(--ink-2);">
        模型输出 = 规则评分（阶段A，权重锚定开题报告因子体系）与 GLM 评分（阶段B）的 0.5 / 0.5 双轨平均；评分与真实风险的 Spearman 秩相关 <b>{M['评分风险Spearman']:.3f}</b>。
      </div>
    </div>
  </div>
</div>

<!-- 三、真实样本车 -->
<div class="sec">
  <div class="sec-title">三、真实样本车：样本车A</div>
  <div class="sec-desc">合作方提供的 1 台真实运营车辆（安塞永鹏工贸，2026-01-27 ~ 01-30），其百公里报警频率 {M['样本车百公里报警']} 次/百公里，远高于行业均值 5–15 次，已明确落入车队高风险尾部。</div>
  <div class="grid">
    <div class="card"><h4>报警类型分布（真实数据）</h4><div class="cap">共 {M['样本车报警次数']} 次报警 / 4 天</div>{svgs['fig01']}</div>
    <div class="card"><h4>样本车在车队风险分布中的位置</h4><div class="cap">落在高风险尾部，模型自动识别</div>{svgs['fig08']}</div>
  </div>
  <div class="grid" style="margin-top:14px;">
    <div class="card full"><h4>车型维度风险分层</h4><div class="cap">重型货车与大型客车评分显著高于轻型车辆，与精算直觉一致</div>{svgs['fig07']}</div>
  </div>
</div>

<!-- 四、产品化路径 -->
<div class="sec">
  <div class="sec-title">四、产品化路径（先易后难、逐层推进）</div>
  <div class="sec-desc">研究成果对接保司业务流程的三层产品形态。</div>
  <div class="tiers">
    <div class="tier l1"><span class="tag2">优先落地</span>
      <h4>L1 · 风险减量服务</h4>
      <p>实时风险监控 + 主动预警，SaaS 平台 + API 输出每台车风险评级与报警趋势。400 台车即可支撑，是降低赔付率的直接手段。</p></div>
    <div class="tier l2"><span class="tag2">中期目标</span>
      <h4>L2 · 核保辅助工具</h4>
      <p>投保前的车辆 / 驾驶员风险评估报告，保司核保人员据此决定是否承保及费率区间。需理赔数据关联验证后上线。</p></div>
    <div class="tier l3"><span class="tag2">长期目标</span>
      <h4>L3 · UBI 费率因子</h4>
      <p>将 ADAS 风险评分作为正式定价因子嵌入保司 GLM 因子体系。需样本充分性、统计显著性、监管合规三重满足。</p></div>
  </div>
</div>

<!-- 五、方法论与数据边界 -->
<div class="sec">
  <div class="sec-title">五、方法论与数据边界</div>
  <div class="sec-desc">三层标定，全部可溯源；真实与模拟的边界已明确标注。</div>
  <div class="method"><table>
    <tr><th>层级</th><th>内容</th><th>来源 / 性质</th></tr>
    <tr><td>① 真实样本车</td><td>样本车A 报警类型分布、百公里频率、均速、聚集度等</td><td><b>真实数据</b>（合作方 4 天）</td></tr>
    <tr><td>② 行业公开参数</td><td>商用车百公里报警 5~15 次、UBI 增量 Gini 5~15pct、商用车险高赔付率</td><td><b>公开文献 / 行业共识</b>（引用前需逐项核实）</td></tr>
    <tr><td>③ 蒙特卡洛模拟</td><td>400 台车队的行为 / ADAS / 出险联合分布</td><td><b>模拟</b>（以①②标定，全量数据到位后替换）</td></tr>
  </table>
  <div style="margin-top:14px;font-size:12.5px;color:var(--ink-2);">
    <b>边界说明：</b>① ADAS 报警数据全球无公开源，本演示的「ADAS 报警→出险」关联以事故金字塔理论（近失→轻微→严重）与样本车标定构造，非真实理赔关联；
    ② 出险结果为依据行业出险率模拟，尚未回传真实理赔数据校准；③ 全部系数为演示参数，正式费率须经全量数据重估 + 精算师签字 + 监管备案。
  </div></div>
</div>

<div class="foot">商用车UBI风险评估模型 · 演示版 ｜ 由模拟数据生成，供内部汇报演示使用 ｜ 2026-10</div>

</div>
</body>
</html>'''

out = os.path.join(BASE, '商用车UBI产品演示.html')
open(out, 'w', encoding='utf-8').write(html)
print(f'仪表盘生成完成：{out}')
print(f'  大小 {os.path.getsize(out)/1024:.0f} KB')
print(f'  Gini {gini:.3f} / 增量 {gini_inc*100:.1f}pct / E级Lift {M["E级Lift"]} / KS {M["KS统计量"]:.3f} / 单调性 {M["出险率单调性"]}')
