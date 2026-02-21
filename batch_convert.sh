#!/bin/bash
# 字幕封装脚本 - 将ASS字幕封装进MKV视频
# 用法: ./batch_convert.sh [起始集数] [结束集数]
# 示例: ./batch_convert.sh 11 25
# 不带参数时默认处理 11-25 集

cd /Volumes/990Pro2TB/bing/Downloads/SPYxFAMILY

# 默认值
START=${1:-11}
END=${2:-25}

echo "=========================================================="
echo "批量处理 S01E${START}-S01E${END}，使用MKV格式+ASS字幕"
echo "=========================================================="
echo ""

# 确保output目录存在
mkdir -p output

SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for i in $(seq -f "%02g" $START $END); do
    mp4_file="S01E${i}.mp4"
    ass_file="sub/S01E${i}.ass"
    output_file="output/S01E${i}s.mkv"
    
    # 检查输出文件是否已存在
    if [ -f "$output_file" ]; then
        echo "⊘ S01E${i}: 输出文件已存在，跳过"
        ((SKIP_COUNT++))
        continue
    fi
    
    # 检查源文件是否存在
    if [ ! -f "$mp4_file" ]; then
        echo "✗ S01E${i}: 找不到 $mp4_file"
        ((FAIL_COUNT++))
        continue
    fi
    
    if [ ! -f "$ass_file" ]; then
        echo "✗ S01E${i}: 找不到 $ass_file"
        ((FAIL_COUNT++))
        continue
    fi
    
    # 处理视频
    echo "处理 S01E${i}..."
    ffmpeg -i "$mp4_file" -i "$ass_file" -c copy -c:s copy "$output_file" -y -loglevel error -stats
    
    if [ -f "$output_file" ]; then
        size=$(du -h "$output_file" | cut -f1)
        echo "  ✓ 完成 ($size)"
        ((SUCCESS_COUNT++))
    else
        echo "  ✗ 失败"
        ((FAIL_COUNT++))
    fi
    echo ""
done

echo "=========================================================="
echo "处理完成！"
echo "  成功: $SUCCESS_COUNT"
echo "  失败: $FAIL_COUNT"
echo "  跳过: $SKIP_COUNT"
echo "=========================================================="
echo ""

if [ $SUCCESS_COUNT -gt 0 ]; then
    echo "新生成的文件："
    ls -lht output/*.mkv | head -n $SUCCESS_COUNT | awk '{print "  " $9 " (" $5 ")"}'
fi
