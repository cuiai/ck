# EDA 灵视一代玄武公安分局版本 v0.3

## 一 、开发环境搭建
### 1. 下载模型文件
- 192.168.16.155 服务器 -- /data/ftpdata/version/EDA/EDA1.2.1/Resource/qdjc_models.zip
- 解压qdjc_models.zip到src

### 2. 下载Resources资源包  
- 192.168.16.155 服务器 -- /data/ftpdata/version/EDA/EDA1.2.1/Resource/qdjc_resources.zip
- 解压qdjc_resources.zip到src/application

### 3.将Resources中的部分工具复制到src
```python
python copy_resources.py
```
- **增加新工具时请将文件或文件夹路径添加到copy_resources.py脚本中!** 
