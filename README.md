# 视频批量转换工具

这是一个基于Python和FFmpeg的视频批量转换工具，能够将多种格式的视频文件转换为H.265/HEVC编码的MP4格式，显著减小文件体积。

## 功能特点

- 支持多种输入格式：MP4, MKV, AVI, MOV, WMV, FLV, TS, WEBM
- 自动检测系统主题(暗黑/浅色模式)
- 多线程处理，提高转换效率
- 进度条显示转换进度
- 转换完成后显示系统通知
- 自动适应视频分辨率设置合适的编码参数
- 支持硬件加速编码(AMF/Vulkan)

## 系统要求

- Windows操作系统
- Python 3.7+
- FFmpeg已安装并添加到系统PATH
- 推荐使用支持硬件加速的显卡(AMD/NVIDIA)

## 安装指南

1. 克隆或下载本项目
2. 安装Python依赖：
   ```
   pip install ttkbootstrap plyer
   ```
3. 确保FFmpeg已正确安装并添加到系统PATH

## 使用说明

1. 运行 `GUI_Drakmode.py`启动图形界面
2. 点击"浏览"按钮选择包含视频文件的文件夹
3. 点击"开始转换"按钮开始转换过程
4. 转换完成后，转换的视频将保存在源文件夹下的"Converted"子文件夹中
5. 日志文件保存在"Logs"子文件夹中

## 注意事项

1. 转换过程中请不要关闭程序
2. 转换时间取决于视频大小和硬件性能
3. 如果转换失败，程序会自动尝试软件编码方式
4. 转换后的文件名会添加"_hevc"后缀

## 构建可执行文件

可以使用nuitka构建独立的可执行文件：

```
python -m nuitka --onefile --enable-plugin=tk-inter --windows-disable-console .\GUI_Drakmode.py
```

## 许可证

MIT License
