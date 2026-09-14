# 光伏铝框跟线仿真

清扫车沿组件之间的铝框走直。本仓库用合成俯视图验证「提缝 → 偏差 → PID」链路，不是电站真机。

```text
下视相机
   ↓
OpenCV 提取铝框纵缝
   ↓
e_y（横向） / e_θ（航向）
   ↓
PID 转向
   ↓
差速积分（仿真位姿）
```

## 跑

```bash
source scripts/env.sh
python apps/pv_cleaner/run.py
bash scripts/open_report.sh pv_cleaner
```

产物：`output/pv_cleaner/report.html`、`overlay.png`、`follow.mp4`。

本次本机：起步偏置 180 mm，能贴回锁定纵缝（终点横向厘米级），提线平均约 3 ms。

## 做了什么

- 合成光伏阵列：玻璃、电池格、铝框、少量脏点和眩光
- 下视相机：车体朝画面上方，机器人在画面底部
- 只跟纵缝（夹角过大的横框丢掉），锁定当前缝避免跳到隔壁
- 起步带横向偏置和航向偏差，看能否贴回铝框

## 不做

- 真车、真相机、刷盘/水路
- YOLO 分割（网格太规整，霍夫直线够用）
- 换列、避障、越障
