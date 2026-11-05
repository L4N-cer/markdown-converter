# Markdown 转换器

一个本地运行的桌面小工具，用于 **Markdown 与常见文档格式的双向转换**。基于 Python + PyQt6，单窗口、拖放即用，转换在后台线程执行，不卡界面。

正向转换会把文档里的图片抽取后以 Base64 内嵌，生成**自包含的单个 `.md` 文件**，不依赖外部图片目录；反向转换把 Markdown 还原成 Word 文档。

## 功能

| 方向 | 输入 | 输出 | 主要支持 |
| --- | --- | --- | --- |
| 正向 | `.docx` `.pdf` `.pptx` `.html` `.htm` `.txt` | `.md` | 标题层级、粗体/斜体/下划线、有序与无序列表、链接、管道表格、代码块、图片 Base64 内嵌 |
| 反向 | `.md` | `.docx` | 标题、水平线、围栏代码块、表格、列表、引用、行内格式、Base64 图片还原 |

操作方式：拖放或选择单个文件 → 「转换」→ 预览区查看（可切换「编辑」）→ 复制到剪贴板 / 另存为 `.md` / 导出为 Word。直接拖入 `.md` 文件时按钮会变成「转为 Word」，也可在预览区编辑后点「导出为 Word」。

设置项：图片最大宽度（200–2000 px，默认 800）、代码块样式（围栏式 / 缩进式）。

## 快速开始

需要 Python 3.11+。

```bash
pip install -r requirements.txt
python main.py
```

Windows 下也可以直接双击：

- `启动.vbs` —— 用 `pythonw` 启动，无控制台窗口（推荐）
- `启动.bat` —— 保留控制台，便于查看报错

## 项目结构

```
.
├── main.py                      # 入口
├── ui/                          # 主窗口、设置对话框、后台转换线程
├── converters/                  # 抽象基类 + 工厂 + 各格式转换器
│   ├── base.py
│   ├── docx_converter.py / pdf_converter.py / pptx_converter.py
│   ├── html_converter.py / txt_converter.py
│   └── md_to_docx_converter.py  # Markdown → Word
└── utils/                       # 格式探测、图片 Base64、表格工具
```

正向转换器继承 `AbstractConverter`，统一实现 `convert(file_path, options) -> str`；`get_converter()` 按扩展名分发，扩展名不明时会嗅探文件头判断是否为 HTML。`.md` 走反向分支，由 `MdToDocxConverter` 生成同目录下的 `.docx`。

## 依赖

PyQt6、python-docx、PyMuPDF、python-pptx、beautifulsoup4、lxml、Pillow、chardet、requests（仅用于 HTML 中的远程图片下载）。详见 `requirements.txt`。

## 已知限制

- 反向转换是轻量实现，用正则逐行解析，不覆盖嵌套列表、内嵌 HTML、脚注等完整 Markdown 语法。
- PDF 的标题层级依赖字号启发式，复杂排版或多栏文档可能需要手工校正。
- 图片以 Base64 内嵌，图片多的文档生成的 `.md` 会明显变大。
- 目前没有自动化测试，也没有打包成 `.exe`。
