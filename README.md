# PDF全文检索工具

一个强大的PDF全文检索工具，支持在指定目录下搜索PDF文件内容，并提供页面预览功能。

## 功能特点

- 支持递归搜索指定目录下的所有PDF文件
- 全文内容检索
- 精确定位关键词所在页码
- 提供页面预览
- 显示关键词上下文
- 多线程处理，提高性能
- 简洁直观的图形界面

## 系统要求

- Python 3.8+
- Windows/Linux/MacOS

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/pdf-search.git
cd pdf-search
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
python main.py
```

2. 在图形界面中：
   - 点击"选择目录"按钮选择要搜索的PDF文件目录
   - 等待索引完成
   - 在搜索框中输入关键词
   - 点击"搜索"按钮或按回车开始搜索
   - 查看搜索结果和页面预览

## 依赖库

- PyMuPDF (fitz): PDF文件处理
- PyQt5: 图形界面
- Whoosh: 全文检索引擎
- OpenCV: 图像处理
- NumPy: 数值计算
- Pillow: 图像处理
- python-magic: 文件类型检测
- tqdm: 进度条显示

## 注意事项

- 首次搜索目录时需要建立索引，可能需要一些时间
- 建议定期更新索引以反映文件变化
- 对于加密的PDF文件可能无法处理

## 许可证

MIT License 