# R1 知识库切块方案 — 验证 Review

**生成日期：** 2026-07-04  
**语料目录：** `E:\AI文档项目\RE_ 报价AI需求沟通`  
**机器可读报告：** `backend/data/validation_reports/engagement_preview.json`

> 本文供 **人工 Review**；由 `scripts/generate_validation_review.py` 从预览 JSON 自动生成。

---

## 1. 结论（Executive Summary）

**切块方案在客户签收模板上可行。**

| 指标 | Demo 现状 | 本次验证（R1 目标） |
|------|-----------|---------------------|
| RFQ 切块 | 1 docx = 1 chunk（截断 8000 字） | **85 chunks**（章节 + 表格感知） |
| RFQ 表格 | 不读表格 | **5573** 个 Word 单元格标记 |
| Q_A | 未 ingest | **35** 行 = 行级 chunk |
| 报价 Excel | Mock baselines | **9** 个 Function Sheet 解析到岗位行 |
| 错误 | — | **0** |

---

## 2. 语料文件

- `Q_A_模板.xlsx`
- `RFQ_模板.doc`
- `Technical Proposal_template.pdf`
- `Technical Proposal_template.pptx`
- `报价人力模板.xlsx`
- `Technical Proposal_template.pptx`（R1 仅 manifest 归档，不切块检索）
- `Technical Proposal_template.pdf`（R1 仅 manifest 归档，不切块检索）

---

## 3. RFQ 切块

| 项 | 值 |
|----|-----|
| 文件 | `RFQ_模板.doc` |
| 读取方式 | word-com |
| 字符数 | 39,078 |
| Chunk 总数 | 85 |
| 其中 `chapter` | 75 |
| 其中 `table` | 10 |

### 3.1 样例 Chunk（供 spot check）

#### Chunk #0 · `table` · 三、

- **字符数：** 7781 · **表格标记：** 1251

```text
三、项目要求
 3.1 项目总体要求
 3.1.1甲方委托乙方进行XXX项目整车工程设计，包含整车总布置、车身系统、底盘系统、电子电器系统、内外饰系统、结构与NVH、尺寸工程的设计开发工作，乙方需满足甲方项目开发的周期需求。
 3.1.2甲方委托乙方开发本协议规定的工作内容，乙方愿意接受甲方委托，并按甲方要求进行整车工程设计的开发工作；
3.1.3乙方须利用自己的数据库、知识和专业技术进行工作，以达到使甲方项目低投资、低生产成本和高质量的目的。
3.1.4本项目工作范围和内容见以下详细内容，甲方提供乙方所需输入资料，乙方按照本协议约定完成工作内容并输入给甲方相关交付物，乙方需对负责部分的交付物的质量负责。
3.1.5甲方输入条件及清单如下：
序号
 | 输入条件内容
 | 用途
 | 数量
 | 输入时间
 | 备注
 | 
 | 1
 | 样车相关
 | 
 | 　
 | 平台车选型及平…
```

#### Chunk #1 · `chapter` · 3.2

- **字符数：** 687 · **表格标记：** 0

```text
3.2 供应商项目管理要求
3.2.1人员要求
3.2.1.1乙方应指定一名在设计、开发和制造等方面具有丰富经验并经甲方认可的专职代表作为乙方的项目经理，同时应分别指定整车总布置、车身、底盘、电子电器、内外饰、尺寸工程、CAE的集成经理7名，集成经理在各自专业领域具有丰富的设计开发、工艺制造等方面的经验并经过甲方认可的专职代表，共同参与甲方产品开发小组会议和设计确认工作。项目经理负责汇报项目总体的关键交付物情况和节点执行状态。
3.2.1.2乙方应保证参与本项目的项目经理及技术骨干拥有整车工程开发方面8年以上的工作经验，且至少负责或参加过3个以上主机厂整车车型的整车工程开发工作，其余人员均需有整车工程开发方面3年以上的工作经验，并向甲方提供详细的工作履历得到甲方的认可。 
3.2.1.3在项目开展过程中，乙方因工作人员能力不满足项目要求，甲方可随时要求乙方更换人员。
3.2.1.4在甲方项…
```

#### Chunk #2 · `table` · 3.2.2.3

- **字符数：** 761 · **表格标记：** 42

```text
3.2.2.3 乙方应有自己的技术规范，如设计工作流程、设计规范，benchmark库等，乙方分析工作对标准的引用，需体现到设计文件中。
3.2.2.4乙方应根据甲方的实际需求提供相关工程等各方面相关的技术支持。
3.2.3开发进度
该项目初步开发计划如下：2022年1月20日-2023年8月30日，主要数据节点如下表（具体开发时间以项目实际开展时间为准,项目开始时间以甲方通知为准）  
序号
 | 数据主要节点
 | 车身/底盘/电器等
 | 外饰
 | 内饰
 | 
 | 
 | 
 | 数据发放计划时间
 | 数据发放计划时间
 | 数据发放计划时间
 | 
 | 1
 | M0数据
 | 2022.02.25
 | 2022.02.25
 | 2022.03.25
 | 
 | 2
 | EM1数据
 | 2022.03.25
 | 2022.03.25
 | 2022.04.25…
```

#### Chunk #7 · `table` · 3.2.10.4

- **字符数：** 988 · **表格标记：** 16

```text
3.2.10.4 乙方向甲方交付完毕应当交付的技术资料后，双方共同签署技术资料交付完毕证明书一式两份，乙方和甲方各持一份。
3.2.10.5乙方完成本协议所规定的有关工作后，甲方将对有关工作进行验收，验收的主要目的是为了确认乙方的有关工作能正确有效的指导协议产品的开发和生产；同时，提供的资料也是准确、完整和有效的。验收的具体标准以本协议为准。验收合格后，双方应签署验收合格报告一式两份，甲方和乙方各持一份。
3.2.10.6验收地点：双方协商。
3.2.10.7验收阶段 
根据双方约定的工作内容，对工作成果分3个阶段进行验收：
验收阶段
 | 节点名称
 | 交付物提交完成时间
 | 
 | 第一阶段
 | P2节点
 | 2022年6月30日
 | 
 | 第二阶段
 | P3节点
 | 2022年10月15日
 | 
 | 第三阶段
 | P5节点
 | 2023年5月30日
 | 
 …
```

#### Chunk #15 · `chapter` · 4.1.2.2

- **字符数：** 54 · **表格标记：** 0

```text
4.1.2.2 制定系统内部定位策略，并组织跨专业校核、评审，按甲方需求提供相应的计算或分析文件及签字报告；
```

#### Chunk #27 · `chapter` · 4.1.3

- **字符数：** 12 · **表格标记：** 0

```text
4.1.3 底盘系统开发
```

#### Chunk #39 · `chapter` · 4.1.6.3

- **字符数：** 29 · **表格标记：** 0

```text
4.1.6.3 结构耐久、NVH仿真分析目标值及竞品车数据
```

#### Chunk #51 · `chapter` · 4.1.7.6

- **字符数：** 25 · **表格标记：** 0

```text
4.1.7.6 产品结构尺寸工程分析及ECR管理。
```

#### Chunk #60 · `table` · 4.2.1

- **字符数：** 1526 · **表格标记：** 300

```text
4.2.1 整车总布置输入与输出内容见表一。工作方向必须包含但不局限于表中所列项目。
表一：整车总布置交付物清单表【R = Responsibility（负责）、A=Approval（批准）、S=Support（支持）、I= Information（被通知）、C = Consult （咨询）】
序号
 | 条件
 | 交付物清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 供应商
 | 备注
 | 
 | 1
 | 1.产品定义报告2.竞品车、标杆车 3.整车配置表4.产品定义四级性能目标5.项目一级计划
 | 总体布置分析报告
 | PPT
 | P2
 | R
 | A
 | -
 | 　
 | 
 | 2
 | 
 | 舱室布置分析报告（初版）
 | PPT
 | P2
 | R
 | A
 | -
 | 　
 | 
 | 3
 | 
 | Mulecar改制…
```

#### Chunk #61 · `table` · 4.2.2

- **字符数：** 2180 · **表格标记：** 470

```text
4.2.2 车身系统输入与输出内容见表二。工作方向必须包含但不局限于表中所列项目。
表二：车身系统交付物清单表【R = Responsibility（负责）、A=Approval（批准）、S=Support（支持）、I= Information（被通知）、C = Consult （咨询）】
序号
 | 条件
 | 交付物清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 供应商
 | 备注
 | 
 | 1
 | 1. 造型效果图2.整车CAS、A面3.整车外观油泥造型4.整车内饰油泥造型5.DTS6.竞品车、标杆车 7.整车质量目标8.整车配置表
 | 标准件清单
 | EXCEL
 | P2
 | R
 | A
 | S
 | 　
 | 
 | 2
 | 
 | 专利排查报告
 | PPT
 | P2
 | R
 | A
 | -
 | 
 | 
 | 3
…
```

#### Chunk #62 · `table` · 4.2.3

- **字符数：** 1461 · **表格标记：** 290

```text
4.2.3 底盘系统输入与输出内容见表三。工作方向必须包含但不局限于表中所列项目。
表三：底盘系统交付物清单表【R = Responsibility（负责）、A=Approval（批准）、S=Support（支持）、I= Information（被通知）、C = Consult （咨询）】
序号
 | 条件
 | 交付物清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 供应商
 | 备注
 | 
 | 1
 | 1.竞品车、标杆车信息2.整车性能目标3.交付物文件模板4.项目主要节点计划
 | 标准件清单
 | EXCEL
 | P2
 | R
 | A
 | S
 | 
 | 
 | 2
 | 
 | 专利排查报告
 | PPT
 | P2
 | R
 | A
 | C
 | 
 | 
 | 3
 | 
 | 第一版制动、转向、悬架、传动系统、进气系统、排气系统、燃…
```

#### Chunk #70 · `chapter` · 4.3.3

- **字符数：** 86 · **表格标记：** 0

```text
4.3.3 GD&T图纸设计需按照甲方的技术规范制定，公差分配需首先进行尺寸链分析，总成分解到单件；
4.3.4本项目技术要求涉及的其他未尽事宜以甲方实际工作中沟通的为准。
```

---

## 4. Q_A 按行切块

- **文件：** `Q_A_模板.xlsx`
- **有效行 chunk 数：** 35
- **Area 分布：** ALL, All, BE, Change Management, Chassis, Data Management, EE, GD&T, Packaging

### 4.1 样例行

- **#1** [Packaging] Who will do the physical benchmark? Does Customer will provide the benchmark report to 我司（DTS, Vehicle dimension,Ergonom…
- **#2** [Packaging] Customer will provide the regulation list&docuemnts? 
Customer会提供法规清单和文档吗？…
- **#3** [Packaging] What is the type of door, any specialy function or requirement ?
什么类型的车门，是否有特殊的功能需求？…
- **#4** [Packaging] Who will do the Feature list/Line up, VTS, performance objectives? 谁来做车型型谱、整车配置表，性能目标？…
- **#5** [GD&T] General tolerance, parts tolerance, mounting concept will provied by Customer? Customer 会提供通用公差，单件公差，工装方案吗？…

---

## 5. 报价 Excel → manpower_baselines

- **文件：** `报价人力模板.xlsx`
- **Project information：** customer=`Customer 客户 : ` project=`Project 项目:`

| Function Sheet | 岗位行数 |
|----------------|----------|
| BIW | 34 |
| CAE | 15 |
| Chassis | 12 |
| EE | 10 |
| GI | 21 |
| Interior | 19 |
| PM | 5 |
| PS | 4 |
| Test validation | 4 |

> 模板为空字段处为占位标签；真实 Engagement 入库后应能读到客户/项目名与人天数字。

---

## 6. Review 检查清单（请你勾选）

- [ ] RFQ 章节边界合理（`chunk_chapter` 与目录/编号一致）
- [ ] 含表格的 chunk 保留了表格结构（`| ` 分隔或单元格内容可读）
- [ ] 无「整篇 RFQ 只有 1 个 chunk」的退化
- [ ] Q_A 行数与 Excel 有效 Question 行一致
- [ ] Q_A 8 列 metadata 字段齐全（No/Area/Question/…）
- [ ] 报价各 Function Sheet 岗位行可被抽取（PM/Chassis/…）
- [ ] PPT/PDF 仅归档、不参与 R1 向量检索 — 符合预期

---

## 7. 已知限制与下一步

| 限制 | 计划 |
|------|------|
| RFQ 为 `.doc`（非 `.docx`） | R1 上传仍以 docx 为主；验证期 Windows Word COM；生产可 IT 批量转换 |
| 章节切分为规则/heuristic | 可对照 golden 样本加回归断言 |
| 尚未写入 pgvector（RFQ/Q_A） | R1-K + I05–I07；本阶段验证切块质量 |
| 尚未写入 `manpower_baselines.json` | R1-K04/K05；Debug 仅 `kb_debug_preview.json` |
| 报价解析：Expense 行混入、每 Sheet 预览截断 20 行 | R1-K04a 加固 |
| 模板 Excel 无真实项目数字 | 客户脱敏 **填好数** Engagement（O-02）到位后复跑 |
| `/quote` 仍用 Mock baselines | M3 前接 Layer 1 JSON；见 [manpower-baselines-spec.md §4](../supplementary/manpower-baselines-spec.md) |

**复现命令：**

```powershell
cd e:\work\aria
$env:PYTHONPATH = "e:\work\aria\backend"
python scripts/preview_engagement_ingest.py
python scripts/generate_validation_review.py
```
