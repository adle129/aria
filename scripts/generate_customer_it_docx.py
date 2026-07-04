#!/usr/bin/env python3
"""Generate customer-facing IT infrastructure Word document (production)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.table import Table

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
DEFAULT_OUT = ROOT / "docs" / "ARIA 智能应用平台-生产环境-大模型与IT基础设施说明.docx"
ALT_OUT = Path(r"e:\AI文档项目\ARIA 智能报价辅助系统-生产环境 -大模型与 IT 基础设施说明.docx")
ALT_OUT_V2 = Path(r"e:\AI文档项目\ARIA 智能应用平台-生产环境-大模型与IT基础设施说明.docx")


def _set_cell_shading(cell, fill: str) -> None:
    from docx.oxml import OxmlElement

    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)


def _set_run_font(run, size_pt: int = 10.5, bold: bool = False, color: RGBColor | None = None) -> None:
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color:
        run.font.color.rgb = color


def _add_para(doc, text: str, *, style: str = "Normal", size: int = 10.5, bold: bool = False, space_after: int = 6):
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    _set_run_font(run, size, bold)
    p.paragraph_format.space_after = Pt(space_after)
    return p


def _add_bullets(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        _set_run_font(run)


def _add_table(doc, headers: list[str], rows: list[list[str]], *, header_fill: str = "D9E2F3") -> Table:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        _set_run_font(r, 10, bold=True)
        _set_cell_shading(hdr[i], header_fill)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = ""
            r = cell.paragraphs[0].add_run(val)
            _set_run_font(r, 10)
    doc.add_paragraph()
    return table


def build_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)

    # Title block
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = t.add_run("ARIA 智能应用平台\n")
    _set_run_font(r1, 22, bold=True)
    r1b = t.add_run("（Assisted Reasoning & Intelligence Applications）\n")
    _set_run_font(r1b, 11, color=RGBColor(0x66, 0x66, 0x66))
    r2 = t.add_run("生产环境 — 大模型与 IT 基础设施说明")
    _set_run_font(r2, 16, bold=True, color=RGBColor(0x15, 0x65, 0xC0))

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    today = date.today()
    mr = meta.add_run(
        f"文档版本：v1.2\n"
        f"日期：{today.year} 年 {today.month} 月 {today.day} 日\n"
        f"适用对象：EDAG IT 管理员、基础设施采购与运维负责人\n"
        f"文档用途：单独讨论 ARIA 平台生产部署所需的服务器、大模型方案、安全边界与运维职责"
    )
    _set_run_font(mr, 10)

    doc.add_paragraph()
    note = doc.add_paragraph()
    nr = note.add_run(
        "说明：本文档描述 ARIA 智能应用平台在内网 GPU 生产环境的规划基线。"
        "当前部署包含首期应用 **报价助手** 及平台级 **知识库**（历史项目工程资料）；"
        "后续应用（如财务助手）可复用同一 /data/aria 与 Ollama 基础设施。"
        "与《ARIA 智能应用平台 · 报价助手 Demo 流程确认说明》相互独立——"
        "远程云 UI 体验环境（4C8G、Mock 模式，docker-compose.aliyun-demo.yml）"
        "不启用真实大模型，也无需独立数据盘。"
    )
    _set_run_font(nr, 10)
    note.paragraph_format.space_after = Pt(12)

    # 1
    doc.add_heading("1. 总体原则", level=1)
    _add_table(
        doc,
        ["原则", "说明"],
        [
            ["本地私有化", "大模型在贵司服务器本地运行，不调用公有云大模型 API"],
            ["数据不出内网", "RFQ、历史报价、技术方案、知识库等数据均在企业内网存储与处理"],
            ["应用与数据分离", "应用部署在系统盘（可重装）；业务数据在独立数据盘 /data（不可丢）"],
            ["模型与业务解耦", "应用通过标准 HTTP 调用本地 Ollama；升级模型一般只需调整配置"],
            ["职责清晰", "ARIA 应用由我方交付与升级；Ollama 及模型文件由贵司 IT 安装与日常维护"],
        ],
    )

    # 2 Deployment Profile
    doc.add_heading("2. 部署画像（Deployment Profile）", level=1)
    _add_table(
        doc,
        ["Profile", "用途", "独立数据盘", "说明"],
        [
            ["Experience", "远程 UI / 流程 / 平台叙事体验", "否", "4C8G Mock；docker-compose.aliyun-demo.yml"],
            ["Production", "报价助手 + 平台知识库日常运行", "必须", "docker-compose.prod.yml；/data/aria"],
        ],
    )
    _add_para(
        doc,
        "两套环境界面与五步操作流程一致（顶栏 ARIA · 智能应用平台 + 报价助手）。"
        "生产环境关闭演示模式（MOCK_LLM=false、MOCK_RAG=false），"
        "接入本地大模型与真实向量知识库。",
    )

    doc.add_heading("2.1 平台与应用（IT 视角）", level=2)
    _add_table(
        doc,
        ["层级", "生产环境内容", "说明"],
        [
            ["ARIA 平台", "知识库、Ollama、RAG、PostgreSQL、部署", "共享基础设施；数据根目录 ARIA_DATA_ROOT=/data/aria"],
            ["应用：报价助手", "RFQ 解析、对标、Excel 人力（五步 UI）", "当前正式交付范围"],
            ["应用：其他（规划）", "如财务助手", "Phase 3；复用同一平台，无需重复建库与模型"],
        ],
    )

    # 3 Architecture
    doc.add_heading("3. 生产环境架构概览", level=1)
    _add_para(doc, "生产环境采用「应用容器化 + 大模型宿主机独立部署」架构：")
    _add_bullets(
        doc,
        [
            "ARIA 前端、后端、PostgreSQL、Nginx 通过 Docker Compose 统一部署（生产使用 docker-compose.prod.yml）",
            "向量检索（ChromaDB）嵌入在后端进程内，持久化于 /data/aria/app/chroma_db，无独立 Chroma 容器",
            "Ollama 在宿主机独立运行（systemd），便于 GPU 直通及大体积模型文件管理",
            "Ollama 不对公网开放，仅监听 127.0.0.1:11434，由 ARIA 后端调用",
            "业务数据与 PostgreSQL 数据目录 bind 至独立数据盘 /data/aria",
        ],
    )

    img_path = ASSETS / "aria-production-architecture.png"
    if img_path.exists():
        doc.add_paragraph()
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cr = cap.add_run("图 1  ARIA 生产环境部署拓扑（Profile: Production）")
        _set_run_font(cr, 10, bold=True)
        pic_p = doc.add_paragraph()
        pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic_p.add_run().add_picture(str(img_path), width=Cm(16))
        foot = doc.add_paragraph()
        foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fr = foot.add_run("注：远程 UI 体验环境不使用独立数据盘，架构以体验环境说明为准。")
        _set_run_font(fr, 9, color=RGBColor(0x66, 0x66, 0x66))

    doc.add_heading("3.1 存储布局", level=2)
    _add_para(doc, "系统盘与数据盘分工如下：")
    layout = doc.add_paragraph()
    lr = layout.add_run(
        "系统盘（可重装）                    独立数据盘（挂载 /data，可整块迁移）\n"
        "/opt/aria/deploy/                   /data/aria/\n"
        "  镜像、compose、.env                 app/       → 上传、知识库、向量库、模板、输出\n"
        "                                      postgres/  → PostgreSQL 数据\n"
        "                                      backups/   → 每日备份\n"
        "                                    /data/ollama/models/  → 大模型文件"
    )
    _set_run_font(lr, 10)
    layout.paragraph_format.left_indent = Cm(0.5)

    # 4 LLM role
    doc.add_heading("4. 大模型在系统中的角色", level=1)
    _add_para(doc, "生产环境中，并非所有功能都依赖大语言模型。规划如下：")
    _add_table(
        doc,
        ["业务环节", "是否使用主大模型", "说明"],
        [
            ["RFQ 解析（职能模块、交付物、里程碑等）", "是", "核心 AI 能力；依赖 Qwen2.5 主模型"],
            ["历史项目检索 / 技术对标", "部分", "Embedding（nomic-embed-text）+ ChromaDB；RFQ 与知识库页共用 RAG 管道"],
            ["人力报价 Excel 生成", "否", "基于贵司 Excel 模板与历史人天基线，不经大模型推理"],
            ["技术方案草案（/proposal）", "Phase 2", "当前生产可预览框架；全量 RAG+LLM 为 Phase 2，复用同一 Ollama"],
            ["澄清问题 QA 清单（/qa）", "Phase 2", "当前生产可预览框架；全量生成依赖主模型（Phase 2）"],
            ["财务相关（远期应用）", "有限", "规划为平台第二应用（Phase 3）；以规则引擎为主，大模型辅助有限"],
        ],
    )
    _add_para(doc, "生产环境需部署的 AI 组件：")
    _add_table(
        doc,
        ["组件类型", "推荐选型", "用途"],
        [
            ["推理框架", "Ollama（宿主机）", "在服务器本地加载与调用模型"],
            ["主大语言模型", "Qwen2.5 系列", "RFQ 解析；Phase 2 方案/QA 文案生成"],
            ["Embedding 模型", "nomic-embed-text", "历史文档向量化与相似检索"],
        ],
    )

    # 5 Model recommendation
    doc.add_heading("5. 生产环境推荐模型方案", level=1)
    doc.add_heading("5.1 默认推荐（生产）", level=2)
    _add_table(
        doc,
        ["组件", "生产推荐", "说明"],
        [
            ["主大语言模型", "Qwen2.5 32B（量化版，如 Q4）", "长文档理解更稳、结构化 JSON 更可靠，适合日常生产"],
            ["Embedding 模型", "nomic-embed-text", "体积小，专用于知识库检索"],
            ["推理框架", "Ollama", "与 ARIA 后端通过 127.0.0.1:11434 通信"],
        ],
    )

    doc.add_heading("5.2 为何生产推荐 32B 而非 14B", level=2)
    _add_para(
        doc,
        "选型需在理解质量、输出稳定性、响应速度、显存与并发之间权衡。"
        "针对 ARIA 生产场景，推荐 32B 作为主要方案，理由如下：",
    )
    _add_table(
        doc,
        ["维度", "Qwen2.5 14B", "Qwen2.5 32B（生产推荐）"],
        [
            ["复杂 RFQ 理解", "一般可满足；长文档、多模块时偶发漏项", "对冗长、多职能 RFQ 更稳定"],
            ["结构化 JSON 输出", "多数可用；异常格式需重试", "格式更规整，利于后续对标与流程串联"],
            ["方案 / QA 长文案质量", "可用作过渡", "更适合 Phase 2 日常方案与澄清问题生成"],
            ["单次 RFQ 处理时间", "相对更快", "相对更慢，但在推荐 GPU 上仍可接受"],
            ["显存需求（约）", "~16 GB", "~20 GB（量化版）"],
            ["多用户并发", "单卡压力相对较小", "资源占用更高，需配合任务排队或硬件扩展"],
        ],
    )
    _add_para(doc, "结论（生产视角）：", bold=True)
    _add_bullets(
        doc,
        [
            "32B 更适合作为日常生产主模型：工程师每日上传 RFQ，对准确率与输出稳定性要求高于「极限速度」。",
            "14B 仅建议在显存不足 24GB、且暂时无法升级 GPU 时作为过渡；若生产抽样发现 Function 漏项多、"
            "JSON 频繁异常，应优先评估升级至 32B 或增强硬件，而非长期依赖 14B。",
        ],
    )

    doc.add_heading("5.3 什么情况下可考虑 14B", level=2)
    _add_para(doc, "仅在以下硬件或过渡约束下，可与贵司 IT 讨论短期使用 14B：")
    _add_bullets(
        doc,
        [
            "现有 GPU 显存不足 24GB，暂时无法采购新卡",
            "生产上线初期并发极低（如同时仅 1–2 人解析），且已确定短期内完成硬件升级",
        ],
    )
    _add_para(doc, "除上述情况外，生产环境默认按 32B 规划采购与部署。")

    doc.add_heading("5.4 环境变量参考（生产）", level=2)
    _add_para(doc, "我方交付的生产 .env 典型配置（由实施时写入，不含密钥）：")
    env_p = doc.add_paragraph()
    env_text = (
        "OLLAMA_BASE_URL=http://host.docker.internal:11434\n"
        "OLLAMA_MODEL=qwen2.5:32b\n"
        "EMBEDDING_MODEL=nomic-embed-text\n"
        "MOCK_LLM=false\n"
        "MOCK_RAG=false\n"
        "ARIA_DATA_ROOT=/data/aria"
    )
    er = env_p.add_run(env_text)
    _set_run_font(er, 9)
    env_p.paragraph_format.left_indent = Cm(0.5)

    # 6 Hardware
    doc.add_heading("6. 硬件配置要求（生产）", level=1)
    _add_para(
        doc,
        "真实大模型推理必须使用 GPU。远程云 UI 体验环境（无 GPU、约 8GB 内存）不能作为生产 AI 环境。",
    )
    doc.add_heading("6.1 推荐生产配置 ★", level=2)
    _add_table(
        doc,
        ["指标", "推荐值", "说明"],
        [
            ["GPU", "NVIDIA RTX 4090 24GB × 1", "可稳定运行 Qwen2.5 32B（量化版）"],
            ["CPU", "32 核级", "应用服务、数据库、文档解析与并发请求"],
            ["内存", "128 GB（建议 ECC）", "PostgreSQL、应用缓存及多用户并发"],
            ["系统盘", "1 TB NVMe SSD", "操作系统、容器镜像、/opt/aria 应用交付"],
            ["数据盘", "≥ 4 TB（建议 RAID1）", "知识库 10–500 GB 增长；含 postgres 与备份"],
            ["模型存储", "/data/ollama/models", "32B 量化约 20 GB；与业务数据同挂载点 /data"],
            ["操作系统", "Ubuntu Server 22.04 LTS", "与交付方案一致"],
            ["网络", "双千兆网口；生产建议 HTTPS", "内网访问 + VPN 远程"],
            ["UPS", "建议配置", "防止意外断电导致数据库/索引损坏"],
        ],
    )
    _add_para(doc, "预算参考（含 RTX 4090）：约 6–10 万元人民币区间，以实际采购为准。")
    _add_para(
        doc,
        "采购说明：服务器硬件通常由贵司自行采购；我方可提供配置清单、部署文档与验收配合。",
    )

    doc.add_heading("6.2 按 GPU 显存的模型适配（供采购参考）", level=2)
    _add_table(
        doc,
        ["GPU 显存", "生产主模型建议"],
        [
            ["无独显 / < 16 GB", "不满足 ARIA 生产 AI 要求"],
            ["16 GB", "可运行 14B；不建议作为长期生产方案"],
            ["24 GB（4090）★", "推荐：32B 量化版生产主模型"],
            ["40 GB 及以上（如 A100）", "32B 更宽裕；多用户并发可考虑多卡或任务队列"],
        ],
    )

    doc.add_heading("6.3 存储规划（/data 目录）", level=2)
    _add_table(
        doc,
        ["路径", "预估空间", "说明"],
        [
            ["/data/ollama/models", "20–80 GB", "Qwen2.5 32B + nomic-embed-text"],
            ["/data/aria/app/knowledge_base", "10–500 GB", "历史项目原始文档（核心资产）"],
            ["/data/aria/app/chroma_db", "5–50 GB", "向量索引，随知识库增长"],
            ["/data/aria/app/uploads", "1–10 GB", "用户上传 RFQ"],
            ["/data/aria/app/outputs", "1–10 GB", "生成的 Excel 等"],
            ["/data/aria/postgres", "1–20 GB", "PostgreSQL 数据目录"],
            ["/data/aria/backups", "按保留策略", "建议每日备份，保留不少于 30 天"],
            ["/data/aria/app/templates", "按模板数量", "报价/QA Excel 模板；首次部署自交付包复制"],
            ["/opt/aria/deploy", "< 5 GB", "镜像、compose、.env（系统盘）"],
        ],
    )

    doc.add_heading("6.4 并发与扩展", level=2)
    _add_table(
        doc,
        ["场景", "建议"],
        [
            ["约 10–15 人同时使用（生产目标）", "单台 4090 + 32B + 后端异步任务队列通常可满足"],
            ["接近 20–30 人频繁触发 RFQ 解析", "评估第二块 GPU、解析任务排队策略或分时段限流"],
            ["仅升级更大参数模型（如 72B）", "通常不是首选；优先队列 + 多卡或维持 32B"],
        ],
    )

    # 7 Network
    doc.add_heading("7. 网络、访问与安全", level=1)
    doc.add_heading("7.1 访问方式", level=2)
    _add_table(
        doc,
        ["用户", "访问路径"],
        [
            ["办公室内网", "浏览器访问内网域名（如 http://aria.company.internal）"],
            ["远程办公", "先连接贵司 VPN，再访问上述内网地址"],
            ["推荐浏览器", "Chrome / Edge 最新版"],
        ],
    )
    doc.add_heading("7.2 端口与安全策略", level=2)
    _add_table(
        doc,
        ["端口 / 服务", "对外暴露", "说明"],
        [
            ["80 / 443", "内网或 VPN 内可访问", "ARIA Web 入口（Nginx）"],
            ["22（SSH）", "建议限制来源 IP", "服务器运维"],
            ["PostgreSQL、后端 API", "禁止对公网开放", "仅 Docker 内网"],
            ["Ollama 11434", "仅 127.0.0.1", "大模型不直接暴露给终端用户"],
        ],
    )
    doc.add_heading("7.3 数据安全要求", level=2)
    _add_table(
        doc,
        ["要求", "说明"],
        [
            ["禁止公有云 API", "RFQ 及历史资料不得上传至外部大模型服务"],
            ["内网存储", "上传文件、知识库、向量索引、生成 Excel 均存于贵司服务器 /data"],
            ["凭证管理", "数据库密码等通过环境变量配置，不写入代码仓库"],
            ["HTTPS", "生产环境建议启用内网 CA 或企业证书"],
            ["日志", "避免将 RFQ 全文写入可被外部采集的日志系统"],
        ],
    )

    # 8 Performance
    doc.add_heading("8. 生产性能目标（参考）", level=1)
    _add_para(doc, "在推荐硬件（4090 + 32B）及正常网络条件下，规划目标如下：")
    _add_table(
        doc,
        ["指标", "生产目标（参考）"],
        [
            ["RFQ 解析 + 对标（端到端 P95）", "< 3 分钟"],
            ["人力 Excel 生成", "< 30 秒（不经大模型）"],
            ["并发用户", "10–15 人同时使用"],
            ["RFQ 单文件大小上限", "50 MB"],
            ["主模型 JSON 解析成功率", "≥ 95%（配合校验与重试机制）"],
        ],
    )
    _add_para(
        doc,
        "实际表现与 RFQ 篇幅、知识库规模及并发负载有关，上线后可通过抽样 RFQ 与监控指标联合验收。",
    )

    # 9 Responsibilities
    doc.add_heading("9. 职责分工", level=1)
    _add_table(
        doc,
        ["事项", "责任方", "说明"],
        [
            ["ARIA 应用交付、版本升级、部署文档", "我方", "含 Docker 镜像、配置模板、验收支持"],
            ["GPU 服务器与独立数据盘采购", "贵司", "含 UPS、散热、网络"],
            ["操作系统、NVIDIA 驱动、Docker 安装", "贵司 IT", "Ubuntu 22.04 LTS 推荐"],
            ["Ollama 安装、模型拉取与版本管理", "贵司 IT", "含 Qwen2.5 32B、nomic-embed-text"],
            ["Ollama 日常监控与重启", "贵司 IT", "如 GPU OOM、服务无响应"],
            ["历史知识库目录规范、脱敏资料提供", "贵司业务 + IT", "Demo：knowledge_base/<项目名>/ + 触发索引；Phase 2：Engagement 项目包（manifest 关联 RFQ/QA/报价）"],
            ["数据库与业务数据备份策略", "贵司 IT（我方提供脚本建议）", "含 PostgreSQL、向量库、上传目录"],
            ["内网 DNS、VPN、HTTPS 证书", "贵司 IT", ""],
            ["RFQ / 报价 / QA 内容审阅与对外定稿", "贵司报价工程师", "AI 输出为草稿"],
        ],
    )

    # 10 Ops
    doc.add_heading("10. 运维要点（IT 日常）", level=1)
    doc.add_heading("10.1 上线前检查清单", level=2)
    _add_bullets(
        doc,
        [
            "GPU 驱动正常（nvidia-smi 可见 4090）",
            "Ollama 服务已启动，模型已拉取（32B + nomic-embed-text）",
            "Ollama 仅监听 127.0.0.1:11434",
            "ARIA 健康检查接口返回模型就绪（ollama_reachable、ollama_model_ready 等为正常）",
            "docker-compose.prod.yml 一键启动成功，Web 内网可访问",
            "防火墙仅开放必要端口（80/443、受限 SSH）",
            "/data/aria 数据目录 bind 挂载正确，备份任务已配置（deploy/scripts/backup.sh）",
        ],
    )
    doc.add_heading("10.2 模型与版本更新", level=2)
    _add_bullets(
        doc,
        [
            "主模型升级（如 32B 小版本更新）一般通过 Ollama 重新拉取模型并调整配置完成，无需修改 ARIA 业务代码",
            "建议在维护窗口进行，更新后用 2–3 份脱敏 RFQ 做回归抽检",
            "Embedding 模型更新后，需按我方文档重新索引知识库",
        ],
    )
    doc.add_heading("10.3 备份与迁移", level=2)
    _add_table(
        doc,
        ["项", "说明"],
        [
            ["日备", "deploy/scripts/backup.sh → /data/aria/backups/YYYYMMDD/"],
            ["内容", "数据库 dump + knowledge_base + chroma_db + uploads 等"],
            ["保留", "建议 30 天"],
            ["换机", "停止服务 → rsync /data 至新服务器 → 重装应用 → deploy/scripts/start.sh"],
            ["RPO / RTO", "日备：RPO ≤ 24h；含上架 RTO 约 4–8h"],
        ],
    )
    doc.add_heading("10.4 常见问题排查方向", level=2)
    _add_table(
        doc,
        ["现象", "可能原因", "IT 侧排查"],
        [
            ["RFQ 长时间「解析中」", "Ollama 无响应或 GPU 显存不足", "检查 Ollama 服务、nvidia-smi 显存占用"],
            ["健康检查显示模型未就绪", "模型未拉取或名称与配置不一致", "ollama list，核对配置中的模型名"],
            ["检索无历史命中", "知识库未导入或索引未构建", "检查 knowledge_base 目录与导入任务"],
            ["磁盘增长过快", "上传文件与生成物累积", "清理策略或扩容数据盘"],
        ],
    )

    # 11 Confirmation
    doc.add_heading("11. 建议与贵司 IT 一并确认的事项", level=1)
    _add_bullets(
        doc,
        [
            "生产服务器是否按 RTX 4090 24GB + 128GB 内存推荐档采购？",
            "是否配置独立数据盘并挂载至 /data（含 /data/aria 与 /data/ollama）？",
            "主大模型是否同意采用 Qwen2.5 32B（量化版）作为生产默认？",
            "Ollama 与模型运维是否由贵司 IT 承担（当前方案按此划分）？",
            "内网访问方式：纯内网域名，或 VPN + HTTPS？",
            "预计生产期同时在线用户数（用于评估是否需双卡或排队策略）？",
            "历史知识库文档的存放路径、脱敏规范与备份责任是否已有企业标准？（Phase 2 将支持 Web 上传项目包）",
            "是否确认禁止任何公有云大模型 API（与当前安全设计一致）？",
        ],
    )

    # 12 Summary
    doc.add_heading("12. 附：一句话摘要", level=1)
    summary = doc.add_paragraph()
    sr = summary.add_run(
        "ARIA 智能应用平台生产环境在贵司内网 GPU 服务器上运行，首期应用为报价助手；"
        "通过宿主机 Ollama 本地部署 Qwen2.5 32B 与 nomic-embed-text 完成 RFQ 解析与平台知识库向量检索。"
        "业务数据保存在独立数据盘 /data/aria，应用在系统盘 /opt/aria 可重装。"
        "数据不出内网，不调用公有云 API。推荐硬件为 RTX 4090 24GB、128GB 内存；"
        "Ollama 与模型由贵司 IT 运维，ARIA 应用由我方交付与升级。"
    )
    _set_run_font(sr, 10.5, bold=True)

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer_p.add_run(
        "\n\n本文档由 ARIA 项目组整理，与 customer-it-infrastructure.md / deployment-guide.md 保持一致。\n— 文档结束 —"
    )
    _set_run_font(fr, 9, color=RGBColor(0x99, 0x99, 0x99))

    return doc


def main() -> int:
    out_paths = [DEFAULT_OUT]
    if len(sys.argv) > 1:
        out_paths = [Path(p) for p in sys.argv[1:]]
    else:
        if ALT_OUT.parent.exists():
            out_paths.append(ALT_OUT)
        if ALT_OUT_V2.parent.exists():
            out_paths.append(ALT_OUT_V2)

    doc = build_document()
    for path in out_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(path))
        print(f"Wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
