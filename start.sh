#!/bin/bash
# Hotkey Manager 启动脚本
# 处理本地和 RDP 场景的 Display 兼容性问题

set -e

echo "🔥 启动 Hotkey Manager..."

# 方法1：检查本地 X11 socket
if [ -z "$DISPLAY" ]; then
    X11_SOCKETS=$(ls -1 /tmp/.X11-unix/X* 2>/dev/null | head -1)
    if [ -n "$X11_SOCKETS" ]; then
        DISPLAY_NUM=$(basename "$X11_SOCKETS" | sed 's/X//')
        export DISPLAY=":$DISPLAY_NUM"
        echo "🔧 检测到 X11 socket，使用 Display: $DISPLAY"
    fi
fi

# 方法2：检查 WAYLAND
if [ -z "$DISPLAY" ] && [ -n "$WAYLAND_DISPLAY" ]; then
    export DISPLAY="$WAYLAND_DISPLAY"
    echo "🔧 检测到 Wayland，使用 Display: $DISPLAY"
fi

# 方法3：尝试使用 xdpyinfo 探测
if [ -z "$DISPLAY" ] && command -v xdpyinfo &> /dev/null; then
    DETECTED_DISPLAY=$(xdpyinfo 2>/dev/null | grep "display name" | head -1 | awk '{print $NF}')
    if [ -n "$DETECTED_DISPLAY" ]; then
        export DISPLAY="$DETECTED_DISPLAY"
        echo "🔧 通过 xdpyinfo 检测到 Display: $DISPLAY"
    fi
fi

# 最终检查
if [ -z "$DISPLAY" ]; then
    echo "⚠️ 未检测到显示环境，将以无头模式运行（仅限命令行功能）"
else
    echo "✅ Display 配置完成: $DISPLAY"
fi

# 启动应用
exec python3 main.py "$@"
