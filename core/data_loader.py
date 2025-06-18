import logging
from PyPDF2 import PdfReader
import os

def load_text_file(filepath: str) -> str | None:
    """
    Loads text content from a specified file.

    Args:
        filepath: The path to the text file.

    Returns:
        The content of the file as a string, or None if an error occurs.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Data file not found at path: {filepath}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while reading the file {filepath}: {e}")
        return None

def load_pdf_file(filepath: str) -> str | None:
    """
    Loads text content from a PDF file.

    Args:
        filepath: The path to the PDF file.

    Returns:
        The extracted text content as a string, or None if an error occurs.
    """
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text if text.strip() else None
    except FileNotFoundError:
        logging.error(f"PDF file not found at path: {filepath}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while reading the PDF file {filepath}: {e}")
        return None

def load_all_texts_from_dir(dir_path: str) -> list[tuple[str, str]]:
    """
    批量读取目录下所有txt和pdf文件，返回[(文件名, 文本内容)]列表。
    """
    results = []
    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            if fname.lower().endswith('.txt'):
                text = load_text_file(fpath)
                if text and text.strip():
                    results.append((fname, text))
            elif fname.lower().endswith('.pdf'):
                text = load_pdf_file(fpath)
                if text and text.strip():
                    results.append((fname, text))
    return results

def split_pdf_to_chunks(filepath: str, max_chunk_chars: int = 3000) -> list[str]:
    """
    先按章节/小标题/段落进行大分块，大块超长时先按段落分，再对超长段落按句号/换行等自然断点细分。
    """
    import re
    try:
        reader = PdfReader(filepath)
        all_text = ""
        for page in reader.pages:
            all_text += page.extract_text() or ""
        all_text = all_text.strip()
        # 按章节/小标题分大块
        section_pattern = re.compile(r"(^|\n)(\d+\.\d*|[IVX]+\.|Abstract|Introduction|Conclusion|参考文献|致谢|Acknowledgements|Results|Discussion|Methods|Materials|Experimental|Table|Figure)[^\n]*\n", re.IGNORECASE)
        splits = [m.start() for m in section_pattern.finditer(all_text)]
        splits.append(len(all_text))
        chunks = []
        for i in range(len(splits)-1):
            chunk = all_text[splits[i]:splits[i+1]].strip()
            if not chunk:
                continue
            # 若大块超长，先按段落分
            if len(chunk) > max_chunk_chars:
                paras = re.split(r'\n{2,}', chunk)
                for para in paras:
                    para = para.strip()
                    if not para:
                        continue
                    # 段落超长再按句号/换行细分
                    while len(para) > max_chunk_chars:
                        sub_chunk = para[:max_chunk_chars]
                        last_break = max(sub_chunk.rfind("。"), sub_chunk.rfind(". "), sub_chunk.rfind("\n"))
                        if 0 < last_break < len(sub_chunk) - 20:
                            sub_chunk = sub_chunk[:last_break+1]
                        chunks.append(sub_chunk)
                        para = para[len(sub_chunk):].lstrip()
                    if para:
                        chunks.append(para)
            else:
                chunks.append(chunk)
        return [c for c in chunks if c.strip()]
    except Exception as e:
        logging.error(f"Error splitting PDF {filepath}: {e}")
        return []
