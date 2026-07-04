#!/usr/bin/env python3
"""Generate customer-facing Demo flow confirmation Word document."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "ARIA 智能应用平台-报价助手-Demo流程确认说明.docx"
ALT_OUT = Path(r"e:\AI文档项目\ARIA 智能报价辅助系统Demo 流程确认说明.docx")
ALT_OUT_V2 = Path(r"e:\AI文档项目\ARIA 智能应用平台-报价助手-Demo流程确认说明.docx")


def _set_run_font(run, size_pt: int = 10.5, bold: bool = False) -> None:
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size_pt)
    run.bold = bold


def _add_para(doc: Document, text: str, *, bold: bool = False, space_after: int = 6) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    _set_run_font(run, bold=bold)
    p.paragraph_format.space_after = Pt(space_after)


def _add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        _set_run_font(run)


def _add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
        for p in table.rows[0].cells[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            table.rows[ri + 1].cells[ci].text = val
    doc.add_paragraph()


def build_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("ARIA 智能应用平台 · 报价助手\nDemo 流程确认说明")
    _set_run_font(run, 16, bold=True)

    doc.add_paragraph()
    _add_para(
        doc,
        f"文档版本：v1.1\n日期：{date.today().strftime('%Y 年 %m 月 %d 日')}\n"
        "适用对象：EDAG 报价工程师、业务负责人、IT\n"
        "文档用途：供贵司远程体验 Demo 环境，确认 ARIA 平台与报价助手 "
        "工作流程、界面设计及平台扩展路径是否符合业务习惯",
    )

    doc.add_heading("1. 文档说明", level=1)
    _add_para(
        doc,
        "本文档说明 ARIA（Assisted Reasoning & Intelligence Applications，智能应用平台）"
        "当前 Demo 环境中 **报价助手** 应用的设计目标、操作路径与能力边界。",
    )
    _add_para(doc, "ARIA 是部署在贵司内网的 AI 智能应用平台，统一提供知识库、本地大模型与检索能力。"
             "本次 Demo 仅交付 **报价助手** 应用；知识库页面展示 **平台级共享能力**。")
    _add_para(doc, "贵司可通过远程访问该环境，逐步体验从 RFQ 上传到人力报价 Excel 导出的完整流程，重点确认：")
    _add_bullets(
        doc,
        [
            "五步流程的顺序是否合理",
            "各步骤页面结构与信息字段是否符合贵司习惯",
            "人工审阅、编辑、确认等环节是否满足内控要求",
            "平台定位与知识库扩展路径是否清晰可理解",
        ],
    )
    _add_para(
        doc,
        "说明：本 Demo 远程环境主要用于 UI、流程与平台叙事体验。"
        "RFQ 解析与历史对标采用 **演示模式**（Mock LLM / Mock RAG，秒级返回，顶栏可见 Tag），"
        "以便在普通云服务器上稳定、快速演示。"
        "技术方案与澄清问题页面展示正式版 **界面结构与交互方式**，页面标注 **「Demo 预览」**，内容为演示样例。"
        "真实 AI 能力将在贵司本地私有化环境（含 GPU 大模型与真实向量知识库）另行验证；"
        "界面与流程保持不变，仅将演示数据替换为真实 AI 结果。",
    )
    _add_para(doc, "具体的确认问题与反馈表，将另行通过 Excel 提供。")

    doc.add_heading("2. 系统定位", level=1)
    _add_para(
        doc,
        "ARIA 智能应用平台面向 EDAG 车辆工程服务场景，首期应用 **报价助手** 用于响应客户 RFQ（询价需求）时，"
        "辅助工程师完成：",
    )
    _add_table(
        doc,
        ["输出", "说明"],
        [
            ["历史技术对标", "检索相似历史项目，输出结构化对比矩阵"],
            ["技术方案草案", "按 Function 组织的技术方案初稿（Demo 为界面预览）"],
            ["澄清问题清单", "待与客户确认的技术问题列表（Demo 为界面预览）"],
            ["人力报价 Excel", "符合 EDAG 模板的人力排布初稿"],
        ],
    )
    _add_para(
        doc,
        "基本原则：系统输出为 **参考草稿**（约占 50%–70%），工程师负责审阅、编辑与定稿（约占 50%–30%），"
        "对外文件质量由人工最终把控。",
    )
    _add_para(
        doc,
        "平台扩展：后续更多内部 AI 应用（如财务助手等）可在同一 ARIA 平台上挂载，"
        "复用知识库、大模型与部署基础设施，无需重复建设。",
    )

    doc.add_heading("3. 远程 Demo 环境说明", level=1)
    _add_table(
        doc,
        ["项", "说明"],
        [
            ["部署方式", "远程云服务器（如阿里云 ECS），供贵司浏览器访问"],
            ["主要用途", "远程 UI / 五步流程 / 平台叙事体验"],
            ["运行模式", "演示模式（MOCK_LLM + MOCK_RAG，无需 GPU，响应快、结果稳定）"],
            ["顶栏标识", "ARIA · 智能应用平台 + Tag「报价助手」；右侧 Mock LLM / Mock RAG"],
            ["访问地址", "（由我方提供，如 http://<ECS公网IP>/）"],
            ["推荐浏览器", "Chrome / Edge 最新版"],
        ],
    )
    _add_para(doc, "与本地能力验证环境的区别：", bold=True)
    _add_table(
        doc,
        ["环境", "LLM / RAG", "适合验证什么"],
        [
            ["远程体验环境", "Mock（演示模式）", "五步 UI、平台叙事、流程与人工审阅交互"],
            ["能力档环境（内网 GPU）", "Ollama 真实模型 + Chroma 真实检索", "RFQ 解析质量、对标相关性、Excel 真实生成"],
        ],
    )
    _add_para(doc, "演示用 RFQ 样例（建议上传体验）：", bold=True)
    _add_table(
        doc,
        ["样例", "路径", "说明"],
        [
            ["Chassis 基础场景", "samples/rfq/mock_chassis_rfq.docx", "覆盖 PM、Chassis，适合走通完整流程"],
            [
                "多 Function 场景",
                "samples/rfq/demo_multifunction_rfq.docx",
                "含 BIW、EE 等模块，可体验「工程领域缺少历史参考」提示",
            ],
        ],
    )

    doc.add_heading("4. 界面结构与五步工作流程", level=1)
    _add_para(
        doc,
        "系统采用 **「一条 RFQ 任务贯穿全流程」** 的设计：上传 RFQ 后创建一条分析任务；"
        "后续各业务页面顶部均显示 **「当前报价任务」** 与 **五步进度条**，可在步骤间自由切换，不丢失上下文。",
    )
    _add_para(doc, "侧栏分组：", bold=True)
    _add_bullets(
        doc,
        [
            "**应用 · 报价流程**：RFQ 分析 → 方案草案 → QA 清单 → 人力报价",
            "**平台 · 知识库**：平台共享能力（管理员入库、索引与检索验证）",
        ],
    )
    _add_para(doc, "流程概览：")
    _add_para(doc, "① RFQ 分析 / 历史对标  →  ② 技术方案  →  ③ 澄清问题  →  ④ 人力报价")
    _add_para(doc, "                              ↑")
    _add_para(doc, "                        平台 · 知识库（共享检索底座）")

    doc.add_heading("4.1 第一步：RFQ 分析 + 历史对标", level=2)
    _add_para(doc, "页面：RFQ 分析", bold=True)
    _add_para(doc, "主要操作：")
    _add_bullets(
        doc,
        [
            "上传客户 RFQ 文件（Demo 支持 Word .docx 格式）",
            "等待系统解析（远程演示模式通常数秒完成；GPU 环境约 1–3 分钟）",
            "查看解析结果：Function 工作模块、交付物清单、里程碑及特殊要求",
            "查看 **技术维度对比表**：系统匹配 3–5 个相似历史项目，展示平台类型、车身材料、"
            "仿真类型、交付物数量、历史人天等维度，并标注相似度、置信度与来源引用",
            "可展开相似项目行，查看检索命中片段与 **来源文档（source_doc）**",
            "若部分 Function 无足够历史参考，页面显示 **「工程领域缺少历史参考」** 警告（如 BIW、EE）",
            "相似项目表下方可 **「用相同关键词验证」** 跳转平台知识库，证明与 RFQ 对标共用同一检索引擎",
            "工程师可 **编辑对比表、保存修订、勾选确认** 后，进入下一步",
        ],
    )
    _add_para(
        doc,
        "Function 领域（与 EDAG Excel 模板一致）："
        "PM、BIW、Interior、GI、Chassis、CAE、EE、PS、Test validation",
    )
    _add_para(doc, "置信度说明：高 / 中 / 低；低置信度及「无历史参考」项须重点人工核对。")

    doc.add_heading("4.2 第二步：技术方案草案", level=2)
    _add_para(doc, "页面：方案草案（五步进度条标注 **Demo 预览**）", bold=True)
    _add_bullets(
        doc,
        [
            "须已在第一步选定 RFQ 任务",
            "点击「加载 Mock 方案示例」或「生成方案草案」",
            "按 Function 查看技术模块卡片，每卡片包含：假设、输入、工作内容、交付物 四段式结构",
            "确认结构符合预期后，进入澄清问题步骤",
        ],
    )
    _add_para(
        doc,
        "Demo 说明：本步骤为 **界面与数据结构预览**，页面标注 **「Demo 预览」**，内容为演示样例，"
        "不代表正式版 AI 生成质量。正式版将基于贵司平台知识库由 AI 真实生成，并支持 PPT 模板导出。",
    )

    doc.add_heading("4.3 第三步：澄清问题清单", level=2)
    _add_para(doc, "页面：QA 清单（五步进度条标注 **Demo 预览**）", bold=True)
    _add_bullets(
        doc,
        [
            "加载并查看待澄清技术问题表格",
            "表格字段包括：序号、待澄清问题、涉及功能、影响程度、历史依据等",
            "可下载 Q_A Excel 样例，预览导出形态",
            "确认表格结构符合预期后，进入人力报价步骤",
        ],
    )
    _add_para(
        doc,
        "Demo 说明：本步骤为 **界面与数据结构预览**，内容为演示样例。"
        "正式版将基于历史 Q_A 文档由 AI 生成真实澄清清单。",
    )

    doc.add_heading("4.4 第四步：人力报价", level=2)
    _add_para(doc, "页面：人力报价", bold=True)
    _add_bullets(
        doc,
        [
            "确认当前 RFQ 任务与项目信息",
            "勾选 **「已人工审阅，确认导出」**",
            "点击 **「生成 Excel 报价初稿」**",
            "下载 .xlsx 文件，在 Excel 中进一步调整定稿",
            "页面另有人天构成明细预览表（标注 Demo 预览），展示「交付物 → 贡献人天」的信息形态",
        ],
    )
    _add_para(
        doc,
        "Demo 说明：Excel 文件可真实生成并下载；Demo 阶段自动填充 **PM** 与 **Chassis** 两个 Function Sheet。"
        "远程体验环境可能采用 Mock 规则填充；GPU 能力档为真实逻辑。"
        "人天构成明细为预览展示，正式版将提供全部 9 个 Function Sheet 及交付物级人天基线。",
    )

    doc.add_heading("4.5 平台 · 知识库（管理员后台）", level=2)
    _add_para(doc, "页面：知识库（侧栏 **平台 · 知识库**；页顶 Tag **平台能力**）", bold=True)
    _add_para(
        doc,
        "定位：ARIA **平台共享检索底座**，管理历史项目 RFQ、方案、报价等工程资料，"
        "供报价助手及未来应用消费；不是报价助手私有文件夹。",
    )
    _add_para(doc, "主要功能（Demo）：")
    _add_bullets(
        doc,
        [
            "**平台说明**（可折叠）：消费方关系（报价助手当前 Demo / 更多应用平台扩展）+ 报价消费路径表",
            "**入库与验证向导** 四步：准备项目资料 → 更新索引 → 查看清单 → 检索验证",
            "**资料概览**：文档数、可检索片段数、项目数、Function 覆盖、最近索引时间",
            "**文档清单**：路径、类型、大小、状态（已索引 / 待索引 / 失败）",
            "**检索实验室**：关键词 + 工程领域 / 文档类型筛选，查看命中片段与来源",
            "**更新知识库索引**：扫描 knowledge_base 目录并写入向量库",
        ],
    )
    _add_para(doc, "Demo 入库说明（当前）：", bold=True)
    _add_bullets(
        doc,
        [
            "将历史 **.docx** 放入服务器 knowledge_base/<项目名>/，点击「更新知识库索引」",
            "同一文件夹下多份 docx 视为同一项目的弱关联",
            "Excel 等格式在 Demo 清单中可能显示「失败」，属 Demo 能力边界，非正式版限制",
        ],
    )
    _add_para(doc, "Phase 2 规划（正式版知识库运营化）：", bold=True)
    _add_bullets(
        doc,
        [
            "**Engagement 项目包**：通过 manifest.json 关联 RFQ、QA 清单（Excel）、人力报价（Excel）、方案等多份文件",
            "本页 **Web 上传整套项目资料**",
            "报价任务完成后 **归档回知识库**",
            "原子模块目录、Re-index 运维界面等",
        ],
    )
    _add_para(
        doc,
        "与 RFQ 对标的关系：RFQ 页相似项目检索与知识库检索实验室共用 **同一 RAG 检索引擎**；"
        "Demo 远程环境为 Mock 固定样例，GPU 环境为真实向量检索。",
    )

    doc.add_heading("5. 人机协同设计", level=1)
    _add_para(doc, "系统在以下环节强调 **人工介入与确认**：")
    _add_table(
        doc,
        ["环节", "设计"],
        [
            ["对标结果", "可编辑对比表，保存修订后勾选确认"],
            ["方案与 QA", "当前 Demo 为结构预览；导出/定稿前的审阅方式（系统内编辑 vs 下载后编辑）待与贵司确认"],
            ["低置信度 / 无历史参考", "界面重点标注，提示人工核对或补充知识库资料"],
            ["Excel 导出", "导出前须勾选「已人工审阅，确认导出」"],
            ["任务切换", "各页顶栏可切换历史 RFQ 任务，便于多人或多项目并行体验"],
        ],
    )

    doc.add_heading("6. Demo 与后续正式版能力边界", level=1)
    _add_para(
        doc,
        "下表说明 **本次远程 Demo** 与 **后续本地能力验证 / 正式版** 的差异，便于贵司正确理解体验范围。",
    )
    _add_table(
        doc,
        ["能力项", "本次远程 Demo", "本地能力验证 / 正式版"],
        [
            ["五步 UI 与任务上下文", "✓ 完整可用", "✓ 完整可用"],
            ["平台品牌与侧栏 IA", "✓ ARIA 智能应用平台 + 报价助手", "✓ 一致"],
            ["RFQ 解析", "演示模式（Mock LLM）", "真实大模型解析"],
            ["历史对标 / 相似项目", "Mock 预设演示结果", "真实向量检索与对比"],
            ["Function 缺口 Alert", "✓（推荐 multifunction RFQ 样例）", "✓"],
            ["技术方案草案", "界面预览（Demo 预览样例）", "真实 AI 生成 + PPT 导出"],
            ["QA 澄清清单", "界面预览（Demo 预览样例）", "真实 AI 生成 + 正式 Excel"],
            [
                "人力 Excel 导出",
                "可下载；自动填充 PM、Chassis 两个职能 Sheet",
                "按 RFQ 范围自动填充全部 9 个职能 Sheet；交付物级人天基线",
            ],
            [
                "知识库",
                "平台说明 + 向导 + 清单 + 检索；目录放置 .docx 并触发导入",
                "Engagement 项目包（manifest 关联 RFQ/QA/报价）；Web 上传；归档回库；Excel/PDF 解析",
            ],
            ["RFQ 格式", "Word .docx", "增加 PDF 等"],
            ["其他应用（如财务助手）", "文档与平台叙事说明，无独立模块", "Phase 3 规划"],
            ["基础设施", "普通云服务器即可", "本地私有化 + GPU / 大内存 + 大模型"],
        ],
    )
    _add_para(doc, "本次 Demo 重点验证：完整五步路径是否清晰、界面与审阅流程是否符合贵司习惯、平台扩展路径是否可理解。")
    _add_para(
        doc,
        "本次 Demo 不涵盖：真实大模型解析准确率、真实历史检索相关性、方案与 QA 的 AI 生成质量，"
        "以及 PPT 正式导出、财务助手应用、全 Function 自动化、知识库 Web 上传等后续阶段能力。",
    )

    doc.add_heading("7. 建议体验路径", level=1)
    _add_para(doc, "为高效完成流程确认，建议按以下顺序体验：")
    _add_para(doc, "路径 A — 标准完整流程（约 15–20 分钟）", bold=True)
    _add_bullets(
        doc,
        [
            "指顶栏 **ARIA · 智能应用平台** 与侧栏 **应用 / 平台** 分组",
            "上传 mock_chassis_rfq.docx（Chassis 基础场景）",
            "完成 Step ①：查看解析结果与对标表，尝试编辑并确认",
            "依次浏览 Step ② 方案、Step ③ 澄清问题（关注页面结构与 Demo 预览 标识）",
            "完成 Step ④：勾选确认并下载 Excel 样例",
            "进入 **平台 · 知识库**：展开平台说明，走一遍入库向导与检索实验室",
        ],
    )
    _add_para(doc, "路径 B — 边界场景（约 5 分钟）", bold=True)
    _add_bullets(
        doc,
        [
            "上传 demo_multifunction_rfq.docx（多 Function 场景）",
            "在 Step ① 查看 BIW、EE 等模块的「缺少历史参考」提示",
            "点击「用相同关键词验证」跳转知识库，确认检索来源一致",
            "确认此类边界反馈是否符合贵司使用预期",
        ],
    )

    doc.add_heading("8. 附：一句话说明", level=1)
    _add_para(
        doc,
        "本 Demo 供贵司远程体验 **ARIA 智能应用平台** 上 **报价助手** 从 RFQ 到人力 Excel 的完整五步流程，"
        "并了解 **平台知识库** 的共享检索能力与未来项目包扩展路径。"
        "远程环境为演示模式，重点确认流程顺序、页面结构、人工审阅方式与平台定位；"
        "真实 AI 能力将在贵司本地私有化 GPU 环境验证，界面与流程保持不变。",
    )

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "本文档由 ARIA 项目组整理，与工程文档 demo-scope-brief.md / demo-rehearsal-guide.md 保持一致。"
        "如有疑问请联系项目组。"
    )
    _set_run_font(run, 9)
    run.italic = True

    return doc


def main() -> None:
    doc = build_document()
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(DEFAULT_OUT)
    print(f"Generated: {DEFAULT_OUT}")

    if ALT_OUT.parent.exists():
        doc.save(ALT_OUT)
        print(f"Generated: {ALT_OUT}")
    if ALT_OUT.parent.exists():
        doc.save(ALT_OUT_V2)
        print(f"Generated: {ALT_OUT_V2}")


if __name__ == "__main__":
    main()
