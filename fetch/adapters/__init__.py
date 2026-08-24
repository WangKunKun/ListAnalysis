"""平台适配器注册表。新平台 = 新增 adapters/<name>.py + 在此注册一行。"""

from .ios import IosAdapter


def get_adapter(name):
    if name == "play":
        from .play import PlayAdapter   # 延迟导入：未装依赖不影响 iOS
        return PlayAdapter
    if name == "ios":
        return IosAdapter
    raise ValueError(f"未知平台: {name}，可选: ios, play")
