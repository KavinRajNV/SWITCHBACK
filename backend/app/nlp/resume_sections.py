import io
import re
from typing import Dict, List, Any, Tuple
import pdfplumber
import docx

HEADER_KEYWORDS = [
    "summary", "objective", "profile", "about me", "professional summary", "executive summary",
    "experience", "work experience", "professional experience", "employment history", "work history", "internships",
    "education", "academic background", "qualifications", "education & training", "educational background",
    "skills", "technical skills", "core competencies", "skills & tools", "key skills", "technologies", "expertise",
    "projects", "academic projects", "key projects", "personal projects",
    "certifications", "licenses", "certificates", "courses & certifications", "credentials", "accomplishments", "honors", "awards"
]

def _is_probable_header(line_text: str, avg_font_size: float = 10.0, max_line_font_size: float = 10.0) -> bool:
    """
    Heuristic check if a line is likely a section header:
    - Short length (<= 40 chars)
    - Not ending with sentence punctuation (. , ;)
    - AND (ALL CAPS OR font size notably larger than body OR matches header keywords)
    """
    clean = line_text.strip()
    if not clean or len(clean) > 40:
        return False

    if clean.endswith(".") or clean.endswith(",") or clean.endswith(";"):
        return False

    clean_lower = clean.lower()

    # Match against known keyword list
    for kw in HEADER_KEYWORDS:
        if clean_lower == kw or clean_lower.startswith(f"{kw}:") or clean_lower.startswith(f"{kw} -"):
            return True

    # Check ALL CAPS
    alpha_chars = [c for c in clean if c.isalpha()]
    if alpha_chars and all(c.isupper() for c in alpha_chars) and len(clean.split()) <= 4:
        return True

    # Check font size differential
    if max_line_font_size > (avg_font_size + 1.5) and len(clean.split()) <= 4:
        return True

    return False

def extract_pdf_sections(file_bytes: bytes) -> Dict[str, str]:
    """
    Extracts text and groups lines into sections from PDF bytes using pdfplumber character attributes.
    Returns dict mapping {raw_header: section_text}. Fallbacks to {'UNSTRUCTURED': full_text} if 0 headers found.
    """
    sections: Dict[str, List[str]] = {}
    current_header = "UNSTRUCTURED"
    all_lines: List[str] = []

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                chars = page.chars
                if not chars:
                    t = page.extract_text()
                    if t:
                        all_lines.extend(t.splitlines())
                    continue

                # Compute average font size on page
                sizes = [c.get("size", 10.0) for c in chars if c.get("size")]
                avg_size = float(sum(sizes) / len(sizes)) if sizes else 10.0

                # Group characters into lines by vertical 'top' coordinate (tolerance 3pt)
                line_groups: List[Tuple[float, float, str]] = []
                # Sort chars by top then x0
                sorted_chars = sorted(chars, key=lambda c: (round(c.get("top", 0) / 3.0) * 3.0, c.get("x0", 0)))

                curr_line_top = None
                curr_line_chars: List[dict] = []

                for c in sorted_chars:
                    top = c.get("top", 0)
                    if curr_line_top is None or abs(top - curr_line_top) <= 3.0:
                        curr_line_chars.append(c)
                        if curr_line_top is None:
                            curr_line_top = top
                    else:
                        line_text = "".join(ch.get("text", "") for ch in curr_line_chars).strip()
                        line_max_size = max([ch.get("size", 10.0) for ch in curr_line_chars], default=10.0)
                        if line_text:
                            line_groups.append((avg_size, line_max_size, line_text))
                        curr_line_chars = [c]
                        curr_line_top = top

                if curr_line_chars:
                    line_text = "".join(ch.get("text", "") for ch in curr_line_chars).strip()
                    line_max_size = max([ch.get("size", 10.0) for ch in curr_line_chars], default=10.0)
                    if line_text:
                        line_groups.append((avg_size, line_max_size, line_text))

                for page_avg, line_max, l_text in line_groups:
                    if _is_probable_header(l_text, page_avg, line_max):
                        current_header = l_text.strip()
                        sections.setdefault(current_header, [])
                    else:
                        sections.setdefault(current_header, []).append(l_text)
                        all_lines.append(l_text)

    except Exception as e:
        print(f"[PDF Extraction Warning] Error reading PDF bytes: {e}")

    # Process extracted sections
    result: Dict[str, str] = {}
    if len(sections) > 1 and "UNSTRUCTURED" in sections and not sections["UNSTRUCTURED"]:
        sections.pop("UNSTRUCTURED", None)

    for hdr, lines in sections.items():
        text_content = "\n".join(lines).strip()
        if text_content or len(sections) == 1:
            result[hdr] = text_content

    if not result:
        full_txt = "\n".join(all_lines).strip()
        result["UNSTRUCTURED"] = full_txt if full_txt else ""

    return result

def extract_docx_sections(file_bytes: bytes) -> Dict[str, str]:
    """
    Extracts text and groups lines into sections from DOCX bytes using python-docx paragraph iteration.
    Returns dict mapping {raw_header: section_text}. Fallbacks to {'UNSTRUCTURED': full_text} if 0 headers found.
    """
    sections: Dict[str, List[str]] = {}
    current_header = "UNSTRUCTURED"
    all_lines: List[str] = []

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        for p in doc.paragraphs:
            p_text = p.text.strip()
            if not p_text:
                continue

            all_lines.append(p_text)
            style_name = p.style.name if p.style else ""
            is_bold = any(r.bold for r in p.runs) if p.runs else False

            is_header = False
            if "heading" in style_name.lower():
                is_header = True
            elif is_bold and len(p_text) <= 40 and not p_text.endswith("."):
                is_header = True
            elif _is_probable_header(p_text):
                is_header = True

            if is_header:
                current_header = p_text
                sections.setdefault(current_header, [])
            else:
                sections.setdefault(current_header, []).append(p_text)

    except Exception as e:
        print(f"[DOCX Extraction Warning] Error reading DOCX bytes: {e}")

    result: Dict[str, str] = {}
    if len(sections) > 1 and "UNSTRUCTURED" in sections and not sections["UNSTRUCTURED"]:
        sections.pop("UNSTRUCTURED", None)

    for hdr, lines in sections.items():
        text_content = "\n".join(lines).strip()
        if text_content or len(sections) == 1:
            result[hdr] = text_content

    if not result:
        full_txt = "\n".join(all_lines).strip()
        result["UNSTRUCTURED"] = full_txt if full_txt else ""

    return result

def extract_text_sections(raw_text: str) -> Dict[str, str]:
    """
    Groups lines from plain text into sections by detecting headers.
    """
    sections: Dict[str, List[str]] = {}
    current_header = "UNSTRUCTURED"

    for line in raw_text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue

        if _is_probable_header(line_str):
            current_header = line_str
            sections.setdefault(current_header, [])
        else:
            sections.setdefault(current_header, []).append(line_str)

    result: Dict[str, str] = {}
    if len(sections) > 1 and "UNSTRUCTURED" in sections and not sections["UNSTRUCTURED"]:
        sections.pop("UNSTRUCTURED", None)

    for hdr, lines in sections.items():
        text_content = "\n".join(lines).strip()
        if text_content or len(sections) == 1:
            result[hdr] = text_content

    if not result:
        result["UNSTRUCTURED"] = raw_text.strip()

    return result
