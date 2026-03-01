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

## Python 脚本：批量解压并将 SRT 转为 ASS

项目中新增了两个 Python 脚本：`srt_to_ass.py`（单文件转换，可强制对齐）和 `process_sub_archives.py`（扫描 `sub/`，解压压缩包并将所有 `.srt` 转为 `.ass`，结果收集到 `output/`）。

简单用法：

```bash
python3 -m pip install -r requirements.txt
python3 process_sub_archives.py --subdir sub --outdir output --align bottom-center --inputdir input
```

## 一键主流程脚本

仓库包含 `run_pipeline.sh`，它把上面的步骤串成一个完整流程：

- 在 `sub/` 下递归解压压缩包（支持 zip/tar/tgz/tar.bz2/tar.xz/7z/rar，当系统有相应工具时使用），或直接处理文件夹。
- 在临时 `staging` 中尝试将字幕文件重命名为 `sXXeYY.ass`（如果能从文件名或其父目录识别出 SxxExx 编号）。
- 调用 `process_sub_archives.py` 进行 `.srt -> .ass` 的转换（默认强制 `bottom-center` 对齐），并尝试把生成的 `.ass` 复制到 `input/` 下与对应 `.mp4` 同一目录。
- 最终产物汇总在 `output/`，脚本可选生成 `output.zip`。
- 可选：使用 `--mux`（在 `process_sub_archives.py` 中）可尝试用 `ffmpeg` 将生成的 `.ass` 作为字幕轨道封装进新的 `.mkv` 文件，输出在与视频同目录下（脚本仍会保留 `.ass` 文件）。注意：
   - 该操作仅在系统安装 `ffmpeg` 时可用；若 `ffmpeg` 不存在，脚本会跳过打包步骤。
   - 输出为 MKV（不会修改原 MP4），若需硬字幕（把字幕烧录进视频）会需要转码，时间较长。

变更：输出扁平化
- 现在 `process_sub_archives.py` 会将所有最终生成的 `.ass` 直接放入 `output/` 根目录（不再为每个压缩包创建子文件夹）。
- 若同名文件冲突，脚本会自动在文件名后追加 `_1/_2` 等确保不覆盖现有文件。


运行示例（仓库根目录）：

```bash
bash run_pipeline.sh
```

脚本会创建或复用 `.venv`，并按照 `requirements.txt` 安装依赖。


默认会将转换后的字幕强制定位到底部（`bottom-center`），也可以选择 `bottom-left` 或 `top-center`。
