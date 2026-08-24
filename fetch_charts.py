#!/usr/bin/env python3
"""兼容入口：转发到 fetch 包。新代码请用 python3 -m fetch.charts。"""

from fetch.core import *          # noqa: F401,F403
from fetch.core import main


if __name__ == "__main__":
    raise SystemExit(main())
