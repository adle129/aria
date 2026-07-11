from pathlib import Path

from docx import Document


class RFQParser:
    def extract_text_from_docx(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        doc = Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            raise ValueError("文档内容为空")
        return "\n".join(paragraphs)

    def build_parse_prompt(self, rfq_text: str, prompt_root: Path) -> str:
        template_path = prompt_root / "rfq_parse.txt"
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
            return template.replace("{rfq_text}", rfq_text)
        return (
            "你是 EDAG 车辆工程报价专家。请分析以下 RFQ 并只输出 JSON。\n\n"
            f"RFQ 内容：\n{rfq_text}"
        )
