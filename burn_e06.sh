#!/bin/bash
cd /Volumes/990Pro2TB/bing/Downloads/SPYxFAMILY

echo "开始处理 S01E06，使用MKV格式+ASS字幕（完整保留所有样式和位置信息）..."
echo ""

ffmpeg -i S01E06.mp4 -i sub/S01E06.ass -c copy -c:s copy output/S01E06s.mkv -y

if [ -f output/S01E06s.mkv ]; then
    size=$(du -h output/S01E06s.mkv | cut -f1)
    echo ""
    echo "✓ 完成！输出文件: output/S01E06s.mkv ($size)"
    echo "   字幕已作为独立流嵌入，播放器可选择开关"
else
    echo ""
    echo "✗ 处理失败"
fi
