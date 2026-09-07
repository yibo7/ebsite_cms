import os
import random
from flask import jsonify, current_app, send_from_directory

from decorators import rate_limit_ip
from eb_modules.aitanqin import bp_aitanqin
from eb_utils import http_helper
from entity import api_msg
from bll.new_content import NewsContent

# ── 模拟制谱师数据池 ──────────────────────────────────────
_ARRANGER_NAMES = [
    "ElephantPiano", "FingerFlow", "SixStringWalker", "HalfToneTraveller", "HarmonyWeaver",
    "PickPrince", "StringBreeze", "FingerstyleZhe", "ScoreHunter", "RhythmPoet",
    "BluesZhang", "FolkChen", "ClassicJushi", "JazzCat", "RockAfie",
    "GuitarBunny", "NeverForget", "WoodGuitarist", "MidnightPlayer", "SunnyTown",
]

# 用于确定性随机：同一个乐谱 _id 每次都返回相同的 20 个制谱师列表
def _get_arrangers(seed_str: str):
    """根据乐谱 _id 生成确定性随机制谱师列表"""
    rng = random.Random(seed_str)
    # 打乱顺序
    indices = list(range(20))
    rng.shuffle(indices)

    arrangers = []
    for i in indices:
        name = _ARRANGER_NAMES[i]
        scores_count = rng.randint(5, 500)
        arrangers.append({
            "avatar": name[0],          # 取名称首字符作为头像
            "name": name,
            "verified": rng.random() < 0.4,   # 约 40% 认证
            "scores_count": scores_count,
            "sub": f"制谱师 · 已上传 {scores_count} 首曲谱",
        })
    return arrangers


@bp_aitanqin.route('arrangers', methods=['GET'])
def get_arrangers():
    """
    获取模拟制谱师列表（20 人）。
    传入乐谱 _id 确保同个乐谱每次返回一致的数据，
    方便后续替换为真实数据。
    ---
    参数:
      id  - 乐谱 _id（字符串），用于确定性种子
    返回:
      { code:0, msg:"successful", data:[ ... ] }
    """
    tid = http_helper.get_prams('id') or "default_seed"
    try:
        data = _get_arrangers(str(tid))
        return jsonify(api_msg.api_succesful(data))
    except Exception as e:
        return jsonify(api_msg.api_err(f"获取制谱师列表失败: {str(e)}"))


@bp_aitanqin.route('totab', methods=['POST', 'GET'])
@rate_limit_ip(10,1) # 一分钟只允许调用3次
def get_tab():
    """
    获取乐谱文件
    通过tid（NewsContent的_id）查询column_5字段中的乐谱文件路径，
    从本地upload目录下读取文件并返回。
    """
    tid = http_helper.get_prams('id')

    if not tid:
        return jsonify(api_msg.api_err("id不能为空"))
    print(f"乐谱ID：{tid}")
    # 获取文件内容
    try:
        # 通过tid查询NewsContent实例
        bll = NewsContent()
        model = bll.find_one_by_id(tid)

        if not model:
            return jsonify(api_msg.api_err("未找到对应的内容"))

        # 获取乐谱文件路径（column_5），如 /scores/gtp/xxx.gp
        score_path = model.column_5
        print(f'乐谱路径：{score_path}')
        if not score_path:
            return jsonify(api_msg.api_err("未设置乐谱文件路径"))

        # 解析路径：去除开头的 /，分离目录和文件名
        relative_path = score_path.lstrip('/')
        directory = os.path.dirname(relative_path)  # 如 scores/gtp
        filename = os.path.basename(relative_path)  # 如 xxx.gp

        # 文件实际存放在 uploads 目录下
        upload_folder = os.path.join(current_app.root_path, 'uploads', directory)

        # 检查文件是否存在
        if not os.path.exists(os.path.join(upload_folder, filename)):
            return jsonify(api_msg.api_err("乐谱文件不存在"))

        # 使用 send_from_directory 发送文件（与 uploaded_file 函数一致的方式）
        return send_from_directory(
            upload_folder,
            filename,
            mimetype='application/octet-stream',
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        return jsonify(api_msg.api_err(f"获取文件失败: {str(e)}"))