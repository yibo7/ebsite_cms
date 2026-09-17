"""部件包。

部件采用自动发现机制，无需在此手动导入。
每个部件是一个独立的文件夹，包含 __init__.py 和 admin.html。

发现流程：
  1. bll/widget_discover.py 扫描项目下所有 widgets/ 目录
  2. 遍历每个子文件夹，import __init__.py
  3. WidgetBase.__init_subclass__ 钩子自动注册到全局注册表

导入此包即触发发现。
"""
from bll import widget_discover as _discover

# 触发发现（只在首次导入时执行一次）
_discover.get_widget_count()