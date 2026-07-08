"""图片工具 —— 保存、删除、路径处理"""

import os
import uuid

from config import UPLOAD_DIR, MAX_IMAGE_SIZE, ALLOWED_IMAGE_TYPES


def ensure_upload_dir():
    """确保上传目录存在"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_image(uploaded_file) -> str:
    """保存上传的图片，返回文件路径（空字符串表示无图片）"""
    if uploaded_file is None:
        return ""

    ensure_upload_dir()

    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise ValueError(f"图片大小不能超过 {MAX_IMAGE_SIZE // (1024 * 1024)}MB")

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"不支持的图片格式：{ext}，仅支持 jpg / png")

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filepath


def delete_image(filepath: str):
    """删除图片文件"""
    if filepath and os.path.isfile(filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass  # 文件不存在或无法删除，忽略


def get_image_path(relative_path: str) -> str:
    """获取图片完整路径（用于显示）"""
    if not relative_path:
        return ""
    return relative_path
