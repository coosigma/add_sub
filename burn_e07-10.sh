#!/bin/bash
cd /Volumes/990Pro2TB/bing/Downloads/SPYxFAMILY

echo "开始批量处理 S01E07-S01E10，使用MKV格式+ASS字幕"
echo "========================================================"
echo ""

for i in 07 08 09 10; do
    mp4_file="S01E${i}.mp4"
    ass_file="sub/S01E${i}.ass"
    output_file="output/S01E${i}s.mkv"
    
    if [ -f "$mp4_file" ] && [ -f "$ass_file" ]; then
        echo "处理 S01E${i}..."
        ffmpeg -i "$mp4_file" -i "$ass_file" -c copy -c:s copy "$output_file" -y -loglevel error
        
        if [ -f "$output_file" ]; then
            size=$(du -h "$output_file" | cut -f1)
            echo "  ✓ 完成 ($size)"
        else
            echo "  ✗ 失败"
        fi
    else
        echo "✗ S01E${i}: 缺少文件"
    fi
    echo ""
done

echo "========================================================"
echo "✓ 所有文件处理完成！"
echo ""
echo "输出文件列表："
ls -lh output/*.mkv | awk '{print "  " $9 " (" $5 ")"}'
