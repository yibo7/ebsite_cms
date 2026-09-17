"""
部件自动发现与注册模块。

设计思路：
  遵循模型控件的惯例，部件 ID 采用字符串格式 模块名_序号（如 sys_1、shop_1），
  支持将部件放在项目任意位置的 widgets/ 目录下，自动扫描发现。

工作流程：
  1. 扫描项目目录下所有名为 widgets/ 的文件夹
  2. 遍历每个子文件夹，import 其 __init__.py
  3. WidgetBase.__init_subclass__ 钩子自动将子类注册到 _registry
  4. 启动时检测 ID 冲突，确保全局唯一
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Type


# ── 全局注册表 ──────────────────────────────────────────────
_registry: dict[str, Type] = {}
_discovered = False

# 要扫描的额外根目录（可在应用启动时追加）
_extra_scan_roots: list[Path] = []


def add_scan_root(root: str | Path):
    """允许三方模块在初始化时注册自己的扫描根目录"""
    _extra_scan_roots.append(Path(root))


# ── 内部接口 ────────────────────────────────────────────────

def register(cls: Type):
    """由 WidgetBase.__init_subclass__ 调用，自动注册子类。"""
    widget_id: str = getattr(cls, 'id', '')
    if not widget_id:
        return

    existing = _registry.get(widget_id)
    if existing is not None:
        raise Exception(
            f"部件 ID 冲突: '{existing.__module__}' "
            f"和 '{cls.__module__}' "
            f"都使用了 ID='{widget_id}'。\n"
            f"请确保每个部件的 id 全局唯一（格式：模块名_序号，如 sys_1、aitanqin_1、eb_shop_1）。"
        )
    _registry[widget_id] = cls


def _discover():
    """扫描所有 widgets/ 目录，import 其中的 __init__.py 触发自动注册。"""
    global _discovered
    if _discovered:
        return
    _discovered = True

    # 确定项目根目录：以本文件所在位置的父目录为基准
    project_root = Path(inspect.getfile(_discover)).resolve().parent.parent

    scan_roots = [project_root] + _extra_scan_roots

    seen_init_files: set[Path] = set()

    for root in scan_roots:
        root = root.resolve()
        if not root.is_dir():
            continue

        # 递归查找所有名为 widgets/ 的目录
        for wdir in root.rglob('widgets'):
            if not wdir.is_dir():
                continue
            # 跳过 __pycache__ 等缓存目录
            if '__pycache__' in wdir.parts:
                continue

            # 遍历 widgets 目录下的每个子文件夹
            for subdir in sorted(wdir.iterdir()):
                if not subdir.is_dir():
                    continue
                if subdir.name.startswith('_') or subdir.name.startswith('.'):
                    continue

                init_file = subdir / '__init__.py'
                if not init_file.exists():
                    continue

                if init_file in seen_init_files:
                    continue
                seen_init_files.add(init_file)

                # 动态导入 __init__.py，触发 __init_subclass__ 钩子
                try:
                    module_name = f"_widget_{subdir.name}"
                    spec = importlib.util.spec_from_file_location(
                        module_name, init_file,
                        submodule_search_locations=[]
                    )
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        # 必须先注册到 sys.modules，exec_module 才能正确设置 module 属性
                        sys.modules[module_name] = mod
                        spec.loader.exec_module(mod)
                except Exception as e:
                    print(f"[widget] 导入失败: {init_file} ({e})")


# ── 旧数据兼容映射 int → str ───────────────────────────────
# 数据库中已存在的 temp_type 数字需要映射到新的字符串 ID
LEGACY_ID_MAP: dict[str, str] = {
    '1': 'sys_1',
    '2': 'sys_2',
    '3': 'sys_3',
    '4': 'sys_4',
    '5': 'sys_5',
    '6': 'sys_6',
    '7': 'sys_7',
    '8': 'sys_8',
    '9': 'sys_9',
    '11': 'sys_11',
    '12': 'sys_12',
}


def resolve_widget_id(raw_id: int | str) -> str:
    """将可能为旧 int 格式的 ID 转为字符串 ID。"""
    str_id = str(raw_id).strip()
    # 已经是字符串格式（如 sys_1）
    if '_' in str_id:
        return str_id
    # 可能是旧 int 格式
    return LEGACY_ID_MAP.get(str_id, str_id)


# ── 公开 API ────────────────────────────────────────────────

def get_widget(widget_id: int | str):
    """按 ID 获取一个部件实例。兼容旧的 int ID。"""
    _discover()
    resolved_id = resolve_widget_id(widget_id)
    cls = _registry.get(resolved_id)
    if not cls:
        cls = _registry.get(str(widget_id))
    if not cls:
        raise ValueError(f"未找到部件: {widget_id}，可用部件: {list(_registry.keys())}")
    return cls()


def get_widget_class(widget_id: str) -> Type:
    """按 ID 获取部件类（不实例化），常用于读取类方法。"""
    _discover()
    resolved_id = resolve_widget_id(widget_id)
    cls = _registry.get(resolved_id)
    if not cls:
        raise ValueError(f"未找到部件: {widget_id}")
    return cls


def get_all_widgets() -> list:
    """获取所有部件实例列表。"""
    _discover()
    return [cls() for cls in _registry.values()]


def get_widget_count() -> int:
    """获取已注册的部件数量。"""
    _discover()
    return len(_registry)