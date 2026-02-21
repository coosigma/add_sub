# meta_extract_and_convert.sh 使用说明

本脚本用于批量解压 `sub` 目录下的字幕压缩包（支持 zip、rar、7z、tar、tar.gz、tgz、tar.bz2），自动提取并重命名为标准格式（如 S01E01.ass），并调用 `batch_convert.sh` 进行后续转换。

## 使用方法

1. 打开终端，进入脚本所在目录：

   ```sh
   cd /Volumes/990Pro2TB/bing/Downloads/SPYxFAMILY
   ```

2. （可选）设置季和起始集数（默认第1季第1集）：

   ```sh
   export SEASON=1      # 设置季数（可选，默认1）
   export START_EP=1    # 设置起始集数（可选，默认1）
   ```

3. 运行脚本：

   ```sh
   sh meta_extract_and_convert.sh
   # 或（推荐，需先赋予执行权限）
   chmod +x meta_extract_and_convert.sh
   ./meta_extract_and_convert.sh
   ```

4. 脚本会自动：
   - 查找 `sub/` 目录下所有字幕压缩包
   - 解压并提取 `.ass` 字幕文件
   - 自动重命名为 SXXEXX.ass 格式（如 S01E01.ass）
   - 调用 `batch_convert.sh` 进行批量转换

## 依赖环境
- bash
- unzip、ditto（macOS）、unrar、7z、tar（至少需有其中之一，建议安装 7z）

## 注意事项
- 请确保 `sub/` 目录存在并包含字幕压缩包。
- `batch_convert.sh` 应在同一目录下。
- 如遇权限问题，请为脚本赋予可执行权限：`chmod +x meta_extract_and_convert.sh`。

---
如有疑问可继续提问。