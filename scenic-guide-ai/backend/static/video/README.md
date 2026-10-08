# 预生成数字人视频目录

请将以下视频文件放入此目录：

## 必需文件
- `opening.mp4`  — 开场白视频（"您好，欢迎来到灵山胜境..."）
- `idle.mp4`     — 待机视频（数字人呼吸/idle 动画，循环播放）
- `idle_1.mp4` ~ `idle_5.mp4` — 备用待机视频（可选，没有则循环 idle.mp4）

## 获取方式
1. 从 SadTalker 开发机生成后复制到此处
2. 或从历史 output 目录中复制已生成的视频

## 访问路径（Docker 中）
容器内: /app/static/video/
外部:   http://<host>:8000/static/video/
Kiosk:  自动映射 /output/opening.mp4 → /static/video/opening.mp4
